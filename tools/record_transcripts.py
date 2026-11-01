"""Record the model layer's responses into data/llm_transcripts.json.

Why a transcript ships with the repository: the proposal promises that `--llm`
works without a key and without a network, so a reader can see the model path
without signing up for anything. The recorded response is the *raw* text the model
returned, not a cleaned-up result — it is re-parsed and re-checked on every replay,
so a transcript cannot smuggle in an accepted rewrite the guardrail would now
reject. Each entry also stores the sha256 of the prompt that produced it, so editing
prompts/rewrite.txt marks the transcript stale instead of silently reusing it.

Usage:
    python3 tools/record_transcripts.py                 # all records that draft
    python3 tools/record_transcripts.py 14.40.377       # one record
    python3 tools/record_transcripts.py --corpus data/frozen_corpus_egyptian.json
    python3 tools/record_transcripts.py --check         # verify without writing

Requires a key (LABELDESK_API_KEY or .env) and network access.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk import load_corpus  # noqa: E402
from labeldesk.llm import (  # noqa: E402
    TRANSCRIPT_PATH,
    config_from_env,
    load_transcripts,
    prompt_hash,
    record_one,
    save_transcripts,
    transcript_key,
)
from labeldesk.pipeline import draft  # noqa: E402
from labeldesk.sources import resolve_corpus  # noqa: E402


def targets(corpus, only: list[str] | None) -> list[tuple[dict, dict]]:
    """Records that reach the model at all, with their offline draft.

    A refusal never makes a call, so the 4 boundary records in the corpus are
    skipped here and stay skipped in every model-on run.
    """
    numbers = only or corpus.catalogue_numbers()
    wanted = []
    for number in numbers:
        result = draft(corpus, number)
        if result["status"] == "drafted":
            wanted.append((result["record"], result))
    return wanted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numbers", nargs="*", help="catalogue numbers; default is all records")
    parser.add_argument("--corpus", help="a registered alias or a path to a corpus JSON file")
    parser.add_argument("--check", action="store_true", help="report coverage, write nothing")
    parser.add_argument("--force", action="store_true", help="re-record entries that already exist")
    args = parser.parse_args()

    config = config_from_env()
    if not config.has_key and not args.check:
        print("no API key: set LABELDESK_API_KEY or put it in .env", file=sys.stderr)
        return 2

    corpus = load_corpus(resolve_corpus(args.corpus))
    corpus_name = corpus.meta["name"]
    payload = load_transcripts()
    entries = payload.setdefault("transcripts", {})
    digest = prompt_hash()

    records = targets(corpus, args.numbers or None)
    print(f"{len(records)} records reach the model · prompt sha256 {digest[:12]}")
    print(f"corpus {corpus_name} · keys scoped as {transcript_key('<number>', corpus_name)}")

    written = 0
    for record, offline in records:
        number = record["catalogue_number"]
        key = transcript_key(number, corpus_name)
        # A pre-scoping entry for the primary corpus is still valid; keep reading it.
        existing = entries.get(key) or (entries.get(number) if corpus_name == "labeldesk-frozen-corpus" else None)
        if args.check:
            state = "recorded" if existing else "missing"
            fresh = existing and existing.get("prompt_sha256") == digest
            print(f"  {number:<14} {state}{'' if fresh else ' (stale or absent)'}")
            continue
        if existing and not args.force and existing.get("prompt_sha256") == digest:
            print(f"  {number:<14} kept")
            continue
        entry = record_one(record, offline, config, corpus=corpus_name)
        entries[key] = entry
        written += 1
        print(f"  {number:<14} recorded · {len(entry['response'])} chars")

    if args.check:
        missing = [
            record["catalogue_number"]
            for record, _ in records
            if transcript_key(record["catalogue_number"], corpus_name) not in entries
            and record["catalogue_number"] not in entries
        ]
        stale = [
            number
            for number, entry in entries.items()
            if entry.get("prompt_sha256") != digest
        ]
        print(f"\n{len(entries)} entries · {len(missing)} missing · {len(stale)} stale")
        return 0 if not missing and not stale else 1

    payload["meta"] = {
        "model": config.model,
        "base_url": config.base_url,
        "prompt_sha256": digest,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temperature": config.temperature,
        "note": (
            "Raw model responses, one per catalogue number, re-parsed and re-checked "
            "on replay. Editing prompts/rewrite.txt invalidates every entry."
        ),
    }
    save_transcripts(payload)
    print(f"\nwrote {TRANSCRIPT_PATH.relative_to(ROOT)} · {len(entries)} entries · {written} new")
    return 0


if __name__ == "__main__":
    sys.exit(main())
