"""Command-line entry point.

    python -m labeldesk 14.40.377
    python -m labeldesk 14.40.377 --json
    python -m labeldesk 62.98.1                 # refusal: no object date
    python -m labeldesk 14.40.377 --ask "what is it worth?"
    python -m labeldesk --list
    python -m labeldesk --info

Exit codes: 0 drafted and all checks passed, 1 drafted but a check failed,
3 refused (a designed outcome, reported with its reason).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .corpus import FIELD_LABELS, load_corpus
from .pipeline import draft


def _rule(char: str = "-", width: int = 74) -> str:
    return char * width


def print_info(corpus) -> None:
    meta = corpus.meta
    print(f"Label Desk {__version__}")
    print(f"Corpus   {meta['name']} v{meta['version']}")
    print(f"Source   {meta['source']} · {meta['license']}")
    print(f"Records  {len(corpus)}")
    print(f"Fetched  {meta['fetched_at']}")
    print(f"sha256   {corpus.checksum}")
    print(f"File     {corpus.path}")


def print_list(corpus) -> None:
    print(f"{len(corpus)} records in {corpus.meta['name']} v{corpus.meta['version']}")
    print(_rule())
    print(f"{'CATALOGUE':<16} {'DATE':<26} {'PLACE/CULTURE':<20} TITLE")
    for record in corpus.records:
        date = record["object_date"] or "— (missing)"
        place = record["place_or_culture"] or "— (missing)"
        print(
            f"{record['catalogue_number']:<16} {date[:25]:<26} {place[:19]:<20} {record['title'][:28]}"
        )


def print_result(result: dict, corpus) -> None:
    print(f"Label Desk {__version__} · offline draft")
    print(
        f"Corpus  {corpus.meta['name']} v{corpus.meta['version']} · "
        f"{len(corpus)} records · sha256 {corpus.short_checksum}"
    )
    record = result.get("record")
    if record:
        print(
            f"Record  {record['catalogue_number']} · {record['title']} · "
            f"Met object {record['object_id']} · {record['department']}"
        )
    print()

    if result["status"] == "refused":
        print("STATUS  REFUSED")
        print(f"Reason  {result['reason']}")
        print()
        for line in _wrap(result["reason_text"], 70):
            print(f"  {line}")
        return

    checks = result["checks"]
    print("STATUS  DRAFTED")
    print(f"Label   {result['word_count']} words (band 60–80)")
    print()
    for line in _wrap(result["label"], 70):
        print(f"  {line}")
    print()
    print("Claims")
    for claim in result["claims"]:
        label = FIELD_LABELS[claim["source_field"]]
        print(f'  {claim["id"]:<4}{label:<18}-> "{claim["value_span"]}"')
    print()
    print("Checks")
    for key in ("field_existence", "value_containment", "citation_resolution", "readability"):
        check = checks[key]
        state = "PASS" if check["passed"] else "FAIL"
        print(f"  {state}  {check['name']:<22}{check['detail']}")
    print(
        f"  claim precision {checks['claim_precision']:.0%} · "
        f"citation resolution {checks['citation_resolution_rate']:.0%} · "
        f"average sentence {checks['average_sentence_length']} words"
    )
    if result["shortened_medium"]:
        print("  note  medium cited as a shortened slice of the record value")
    print()
    print(f"  {result['notice']}")


def _wrap(text: str, width: int) -> list[str]:
    import textwrap

    return textwrap.wrap(text, width=width) or [""]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="labeldesk",
        description="Draft a cited exhibition label from one frozen catalogue record.",
    )
    parser.add_argument("catalogue_number", nargs="?", help="e.g. 14.40.377")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--ask", metavar="QUESTION", help="ask a question; out-of-scope asks are refused")
    parser.add_argument("--list", action="store_true", help="list the catalogue numbers in the corpus")
    parser.add_argument("--info", action="store_true", help="print corpus metadata and checksum")
    parser.add_argument("--corpus", help="path to a corpus JSON file")
    args = parser.parse_args(argv)

    corpus = load_corpus(args.corpus)

    if args.info:
        print_info(corpus)
        return 0
    if args.list:
        print_list(corpus)
        return 0
    if not args.catalogue_number:
        parser.error("a catalogue number is required (or use --list / --info)")

    result = draft(corpus, args.catalogue_number, question=args.ask)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_result(result, corpus)

    if result["status"] == "refused":
        return 3
    return 0 if result["checks"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
