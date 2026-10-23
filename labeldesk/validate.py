"""Required-field validation.

Step 1 of the pipeline. A record that cannot supply all five fields is not
patched and not guessed at: the pipeline stops and names what is missing.
"""

from __future__ import annotations

from .corpus import FIELD_LABELS, REQUIRED_FIELDS


def missing_fields(record: dict) -> list[str]:
    """Return the required fields whose value is blank or absent, in fixed order."""
    missing = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or not str(value).strip():
            missing.append(field)
    return missing


def describe_missing(missing: list[str]) -> str:
    """Readable list of the missing fields, e.g. 'object date and place or culture'."""
    labels = [FIELD_LABELS.get(field, field) for field in missing]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]
