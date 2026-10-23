"""Refusal is a designed outcome: the system says no instead of guessing."""

from __future__ import annotations

import pytest

from labeldesk import draft, load_corpus


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_missing_object_date_is_refused(corpus):
    result = draft(corpus, "62.98.1")
    assert result["status"] == "refused"
    assert result["reason"] == "missing_required_field"
    assert result["missing_fields"] == ["object_date"]
    assert result["label"] is None
    assert result["claims"] == []
    assert result["checks"] is None


def test_refusal_names_the_missing_field(corpus):
    result = draft(corpus, "62.98.1")
    assert "object date" in result["reason_text"]
    assert "62.98.1" in result["reason_text"]


def test_missing_place_or_culture_is_refused(corpus):
    result = draft(corpus, "09.13.5")
    assert result["reason"] == "missing_required_field"
    assert result["missing_fields"] == ["place_or_culture"]


def test_unknown_catalogue_number_is_refused_as_out_of_corpus(corpus):
    result = draft(corpus, "99.99.99")
    assert result["status"] == "refused"
    assert result["reason"] == "out_of_corpus"
    assert result["record"] is None
    assert "does not describe a similar object" in result["reason_text"]


def test_valuation_question_is_refused_as_out_of_scope(corpus):
    result = draft(corpus, "14.40.377", question="What is this vase worth?")
    assert result["status"] == "refused"
    assert result["reason"] == "out_of_scope"
    assert result["label"] is None


def test_authenticity_question_is_refused_as_out_of_scope(corpus):
    result = draft(corpus, "14.40.377", question="Can you authenticate it for me?")
    assert result["reason"] == "out_of_scope"


def test_in_scope_question_still_drafts(corpus):
    result = draft(corpus, "14.40.377", question="Write a label for a student exhibition.")
    assert result["status"] == "drafted"


def test_every_refusal_states_a_reason_and_no_prose(corpus):
    for number in ("62.98.1", "09.13.5", "99.99.99"):
        result = draft(corpus, number)
        assert result["status"] == "refused"
        assert result["reason"]
        assert result["reason_text"]
        assert result["label"] is None
