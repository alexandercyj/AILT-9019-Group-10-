"""The grounding check must reject the failures it exists to catch.

These tests break the output on purpose. A checker that passed everything would
fail this file.
"""

from __future__ import annotations

import pytest

from labeldesk.grounding import (
    check_citation_resolution,
    check_field_existence,
    check_readability,
    check_value_containment,
)

RECORD = {
    "title": "Vase",
    "object_date": "18th century",
    "medium": "Porcelain with peach-bloom glaze (Jingdezhen ware)",
    "place_or_culture": "probably Iran",
    "credit_line": "Rogers Fund, 1920",
}


def claim(text: str, field: str, span: str) -> dict:
    return {"id": "t1", "text": text, "source_field": field, "value_span": span}


def check(text: str, field: str, span: str, record: dict | None = None) -> dict:
    return check_value_containment([claim(text, field, span)], record or RECORD)


def test_verbatim_claim_passes():
    assert check('The object is titled "Vase".', "title", "Vase")["passed"] is True


def test_invented_place_is_rejected():
    result = check("It was made in Egypt.", "place_or_culture", "Iran", {**RECORD, "place_or_culture": "Iran"})
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "unsupported_word"
    assert "egypt" in result["failures"][0]["words"]


def test_narrowed_date_is_rejected():
    result = check("It was made in 1750.", "object_date", "18th century")
    assert result["passed"] is False
    assert result["failures"][0]["reason"] in {"unsupported_word", "new_number"}


def test_dropped_hedge_is_rejected():
    result = check("It was made in Iran.", "place_or_culture", "probably Iran")
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "dropped_hedge"
    assert "probable" in result["failures"][0]["markers"]


def test_synonym_hedge_is_accepted():
    result = check("It was made around 1750.", "object_date", "ca. 1750", {**RECORD, "object_date": "ca. 1750"})
    assert result["passed"] is True


def test_removed_doubt_marker_is_rejected():
    record = {**RECORD, "object_date": "late 18th century (?)"}
    result = check(
        "The catalogue dates it to late 18th century.",
        "object_date",
        "late 18th century (?)",
        record,
    )
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "dropped_hedge"


def test_dropped_disjunction_is_rejected():
    record = {**RECORD, "place_or_culture": "Old Assyrian Trading Colony or Hittite"}
    result = check("It was made in Hittite.", "place_or_culture", record["place_or_culture"], record)
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "dropped_hedge"


def test_field_existence_rejects_unknown_field():
    result = check_field_existence([claim("Something.", "image_url", "x")], RECORD)
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "unknown_field"


def test_field_existence_rejects_blank_field():
    record = {**RECORD, "object_date": ""}
    result = check_field_existence([claim("Something.", "object_date", "18th century")], record)
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "empty_field"


def test_citation_must_resolve_to_the_record():
    bad = [{"field": "object_date", "value_span": "mid-18th century"}]
    result = check_citation_resolution(bad, RECORD)
    assert result["passed"] is False
    assert result["failures"][0]["reason"] == "unresolved"


def test_shortened_medium_citation_resolves():
    good = [{"field": "medium", "value_span": "Porcelain with peach-bloom glaze"}]
    assert check_citation_resolution(good, RECORD)["passed"] is True


def test_readability_rejects_a_short_label():
    assert check_readability("Too short.")["passed"] is False


def test_readability_rejects_a_long_label():
    label = " ".join(["word"] * 90) + "."
    assert check_readability(label)["passed"] is False


def test_readability_rejects_long_sentences():
    sentence = " ".join(["word"] * 40) + "."
    result = check_readability(" ".join([sentence] * 2))
    assert result["passed"] is False
    assert any(failure["reason"] == "long_sentences" for failure in result["failures"])


@pytest.mark.parametrize(
    ("text", "field", "span"),
    [
        ('The object is titled "Vase".', "title", "Vase"),
        ("It was made in Iran.", "place_or_culture", "Iran"),
        (
            'The medium is recorded as "Porcelain with peach-bloom glaze (Jingdezhen ware)".',
            "medium",
            "Porcelain with peach-bloom glaze (Jingdezhen ware)",
        ),
        ("The credit line reads: Rogers Fund, 1920.", "credit_line", "Rogers Fund, 1920"),
    ],
)
def test_template_carriers_do_not_fail_containment(text, field, span):
    record = {**RECORD, field: span}
    assert check(text, field, span, record)["passed"] is True
