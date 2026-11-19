"""The local server: static files, the frozen-corpus API, and live fetch.

The handler is tested over real HTTP on an ephemeral port, with the museum
providers monkeypatched so no test touches the network. The point of each test
is the contract the page relies on: the shape of /api/records, the refusal
statuses from /api/draft, and the rule that /api/fetch runs the same pipeline on
an outside record — grounded, checked, and policy-gated like any other draft.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from io import BytesIO

import pytest

import server

MET_RAW = {
    "objectID": 436535,
    "accessionNumber": "64.165",
    "title": "Self-Portrait with a Straw Hat",
    "objectDate": "1887",
    "medium": "Oil on canvas",
    "culture": "",
    "country": "Netherlands",
    "creditLine": "Bequest of Miss Adelaide Milton de Groot (1876-1967), 1967",
    "department": "European Paintings",
    "isPublicDomain": True,
    "objectURL": "https://www.metmuseum.org/art/collection/search/436535",
    "primaryImage": "https://images.metmuseum.org/full.jpg",
    "primaryImageSmall": "https://images.metmuseum.org/small.jpg",
}

CLEVELAND_RAW = {
    "id": 130607,
    "accession_number": "1944.479",
    "title": "The Burning of the Houses of Parliament",
    "creation_date": "c. 1835",
    "technique": "oil on canvas",
    "culture": ["England"],
    "creditline": "Bequest of John L. Severance",
    "department": "European Painting and Sculpture",
    "share_license_status": "CC0",
    "url": "https://www.clevelandart.org/art/1944.479",
    "images": {
        "web": {"url": "https://media.clevelandart.org/web.jpg"},
        "full": {"url": "https://media.clevelandart.org/full.jpg"},
    },
}

MET_INCOMPLETE_RAW = {
    "objectID": 1,
    "accessionNumber": "00.0.1",
    "title": "Fragment",
    "objectDate": "",
    "medium": "Stone",
    "culture": "Egypt",
    "creditLine": "Gift of X",
    "department": "Egyptian Art",
    "isPublicDomain": True,
    "objectURL": "https://example.invalid/1",
}


def _payload_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _request(url: str, payload: dict | None = None) -> tuple[int, object]:
    """POST (or GET, when payload is None). JSON body parsed when possible."""
    data = None if payload is None else _payload_bytes(payload)
    request = urllib.request.Request(url, data=data, method="GET" if payload is None else "POST")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


@pytest.fixture(scope="module")
def httpd():
    """The real server on an ephemeral port, providers monkeypatched offline."""
    server.CORPUS = server.load_corpus()
    original = dict(server.PROVIDERS)

    def fake_met(oid: int):
        if oid == 404000:
            raise urllib.error.HTTPError(
                "https://example.invalid", 404, "not found", {}, BytesIO(b"")
            )
        if oid == 1:
            return MET_INCOMPLETE_RAW
        return MET_RAW

    def fake_cleveland(oid: int):
        return CLEVELAND_RAW

    server.PROVIDERS["met"] = {**original["met"], "fetch": fake_met}
    server.PROVIDERS["cleveland"] = {**original["cleveland"], "fetch": fake_cleveland}

    # Name search is monkeypatched the same way: the searchers return raw
    # candidate records and the endpoint normalises them through the live maps.
    def fake_search_met(query: str, limit: int):
        return [MET_RAW, MET_INCOMPLETE_RAW, {"objectID": 2, "title": ""}]

    def fake_search_cleveland(query: str, limit: int):
        return [CLEVELAND_RAW]

    original_searchers = dict(server.SEARCHERS)
    server.SEARCHERS["met"] = fake_search_met
    server.SEARCHERS["cleveland"] = fake_search_cleveland
    # The Met searcher sleeps between object GETs; a fake must not.
    server.PROVIDERS["met"] = {**server.PROVIDERS["met"], "pause": 0}

    server.ALLOW_RESEARCH = True
    server.ALLOW_LIVE = False
    instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{instance.server_address[1]}"
    instance.shutdown()
    thread.join(timeout=5)
    server.PROVIDERS.clear()
    server.PROVIDERS.update(original)
    server.SEARCHERS.clear()
    server.SEARCHERS.update(original_searchers)
    server.ALLOW_RESEARCH = False
    server.ALLOW_LIVE = False


# --------------------------------------------------------------------------- #
# static and frozen-corpus endpoints
# --------------------------------------------------------------------------- #


def test_index_and_static_serve(httpd):
    for path in ("/", "/index.html", "/styles.css", "/app.js"):
        status, _ = _request(f"{httpd}{path}")
        assert status == 200, path


def test_records_payload_lists_live_providers(httpd):
    status, body = _request(f"{httpd}/api/records")
    assert status == 200
    assert body["corpus"]["record_count"] == len(body["records"])
    providers = {p["id"]: p for p in body["live_providers"]}
    assert set(providers) == {"met", "cleveland"}
    assert providers["met"]["examples"], "the page needs example IDs to offer"


def test_draft_drafted_and_refused(httpd):
    status, body = _request(f"{httpd}/api/draft", {"catalogue_number": "14.40.377"})
    assert status == 200
    assert body["status"] == "drafted"
    assert body["checks"]["passed"] is True

    status, body = _request(f"{httpd}/api/draft", {"catalogue_number": "99.99.99"})
    assert status == 200
    assert body["status"] == "refused"
    assert body["reason"] == "out_of_corpus"


def test_draft_question_refusal(httpd):
    status, body = _request(
        f"{httpd}/api/draft",
        {"catalogue_number": "14.40.377", "question": "what is it worth?"},
    )
    assert status == 200
    assert body["status"] == "refused"
    assert body["reason"] == "out_of_scope"


def test_draft_validates_input(httpd):
    status, body = _request(f"{httpd}/api/draft", {})
    assert status == 400
    assert body["error"] == "catalogue_number_required"

    status, body = _request(f"{httpd}/api/draft", {"catalogue_number": "14.40.377", "llm": "sideways"})
    assert status == 400
    assert body["error"] == "bad_llm_mode"


# --------------------------------------------------------------------------- #
# live fetch: outside records through the same pipeline
# --------------------------------------------------------------------------- #


def test_fetch_met_record_drafts(httpd):
    status, body = _request(f"{httpd}/api/fetch", {"provider": "met", "object_id": 436535})
    assert status == 200
    assert body["live"] is True
    assert body["provider"] == "met"

    record = body["record"]
    # culture is blank on this record; the live map must fall back to country.
    assert record["place_or_culture"] == "Netherlands"
    assert record["catalogue_number"] == "64.165"

    result = body["result"]
    assert result["status"] == "drafted"
    assert result["checks"]["passed"] is True
    # The record came from outside, so the provenance must still name its source.
    assert result["provenance"]["id"] == "met"
    assert result["provenance"]["ai_input"] is True


def test_fetch_cleveland_record_drafts(httpd):
    status, body = _request(f"{httpd}/api/fetch", {"provider": "cleveland", "object_id": 130607})
    assert status == 200
    assert body["record"]["place_or_culture"] == "England"
    result = body["result"]
    assert result["status"] == "drafted"
    assert result["checks"]["passed"] is True
    assert result["provenance"]["id"] == "cleveland"


def test_fetch_incomplete_record_is_refused_not_filled(httpd):
    """An outside record with a blank date must hit the same refusal as a frozen one.

    The fixture's Met provider returns MET_INCOMPLETE_RAW for object ID 1.
    """
    status, body = _request(f"{httpd}/api/fetch", {"provider": "met", "object_id": 1})
    assert status == 200
    result = body["result"]
    assert result["status"] == "refused"
    assert result["reason"] == "missing_required_field"
    assert result["missing_fields"] == ["object_date"]
    assert result["label"] is None


def test_fetch_validates_input(httpd):
    status, body = _request(f"{httpd}/api/fetch", {"provider": "louvre", "object_id": 1})
    assert status == 400
    assert body["error"] == "bad_provider"

    status, body = _request(f"{httpd}/api/fetch", {"provider": "met", "object_id": "abc"})
    assert status == 400
    assert body["error"] == "bad_object_id"


def test_fetch_upstream_error_is_reported(httpd):
    status, body = _request(f"{httpd}/api/fetch", {"provider": "met", "object_id": 404000})
    assert status == 502
    assert body["error"] == "upstream_http"
    assert body["status"] == 404


# --------------------------------------------------------------------------- #
# name search: candidates without drafting
# --------------------------------------------------------------------------- #


def test_search_returns_normalised_candidates(httpd):
    status, body = _request(f"{httpd}/api/search", {"provider": "met", "name": "straw hat"})
    assert status == 200
    assert body["provider"] == "met"
    assert body["query"] == "straw hat"
    assert len(body["results"]) == 2, "the title-less candidate is dropped as noise"

    record = body["results"][0]
    assert record["catalogue_number"] == "64.165"
    # culture is blank on this record; the live map must fall back to country.
    assert record["place_or_culture"] == "Netherlands"
    assert record["source_url"].startswith("https://www.metmuseum.org/")

    incomplete = body["results"][1]
    assert incomplete["missing"] == ["object_date"], "incompleteness is reported, never filled"


def test_search_cleveland_candidates(httpd):
    status, body = _request(f"{httpd}/api/search", {"provider": "cleveland", "name": "parliament"})
    assert status == 200
    assert body["provider_name"] == "The Cleveland Museum of Art"
    assert body["results"][0]["title"] == "The Burning of the Houses of Parliament"


def test_search_validates_input(httpd):
    status, body = _request(f"{httpd}/api/search", {"provider": "louvre", "name": "x"})
    assert status == 400
    assert body["error"] == "bad_provider"

    status, body = _request(f"{httpd}/api/search", {"provider": "met", "name": "   "})
    assert status == 400
    assert body["error"] == "name_required"


def test_search_upstream_error_is_reported(httpd):
    """A search API that 503s must surface as upstream_http, not as no results."""
    def failing_search(query: str, limit: int):
        raise urllib.error.URLError("search api down")

    original = server.SEARCHERS["met"]
    server.SEARCHERS["met"] = failing_search
    try:
        status, body = _request(f"{httpd}/api/search", {"provider": "met", "name": "straw hat"})
    finally:
        server.SEARCHERS["met"] = original
    assert status == 502
    assert body["error"] == "upstream_unreachable"


# --------------------------------------------------------------------------- #
# encyclopaedia search and cited web research
# --------------------------------------------------------------------------- #


def test_search_all_combines_museums_and_images(httpd):
    status, body = _request(f"{httpd}/api/search", {"provider": "all", "name": "portrait"})
    assert status == 200
    assert {record["provider"] for record in body["results"]} == {"met", "cleveland"}
    met = next(record for record in body["results"] if record.get("catalogue_number") == "64.165")
    assert met["image_thumbnail"] == "https://images.metmuseum.org/small.jpg"
    cleveland = next(record for record in body["results"] if record["provider"] == "cleveland")
    assert cleveland["image_thumbnail"] == "https://media.clevelandart.org/web.jpg"


def test_fetch_returns_open_images(httpd):
    status, body = _request(f"{httpd}/api/fetch", {"provider": "met", "object_id": 436535})
    assert status == 200
    assert body["record"]["image_url"] == "https://images.metmuseum.org/full.jpg"


def test_research_selected_record_uses_cache(httpd, monkeypatch):
    calls = []
    outcome = {
        "status": "ready", "title": "Self-Portrait", "lead": {"text": "Introduction", "citation_ids": [1]},
        "sections": [], "conclusion": {"text": "Explanation", "citation_ids": [1]},
        "sources": [{"id": 1, "title": "Museum", "url": "https://example.org/object", "domain": "example.org"}],
        "steps": [{"kind": "search", "title": "Web search", "detail": "self portrait"}],
    }
    def fake_research(query, record=None, *, provider_name=""):
        calls.append((query, record, provider_name))
        return outcome
    monkeypatch.setattr(server, "research", fake_research)
    server.RESEARCH_CACHE.clear()
    payload = {"provider": "met", "object_id": 436535, "query": "Self-Portrait with a Straw Hat"}
    first = _request(f"{httpd}/api/research", payload)
    second = _request(f"{httpd}/api/research", payload)
    assert first[0] == second[0] == 200
    assert first[1]["research"]["status"] == "ready"
    assert len(calls) == 1
    assert calls[0][1]["image_url"] == "https://images.metmuseum.org/full.jpg"
    server.RESEARCH_CACHE.clear()


def test_research_without_a_museum_match(httpd, monkeypatch):
    monkeypatch.setattr(server, "research", lambda *args, **kwargs: {
        "status": "unavailable", "reason": "no_sources", "message": "No verifiable sources found", "steps": [],
    })
    status, body = _request(f"{httpd}/api/research", {"query": "an otherwise unknown object"})
    assert status == 200
    assert body["record"] is None
    assert body["research"]["reason"] == "no_sources"


def test_research_refuses_valuation_before_calling_model(httpd, monkeypatch):
    called = False
    def fake_research(*args, **kwargs):
        nonlocal called
        called = True
    monkeypatch.setattr(server, "research", fake_research)
    status, body = _request(f"{httpd}/api/research", {"query": "what is it worth?"})
    assert status == 200
    assert body["research"]["status"] == "refused"
    assert called is False


def test_reader_page_has_no_debug_or_search_redirect_controls(httpd):
    for path in ("/", "/app.js"):
        status, raw = _request(f"{httpd}{path}")
        page = raw.decode("utf-8").casefold()
        assert status == 200
        if path == "/":
            assert "object encyclopedia" in page
        assert not any("\u3400" <= character <= "\u9fff" for character in page)
        for text in ("google", "sha256", "python3", "object id", "model rewrite", "four checks"):
            assert text not in page


def test_post_body_is_capped(httpd):
    import http.client
    from urllib.parse import urlparse

    parsed = urlparse(httpd)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    connection.request(
        "POST",
        "/api/draft",
        body=b"{}",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(server.MAX_BODY + 1),
        },
    )
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    assert response.status == 413
    assert json.loads(raw)["error"] == "body_too_large"


def test_llm_status_and_draft_do_not_expose_a_key(httpd, monkeypatch):
    monkeypatch.delenv("LABELDESK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status, body = _request(f"{httpd}/api/llm")
    assert status == 200
    assert set(body) == {
        "model", "base_url", "has_key", "default_mode", "prompt_sha256",
        "live_enabled", "research_enabled",
    }
    assert body["has_key"] is False
    assert body["live_enabled"] is False
    assert body["research_enabled"] is True
    status, drafted = _request(f"{httpd}/api/draft", {"catalogue_number": "14.40.377"})
    assert status == 200
    encoded = json.dumps(drafted)
    assert "api_key" not in encoded
    assert drafted["llm"]["has_key"] is False


def test_static_allowlist_rejects_escape(httpd):
    status, _ = _request(f"{httpd}/%2e%2e/server.py")
    assert status == 404
    status, _ = _request(f"{httpd}/export_pdf.applescript")
    assert status == 404


def test_research_without_a_key_stays_offline(httpd, monkeypatch):
    monkeypatch.delenv("LABELDESK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status, body = _request(f"{httpd}/api/research", {"query": "porcelain vase"})
    assert status == 200
    assert body["research"]["status"] == "unavailable"
    assert body["research"]["reason"] == "no_key"


def test_research_stays_off_until_the_server_allows_it(httpd, monkeypatch):
    called = False

    def explode(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("research was called")

    monkeypatch.setattr(server, "research", explode)
    server.ALLOW_RESEARCH = False
    try:
        status, body = _request(f"{httpd}/api/research", {"query": "porcelain vase"})
    finally:
        server.ALLOW_RESEARCH = True
    assert status == 200
    assert body["research"]["reason"] == "disabled"
    assert called is False


def test_live_draft_is_refused_unless_the_server_allows_it(httpd):
    server.ALLOW_LIVE = False
    status, body = _request(
        f"{httpd}/api/draft",
        {"catalogue_number": "14.40.377", "llm": "live"},
    )
    assert status == 403
    assert body["error"] == "live_disabled"


def test_search_page_does_not_start_research():
    text = (server.ROOT / "app.js").read_text(encoding="utf-8")
    search = text.split("async function searchObjects", 1)[1].split("function renderSearchResults", 1)[0]
    select = text.split("function selectRecord", 1)[1].split("function renderRecord", 1)[0]
    assert "researchWeb(" not in search
    assert "runResearch(" not in select


def test_non_public_domain_records_do_not_expose_images():
    raw = {**MET_RAW, "isPublicDomain": False}
    record = server.normalise(raw, None, server.LIVE_PROVIDERS["met"]["field_map"], "met")
    assert record["image_url"] == ""
    assert record["image_thumbnail"] == ""
