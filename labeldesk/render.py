"""Deterministic offline renderer.

Five fixed sentence templates, one per required field, plus a fixed notice and,
when the label would otherwise fall under the word band, up to three carrier-only
sentences that add no facts. The same record always produces the same label: no
randomness, no network, no model.

Every sentence produced from a field is emitted as a *claim*: a span of the label
paired with exactly one source field and the exact slice of that field it cites.
The grounding check reads claims, never prose.
"""

from __future__ import annotations

import re

from .factsheet import Fact, build_factsheet
from .text import words

NOTICE = "Draft for curator review, not an official record."

# Sentences that restate the situation rather than the object. Every word is a
# carrier word, so they can never introduce a fact.
PADDING = (
    "Every sentence above restates one field of the catalogue record.",
    "No fact outside that record has been added.",
    "It is a drafting aid for curator review, not a museum record.",
)

WORD_BAND = (60, 80)
MEDIUM_SOFT_LIMIT = 12  # words; longer medium values are shortened before use

TEMPLATES = {
    "title": 'The object is titled "{span}".',
    "object_date": "The catalogue dates it to {span}.",
    "medium": 'The medium is recorded as "{span}".',
    "place_or_culture": "Its place or culture is given as {span}.",
    "credit_line": "The credit line reads: {span}.",
}


def medium_variants(value: str) -> list[str]:
    """Candidate slices of a medium value, longest first.

    Each candidate is a literal prefix of the record value, so a citation can
    always be checked by substring, and a shortened medium is visible as
    `shortened: true` in the output rather than silently rewritten.
    """
    value = value.strip()
    candidates = [value]
    if words(value) > MEDIUM_SOFT_LIMIT:
        for pattern in (r"\s+\(", r";"):
            match = re.search(pattern, value)
            if match:
                prefix = value[: match.start()].rstrip(" ,;")
                if len(prefix.split()) >= 1:
                    candidates.append(prefix)
        tokens = value.split()
        candidates.append(" ".join(tokens[:MEDIUM_SOFT_LIMIT]))
        candidates.append(" ".join(tokens[:8]))
    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _claims_for(record: dict, medium_span: str) -> list[dict]:
    facts = build_factsheet(record, medium_span=medium_span)
    claims = []
    for index, fact in enumerate(facts, start=1):
        text = TEMPLATES[fact.field].format(span=fact.span)
        claims.append(
            {
                "id": f"c{index}",
                "text": text,
                "source_field": fact.field,
                "value_span": fact.span,
            }
        )
    return claims


def _assemble(claims: list[dict]) -> tuple[str, list[str]]:
    body = " ".join(claim["text"] for claim in claims)
    padding: list[str] = []
    total = words(body) + words(NOTICE)
    for sentence in PADDING:
        if total >= WORD_BAND[0]:
            break
        padding.append(sentence)
        total += words(sentence)
    parts = [body, *padding, NOTICE]
    return " ".join(parts), padding


def render_label(record: dict) -> dict:
    """Render the label, claims and citations for one validated record."""
    chosen: dict | None = None
    fallback: dict | None = None

    for span in medium_variants(str(record.get("medium", ""))):
        claims = _claims_for(record, span)
        label, padding = _assemble(claims)
        count = words(label)
        candidate = {"claims": claims, "label": label, "padding": padding, "word_count": count}
        if fallback is None:
            fallback = candidate
        if WORD_BAND[0] <= count <= WORD_BAND[1]:
            chosen = candidate
            break
        # Too long: try the next, shorter medium slice.
        if count > WORD_BAND[1]:
            continue
        # Too short even with all padding: keep the longest slice and stop.
        chosen = candidate
        break

    result = chosen or fallback
    assert result is not None  # medium_variants always yields at least one slice

    citations = [
        {
            "field": claim["source_field"],
            "value_span": claim["value_span"],
            "label": claim["source_field"].replace("_", " "),
        }
        for claim in result["claims"]
    ]
    return {
        "label": result["label"],
        "claims": result["claims"],
        "citations": citations,
        "notice": NOTICE,
        "padding": result["padding"],
        "word_count": result["word_count"],
        "shortened_medium": any(
            claim["value_span"] != str(record.get("medium", "")).strip()
            for claim in result["claims"]
            if claim["source_field"] == "medium"
        ),
    }
