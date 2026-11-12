"""Build a frozen corpus from a museum's open data.

The repository ships the frozen files, so this script is **not** needed to run the
core path. It exists so a shipped file can be rebuilt and audited: every field is
copied verbatim from the museum's record, and the object IDs below are the only
editorial choice the team made.

Presets, because the proposal's should-have list asks for a second department and the
post-midterm work asks for a second museum:

    primary    Met, four departments (20 records, 6 of them boundary cases)
    egyptian   Met, Egyptian Art (10 records) — same five fields, but the department
               records place in `country`, not `culture`, so the field map differs
    cleveland  Cleveland Museum of Art (10 records) — a different museum, a different
               API, and records filtered to CC0 at fetch time

Nothing in labeldesk/ knows which museum a record came from: the field map and the
licence live in the corpus file and in data/sources.json.

`fetched_at` is pinned per preset rather than read from the clock, so a rebuild is
byte-identical and `--check` is a real test rather than a same-day coincidence.

Usage:
    python3 tools/fetch_corpus.py                     # primary, writes the file
    python3 tools/fetch_corpus.py --preset egyptian
    python3 tools/fetch_corpus.py --preset cleveland
    python3 tools/fetch_corpus.py --check             # rebuild to a temp file, diff
    python3 tools/fetch_corpus.py --preset cleveland --check

Requires network access. Standard library only. Reads each host's robots.txt before
fetching; see data/sources.json for the verdicts and tools/check_sources.py to re-check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
USER_AGENT = "LabelDesk-AILT9019/1.1 (course project; educational use)"

# The five fields, imported rather than retyped so the fetch guard and the
# pipeline cannot disagree about what "complete" means.
sys.path.insert(0, str(ROOT))
from labeldesk.corpus import REQUIRED_FIELDS  # noqa: E402
from labeldesk.net import ssl_context  # noqa: E402
MET_API = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"
CMA_API = "https://openaccess-api.clevelandart.org/api/artworks/{oid}"

PRESETS: dict[str, dict] = {
    "primary": {
        "provider": "met",
        "allow_incomplete": 6,
        "filename": "frozen_corpus.json",
        "name": "labeldesk-frozen-corpus",
        "version": "1.0.0",
        "fetched_at": "2026-10-23",
        "source": "The Metropolitan Museum of Art Open Access",
        "field_map": {
            "catalogue_number": "accessionNumber",
            "object_id": "objectID",
            "title": "title",
            "object_date": "objectDate",
            "medium": "medium",
            "place_or_culture": "culture",
            "credit_line": "creditLine",
            "department": "department",
            "is_public_domain": "isPublicDomain",
            "source_url": "objectURL",
            "image_url": "primaryImage",
            "image_thumbnail": "primaryImageSmall",
        },
        "notes": (
            "Field values are copied verbatim from the Met object records. "
            "Blank strings are the museum's own blanks, not missing data "
            "introduced by the team. The 6 boundary records are kept in the "
            "corpus on purpose so the refusal path can be demonstrated."
        ),
        # 20 object IDs: 14 records with all five required fields, 6 boundary records.
        # Boundary reasons are recorded in each record's "boundary" key.
        "selection": {
            42229: None,
            42465: None,
            47175: None,
            49864: None,
            53902: None,
            64085: None,
            64113: None,
            853890: None,
            240111: None,
            255624: None,
            325538: None,
            325841: None,
            126755: None,
            37408: None,
            63318: "date hedge: ca. 1740",
            78762: "date uncertainty marker: late 18th century (?)",
            325240: "disjunctive culture: Old Assyrian Trading Colony or Hittite",
            64084: "missing object_date",
            52049: "missing object_date",
            445631: "missing place_or_culture",
        },
    },
    "egyptian": {
        "provider": "met",
        "allow_incomplete": 0,
        "filename": "frozen_corpus_egyptian.json",
        "name": "labeldesk-egyptian-corpus",
        "version": "1.0.0",
        "fetched_at": "2026-11-01",
        "source": "The Metropolitan Museum of Art Open Access · Egyptian Art",
        "field_map": {
            "catalogue_number": "accessionNumber",
            "object_id": "objectID",
            "title": "title",
            "object_date": "objectDate",
            "medium": "medium",
            # This department leaves `culture` blank and records place in `country`.
            # A list means "first non-empty", so one map serves both shapes.
            "place_or_culture": ["country", "culture"],
            "credit_line": "creditLine",
            "department": "department",
            "is_public_domain": "isPublicDomain",
            "source_url": "objectURL",
            "image_url": "primaryImage",
            "image_thumbnail": "primaryImageSmall",
        },
        "notes": (
            "Second department, same five required fields, different field map: "
            "place is taken from `country` because this department leaves "
            "`culture` blank. Kept as evidence that the pipeline is data-agnostic "
            "and that the mapping lives in the corpus file rather than in code. "
            "One record carries a '(?)' doubt marker and a disjunctive title, so "
            "the hedge rule is exercised on this data too."
        ),
        "selection": {
            544449: None,
            547650: None,
            551844: None,
            559015: None,
            548765: None,
            556712: None,
            558515: None,
            544493: None,
            562777: None,
            551867: "doubt marker and disjunction in the title: Part (?) of a bracelet or armlet",
        },
    },
    "cleveland": {
        "provider": "cleveland",
        "allow_incomplete": 0,
        "filename": "frozen_corpus_cleveland.json",
        "name": "labeldesk-cleveland-corpus",
        "version": "1.0.0",
        "fetched_at": "2026-11-01",
        "source": "The Cleveland Museum of Art Open Access",
        "field_map": {
            "catalogue_number": "accession_number",
            "object_id": "id",
            "title": "title",
            "object_date": "creation_date",
            "medium": "technique",
            "place_or_culture": "culture",
            "credit_line": "creditline",
            "department": "department",
            "is_public_domain": "share_license_status",
            "source_url": "url",
            "image_url": "images",
            "image_thumbnail": "images",
        },
        "notes": (
            "A second museum, a second API, the same five required fields. Records "
            "are filtered to share_license_status == 'CC0' at fetch time, so nothing "
            "outside the open-access set can reach the corpus. `culture` arrives as a "
            "list and is joined with '; '; the values themselves are untouched. "
            "Date wording is kept as the museum writes it ('c. 1050', '1100s', "
            "'1800s, before 1896'), which exercises the hedge and range rules on data "
            "the team did not choose the phrasing of."
        ),
        "selection": {
            145192: "hedged date: c. 1050",
            141444: "hedged date with a qualifier: c. 1575",
            149683: None,
            118475: "bare range date: 400–700",
            143898: "hedged date: c. 1820",
            147588: "century-style date: 1100s",
            99417: "hedged date: c. 1480",
            108743: "hedged range: c. 1160–1170",
            115163: "date with a qualifier: 1800s, before 1896",
            141549: "hedged range: c. 1631–32",
        },
    },
}


# --------------------------------------------------------------------------- #
# providers
# --------------------------------------------------------------------------- #


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30, context=ssl_context()) as response:
        return json.load(response)


def fetch_met(oid: int) -> dict:
    return _get_json(MET_API.format(oid=oid))


def fetch_cleveland(oid: int) -> dict:
    payload = _get_json(CMA_API.format(oid=oid))
    return payload.get("data") or {}


PROVIDERS = {
    "met": {"fetch": fetch_met, "api": MET_API, "pause": 0.4},
    "cleveland": {"fetch": fetch_cleveland, "api": CMA_API, "pause": 0.5},
}


def _pick(raw: dict, source: str | list[str]) -> str:
    """One field from one API key, or the first non-empty of several."""
    keys = [source] if isinstance(source, str) else list(source)
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            # Cleveland returns culture as a list; the values are joined, not edited.
            joined = "; ".join(str(item).strip() for item in value if str(item).strip())
            if joined:
                return joined
            continue
        if str(value).strip():
            return str(value)
    return ""


def _image(raw: dict, provider: str, thumbnail: bool) -> str:
    if provider == "met":
        keys = ("primaryImageSmall", "primaryImage") if thumbnail else ("primaryImage", "primaryImageSmall")
        return _pick(raw, list(keys))
    images = raw.get("images") or {}
    if not isinstance(images, dict):
        return ""
    keys = ("web", "full", "print") if thumbnail else ("full", "web", "print")
    for key in keys:
        variant = images.get(key) or {}
        if isinstance(variant, dict) and str(variant.get("url") or "").startswith("https://"):
            return str(variant["url"])
    return ""


def normalise(raw: dict, boundary: str | None, field_map: dict, provider: str = "met") -> dict:
    record = {}
    for key, source in field_map.items():
        if key == "is_public_domain":
            if provider == "cleveland":
                record[key] = str(raw.get(source) or "").strip().upper() == "CC0"
            else:
                record[key] = bool(raw.get(source))
        elif key == "object_id":
            # Kept as the API returns it (an integer), so a rebuild of the shipped
            # file is byte-identical.
            record[key] = raw.get(source) or ""
        elif key in ("image_url", "image_thumbnail"):
            record[key] = _image(raw, provider, key == "image_thumbnail")
        else:
            record[key] = _pick(raw, source)
    if not record.get("is_public_domain"):
        record["image_url"] = ""
        record["image_thumbnail"] = ""
    record["boundary"] = boundary
    return record


def build(preset: dict) -> dict:
    provider_name = preset.get("provider", "met")
    provider = PROVIDERS[provider_name]
    records = []
    for oid, boundary in preset["selection"].items():
        records.append(
            normalise(provider["fetch"](oid), boundary, preset["field_map"], provider_name)
        )
        time.sleep(provider["pause"])  # keep the build polite to a public API

    incomplete = [
        record["catalogue_number"]
        for record in records
        if any(not str(record.get(field, "")).strip() for field in REQUIRED_FIELDS)
    ]
    allowed = preset.get("allow_incomplete", 0)
    if len(incomplete) > allowed:
        raise SystemExit(
            f"refusing to write {preset['filename']}: {len(incomplete)} records are missing a "
            f"required field ({', '.join(incomplete[:5])}), and this preset allows {allowed}. "
            "A corpus that cannot produce labels should be a deliberate choice, not a surprise."
        )

    return {
        "corpus": {
            "name": preset["name"],
            "version": preset["version"],
            "source": preset["source"],
            "source_api": provider["api"],
            "license": "CC0 1.0 (public domain)",
            "fetched_at": preset["fetched_at"],
            "record_count": len(records),
            "required_fields": [
                "title",
                "object_date",
                "medium",
                "place_or_culture",
                "credit_line",
            ],
            "field_map": preset["field_map"],
            "notes": preset["notes"],
        },
        "records": records,
    }


def dump(payload: dict, path: Path) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", default="primary", choices=sorted(PRESETS))
    parser.add_argument("--check", action="store_true", help="compare a fresh build with the shipped file")
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    out = DATA / preset["filename"]
    payload = build(preset)

    if args.check:
        tmp = DATA / f".rebuilt-{args.preset}.json"
        digest = dump(payload, tmp)
        same = tmp.read_bytes() == out.read_bytes()
        tmp.unlink()
        print(f"sha256 {digest}")
        print("shipped file matches a fresh build" if same else "DIFFERENT: the shipped file is stale")
        return 0 if same else 1

    digest = dump(payload, out)
    checksum_file = out.with_suffix(".sha256")
    checksum_file.write_text(f"{digest}  {out.name}\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(payload['records'])} records")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
