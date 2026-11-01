"""The third corpus: a different museum, a different API, the same contract.

The proposal asks for a second department to show the pipeline is data-agnostic.
A second department is a weaker test than it looks: same museum, same API, same
record shape, same house style for dates. This corpus is a different museum with a
different API, and — the part that matters — dates phrased by someone else. The
team did not choose "c. 1050", "1100s" or "1800s, before 1896"; Cleveland did.

If the hedge rule only works on phrasings the team wrote, it is not a rule. These
tests are the check on that.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labeldesk import load_corpus
from labeldesk.corpus import REQUIRED_FIELDS, file_checksum
from labeldesk.pipeline import draft
from labeldesk.sources import ai_input_allowed, provenance

ROOT = Path(__file__).resolve().parents[1]
CLEVELAND = ROOT / "data" / "frozen_corpus_cleveland.json"
PRIMARY = ROOT / "data" / "frozen_corpus.json"


@pytest.fixture(scope="module")
def cleveland():
    return load_corpus(CLEVELAND)


@pytest.fixture(scope="module")
def primary():
    return load_corpus(PRIMARY)


def test_corpus_loads_with_its_own_metadata(cleveland):
    assert len(cleveland) == 10
    assert cleveland.meta["name"] == "labeldesk-cleveland-corpus"
    assert cleveland.meta["record_count"] == 10
    assert cleveland.meta["license"] == "CC0 1.0 (public domain)"
    assert "Cleveland" in cleveland.meta["source"]


def test_checksum_is_recorded_and_matches(cleveland):
    sidecar = CLEVELAND.with_suffix(".sha256")
    assert sidecar.exists(), "a frozen corpus ships with its checksum"
    recorded = sidecar.read_text(encoding="utf-8").split()[0]
    assert recorded == file_checksum(CLEVELAND)


def test_same_required_fields_as_every_other_corpus(cleveland, primary):
    assert tuple(cleveland.meta["required_fields"]) == REQUIRED_FIELDS
    assert tuple(primary.meta["required_fields"]) == REQUIRED_FIELDS


def test_the_field_map_is_clevelands_own(cleveland):
    """A second museum means a second set of API key names, not a second parser."""
    mapping = cleveland.meta["field_map"]
    assert mapping["object_date"] == "creation_date"
    assert mapping["medium"] == "technique"
    assert mapping["catalogue_number"] == "accession_number"
    # Met uses accessionNumber/objectDate/medium; nothing here is shared by luck.
    primary_map = json.loads(PRIMARY.read_text(encoding="utf-8"))["corpus"]["field_map"]
    assert mapping["object_date"] != primary_map["object_date"]


def test_every_record_drafts_cleanly(cleveland):
    for record in cleveland.records:
        result = draft(cleveland, record["catalogue_number"])
        assert result["status"] == "drafted", record["catalogue_number"]
        assert result["checks"]["passed"] is True, record["catalogue_number"]
        assert 60 <= result["word_count"] <= 80, record["catalogue_number"]
        assert len(result["claims"]) == 5
        assert result["checks"]["claim_precision"] == 1.0
        assert result["checks"]["citation_resolution_rate"] == 1.0


def test_records_are_all_cc0(cleveland):
    """The fetch filters on share_license_status; nothing closed-licence got in."""
    assert all(record["is_public_domain"] is True for record in cleveland.records)


def test_the_corpus_is_registered_and_may_reach_the_model(cleveland):
    allowed, source, policy = ai_input_allowed(cleveland)
    assert allowed is True
    assert source["id"] == "cleveland"
    assert source["license"]["id"] == "CC0-1.0"
    assert policy["ai_input"] is True
    assert provenance(cleveland)["robots_verdict"] == "allowed"


# --------------------------------------------------------------------------- #
# dates the team did not phrase
# --------------------------------------------------------------------------- #


def test_a_circa_date_keeps_its_hedge(cleveland):
    """'c. 1050' must not become '1050': the hedge is part of the record."""
    result = draft(cleveland, "1970.36")
    assert result["record"]["object_date"] == "c. 1050"
    assert "c. 1050" in result["label"]
    assert "1050" in result["label"]


def test_a_bare_range_survives(cleveland):
    """'400–700' is one value with an en dash, not two numbers to be joined."""
    result = draft(cleveland, "1939.509")
    assert result["record"]["object_date"] == "400–700"
    assert "400–700" in result["label"]
    assert result["checks"]["value_containment"]["passed"] is True


def test_a_century_style_date_is_copied_not_interpreted(cleveland):
    """'1100s' is the museum's wording. Expanding it to 'the twelfth century'
    would be an addition, however helpful."""
    result = draft(cleveland, "1973.85")
    assert result["record"]["object_date"] == "1100s"
    assert "1100s" in result["label"]


def test_a_qualified_date_keeps_its_qualifier(cleveland):
    result = draft(cleveland, "1935.310")
    assert result["record"]["object_date"] == "1800s, before 1896"
    assert "1800s, before 1896" in result["label"]


def test_a_hedged_range_keeps_both_ends(cleveland):
    result = draft(cleveland, "1926.428")
    assert result["record"]["object_date"] == "c. 1160–1170"
    assert "c. 1160–1170" in result["label"]


# --------------------------------------------------------------------------- #
# values with awkward shapes
# --------------------------------------------------------------------------- #


def test_a_list_shaped_culture_field_is_joined_not_edited(cleveland):
    """The API returns culture as a list; the fetch joins it with '; '."""
    result = draft(cleveland, "1935.310")
    place = result["record"]["place_or_culture"]
    assert "Asante Empire/Kingdom" in place
    assert place in result["label"]


def test_a_long_credit_line_does_not_push_the_label_over_the_band(cleveland):
    """Cleveland's credit lines can run to twenty words; the band still holds."""
    result = draft(cleveland, "1973.85")
    assert len(result["record"]["credit_line"].split()) > 15
    assert 60 <= result["word_count"] <= 80


def test_a_non_ascii_title_is_copied_verbatim(cleveland):
    result = draft(cleveland, "1935.310")
    assert "akrafokɔnmu" in result["label"]
    assert result["checks"]["value_containment"]["passed"] is True


# --------------------------------------------------------------------------- #
# independence from the other corpora
# --------------------------------------------------------------------------- #


def test_a_met_number_is_out_of_corpus_here(cleveland):
    result = draft(cleveland, "14.40.377")
    assert result["status"] == "refused"
    assert result["reason"] == "out_of_corpus"


def test_a_cleveland_number_is_out_of_corpus_in_the_primary(primary):
    result = draft(primary, "1970.36")
    assert result["status"] == "refused"
    assert result["reason"] == "out_of_corpus"


def test_the_result_shape_is_identical_across_museums(primary, cleveland):
    left = draft(primary, "14.40.377")
    right = draft(cleveland, "1970.36")
    assert set(left) == set(right)
    assert set(left["checks"]) == set(right["checks"])
    assert left["provenance"]["id"] != right["provenance"]["id"]


def test_no_personal_data_in_the_corpus(cleveland):
    payload = json.loads(CLEVELAND.read_text(encoding="utf-8"))
    forbidden = {"email", "address", "phone", "donor_contact", "birth"}
    for record in payload["records"]:
        assert not (forbidden & set(record))
