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

    instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{instance.server_address[1]}"
    instance.shutdown()
    thread.join(timeout=5)
    server.PROVIDERS.clear()
    server.PROVIDERS.update(original)


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
