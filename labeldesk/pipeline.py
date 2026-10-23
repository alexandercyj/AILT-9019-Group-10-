"""The pipeline: one record in, one of two outcomes out.

    request -> look up -> validate -> render -> check -> drafted | refused

Refusal is a designed outcome, not an error. The three refusal reasons are:

    out_of_corpus         the catalogue number is not in the frozen corpus
    out_of_scope          the request asks for value, authenticity or rights
    missing_required_field the record itself cannot supply a required field
"""

from __future__ import annotations

from .corpus import Corpus
from .grounding import run_checks
from .render import render_label
from .validate import describe_missing, missing_fields

OUT_OF_SCOPE_TERMS = (
    "value",
    "worth",
    "price",
    "cost",
    "apprais",
    "authentic",
    "forgery",
    "fake",
    "insur",
    "rights",
    "copyright",
    "sell",
    "sale",
    "auction",
    "how much",
)

REASON_TEXT = {
    "out_of_corpus": (
        "Catalogue number {catalogue_number} is not in the frozen corpus. "
        "No label was drafted: the system does not describe a similar object from "
        "memory. Use --list to see the {count} catalogue numbers it can answer for."
    ),
    "out_of_scope": (
        "This request is outside the tool's scope ({term}). Label Desk drafts "
        "labels from a catalogue record; it does not value, authenticate, insure "
        "or clear rights for any object, and it has no data to do so."
    ),
    "missing_required_field": (
        "Record {catalogue_number} has no {missing}. No label was drafted: a blank "
        "field is not filled from outside the record. Supply the missing catalogue "
        "information and run again."
    ),
}


def is_out_of_scope(question: str | None) -> str | None:
    """Return the term that puts a request out of scope, or None."""
    if not question:
        return None
    text = question.casefold()
    for term in OUT_OF_SCOPE_TERMS:
        if term in text:
            return term
    return None


def _refusal(catalogue_number: str, reason: str, reason_text: str, **extra) -> dict:
    payload = {
        "status": "refused",
        "catalogue_number": catalogue_number,
        "reason": reason,
        "reason_text": reason_text,
        "missing_fields": [],
        "label": None,
        "claims": [],
        "citations": [],
        "padding": [],
        "notice": "",
        "word_count": 0,
        "shortened_medium": False,
        "checks": None,
        "record": None,
    }
    payload.update(extra)
    return payload


def draft(corpus: Corpus, catalogue_number: str, question: str | None = None) -> dict:
    """Run the core path for one catalogue number."""
    catalogue_number = str(catalogue_number).strip()

    term = is_out_of_scope(question)
    if term:
        return _refusal(
            catalogue_number,
            "out_of_scope",
            REASON_TEXT["out_of_scope"].format(term=term),
            question=question,
        )

    record = corpus.get(catalogue_number)
    if record is None:
        return _refusal(
            catalogue_number,
            "out_of_corpus",
            REASON_TEXT["out_of_corpus"].format(
                catalogue_number=catalogue_number, count=len(corpus)
            ),
        )

    missing = missing_fields(record)
    if missing:
        return _refusal(
            catalogue_number,
            "missing_required_field",
            REASON_TEXT["missing_required_field"].format(
                catalogue_number=record["catalogue_number"], missing=describe_missing(missing)
            ),
            missing_fields=missing,
            record=record,
        )

    rendered = render_label(record)
    checks = run_checks(rendered, record)
    return {
        "status": "drafted",
        "catalogue_number": record["catalogue_number"],
        "reason": None,
        "reason_text": "",
        "missing_fields": [],
        **rendered,
        "checks": checks,
        "record": record,
    }
