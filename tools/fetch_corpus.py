"""Build the frozen corpus from the Met Open Access API.

The repository ships `data/frozen_corpus.json`, so this script is **not** needed to
run the core path. It exists so the shipped file can be rebuilt and audited: every
field in the corpus is copied verbatim from the Met object record, and the object
IDs below are the only editorial choice the team made.

Usage:
    python tools/fetch_corpus.py            # writes data/frozen_corpus.json
    python tools/fetch_corpus.py --check    # rebuild to a temp file and diff

Requires network access. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "frozen_corpus.json"
API = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"

# 20 object IDs: 14 records with all five required fields, 6 boundary records.
# Boundary reasons are recorded in each record's "boundary" key below.
SELECTION = {
    42229: None,   # well formed
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
}

FIELD_MAP = {
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
}


def fetch(oid: int) -> dict:
    with urllib.request.urlopen(API.format(oid=oid), timeout=30) as response:
        return json.load(response)


def normalise(raw: dict, boundary: str | None) -> dict:
    record = {key: raw.get(src) or "" for key, src in FIELD_MAP.items()}
    record["is_public_domain"] = bool(raw.get("isPublicDomain"))
    record["boundary"] = boundary
    return record


def build() -> dict:
    records = []
    for oid, boundary in SELECTION.items():
        records.append(normalise(fetch(oid), boundary))
    return {
        "corpus": {
            "name": "labeldesk-frozen-corpus",
            "version": "1.0.0",
            "source": "The Metropolitan Museum of Art Open Access",
            "source_api": API,
            "license": "CC0 1.0 (public domain)",
            "fetched_at": date.today().isoformat(),
            "record_count": len(records),
            "required_fields": [
                "title",
                "object_date",
                "medium",
                "place_or_culture",
                "credit_line",
            ],
            "field_map": FIELD_MAP,
            "notes": (
                "Field values are copied verbatim from the Met object records. "
                "Blank strings are the museum's own blanks, not missing data "
                "introduced by the team. The 6 boundary records are kept in the "
                "corpus on purpose so the refusal path can be demonstrated."
            ),
        },
        "records": records,
    }


def dump(payload: dict, path: Path) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare a fresh build with the shipped file")
    args = parser.parse_args()

    payload = build()
    if args.check:
        tmp = ROOT / "data" / ".rebuilt.json"
        digest = dump(payload, tmp)
        same = tmp.read_bytes() == OUT.read_bytes()
        tmp.unlink()
        print(f"sha256 {digest}")
        print("shipped file matches a fresh build" if same else "DIFFERENT: the shipped file is stale")
        return 0 if same else 1

    digest = dump(payload, OUT)
    (ROOT / "data" / "frozen_corpus.sha256").write_text(f"{digest}  frozen_corpus.json\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(payload['records'])} records")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
