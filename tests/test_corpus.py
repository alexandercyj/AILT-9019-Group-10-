"""The corpus is frozen: same file, same checksum, same 20 records."""

from __future__ import annotations

from labeldesk.corpus import DEFAULT_CORPUS, REQUIRED_FIELDS, file_checksum, load_corpus


def test_corpus_loads_twenty_records():
    corpus = load_corpus()
    assert len(corpus) == 20
    assert corpus.meta["record_count"] == 20


def test_checksum_matches_sidecar_file():
    corpus = load_corpus()
    sidecar = (DEFAULT_CORPUS.parent / "frozen_corpus.sha256").read_text().split()[0]
    assert file_checksum(DEFAULT_CORPUS) == sidecar
    assert corpus.checksum == sidecar


def test_catalogue_numbers_are_unique_and_resolvable():
    corpus = load_corpus()
    numbers = corpus.catalogue_numbers()
    assert len(set(numbers)) == len(numbers)
    for number in numbers:
        assert corpus.get(number) is not None


def test_lookup_ignores_case_and_spacing():
    corpus = load_corpus()
    assert corpus.get("  1970.103a–e  ")["title"] == "Screen"
    assert corpus.get("14.40.377") is corpus.get("14.40.377")


def test_every_record_carries_the_five_fields():
    for record in load_corpus().records:
        for field in REQUIRED_FIELDS:
            assert field in record, f"{record['catalogue_number']} has no {field} key"


def test_unknown_catalogue_number_returns_none():
    assert load_corpus().get("99.99.99") is None
