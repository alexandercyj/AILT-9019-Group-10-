#!/usr/bin/env python3
"""Local server for the browser view.

The browser view is a convenience layer over the same Python pipeline the CLI
uses: it serves the static page, lists the frozen corpus, and runs
`labeldesk.draft` for the record the user picks. There is no second
implementation of the logic in JavaScript.

The model layer is reachable from the page through the same call, and only when
the page asks for it: `{"llm": "auto"}` means "use the model if a key is set,
otherwise replay the transcript". A page that never asks never calls out.

    python3 server.py                        # http://127.0.0.1:8000
    python3 server.py --port 8080
    python3 server.py --corpus cleveland     # a registered alias, or a path
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from labeldesk import __version__, draft, load_corpus
from labeldesk.llm import config_from_env, prompt_hash, resolve_mode
from labeldesk.sources import aliases, provenance, resolve_corpus
from labeldesk.validate import missing_fields

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
        if path != "/api/draft":
            return self._json(404, {"error": "not_found", "path": path})

        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad_json"})

        number = str(payload.get("catalogue_number", "")).strip()
        if not number:
            return self._json(400, {"error": "catalogue_number_required"})

        # Only an explicit request reaches the model; the default stays offline.
        llm = payload.get("llm")
        if llm not in (None, False, "auto", "live", "replay"):
            return self._json(400, {"error": "bad_llm_mode", "got": llm})

        result = draft(CORPUS, number, question=payload.get("question"), llm=llm)
        return self._json(200, result)

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
