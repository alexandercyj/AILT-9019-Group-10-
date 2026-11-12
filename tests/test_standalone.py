"""The standalone file must be the pipeline's own output, and must not be stale.

`labeldesk.html` is the artefact someone opens without a checkout, a Python
interpreter or a server. That makes it the easiest thing in the repository to let rot:
nothing in the normal test path reads it.

So these tests read it, and they assert the one property that makes it trustworthy —
that every label, claim, citation and check in the file is what `labeldesk.draft()`
returns right now, not what it returned when the file was last built. A change to the
renderer, the grounding rules or the prompt fails here until the file is rebuilt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_standalone as builder  # noqa: E402

from labeldesk import load_corpus  # noqa: E402
from labeldesk.llm import prompt_hash  # noqa: E402
from labeldesk.pipeline import OUT_OF_SCOPE_TERMS, REASON_TEXT, draft  # noqa: E402
from labeldesk.sources import aliases, sources  # noqa: E402

HTML = ROOT / "labeldesk.html"
DATA_PATTERN = re.compile(
    r'<script type="application/json" id="labeldesk-data">\n(.*?)\n\s*</script>', re.S
)


@pytest.fixture(scope="module")
def html() -> str:
    assert HTML.exists(), "labeldesk.html is missing; run python3 tools/build_standalone.py"
    return HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def payload(html) -> dict:
    match = DATA_PATTERN.search(html)
    assert match, "the data block is missing or malformed"
    return json.loads(match.group(1).replace("<\\/", "</"))


@pytest.fixture(scope="module")
def markup(html) -> str:
    """The page without its data block, for checking what the browser is told to load."""
    return DATA_PATTERN.sub("", html)


# --------------------------------------------------------------------------- #
# it is one file, and it opens
# --------------------------------------------------------------------------- #


def test_the_file_exists_and_is_a_single_document(html):
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert html.count("<html") == 1
    assert html.count("</html>") == 1


def test_the_reader_interface_is_english(markup):
    assert '<html lang="en">' in markup
    assert not re.search(r"[\u3400-\u9fff]", markup)


def test_no_code_is_loaded_from_outside(markup):
    """No external code assets; disclosed museum images may still use HTTPS."""
    assert not re.search(r'<link[^>]+rel="stylesheet"', markup)
    assert not re.search(r"<script[^>]+\bsrc=", markup)
    assert "fetch(" not in markup
    assert "XMLHttpRequest" not in markup
    assert "@import" not in markup


def test_the_styles_are_inlined(html):
    assert "--green" in html, "styles.css was not inlined"
    assert ".corpus-tab" in html, "standalone.css was not inlined"


def test_the_data_block_is_parseable_and_complete(payload):
    assert set(payload) == {"meta", "corpora"}
    assert payload["meta"]["labeldesk_version"]
    assert len(payload["corpora"]) >= 3


def test_the_page_does_not_reference_a_server(html):
    assert "/api/draft" not in html
    assert "127.0.0.1" not in html


# --------------------------------------------------------------------------- #
# every label is the pipeline's own
# --------------------------------------------------------------------------- #


def test_every_registered_corpus_is_embedded(payload):
    embedded = {entry["alias"] for entry in payload["corpora"]}
    assert embedded == set(aliases())


def test_every_record_has_both_results(payload):
    for entry in payload["corpora"]:
        numbers = {record["catalogue_number"] for record in entry["records"]}
        assert set(entry["results"]) == numbers, entry["alias"]
        for number, bundle in entry["results"].items():
            assert set(bundle) == {"offline", "replay"}, number


def test_the_embedded_offline_results_match_a_fresh_run(payload):
    """The whole point of the file: a label here is a label the CLI prints."""
    for entry in payload["corpora"]:
        corpus = load_corpus(aliases()[entry["alias"]])
        for record in corpus.records:
            number = record["catalogue_number"]
            fresh = {k: v for k, v in draft(corpus, number).items() if k not in ("record", "provenance")}
            assert entry["results"][number]["offline"] == fresh, f"{entry['alias']}/{number}"


def test_the_embedded_rewrites_match_a_fresh_replay(payload):
    for entry in payload["corpora"]:
        corpus = load_corpus(aliases()[entry["alias"]])
        for record in corpus.records:
            number = record["catalogue_number"]
            fresh = {
                k: v
                for k, v in draft(corpus, number, llm="replay").items()
                if k not in ("record", "provenance")
            }
            assert entry["results"][number]["replay"] == fresh, f"{entry['alias']}/{number}"


def test_the_checks_embedded_are_the_checks_that_ran(payload):
    """A spot check with named expectations, so a silent all-green cannot pass."""
    primary = next(entry for entry in payload["corpora"] if entry["alias"] == "primary")
    drafted = primary["results"]["14.40.377"]["offline"]
    assert drafted["status"] == "drafted"
    assert drafted["checks"]["passed"] is True
    assert drafted["checks"]["claim_precision"] == 1.0
    assert len(drafted["claims"]) == 5

    refused = primary["results"]["62.98.1"]["offline"]
    assert refused["status"] == "refused"
    assert refused["reason"] == "missing_required_field"
    assert refused["label"] is None
    assert refused["checks"] is None


def test_the_second_museum_keeps_its_hedge(payload):
    cleveland = next(entry for entry in payload["corpora"] if entry["alias"] == "cleveland")
    assert "c. 1160–1170" in cleveland["results"]["1926.428"]["offline"]["label"]


def test_at_least_one_rewrite_is_embedded_as_discarded(payload):
    """If the file only ever showed accepted rewrites, it would be hiding the fallback."""
    discarded = [
        (entry["alias"], number)
        for entry in payload["corpora"]
        for number, bundle in entry["results"].items()
        if (bundle["replay"].get("llm") or {}).get("requested")
        and not bundle["replay"]["llm"]["applied"]
    ]
    assert discarded, "no discarded rewrite is embedded, so the page cannot show one"


# --------------------------------------------------------------------------- #
# the small things the page computes for itself
# --------------------------------------------------------------------------- #


def test_the_out_of_scope_terms_are_copied_not_retyped(payload):
    """The page tests questions against this list, so it must be the real one."""
    assert payload["meta"]["out_of_scope_terms"] == list(OUT_OF_SCOPE_TERMS)


def test_the_refusal_wording_is_the_pipelines_own(payload):
    assert payload["meta"]["reason_text"] == dict(REASON_TEXT)


def test_the_reason_templates_need_only_the_values_the_page_has(payload):
    """A template asking for a key the page does not supply would render literally."""
    corpus = next(entry for entry in payload["corpora"] if entry["alias"] == "primary")
    available = {"catalogue_number", "count", "term", "missing"}
    for name, template in payload["meta"]["reason_text"].items():
        keys = set(re.findall(r"\{(\w+)\}", template))
        assert keys <= available, f"{name} needs {keys - available}"
    assert corpus["corpus"]["record_count"] > 0


def test_the_source_register_is_embedded(payload):
    embedded = payload["meta"]["sources"]
    assert [entry["id"] for entry in embedded] == [entry["id"] for entry in sources()]
    refused = [entry["id"] for entry in embedded if entry["decision"]["status"] == "refused"]
    assert "british-museum" in refused and "palace-museum" in refused


def test_the_prompt_hash_travels_with_the_file(payload):
    assert payload["meta"]["prompt_sha256"] == prompt_hash()


# --------------------------------------------------------------------------- #
# the file is reproducible
# --------------------------------------------------------------------------- #


def test_a_rebuild_is_byte_identical(html):
    """No timestamp, no set ordering: a stale file is a content change, not a rebuild."""
    assert builder.build() == html, "labeldesk.html is stale; rebuild with tools/build_standalone.py"


def test_the_file_is_small_enough_to_open(html):
    size = len(html.encode("utf-8"))
    assert size < 700_000, f"{size / 1024:.0f} KiB is larger than this artefact should be"
