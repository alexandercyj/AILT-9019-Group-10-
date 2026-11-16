#!/usr/bin/env python3
"""Every corpus, every record, both modes: does the pipeline hold on data it did not choose?

`eval/evaluate.py` scores the golden set: hand-picked cases on the primary
corpus, with expectations written beside those records. This script asks a
different question. It runs every record in every registered corpus and
reports what the pipeline says about itself.

A refusal is expected only when one of the five required fields is blank in
the frozen record. A drafted label is expected otherwise. Asking who made an
object is not part of this run, so `unknown_maker` does not appear here.
Replay uses recorded transcripts. It does not call a model.

    python3 eval/cross_corpus.py              # offline, plus replay if transcripts exist
    python3 eval/cross_corpus.py --no-replay  # offline only
    python3 eval/cross_corpus.py --reports /tmp/cross

Writes eval/reports/cross_corpus.md unless --reports is set. Exit code 0 when
no drafted label fails a check and every blank required field is refused.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk import __version__, load_corpus  # noqa: E402
from labeldesk.corpus import REQUIRED_FIELDS  # noqa: E402
from labeldesk.llm import prompt_hash  # noqa: E402
from labeldesk.pipeline import draft  # noqa: E402
from labeldesk.sources import aliases, provenance  # noqa: E402

REPORTS = ROOT / "eval" / "reports"


def blank_required(record: dict) -> list[str]:
    """Required fields that are empty in the frozen record, independent of the reason text."""
    missing = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or not str(value).strip():
            missing.append(field)
    return missing


def run(corpus, llm=None) -> dict:
    counts: Counter = Counter()
    reasons: Counter = Counter()
    word_counts: list[int] = []
    sentences: list[float] = []
    check_failures: list[str] = []
    expectation_failures: list[str] = []
    outcomes: list[dict] = []

    for record in corpus.records:
        result = draft(corpus, record["catalogue_number"], llm=llm)
        missing = blank_required(record)
        counts[result["status"]] += 1
        block = result["llm"] or {}
        outcome = {
            "catalogue_number": record["catalogue_number"],
            "boundary": record.get("boundary"),
            "missing_fields": missing,
            "status": result["status"],
            "reason": result.get("reason"),
            "checks_passed": None,
            "llm_applied": block.get("applied"),
            "llm_reason": block.get("reason"),
        }
        if result["status"] == "refused":
            reasons[result["reason"]] += 1
            if missing and result["reason"] == "missing_required_field":
                outcome["expectation"] = "expected_refusal"
            else:
                outcome["expectation"] = "unexpected_refusal"
                expectation_failures.append(
                    f"{corpus.meta['name']}/{record['catalogue_number']}"
                )
        else:
            outcome["checks_passed"] = bool(result["checks"]["passed"])
            counts["drafted_checks_passed"] += outcome["checks_passed"]
            if not outcome["checks_passed"]:
                check_failures.append(
                    f"{corpus.meta['name']}/{record['catalogue_number']}"
                )
            if missing:
                outcome["expectation"] = "unexpected_draft"
                expectation_failures.append(
                    f"{corpus.meta['name']}/{record['catalogue_number']}"
                )
            else:
                outcome["expectation"] = "expected_draft"
            word_counts.append(result["word_count"])
            sentences.append(result["checks"]["average_sentence_length"])
            if block.get("requested"):
                if block["applied"]:
                    counts["rewrite_accepted"] += 1
                else:
                    counts["rewrite_discarded"] += 1
                    reasons[f"discarded:{block['reason']}"] += 1
        outcomes.append(outcome)

    return {
        "records": len(corpus),
        "counts": dict(counts),
        "reasons": dict(reasons),
        "mean_words": round(sum(word_counts) / len(word_counts), 1) if word_counts else None,
        "mean_sentence": round(sum(sentences) / len(sentences), 2) if sentences else None,
        "check_failures": check_failures,
        "expectation_failures": expectation_failures,
        "failures": check_failures,
        "outcomes": outcomes,
    }


def _lines_for(rows: list[dict], key: str, expectation: str) -> list[str]:
    found = []
    for row in rows:
        for item in row["offline"]["outcomes"]:
            if item["expectation"] == expectation:
                fields = ", ".join(item["missing_fields"]) or "none"
                boundary = item["boundary"] or "no boundary note"
                found.append(
                    f"- `{row['alias']}` `{item['catalogue_number']}` · "
                    f"{item['reason']} · blank fields: {fields} · {boundary}"
                )
    return found


def render(rows: list[dict]) -> str:
    lines = [
        "# Cross-corpus run",
        "",
        f"Generated by `eval/cross_corpus.py` · Label Desk {__version__} · "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Prompt sha256 `{prompt_hash()[:12]}`",
        "",
        "Every record in every registered corpus. Offline drafting, then replay of "
        "recorded transcripts. Replay is not a live model call. This run does not "
        "ask who made an object, so an unknown-maker refusal is outside these counts.",
        "",
        "A refusal is the expected result only when a required field is blank in the "
        "frozen record. A record with all five fields is expected to draft.",
        "",
        "| corpus | records | drafted | refused | checks pass | rewrite accepted | discarded | mean words |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        offline = row["offline"]["counts"]
        llm = row["llm"]["counts"] if row["llm"] else {}
        drafted = offline.get("drafted", 0)
        lines.append(
            "| {name} | {records} | {drafted} | {refused} | {passed}/{drafted} | {acc} | {dis} | {words} |".format(
                name=row["alias"],
                records=row["offline"]["records"],
                drafted=drafted,
                refused=offline.get("refused", 0),
                passed=offline.get("drafted_checks_passed", 0),
                acc=llm.get("rewrite_accepted", "—") if row["llm"] else "—",
                dis=llm.get("rewrite_discarded", 0) if row["llm"] else "—",
                words=row["offline"]["mean_words"],
            )
        )

    lines += ["", "## Expected refusals", ""]
    expected = _lines_for(rows, "offline", "expected_refusal")
    lines += expected or ["- none"]

    lines += ["", "## Unexpected refusals or drafts", ""]
    unexpected = []
    for row in rows:
        for item in row["offline"]["outcomes"]:
            if item["expectation"] in {"unexpected_refusal", "unexpected_draft"}:
                unexpected.append(
                    f"- `{row['alias']}` `{item['catalogue_number']}` · {item['expectation']} · "
                    f"status {item['status']} · reason {item['reason']}"
                )
    lines += unexpected or ["- none"]

    lines += ["", "## Refusals, by reason", ""]
    for row in rows:
        for reason, count in sorted(row["offline"]["reasons"].items()):
            lines.append(f"- `{row['alias']}` · {reason} × {count}")
    if not any(row["offline"]["reasons"] for row in rows):
        lines.append("- none")

    lines += ["", "## Discarded rewrites, by reason", ""]
    discarded = []
    for row in rows:
        if not row["llm"]:
            continue
        for item in row["llm"]["outcomes"]:
            if item["llm_applied"] is False:
                discarded.append(
                    f"- `{row['alias']}` `{item['catalogue_number']}` · {item['llm_reason']}"
                )
    lines += discarded or ["- none"]

    failures = [f for row in rows for f in row["offline"]["check_failures"]]
    failures += [f for row in rows if row["llm"] for f in row["llm"]["check_failures"]]
    lines += ["", "## Check failures", ""]
    lines += [f"- `{name}`" for name in failures] or ["- none"]

    lines += [
        "",
        "## What this does and does not show",
        "",
        "It shows whether any shipped record produces a label whose checks fail, and "
        "whether a blank required field is refused instead of drafted. A discarded "
        "rewrite is not a check failure: the offline draft remains. It does not show "
        "that the labels are good prose. The checks measure grounding, not taste. "
        "It also does not re-fetch the museums.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-replay", action="store_true", help="skip the model replay run")
    parser.add_argument("--json", action="store_true", help="also dump JSON to stdout")
    parser.add_argument(
        "--reports",
        type=Path,
        default=None,
        help="write this run's reports here instead of eval/reports",
    )
    args = parser.parse_args()

    rows = []
    for alias in sorted(aliases()):
        corpus = load_corpus(aliases()[alias])
        row = {"alias": alias, "offline": run(corpus)}
        if not args.no_replay:
            row["llm"] = run(corpus, llm="replay")
        else:
            row["llm"] = None
        row["provenance"] = provenance(corpus)
        rows.append(row)
        offline = row["offline"]["counts"]
        print(
            f"{alias:<10} {row['offline']['records']:>2} records · "
            f"{offline.get('drafted', 0)} drafted · {offline.get('refused', 0)} refused · "
            f"{offline.get('drafted_checks_passed', 0)}/{offline.get('drafted', 0)} checks pass"
            + (
                f" · rewrite {row['llm']['counts'].get('rewrite_accepted', 0)} accepted, "
                f"{row['llm']['counts'].get('rewrite_discarded', 0)} discarded"
                if row.get("llm")
                else ""
            )
        )

    text = render(rows)
    reports = args.reports or REPORTS
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "cross_corpus.md").write_text(text, encoding="utf-8")
    (reports / "cross_corpus.json").write_text(
        json.dumps(
            {"generated": datetime.now(timezone.utc).isoformat(), "runs": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {reports / 'cross_corpus.md'}")

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))

    failed = any(
        row["offline"]["check_failures"] or row["offline"]["expectation_failures"]
        for row in rows
    ) or any(
        row.get("llm")
        and (row["llm"]["check_failures"] or row["llm"]["expectation_failures"])
        for row in rows
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
