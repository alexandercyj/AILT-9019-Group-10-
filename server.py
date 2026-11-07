#!/usr/bin/env python3
"""Local server for the browser view.

The browser view is a convenience layer over the same Python pipeline the CLI
uses: it serves the static page, lists the frozen corpus, and runs
`labeldesk.draft` for the record the user picks. There is no second
implementation of the logic in JavaScript.

The model layer is reachable from the page through the same call, and only when
the page asks for it: `{"llm": "auto"}` means "use the model if a key is set,
otherwise replay the transcript". A page that never asks never calls out.

One endpoint reaches outside the frozen corpus: POST /api/fetch takes a museum
and an object ID, reads that one record from the museum's open API at request
time, and drafts it through the identical pipeline. The record is not added to
any corpus; it is fetched, drafted, and forgotten. The same guardrails apply —
a record missing a required field is refused, and the model layer is used only
when the page asks and the source register permits it.

A second endpoint, POST /api/search, takes a collection name instead of an ID:
it asks the museum's own search API for candidate object IDs, reads each one
through the same normaliser the frozen corpora were built with, and returns the
candidates without drafting anything. Drafting happens only when the page picks
a candidate, which goes through /api/fetch like any other live record.

    python3 server.py                        # http://127.0.0.1:8000
    python3 server.py --port 8080
    python3 server.py --corpus cleveland     # a registered alias, or a path
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse

from labeldesk import __version__, draft, load_corpus
from labeldesk.corpus import REQUIRED_FIELDS, Corpus
from labeldesk.llm import config_from_env, prompt_hash, resolve_mode
from labeldesk.net import ssl_context
from labeldesk.sources import aliases, provenance, resolve_corpus
from labeldesk.validate import missing_fields

from tools.fetch_corpus import PROVIDERS, normalise

ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}

# Set in main(); the handler reads it. One corpus per process, chosen at start-up,
# so the page cannot ask for records the process was not started with.
CORPUS = load_corpus()

DATA_DIR = ROOT / "data"

# Live fetch: one record from a museum's open API, drafted through the same
# pipeline as the frozen corpus. The field maps deliberately mirror the frozen
# corpora's registered maps, with one addition: a Met record is read culture-first
# and falls back to country, so any department works, not only the two that were
# frozen. The corpus name is the registered name for that source so provenance()
# and the ai_input policy resolve against data/sources.json exactly as they do
# for the frozen files. Nothing is written to disk; the response is the only
# place the record exists.
LIVE_PROVIDERS = {
    "met": {
        "name": "The Metropolitan Museum of Art",
        "corpus_name": "labeldesk-frozen-corpus",
        "registered_file": DATA_DIR / "frozen_corpus.json",
        "examples": [37251, 59842],
        "field_map": {
            "catalogue_number": "accessionNumber",
            "object_id": "objectID",
            "title": "title",
            "object_date": "objectDate",
            "medium": "medium",
            "place_or_culture": ["culture", "country"],
            "credit_line": "creditLine",
            "department": "department",
            "is_public_domain": "isPublicDomain",
            "source_url": "objectURL",
        },
    },
    "cleveland": {
        "name": "The Cleveland Museum of Art",
        "corpus_name": "labeldesk-cleveland-corpus",
        "registered_file": DATA_DIR / "frozen_corpus_cleveland.json",
        "examples": [130607, 149681],
        "field_map": {
            "catalogue_number": "accession_number",
            "object_id": "id",
            "title": "title",
            "object_date": "creation_date",
            "medium": "technique",
            "place_or_culture": "culture",
            "credit_line": "creditline",
            "department": "department",
            "is_public_domain": "share_license_status",
            "source_url": "url",
        },
    },
}


def live_provider_payload() -> list[dict]:
    """What the page needs to offer live fetch: names, endpoints, example IDs."""
    return [
        {
            "id": provider_id,
            "name": spec["name"],
            "endpoint": PROVIDERS[provider_id]["api"],
            "examples": spec["examples"],
        }
        for provider_id, spec in sorted(LIVE_PROVIDERS.items())
    ]


# Name search: each museum exposes its own search API, so each provider gets a
# searcher that returns raw candidate records. The Met search endpoint answers
# with object IDs only (the Solr-backed v1 endpoint was retired on 2026-10-01;
# v1.1 keeps the same response shape), so each candidate needs its own object
# GET. Cleveland returns full records in one request. Searchers are module
# level so tests can monkeypatch them the way they monkeypatch PROVIDERS.
def search_met(query: str, limit: int) -> list[dict]:
    """Candidate Met records for a name: one search call, then one GET per ID."""
    url = (
        "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
        "?hasImages=true&q=" + _quote(query)
    )
    payload = _get_json(url)
    records = []
    for object_id in (payload.get("objectIDs") or [])[:limit]:
        time.sleep(PROVIDERS["met"]["pause"])
        records.append(PROVIDERS["met"]["fetch"](object_id))
    return records


def search_cleveland(query: str, limit: int) -> list[dict]:
    """Candidate Cleveland records for a name: one request returns them all."""
    url = (
        "https://openaccess-api.clevelandart.org/api/artworks/"
        f"?cc0=1&has_image=1&limit={limit}&q={_quote(query)}"
    )
    return _get_json(url).get("data") or []


def _get_json(url: str) -> dict:
    """One GET that expects JSON, with the same timeout and TLS care as fetch."""
    request = urllib.request.Request(url, headers={"User-Agent": "LabelDesk-AILT9019/1.1"})
    with urllib.request.urlopen(request, timeout=30, context=ssl_context()) as response:
        return json.load(response)


def _quote(text: str) -> str:
    return quote(text, safe="")


SEARCHERS = {
    "met": search_met,
    "cleveland": search_cleveland,
}


def search_and_normalise(provider: str, query: str, limit: int) -> dict:
    """Run one museum search, normalise the candidates, and hand them to the page.

    Nothing here drafts a label and nothing is stored: the candidates exist only
    in this response. Records the museum returns without a title are dropped as
    noise — a draft of a title-less record is refused anyway, so showing it as a
    candidate would only offer a dead end.
    """
    spec = LIVE_PROVIDERS[provider]
    results = []
    for raw in SEARCHERS[provider](query, limit)[:limit]:
        record = normalise(raw, None, spec["field_map"], provider)
        if not str(record.get("title") or "").strip():
            continue
        results.append({**record, "missing": missing_fields(record)})
    return {
        "provider": provider,
        "provider_name": spec["name"],
        "query": query,
        "results": results,
    }


def fetch_and_draft(provider: str, object_id: int, llm) -> dict:
    """Fetch one record live, then run the ordinary pipeline on it.

    The ephemeral corpus borrows the registered corpus name and file path of the
    matching frozen corpus so the source register (provenance, ai_input policy)
    applies unchanged. `path` is never read by draft(); it only satisfies the
    Corpus shape. The record is not stored anywhere.
    """
    spec = LIVE_PROVIDERS[provider]
    raw = PROVIDERS[provider]["fetch"](object_id)
    record = normalise(raw, None, spec["field_map"], provider)
    corpus = Corpus(
        meta={
            "name": spec["corpus_name"],
            "version": "live",
            "source": spec["name"],
            "source_api": PROVIDERS[provider]["api"],
            "license": "CC0 1.0 (public domain)",
            "fetched_at": date.today().isoformat(),
            "record_count": 1,
            "required_fields": list(REQUIRED_FIELDS),
            "field_map": spec["field_map"],
            "notes": "Fetched live at request time; not part of the frozen corpus.",
        },
        records=(record,),
        path=spec["registered_file"],
    )
    result = draft(corpus, record["catalogue_number"], llm=llm)
    return {
        "live": True,
        "provider": provider,
        "provider_name": spec["name"],
        "object_id": object_id,
        "fetched_at": corpus.meta["fetched_at"],
        "record": record,
        "result": result,
    }


def corpus_payload() -> dict:
    return {
        "labeldesk_version": __version__,
        "corpus": {
            "name": CORPUS.meta["name"],
            "version": CORPUS.meta["version"],
            "source": CORPUS.meta["source"],
            "license": CORPUS.meta["license"],
            "record_count": len(CORPUS),
            "checksum": CORPUS.checksum,
            "fetched_at": CORPUS.meta["fetched_at"],
        },
        "provenance": provenance(CORPUS),
        "corpora": sorted(aliases()),
        "live_providers": live_provider_payload(),
        "records": [
            {
                **record,
                "missing": missing_fields(record),
            }
            for record in CORPUS.records
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"LabelDesk/{__version__}"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            body = (ROOT / filename).read_bytes()
            return self._send(200, body, content_type)

        if path == "/api/records":
            return self._json(200, corpus_payload())

        if path == "/api/llm":
            config = config_from_env()
            return self._json(
                200,
                {
                    "model": config.model,
                    "base_url": config.base_url,
                    "has_key": config.has_key,
                    "default_mode": resolve_mode("auto", config),
                    "prompt_sha256": prompt_hash(),
                },
            )

        if path.startswith("/api/record/"):
            number = unquote(path[len("/api/record/") :])
            record = CORPUS.get(number)
            if record is None:
                return self._json(404, {"error": "out_of_corpus", "catalogue_number": number})
            return self._json(200, {**record, "missing": missing_fields(record)})

        self._json(404, {"error": "not_found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in ("/api/draft", "/api/fetch", "/api/search"):
            return self._json(404, {"error": "not_found", "path": path})

        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad_json"})

        # Only an explicit request reaches the model; the default stays offline.
        llm = payload.get("llm")
        if llm not in (None, False, "auto", "live", "replay"):
            return self._json(400, {"error": "bad_llm_mode", "got": llm})

        if path == "/api/fetch":
            return self._fetch(payload, llm)

        if path == "/api/search":
            return self._search(payload)

        number = str(payload.get("catalogue_number", "")).strip()
        if not number:
            return self._json(400, {"error": "catalogue_number_required"})

        result = draft(CORPUS, number, question=payload.get("question"), llm=llm)
        return self._json(200, result)

    def _fetch(self, payload: dict, llm) -> None:
        """One live record from a museum's open API, drafted by the same pipeline."""
        provider = str(payload.get("provider", "")).strip().casefold()
        if provider not in LIVE_PROVIDERS:
            return self._json(
                400,
                {"error": "bad_provider", "got": provider, "expected": sorted(LIVE_PROVIDERS)},
            )
        try:
            object_id = int(str(payload.get("object_id", "")).strip())
        except ValueError:
            return self._json(400, {"error": "bad_object_id", "got": payload.get("object_id")})
        if not 1 <= object_id <= 999_999_999:
            return self._json(400, {"error": "bad_object_id", "got": object_id})

        try:
            body = fetch_and_draft(provider, object_id, llm)
        except HTTPError as error:
            return self._json(502, {"error": "upstream_http", "status": error.code})
        except (URLError, TimeoutError, OSError) as error:
            return self._json(502, {"error": "upstream_unreachable", "detail": str(error)[:200]})
        return self._json(200, body)

    def _search(self, payload: dict) -> None:
        """Candidates for a collection name, from a museum's own search API.

        No drafting happens here and the model layer is never called: the page
        drafts a candidate only after picking one, through /api/fetch.
        """
        provider = str(payload.get("provider", "")).strip().casefold()
        if provider not in LIVE_PROVIDERS:
            return self._json(
                400,
                {"error": "bad_provider", "got": provider, "expected": sorted(LIVE_PROVIDERS)},
            )
        query = str(payload.get("name", "")).strip()
        if not query:
            return self._json(400, {"error": "name_required"})
        try:
            limit = min(max(int(payload.get("limit", 4)), 1), 6)
        except (TypeError, ValueError):
            limit = 4

        try:
            body = search_and_normalise(provider, query, limit)
        except HTTPError as error:
            return self._json(502, {"error": "upstream_http", "status": error.code})
        except (URLError, TimeoutError, OSError) as error:
            return self._json(502, {"error": "upstream_unreachable", "detail": str(error)[:200]})
        return self._json(200, body)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"  {self.address_string()} {fmt % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Label Desk browser view.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--corpus", metavar="ALIAS_OR_PATH", help="a registered alias (primary, egyptian, cleveland) or a path"
    )
    args = parser.parse_args()

    global CORPUS
    CORPUS = load_corpus(resolve_corpus(args.corpus))

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    prov = provenance(CORPUS)
    print(f"Label Desk {__version__} · {len(CORPUS)} records · sha256 {CORPUS.short_checksum}")
    print(f"Corpus  {CORPUS.meta['name']} · source {prov.get('id') or 'unregistered'} · ai_input {'yes' if prov.get('ai_input') else 'no'}")
    live = " · ".join(f"{p['name']} ({p['id']})" for p in live_provider_payload())
    print(f"Live    one-record fetch from {live}")
    print(f"Serving http://{args.host}:{args.port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
