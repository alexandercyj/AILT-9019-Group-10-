#!/usr/bin/env python3
"""Golden-set evaluation.

Runs the 15 hand-written record cases and 2 request cases through the core path
and scores them on the three checks the proposal commits to, plus the boundary
probes that test the grounding rule itself.

    python eval/evaluate.py            # run, print, write reports
    python eval/evaluate.py --json     # also dump the full JSON to stdout

Reports are written to eval/reports/golden_report.json and golden_report.md.
Exit code 0 when every gate passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk import __version__, draft, load_corpus  # noqa: E402
from labeldesk.grounding import check_value_containment  # noqa: E402

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


def evaluate_record_case(corpus, case: dict) -> dict:
    result = draft(corpus, case["catalogue_number"])
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
        "restatements_checked": restatements_checked,
        "restatements_matched": restatements_matched,
        "problems": problems,
        "passed": not problems,
        "notes": case.get("notes", ""),
    }


def evaluate_request_case(corpus, case: dict) -> dict:
    result = draft(corpus, case["catalogue_number"], question=case.get("question"))
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


def summarise(record_rows, request_rows, probes) -> dict:
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
    lines = [
        "# Golden-set evaluation",
        "",
        f"Generated {report['generated_at']} · Label Desk {report['labeldesk_version']} · "
        f"corpus sha256 `{report['corpus_checksum'][:12]}`",
        "",
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
        "",
        "## Record cases",
        "",
        "| Case | Catalogue | Expected | Actual | Words | Claim precision | Citations | Restatements | Result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["record_cases"]:
        precision = "—" if row["claim_precision"] is None else f"{row['claim_precision']:.0%}"
        citations = (
            "—" if row["citation_resolution_rate"] is None else f"{row['citation_resolution_rate']:.0%}"
        )
        lines.append(
            f"| {row['id']} | {row['catalogue_number']} | {row['expected_status']} | "
            f"{row['actual_status']} | {row['word_count']} | {precision} | {citations} | "
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--quiet", action="store_true", help="only print the summary")
    args = parser.parse_args()

    corpus = load_corpus()
    golden = json.loads((DATA / "golden_set.json").read_text(encoding="utf-8"))
    probes = json.loads((ROOT / "eval" / "probes.json").read_text(encoding="utf-8"))["probes"]

    record_rows = [evaluate_record_case(corpus, case) for case in golden["cases"]]
    request_rows = [evaluate_request_case(corpus, case) for case in golden["request_cases"]]
    probe_report = evaluate_probes(probes)
    summary = summarise(record_rows, request_rows, probe_report)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "labeldesk_version": __version__,
        "corpus_version": corpus.meta["version"],
        "corpus_checksum": corpus.checksum,
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

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "golden_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(report, REPORTS / "golden_report.md")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Golden set · {summary['cases_passed']}/{summary['cases_total']} cases passed")
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
        if not args.quiet:
            for row in record_rows + request_rows:
                state = "PASS" if row["passed"] else "FAIL"
                print(f"  {state}  {row['id']}  {row['catalogue_number']:<14} {row['actual_status']}")
                for problem in row["problems"]:
                    print(f"        - {problem}")
        print(f"\nreport written to {(REPORTS / 'golden_report.md').relative_to(ROOT)}")

    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
