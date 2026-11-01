"""Command-line entry point.

    python -m labeldesk 14.40.377
    python -m labeldesk 14.40.377 --json
    python -m labeldesk 14.40.377 --llm          # model rewrite, guarded
    python -m labeldesk 14.40.377 --llm --replay # recorded response, no network
    python -m labeldesk 62.98.1                 # refusal: no object date
    python -m labeldesk 14.40.377 --ask "what is it worth?"
    python -m labeldesk --list
    python -m labeldesk --info
    python -m labeldesk --sources                # the source register
    python -m labeldesk 1970.36 --corpus cleveland --list
    python -m labeldesk --llm --status           # model layer configuration

`--corpus` takes a registered alias (`primary`, `egyptian`, `cleveland`) or a path.
An alias that is not in data/sources.json is an error, not a silent fallback.

Exit codes: 0 drafted and all checks passed, 1 drafted but a check failed,
3 refused (a designed outcome, reported with its reason), 4 the model layer was
asked for but could not run — no configuration, or a source whose terms forbid it.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .corpus import FIELD_LABELS, ROOT, load_corpus
from .llm import PROMPT_PATH, TRANSCRIPT_PATH, config_from_env, load_transcripts, prompt_hash
from .pipeline import draft
from .sources import ai_input_allowed, format_table, resolve_corpus, sources


def _rule(char: str = "-", width: int = 74) -> str:
    return char * width


def print_info(corpus) -> None:
    meta = corpus.meta
    allowed, source, _policy = ai_input_allowed(corpus)
    print(f"Label Desk {__version__}")
    print(f"Corpus   {meta['name']} v{meta['version']}")
    print(f"Source   {meta['source']} · {meta['license']}")
    print(f"Records  {len(corpus)}")
    print(f"Fetched  {meta['fetched_at']}")
    print(f"sha256   {corpus.checksum}")
    print(f"File     {corpus.path}")
    print()
    if source is None:
        print("Register NOT REGISTERED — no licence on file, so --llm is refused")
        print("         Offline drafting works. See data/sources.json.")
    else:
        print(f"Register {source['id']} · {source['license']['id']} · robots {source['robots']['verdict']}")
        print(f"         decision {source['decision']['status']} · ai_input {'yes' if allowed else 'no'}")
        if not allowed:
            print("         --llm will refuse: this source's terms do not permit it")


def print_sources() -> None:
    print(f"Label Desk {__version__} · source register")
    print(_rule())
    print(format_table())
    print()
    print("Admitted sources can supply records. Refused sources were checked and")
    print("rejected — that is a result, not a gap. Records from a refused source may")
    print("still enter through tools/import_records.py, supplied by a person with")
    print("legitimate access, and the licence they assert is recorded with them.")
    print()
    print("Corpus aliases for --corpus:")
    for source in sources():
        for corpus in source.get("corpora", []):
            relative = (ROOT / corpus["file"]).relative_to(ROOT)
            print(f"  {corpus['alias']:<10} {relative}  ({source['id']})")


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


def print_llm_status() -> None:
    config = config_from_env()
    transcripts = load_transcripts()
    entries = transcripts.get("transcripts") or {}
    print(f"Label Desk {__version__} · model layer")
    print(_rule())
    print(f"Base URL     {config.base_url}")
    print(f"Model        {config.model}")
    print(f"Temperature  {config.temperature}")
    print(f"Thinking     {'on' if config.thinking else 'off (deterministic, cheaper)'}")
    print(f"API key      {'set ' + (config.key_fingerprint or '') if config.has_key else 'not set'}")
    print(f"Prompt       {PROMPT_PATH.name} · sha256 {prompt_hash()[:12]}")
    print(f"Transcript   {TRANSCRIPT_PATH.name} · {len(entries)} recorded responses")
    print(f"Without a key, --llm replays the transcript; with one, it calls the model.")
    print(f"Either way a rewrite that fails the four checks is replaced by the offline draft.")


def print_result(result: dict, corpus) -> None:
    source = result.get("label_source", "offline_template")
    header = {
        "llm_rewrite": "model rewrite",
        "offline_template": "offline draft",
    }.get(source, source)
    print(f"Label Desk {__version__} · {header}")
    print(
        f"Corpus  {corpus.meta['name']} v{corpus.meta['version']} · "
        f"{len(corpus)} records · sha256 {corpus.short_checksum}"
    )
    print(f"Source  {_provenance_line(result.get('provenance'))}")
    record = result.get("record")
    if record:
        print(
            f"Record  {record['catalogue_number']} · {record['title']} · "
            f"object {record['object_id']} · {record['department']}"
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
    _print_llm_line(result.get("llm"))
    # The notice is the last sentence of every label (render.NOTICE), so printing
    # it again here would show the same line twice.


def _provenance_line(prov: dict | None) -> str:
    """One line: who supplied the records and what they allow."""
    if not prov:
        return "unknown"
    if not prov.get("registered"):
        claimed = prov.get("license_claimed")
        suffix = f" (corpus claims {claimed}; not verified)" if claimed else ""
        return f"{prov.get('name') or 'unregistered'} · NOT REGISTERED{suffix} · ai_input no"
    return (
        f"{prov['id']} · {prov['license']} · robots {prov['robots_verdict']} · "
        f"ai_input {'yes' if prov['ai_input'] else 'no'}"
    )


def _print_llm_line(block: dict | None) -> None:
    """One line for the model layer, printed only when it was asked for."""
    if not block or not block.get("requested"):
        return
    if block["applied"]:
        print(f"  Model   {block['model']} · {block['mode']} · rewrite accepted ({block['attempts']} call)")
    elif block["reason"] == "source_policy":
        # Nothing was sent, so "discarded" would misdescribe what happened.
        detail = block.get("detail") or {}
        print(f"  Model   {block['model']} · {block['mode']} · refused before sending: source_policy")
        print(
            f"          source {detail.get('source') or 'unregistered'} · "
            f"licence {detail.get('license') or 'not on file'} · ai_input not granted"
        )
        print("          offline draft printed instead; no record left this machine")
    else:
        print(f"  Model   {block['model']} · {block['mode']} · rewrite discarded: {block['reason']}")
        detail = block.get("detail") or {}
        hint = detail.get("problems") or detail.get("failures") or detail.get("error")
        if hint:
            first = hint[0] if isinstance(hint, list) else hint
            print(f"          {json.dumps(first, ensure_ascii=False)[:100]}")
        print("          offline draft printed instead (no-regression rule)")
    print()


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
    parser.add_argument(
        "--corpus",
        metavar="ALIAS_OR_PATH",
        help="a registered alias (primary, egyptian, cleveland) or a path to a corpus file",
    )
    parser.add_argument(
        "--sources", action="store_true", help="print the source register and the corpus aliases"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="let the model rewrite the draft; discarded unless it passes the same four checks",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="with --llm, use the recorded response instead of a network call",
    )
    parser.add_argument("--status", action="store_true", help="print the model layer configuration")
    args = parser.parse_args(argv)

    if args.sources:
        print_sources()
        return 0

    try:
        corpus_path = resolve_corpus(args.corpus)
    except ValueError as error:
        parser.error(str(error))
        return 2  # unreachable; parser.error exits

    corpus = load_corpus(corpus_path)

    if args.status:
        print_llm_status()
        return 0
    if args.info:
        print_info(corpus)
        return 0
    if args.list:
        print_list(corpus)
        return 0
    if not args.catalogue_number:
        parser.error("a catalogue number is required (or use --list / --info / --sources / --status)")

    mode: bool | str = False
    if args.llm:
        mode = "replay" if args.replay else True

    result = draft(corpus, args.catalogue_number, question=args.ask, llm=mode)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_result(result, corpus)

    if result["status"] == "refused":
        return 3
    # The model layer was asked for and could not run at all: not a drafting
    # failure, so it does not reuse 1 (check failed) or 3 (refused).
    llm_block = result.get("llm") or {}
    if llm_block.get("requested") and llm_block.get("reason") == "source_policy":
        return 4
    return 0 if result["checks"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
