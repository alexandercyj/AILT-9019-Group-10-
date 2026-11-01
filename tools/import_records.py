"""Bring in records by hand, and register where they came from and what may be done with them.

Two of the sources in `data/sources.json` are refused: the British Museum and the
Palace Museum. Neither publishes an open licence for its collection records, and
both block automated clients. The correct response is not to work around the
block; it is to stop, record why, and provide the route a person with legitimate
access would use.

That route is this tool. Someone who can see a record — a curator with collection
access, a researcher under a reading-room agreement, a rights holder — can type
the five fields into a CSV and import them. What the tool will not do is accept
the records without a name attached to the claim:

    --license      the terms the records are held under, which the importer asserts
    --basis        why this person is entitled to hold them, in one sentence
    --ai-input     opt in to sending them to the model, off unless asked for

The last one is the point. Asserting a licence to *read* records is not asserting
a licence to send them to a model, so the default is no. A corpus imported without
`--ai-input` drafts offline and refuses `--llm` with `source_policy`, exactly like
an unregistered corpus, but with a name and a basis on file.

Usage:
    python3 tools/import_records.py --csv records.csv --id bm-import \
        --name "British Museum (imported)" --license "BM Terms of Use" \
        --basis "Collection records copied by a curator with collection access." \
        --alias bm --dry-run

    python3 tools/import_records.py ... --ai-input      # opt in to the model layer

CSV columns, first row a header. Required: catalogue_number, title, object_date,
medium, place_or_culture, credit_line. Optional: object_id, department, source_url.

Exit codes: 0 imported, 1 refused (the input was not usable), 2 usage error.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk.corpus import REQUIRED_FIELDS  # noqa: E402
from labeldesk.sources import REGISTER_PATH, get_source, load_register  # noqa: E402

DATA = ROOT / "data"
OPTIONAL_FIELDS = ("object_id", "department", "source_url")
ALL_FIELDS = ("catalogue_number", *REQUIRED_FIELDS, *OPTIONAL_FIELDS)

SLUG = re.compile(r"[^a-z0-9-]+")


def slugify(value: str) -> str:
    return SLUG.sub("-", value.strip().lower()).strip("-")


def read_csv(path: Path) -> tuple[list[dict], list[str], list[int]]:
    """Rows as dicts, header problems, and rows with the wrong number of fields.

    The third return value exists because a credit line is full of commas. An
    unquoted one does not fail to parse — csv reads the extra pieces as extra
    columns, DictReader drops them into a `None` key, and every field after the
    comma shifts left. That would import wrong data quietly, which is the one
    outcome this tool must not produce.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in (reader.fieldnames or [])]
        missing = [field for field in ALL_FIELDS[:6] if field not in header]
        rows: list[dict] = []
        misaligned: list[int] = []
        for line, row in enumerate(reader, start=2):
            if None in row:
                misaligned.append(line)
            rows.append(
                {key.strip(): (value or "").strip() for key, value in row.items() if key}
            )
    return rows, missing, misaligned


def validate(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Every record must be complete, and no catalogue number may repeat.

    A half-filled import is worse than none: the pipeline would refuse those
    records one at a time, and the reason would look like a tool bug rather than a
    gap in the data someone handed over.
    """
    problems: list[str] = []
    seen: dict[str, int] = {}
    for index, row in enumerate(rows, start=2):  # line 1 is the header
        label = row.get("catalogue_number") or f"line {index}"
        blank = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if blank:
            problems.append(f"{label}: missing {', '.join(blank)}")
        key = row.get("catalogue_number", "").casefold()
        if key:
            if key in seen:
                problems.append(f"{label}: duplicate catalogue number (first at line {seen[key]})")
            else:
                seen[key] = index

    records = []
    for row in rows:
        record = {field: row.get(field, "").strip() for field in ALL_FIELDS}
        record["object_id"] = record["object_id"] or record["catalogue_number"]
        record["is_public_domain"] = False  # the importer's licence is not a PD mark
        record["boundary"] = None
        records.append(record)
    return records, problems


def build_corpus(records: list[dict], *, name: str, source: str, license_id: str) -> dict:
    return {
        "corpus": {
            "name": name,
            "version": "1.0.0",
            "source": source,
            "source_api": None,
            "license": license_id,
            "fetched_at": time.strftime("%Y-%m-%d"),
            "record_count": len(records),
            "required_fields": list(REQUIRED_FIELDS),
            "field_map": {field: field for field in ALL_FIELDS},
            "notes": (
                "Imported by hand through tools/import_records.py. The field map is the "
                "identity map because the CSV columns already use the corpus's own names. "
                "is_public_domain is false for every record: a licence asserted by the "
                "importer is not a public-domain mark."
            ),
        },
        "records": records,
    }


def build_source(args, corpus_name: str, file: str, count: int) -> dict:
    today = time.strftime("%Y-%m-%d")
    return {
        "id": args.id,
        "name": args.name,
        "homepage": args.homepage or "",
        "access": {
            "method": "manual_import",
            "endpoint": None,
            "key_required": False,
            "documented_at": None,
        },
        "robots": {
            "url": None,
            "http_status": None,
            "body_sha256_prefix": None,
            "checked": today,
            "verdict": "not_applicable",
            "notes": (
                "Records were not crawled. They were supplied by a person with "
                "legitimate access, so no robots policy governs this project's use of "
                "them. The basis for holding them is recorded in decision.reason."
            ),
        },
        "license": {
            "id": args.license,
            "url": args.license_url or "",
            "attribution_required": not args.no_attribution,
        },
        "policy": {
            "ai_input": bool(args.ai_input),
            "redistribute": bool(args.redistribute),
            "record_source": True,
            "notes": (
                "Imported records. ai_input is off unless the importer asserted it: a "
                "licence to read records is not a licence to send them to a model."
            ),
        },
        "decision": {
            "status": "imported",
            "reason": f"{args.basis} ({count} records, imported {today})",
        },
        "corpora": [{"alias": args.alias, "name": corpus_name, "file": file}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, type=Path, help="the records, one per row")
    parser.add_argument("--id", required=True, help="source id to register, e.g. bm-import")
    parser.add_argument("--name", required=True, help="human-readable source name")
    parser.add_argument("--license", required=True, help="the licence the importer asserts")
    parser.add_argument("--license-url", default=None)
    parser.add_argument("--basis", required=True, help="why the importer may hold these records")
    parser.add_argument("--alias", default=None, help="alias for --corpus; defaults to --id")
    parser.add_argument("--homepage", default=None)
    parser.add_argument("--ai-input", action="store_true", help="permit the model layer (off by default)")
    parser.add_argument("--redistribute", action="store_true", help="permit redistribution")
    parser.add_argument("--no-attribution", action="store_true", help="the licence requires no credit")
    parser.add_argument("--force", action="store_true", help="overwrite an existing corpus and source entry")
    parser.add_argument("--dry-run", action="store_true", help="print what would be written, write nothing")
    args = parser.parse_args()

    alias = args.alias or args.id
    if slugify(args.id) != args.id:
        print(f"source id {args.id!r} must be lowercase letters, digits and hyphens", file=sys.stderr)
        return 2

    if not args.csv.exists():
        print(f"no such file: {args.csv}", file=sys.stderr)
        return 2

    rows, missing, misaligned = read_csv(args.csv)
    if missing:
        print(f"the CSV is missing required columns: {', '.join(missing)}", file=sys.stderr)
        print(f"expected: {', '.join(ALL_FIELDS[:6])}", file=sys.stderr)
        return 1
    if misaligned:
        print(
            f"refusing to import: {len(misaligned)} row(s) have more fields than the header "
            f"(line {', '.join(str(n) for n in misaligned[:5])})",
            file=sys.stderr,
        )
        print(
            "This usually means a value contains a comma and was not quoted. "
            "Wrap such a value in double quotes and run again.",
            file=sys.stderr,
        )
        return 1
    if not rows:
        print("the CSV has a header and no rows", file=sys.stderr)
        return 1

    records, problems = validate(rows)
    if problems:
        print(f"refusing to import: {len(problems)} problem(s) in the input", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nNothing was written. A record missing a required field would be refused "
            "one at a time later, and the refusal would look like a tool fault rather "
            "than a gap in what was supplied.",
            file=sys.stderr,
        )
        return 1

    register = load_register()
    existing = get_source(args.id)
    if existing and not args.force:
        print(f"source {args.id!r} is already registered; use --force to replace it", file=sys.stderr)
        return 1

    corpus_name = f"labeldesk-{args.id}-corpus"
    relative_file = f"data/frozen_corpus_{slugify(args.id)}.json"
    target = ROOT / relative_file

    corpus = build_corpus(
        records,
        name=corpus_name,
        source=args.name,
        license_id=args.license,
    )
    source = build_source(args, corpus_name, relative_file, len(records))

    payload = json.dumps(corpus, ensure_ascii=False, indent=2) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    print(f"source   {args.id} · {args.name}")
    print(f"licence  {args.license} (asserted by the importer, not verified)")
    print(f"basis    {args.basis}")
    print(f"ai_input {'yes' if args.ai_input else 'no'} · redistribute {'yes' if args.redistribute else 'no'}")
    print(f"records  {len(records)} → {relative_file}")
    print(f"alias    --corpus {alias}")
    print(f"sha256   {digest}")

    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    target.with_suffix(".sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")

    entries = [s for s in register["sources"] if s["id"] != args.id]
    entries.append(source)
    register["sources"] = entries
    register["register"]["updated"] = time.strftime("%Y-%m-%d")
    REGISTER_PATH.write_text(
        json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\nwrote {relative_file} and updated data/sources.json")
    if not args.ai_input:
        print(f"--llm will now refuse this corpus with source_policy. That is the default.")
    print(f"try: python3 -m labeldesk {records[0]['catalogue_number']} --corpus {alias}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
