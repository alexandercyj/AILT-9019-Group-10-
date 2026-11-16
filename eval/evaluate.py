#!/usr/bin/env python3
"""Golden-set evaluation.

Runs the 15 hand-written record cases and 2 request cases through the core path
and scores them on the three checks the proposal commits to, plus the boundary
probes that test the grounding rule itself.

    python3 eval/evaluate.py                  # model off — the offline run
    python3 eval/evaluate.py --llm            # model on  — live if a key is set
    python3 eval/evaluate.py --llm --replay   # model on  — recorded responses
    python3 eval/evaluate.py --compare        # both runs side by side
    python3 eval/evaluate.py --json           # also dump the full JSON to stdout

Reports are written to eval/reports/: golden_report.json/.md for the offline run,
golden_report_llm.json/.md for the model-on run, and model_comparison.md for the
comparison. Exit code 0 when every gate passes, 1 otherwise.

The proposal's rule is that both runs must pass the same gates, so the gates do
not change between them. What the model-on run adds is a count of rewrites
accepted, rewrites discarded and why — a discarded rewrite is not a failure,
because the offline draft is printed in its place.
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

from labeldesk import __version__, draft, load_corpus  # noqa: E402
from labeldesk.grounding import check_value_containment  # noqa: E402
from labeldesk.llm import config_from_env, prompt_hash, resolve_mode  # noqa: E402

DATA = ROOT / "data"
REPORTS = ROOT / "eval" / "reports"

# Gates from the proposal. Everything here must pass.
GATES = {
    "outcome_accuracy": 1.0,
    "claim_precision": 1.0,
    "citation_resolution_rate": 1.0,
    "readability_pass_rate": 1.0,
    "restatement_coverage": 1.0,
}


def evaluate_record_case(corpus, case: dict, llm=None) -> dict:
    result = draft(corpus, case["catalogue_number"], llm=llm)
    problems: list[str] = []
    restatements_checked = 0
    restatements_matched = 0

    if result["status"] != case["expected_status"]:
        problems.append(f"status {result['status']} != {case['expected_status']}")

    if case["expected_status"] == "refused":
        if result["reason"] != case.get("expected_reason"):
            problems.append(f"reason {result['reason']} != {case.get('expected_reason')}")
        if sorted(result["missing_fields"]) != sorted(case.get("expected_missing", [])):
            problems.append(
                f"missing {result['missing_fields']} != {case.get('expected_missing', [])}"
            )
        if result["label"]:
            problems.append("a refusal must not produce label text")
        checks = None
    else:
        label = result["label"]
        for field, expected in case.get("expected_restatements", {}).items():
            restatements_checked += 1
            if expected in label:
                restatements_matched += 1
            else:
                problems.append(f"{field} not restated: {expected!r}")
        lowered = label.casefold()
        for term in case.get("expected_medium_terms", []):
            restatements_checked += 1
            if term.casefold() in lowered:
                restatements_matched += 1
            else:
                problems.append(f"medium term missing: {term!r}")
        checks = result["checks"]
        if not checks["passed"]:
            for name in (
                "field_existence",
                "value_containment",
                "citation_resolution",
                "readability",
            ):
                if not checks[name]["passed"]:
                    problems.append(f"check failed: {name}")

    block = result.get("llm") or {}
    return {
        "id": case["id"],
        "catalogue_number": case["catalogue_number"],
        "expected_status": case["expected_status"],
        "actual_status": result["status"],
        "reason": result["reason"],
        "word_count": result["word_count"],
        "claim_precision": checks["claim_precision"] if checks else None,
        "citation_resolution_rate": checks["citation_resolution_rate"] if checks else None,
        "readability_passed": checks["readability"]["passed"] if checks else None,
        "shortened_medium": result["shortened_medium"],
        "label_source": result.get("label_source"),
        "llm_applied": block.get("applied"),
        "llm_reason": block.get("reason"),
        "restatements_checked": restatements_checked,
        "restatements_matched": restatements_matched,
        "problems": problems,
        "passed": not problems,
        "notes": case.get("notes", ""),
    }


def evaluate_request_case(corpus, case: dict, llm=None) -> dict:
    result = draft(corpus, case["catalogue_number"], question=case.get("question"), llm=llm)
    problems = []
    if result["status"] != case["expected_status"]:
        problems.append(f"status {result['status']} != {case['expected_status']}")
    if result["reason"] != case.get("expected_reason"):
        problems.append(f"reason {result['reason']} != {case.get('expected_reason')}")
    if result["label"]:
        problems.append("a refusal must not produce label text")
    return {
        "id": case["id"],
        "catalogue_number": case["catalogue_number"],
        "question": case.get("question"),
        "expected_status": case["expected_status"],
        "actual_status": result["status"],
        "reason": result["reason"],
        "problems": problems,
        "passed": not problems,
        "notes": case.get("notes", ""),
    }


def evaluate_probes(payload: dict) -> dict:
    rows = []
    for probe in payload["probes"]:
        record = {probe["field"]: probe["span"]}
        claim = {
            "id": probe["id"],
            "text": probe["claim"],
            "source_field": probe["field"],
            "value_span": probe["span"],
        }
        check = check_value_containment([claim], record)
        accepted = check["passed"]
        expected = probe["expect"] == "pass"
        rows.append(
            {
                "id": probe["id"],
                "field": probe["field"],
                "claim": probe["claim"],
                "expect": probe["expect"],
                "accepted": accepted,
                "agrees": accepted == expected,
                "reason": check["failures"][0]["reason"] if check["failures"] else None,
                "why": probe["why"],
            }
        )
    false_accepts = [row for row in rows if row["expect"] == "fail" and row["accepted"]]
    spurious = [row for row in rows if row["expect"] == "pass" and not row["accepted"]]
    return {
        "total": len(rows),
        "agree": sum(1 for row in rows if row["agrees"]),
        "false_accepts": false_accepts,
        "spurious_rejections": spurious,
        "rows": rows,
    }


def model_stats(record_rows) -> dict | None:
    """What the model layer did, or None when it was not asked for."""
    drafted = [row for row in record_rows if row["llm_applied"] is not None]
    if not drafted:
        return None
    accepted = [row for row in drafted if row["llm_applied"]]
    rejected = [row for row in drafted if row["llm_applied"] is False]
    return {
        "attempted": len(drafted),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "acceptance_rate": round(len(accepted) / len(drafted), 4) if drafted else None,
        "rejection_reasons": dict(Counter(row["llm_reason"] for row in rejected)),
        "rejected_cases": [
            {"id": row["id"], "catalogue_number": row["catalogue_number"], "reason": row["llm_reason"]}
            for row in rejected
        ],
        "fell_back": len(rejected),
    }


def summarise(record_rows, request_rows, probes, llm_requested: bool = False) -> dict:
    drafted = [row for row in record_rows if row["actual_status"] == "drafted"]
    restatements_checked = sum(row["restatements_checked"] for row in record_rows)
    restatements_matched = sum(row["restatements_matched"] for row in record_rows)
    cases = record_rows + request_rows

    def mean(values):
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 4) if values else None

    summary = {
        "cases_total": len(cases),
        "cases_passed": sum(1 for row in cases if row["passed"]),
        "outcome_accuracy": round(
            sum(1 for row in cases if not any("status" in p or "reason" in p or "missing" in p for p in row["problems"]))
            / len(cases),
            4,
        ),
        "claim_precision": mean([row["claim_precision"] for row in drafted]),
        "citation_resolution_rate": mean([row["citation_resolution_rate"] for row in drafted]),
        "readability_pass_rate": round(
            sum(1 for row in drafted if row["readability_passed"]) / len(drafted), 4
        )
        if drafted
        else None,
        "restatement_coverage": round(restatements_matched / restatements_checked, 4)
        if restatements_checked
        else None,
        "restatements_matched": restatements_matched,
        "restatements_checked": restatements_checked,
        "probe_agreement": round(probes["agree"] / probes["total"], 4),
        "false_accepts": len(probes["false_accepts"]),
        "spurious_rejections": len(probes["spurious_rejections"]),
        "llm_requested": llm_requested,
        "model": model_stats(record_rows) if llm_requested else None,
    }
    summary["gates"] = {
        name: {
            "value": summary[name],
            "required": required,
            "passed": summary[name] is not None and summary[name] >= required,
        }
        for name, required in GATES.items()
    }
    summary["passed"] = (
        all(gate["passed"] for gate in summary["gates"].values())
        and not probes["false_accepts"]
        and summary["cases_passed"] == summary["cases_total"]
    )
    return summary


def write_markdown(report: dict, path: Path) -> None:
    s = report["summary"]
    run_name = "model on" if s.get("llm_requested") else "model off"
    lines = [
        "# Golden-set evaluation",
        "",
        f"Generated {report['generated_at']} · Label Desk {report['labeldesk_version']} · "
        f"corpus sha256 `{report['corpus_checksum'][:12]}` · **{run_name}**",
        "",
    ]
    if report.get("llm_config"):
        cfg = report["llm_config"]
        lines += [
            f"Model `{cfg['model']}` · mode `{cfg['mode']}` · temperature {cfg['temperature']} · "
            f"thinking {'on' if cfg.get('thinking') else 'off'} · "
            f"prompt sha256 `{(cfg.get('prompt_sha256') or '')[:12]}` · "
            f"key {'set' if cfg.get('has_key') else 'not set'}",
            "",
        ]
    lines += [
        "## Gates",
        "",
        "| Gate | Result | Required | Status |",
        "| --- | --- | --- | --- |",
    ]
    for name, gate in s["gates"].items():
        value = "—" if gate["value"] is None else f"{gate['value']:.0%}"
        lines.append(
            f"| {name} | {value} | {gate['required']:.0%} | {'PASS' if gate['passed'] else 'FAIL'} |"
        )
    lines += [
        "",
        f"- cases passed: **{s['cases_passed']}/{s['cases_total']}**",
        f"- restatements matched: {s['restatements_matched']}/{s['restatements_checked']}",
        f"- probe agreement: {s['probe_agreement']:.0%} "
        f"(false accepts {s['false_accepts']}, spurious rejections {s['spurious_rejections']})",
    ]
    model = s.get("model")
    if model:
        lines += [
            "",
            "## Model layer",
            "",
            f"- rewrites attempted: **{model['attempted']}**",
            f"- accepted: **{model['accepted']}** ({model['acceptance_rate']:.0%})",
            f"- discarded, offline draft printed instead: **{model['rejected']}**",
        ]
        if model["rejection_reasons"]:
            reasons = ", ".join(f"`{name}` × {count}" for name, count in model["rejection_reasons"].items())
            lines.append(f"- discard reasons: {reasons}")
            lines.append("")
            lines.append("| Case | Catalogue | Discard reason |")
            lines.append("| --- | --- | --- |")
            for row in model["rejected_cases"]:
                lines.append(f"| {row['id']} | {row['catalogue_number']} | `{row['reason']}` |")
    lines += [
        "",
        "## Record cases",
        "",
        "| Case | Catalogue | Expected | Actual | Source | Words | Claim precision | Citations | Restatements | Result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["record_cases"]:
        precision = "—" if row["claim_precision"] is None else f"{row['claim_precision']:.0%}"
        citations = (
            "—" if row["citation_resolution_rate"] is None else f"{row['citation_resolution_rate']:.0%}"
        )
        source = row.get("label_source") or "—"
        lines.append(
            f"| {row['id']} | {row['catalogue_number']} | {row['expected_status']} | "
            f"{row['actual_status']} | {source} | {row['word_count']} | {precision} | {citations} | "
            f"{row['restatements_matched']}/{row['restatements_checked']} | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Request cases",
        "",
        "| Case | Request | Expected | Actual | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["request_cases"]:
        request = row["question"] or row["catalogue_number"]
        lines.append(
            f"| {row['id']} | {request} | {row['expected_status']} | "
            f"{row['actual_status']} ({row['reason']}) | {'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Boundary probes",
        "",
        "| Probe | Field | Sentence | Expected | Accepted | Rule fired |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["probes"]["rows"]:
        lines.append(
            f"| {row['id']} | {row['field']} | {row['claim']} | {row['expect']} | "
            f"{'yes' if row['accepted'] else 'no'} | {row['reason'] or '—'} |"
        )
    if report["probes"]["spurious_rejections"]:
        lines += ["", "Spurious rejections (diagnostic, not a gate):"]
        lines += [f"- {row['id']}: {row['claim']}" for row in report["probes"]["spurious_rejections"]]
    if report["failures"]:
        lines += ["", "## Failures", ""]
        for failure in report["failures"]:
            lines.append(f"- **{failure['id']}**: " + "; ".join(failure["problems"]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison(off: dict | None, on: dict | None, path: Path) -> str:
    """Side-by-side table of the two runs. The proposal requires both to pass."""
    lines = [
        "# Model off vs model on",
        "",
        "Both runs are the same 15 record cases, 2 request cases and 12 boundary probes,",
        "scored by the same gates. The point of the comparison is that turning the model",
        "on changes the prose and nothing else: the gates below must be identical.",
        "",
        "| Run | Cases | Claim precision | Citation resolution | Readability | Probe agreement | False accepts | Result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, report in (("model off", off), ("model on", on)):
        if not report:
            lines.append(f"| {label} | — | — | — | — | — | — | not run |")
            continue
        s = report["summary"]
        lines.append(
            f"| {label} | {s['cases_passed']}/{s['cases_total']} | "
            f"{s['claim_precision']:.0%} | {s['citation_resolution_rate']:.0%} | "
            f"{s['readability_pass_rate']:.0%} | {s['probe_agreement']:.0%} | "
            f"{s['false_accepts']} | {'PASS' if s['passed'] else 'FAIL'} |"
        )

    lines += ["", "## Label source per case", "", "| Case | Catalogue | Model off | Model on | Words off → on |", "| --- | --- | --- | --- | --- |"]
    off_rows = {row["id"]: row for row in (off or {}).get("record_cases", [])}
    on_rows = {row["id"]: row for row in (on or {}).get("record_cases", [])}
    for case_id in [*off_rows.keys(), *[k for k in on_rows if k not in off_rows]]:
        left = off_rows.get(case_id, {})
        right = on_rows.get(case_id, {})
        right_source = right.get("label_source") or "—"
        if right.get("llm_applied") is False:
            right_source = f"offline (discarded: {right.get('llm_reason')})"
        lines.append(
            f"| {case_id} | {left.get('catalogue_number') or right.get('catalogue_number')} | "
            f"{left.get('label_source') or '—'} | {right_source} | "
            f"{left.get('word_count', '—')} → {right.get('word_count', '—')} |"
        )

    model = (on or {}).get("summary", {}).get("model")
    if model:
        lines += [
            "",
            "## Model layer in the on-run",
            "",
            f"- attempted **{model['attempted']}**, accepted **{model['accepted']}** "
            f"({model['acceptance_rate']:.0%}), discarded **{model['rejected']}**",
        ]
        if model["rejection_reasons"]:
            lines.append(
                "- discard reasons: "
                + ", ".join(f"`{n}` × {c}" for n, c in model["rejection_reasons"].items())
            )
        lines += [
            "",
            "A discarded rewrite is not a failure. The offline draft is printed in its",
            "place, which is why every gate above still passes in the on-run. The",
            "acceptance rate measures prose quality, not correctness.",
        ]
    if off and on:
        same = all(
            (off["summary"].get(gate) == on["summary"].get(gate)) for gate in GATES
        )
        lines += [
            "",
            f"**Gate values identical across both runs: {'yes' if same else 'no'}.**",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--quiet", action="store_true", help="only print the summary")
    parser.add_argument("--llm", action="store_true", help="run with the model layer on")
    parser.add_argument("--replay", action="store_true", help="with --llm, use recorded responses")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="write eval/reports/model_comparison.md from the two existing reports",
    )
    parser.add_argument(
        "--reports",
        type=Path,
        default=None,
        help="write this run's reports here instead of eval/reports",
    )
    args = parser.parse_args()

    reports = args.reports or REPORTS
    reports.mkdir(parents=True, exist_ok=True)
    if args.compare:
        return compare_reports()

    corpus = load_corpus()
    golden = json.loads((DATA / "golden_set.json").read_text(encoding="utf-8"))
    probes = json.loads((ROOT / "eval" / "probes.json").read_text(encoding="utf-8"))["probes"]

    config = config_from_env()
    mode = resolve_mode("replay" if args.replay else "auto", config) if args.llm else "off"
    llm_arg = mode if mode != "off" else None

    record_rows = [evaluate_record_case(corpus, case, llm_arg) for case in golden["cases"]]
    request_rows = [evaluate_request_case(corpus, case, llm_arg) for case in golden["request_cases"]]
    probe_report = evaluate_probes(probes)
    summary = summarise(record_rows, request_rows, probe_report, llm_requested=bool(llm_arg))

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "labeldesk_version": __version__,
        "corpus_version": corpus.meta["version"],
        "corpus_checksum": corpus.checksum,
        "llm_config": {
            **config.describe(),
            "mode": mode,
            "prompt_sha256": prompt_hash() if llm_arg else None,
        }
        if llm_arg
        else None,
        "summary": summary,
        "record_cases": record_rows,
        "request_cases": request_rows,
        "probes": probe_report,
        "failures": [
            {"id": row["id"], "problems": row["problems"]}
            for row in record_rows + request_rows
            if not row["passed"]
        ],
    }

    stem = "golden_report_llm" if llm_arg else "golden_report"
    (reports / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    written = reports / f"{stem}.md"
    write_markdown(report, written)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        run = f"model {mode}" if llm_arg else "model off"
        print(f"Golden set · {summary['cases_passed']}/{summary['cases_total']} cases passed · {run}")
        print(
            f"  claim precision        {summary['claim_precision']:.0%}"
            f"  citation resolution   {summary['citation_resolution_rate']:.0%}"
            f"  readability {summary['readability_pass_rate']:.0%}"
        )
        print(
            f"  restatements           {summary['restatements_matched']}/{summary['restatements_checked']}"
            f"  probe agreement {summary['probe_agreement']:.0%}"
            f"  (false accepts {summary['false_accepts']}, "
            f"spurious rejections {summary['spurious_rejections']})"
        )
        model = summary.get("model")
        if model:
            print(
                f"  rewrites               {model['accepted']}/{model['attempted']} accepted"
                f"  ({model['acceptance_rate']:.0%}), {model['rejected']} discarded -> offline draft"
            )
            for name, count in model["rejection_reasons"].items():
                print(f"        - {name} x {count}")
        if not args.quiet:
            for row in record_rows + request_rows:
                state = "PASS" if row["passed"] else "FAIL"
                print(f"  {state}  {row['id']}  {row['catalogue_number']:<14} {row['actual_status']}")
                for problem in row["problems"]:
                    print(f"        - {problem}")
        try:
            shown = written.relative_to(ROOT)
        except ValueError:
            shown = written
        print(f"\nreport written to {shown}")

    return 0 if summary["passed"] else 1


def compare_reports() -> int:
    """Read both reports from disk and write the comparison. No run, no model."""
    off_path = REPORTS / "golden_report.json"
    on_path = REPORTS / "golden_report_llm.json"
    off = json.loads(off_path.read_text(encoding="utf-8")) if off_path.exists() else None
    on = json.loads(on_path.read_text(encoding="utf-8")) if on_path.exists() else None
    if off is None and on is None:
        print("no reports yet: run eval/evaluate.py and eval/evaluate.py --llm first")
        return 1
    text = write_comparison(off, on, REPORTS / "model_comparison.md")
    print(text)
    both = [report for report in (off, on) if report]
    return 0 if all(report["summary"]["passed"] for report in both) else 1


if __name__ == "__main__":
    sys.exit(main())
