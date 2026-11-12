#!/usr/bin/env python3
"""Build labeldesk.html: one file, no server, no network, nothing to install.

The served browser view (`server.py` + `app.js`) calls the Python pipeline over HTTP.
That is the right shape for the project but the wrong shape for handing someone a
result: it needs a checkout and a process. This script produces the other shape.

The rule it has to respect is that there is one implementation. So this does not port
the renderer or the checks to JavaScript. It runs the real pipeline over every record
in every corpus, in both modes, and writes the results into the page as data. The page
looks them up. A label on that page is a label `python3 -m labeldesk` prints, byte for
byte, because it is the same function's output.

What the page does compute is two lookups, both of which are membership tests over
data embedded here: is this catalogue number in this corpus, and does this question
contain one of the out-of-scope terms. The term list and the refusal wording are
copied out of `labeldesk.pipeline` rather than retyped, so the page cannot drift into
a slightly different refusal than the CLI's.

Each embedded result is the pipeline's result with `record` and `provenance` hoisted
to the corpus level, where they are identical for every record and would otherwise be
repeated forty times.

Usage:
    python3 tools/build_standalone.py            # writes labeldesk.html
    python3 tools/build_standalone.py --check    # rebuild to a temp file, diff
    python3 tools/build_standalone.py --out /tmp/labeldesk.html

No network, no key, no timestamp: the output is byte-reproducible, so `--check` is a
real test rather than a same-day coincidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from labeldesk import __version__, load_corpus  # noqa: E402
from labeldesk.llm import prompt_hash, config_from_env  # noqa: E402
from labeldesk.pipeline import OUT_OF_SCOPE_TERMS, REASON_TEXT, draft  # noqa: E402
from labeldesk.sources import aliases, provenance, sources  # noqa: E402
from labeldesk.validate import missing_fields  # noqa: E402

TEMPLATE = ROOT / "standalone" / "template.html"
EXTRA_CSS = ROOT / "standalone" / "standalone.css"
SCRIPT = ROOT / "standalone" / "standalone.js"
BASE_CSS = ROOT / "styles.css"
OUTPUT = ROOT / "labeldesk.html"

# Fields the page reads off a record. Everything else in the corpus record stays out
# of the file: the page has no use for it and the file is meant to be openable.
RECORD_FIELDS = (
    "catalogue_number",
    "object_id",
    "title",
    "object_date",
    "medium",
    "place_or_culture",
    "credit_line",
    "department",
    "source_url",
    "image_url",
    "image_thumbnail",
)


def trim_result(result: dict) -> dict:
    """The pipeline's result, minus the two blocks the corpus already carries."""
    return {key: value for key, value in result.items() if key not in ("record", "provenance")}


def collect() -> dict:
    corpora = []
    for alias, path in sorted(aliases().items()):
        corpus = load_corpus(path)
        results = {}
        for record in corpus.records:
            number = record["catalogue_number"]
            results[number] = {
                "offline": trim_result(draft(corpus, number)),
                "replay": trim_result(draft(corpus, number, llm="replay")),
            }
        corpora.append(
            {
                "alias": alias,
                "corpus": {
                    "name": corpus.meta["name"],
                    "version": corpus.meta["version"],
                    "source": corpus.meta["source"],
                    "license": corpus.meta["license"],
                    "fetched_at": corpus.meta["fetched_at"],
                    "record_count": len(corpus),
                    "checksum": corpus.checksum,
                },
                "provenance": provenance(corpus),
                "records": [
                    {**{field: record.get(field, "") for field in RECORD_FIELDS},
                     "missing": missing_fields(record)}
                    for record in corpus.records
                ],
                "results": results,
            }
        )

    return {
        "meta": {
            "labeldesk_version": __version__,
            "prompt_sha256": prompt_hash(),
            "model": config_from_env().model,
            "out_of_scope_terms": list(OUT_OF_SCOPE_TERMS),
            "reason_text": dict(REASON_TEXT),
            "sources": sources(),
        },
        "corpora": corpora,
    }


def build() -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    css = (BASE_CSS.read_text(encoding="utf-8") + "\n\n" + EXTRA_CSS.read_text(encoding="utf-8")).strip()
    script = SCRIPT.read_text(encoding="utf-8").strip()

    # Compact, not indented: the block is parsed, never read by a person, and the
    # indentation alone doubles the file. The same data, indented, is in
    # eval/reports/cross_corpus.json for anyone who wants to inspect it.
    payload = json.dumps(collect(), ensure_ascii=False, separators=(",", ":"))
    # A JSON string may escape "/" as "\/", which keeps a "</script>" inside a record
    # from closing the data block. JSON.parse reads both forms identically.
    payload = payload.replace("</", "<\\/")

    for marker, value in (
        ("/*INLINE:CSS*/", css),
        ("/*INLINE:DATA*/", payload),
        ("/*INLINE:JS*/", script),
    ):
        if marker not in template:
            raise SystemExit(f"template is missing the {marker} marker")
        template = template.replace(marker, value)
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="compare a fresh build with the shipped file")
    args = parser.parse_args()

    html = build()
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()

    if args.check:
        if not args.out.exists():
            print(f"{args.out.name} does not exist; run without --check", file=sys.stderr)
            return 1
        same = args.out.read_text(encoding="utf-8") == html
        print(f"sha256 {digest}")
        print("shipped file matches a fresh build" if same else "DIFFERENT: the shipped file is stale")
        return 0 if same else 1

    args.out.write_text(html, encoding="utf-8")
    size = len(html.encode("utf-8"))
    print(f"wrote {args.out.name} · {size / 1024:.0f} KiB · sha256 {digest[:16]}")
    print(f"open it directly: file://{args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
