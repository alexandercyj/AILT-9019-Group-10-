"""Fact sheet: one entry per field, every entry keeping a pointer to its source.

This is the structure the renderer is allowed to read. Nothing outside the fact
sheet can reach the label, which is why an invented fact cannot be introduced by
a template change without failing the grounding check.
"""

from __future__ import annotations

from dataclasses import dataclass

from .corpus import FIELD_LABELS, REQUIRED_FIELDS


@dataclass(frozen=True)
class Fact:
    field: str
    label: str
    value: str
    span: str
    shortened: bool = False

    def as_dict(self) -> dict:
        return {
            "field": self.field,
            "label": self.label,
            "value": self.value,
            "span": self.span,
            "shortened": self.shortened,
        }


def build_factsheet(record: dict, medium_span: str | None = None) -> tuple[Fact, ...]:
    """Build the fact sheet, in the fixed order the label uses.

    `medium_span` lets the renderer cite a shorter contiguous slice of the medium
    value when the full value would push the label past its word band. The slice
    is always a literal prefix of the record value, never a paraphrase.
    """
    facts = []
    for field in REQUIRED_FIELDS:
        value = str(record.get(field, "") or "")
        span = value
        shortened = False
        if field == "medium" and medium_span is not None and medium_span != value:
            span = medium_span
            shortened = True
        facts.append(
            Fact(
                field=field,
                label=FIELD_LABELS[field],
                value=value,
                span=span,
                shortened=shortened,
            )
        )
    return tuple(facts)
