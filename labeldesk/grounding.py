"""The automatic grounding check.

Three tests on every claim, plus one readability test on the label:

(a) field existence    - the cited field is a required field and is non-empty;
(b) value containment  - every fact-carrying token in the claim comes from the
                         cited slice, no hedge is dropped, no new number appears;
(c) citation resolution- every printed citation resolves to a field and a slice
                         that really occur in the record;
(d) readability        - 60-80 words, average sentence under 20 words.

The check is deliberately conservative. A sentence a curator would accept can
still be rejected, and every rejection is returned with a reason so it can be
audited instead of tuned away.
"""

from __future__ import annotations

from .corpus import REQUIRED_FIELDS
from .text import (
    average_sentence_length,
    content_tokens,
    hedges,
    normalise,
    numbers,
    tokenize,
    words,
)

WORD_BAND = (60, 80)
MAX_AVERAGE_SENTENCE = 20.0


def _result(name: str, total: int, failures: list[dict], unit: str) -> dict:
    passed = total > 0 and not failures
    detail = (
        f"{total - len(failures)}/{total} {unit} pass"
        if total
        else "no items to check"
    )
    return {
        "name": name,
        "passed": passed,
        "detail": detail,
        "failures": failures,
        "total": total,
        "failed": len(failures),
    }


def check_field_existence(claims: list[dict], record: dict) -> dict:
    failures = []
    for claim in claims:
        field = claim.get("source_field")
        if field not in REQUIRED_FIELDS:
            failures.append({"claim": claim["id"], "reason": "unknown_field", "field": field})
        elif not str(record.get(field, "") or "").strip():
            failures.append({"claim": claim["id"], "reason": "empty_field", "field": field})
    return _result("Field existence", len(claims), failures, "claims")


def check_value_containment(claims: list[dict], record: dict) -> dict:
    failures = []
    for claim in claims:
        field = claim.get("source_field")
        span = claim.get("value_span", "")
        if field not in REQUIRED_FIELDS or not str(record.get(field, "") or "").strip():
            continue  # already reported by check_field_existence
        if normalise(span) not in normalise(str(record[field])):
            failures.append(
                {"claim": claim["id"], "reason": "span_not_in_field", "field": field, "span": span}
            )
            continue

        allowed = set(tokenize(span))
        unsupported = [t for t in content_tokens(claim["text"]) if t not in allowed]
        if unsupported:
            failures.append(
                {
                    "claim": claim["id"],
                    "reason": "unsupported_word",
                    "field": field,
                    "words": unsupported,
                    "span": span,
                }
            )
            continue

        dropped = sorted(hedges(span) - hedges(claim["text"]))
        if dropped:
            failures.append(
                {"claim": claim["id"], "reason": "dropped_hedge", "field": field, "markers": dropped}
            )
            continue

        invented = sorted(numbers(claim["text"]) - numbers(span))
        if invented:
            failures.append(
                {"claim": claim["id"], "reason": "new_number", "field": field, "numbers": invented}
            )
    return _result("Value containment", len(claims), failures, "claims")


def check_citation_resolution(citations: list[dict], record: dict) -> dict:
    failures = []
    for index, citation in enumerate(citations, start=1):
        field = citation.get("field")
        span = citation.get("value_span", "")
        if field not in REQUIRED_FIELDS:
            failures.append({"citation": index, "reason": "unknown_field", "field": field})
        elif not str(record.get(field, "") or "").strip():
            failures.append({"citation": index, "reason": "empty_field", "field": field})
        elif normalise(span) not in normalise(str(record[field])):
            failures.append(
                {"citation": index, "reason": "unresolved", "field": field, "span": span}
            )
    return _result("Citation resolution", len(citations), failures, "citations")


def check_readability(label: str) -> dict:
    count = words(label)
    average = average_sentence_length(label)
    failures = []
    if count < WORD_BAND[0]:
        failures.append({"reason": "too_short", "word_count": count, "band": WORD_BAND})
    if count > WORD_BAND[1]:
        failures.append({"reason": "too_long", "word_count": count, "band": WORD_BAND})
    if average >= MAX_AVERAGE_SENTENCE:
        failures.append(
            {"reason": "long_sentences", "average": average, "limit": MAX_AVERAGE_SENTENCE}
        )
    result = _result("Readability", 1, failures, "label")
    result.update({"word_count": count, "average_sentence_length": average})
    return result


def run_checks(result: dict, record: dict) -> dict:
    """Run all four checks over a rendered result and summarise it."""
    claims = result["claims"]
    citations = result["citations"]
    existence = check_field_existence(claims, record)
    containment = check_value_containment(claims, record)
    resolution = check_citation_resolution(citations, record)
    readability = check_readability(result["label"])

    claims_passed = sum(
        1
        for claim in claims
        if not any(
            failure["claim"] == claim["id"]
            for failure in existence["failures"] + containment["failures"]
            if "claim" in failure
        )
    )
    citations_resolved = len(citations) - len(resolution["failures"])
    total = len(claims)
    passed = all(
        check["passed"] for check in (existence, containment, resolution, readability)
    )

    return {
        "field_existence": existence,
        "value_containment": containment,
        "citation_resolution": resolution,
        "readability": readability,
        "claims_total": total,
        "claims_passed": claims_passed,
        "claim_precision": round(claims_passed / total, 4) if total else 0.0,
        "citations_total": len(citations),
        "citations_resolved": citations_resolved,
        "citation_resolution_rate": round(citations_resolved / len(citations), 4)
        if citations
        else 0.0,
        "word_count": readability["word_count"],
        "average_sentence_length": readability["average_sentence_length"],
        "passed": passed,
    }
