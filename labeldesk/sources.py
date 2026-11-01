"""The source register: where records came from, and what may be done with them.

Every corpus in this repository is listed in `data/sources.json` against the host it
came from. That file records three things the code needs and a README cannot enforce:

    robots    what the host publishes about automated access, with the HTTP status,
              a sha256 prefix of the body, and the verdict drawn from it
    license   the terms for the records, which are not the terms for the website
    policy    whether a record may be used as label input at all, and whether it may
              be sent to the model layer

The point of putting policy in code is that a licence then travels with the data. A
corpus whose source forbids `ai_input` cannot reach the model through `--llm`, no
matter which entry point is used, because the pipeline asks this module first. That is
the same posture as the rest of the project: a constraint that is checked, not a note
that is hoped for.

An **unregistered** corpus is treated as `ai_input: false`. Offline drafting still
works; the model layer does not, because there is no licence on file to justify it. A
person who wants the model path for their own records runs `tools/import_records.py`,
which registers the source and the licence the importer asserts.

Nothing here makes a network call. `tools/check_sources.py` is the command that
re-fetches each robots.txt and reports whether the register is still true.
"""

from __future__ import annotations

import json
from pathlib import Path

from .corpus import ROOT

REGISTER_PATH = ROOT / "data" / "sources.json"

# Applied to a corpus whose source is not in the register.
UNREGISTERED_POLICY = {
    "ai_input": False,
    "redistribute": False,
    "record_source": True,
    "notes": (
        "Corpus is not in data/sources.json, so no licence is on file. Offline "
        "drafting is allowed; the model layer is not."
    ),
}


def load_register(path: Path | str | None = None) -> dict:
    target = Path(path) if path else REGISTER_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def sources(path: Path | str | None = None) -> list[dict]:
    return load_register(path)["sources"]


def get_source(source_id: str, path: Path | str | None = None) -> dict | None:
    for source in sources(path):
        if source["id"] == source_id:
            return source
    return None


def source_for_corpus_name(name: str, path: Path | str | None = None) -> dict | None:
    """Find the source that produced a corpus, by the corpus's own `meta.name`."""
    for source in sources(path):
        for corpus in source.get("corpora", []):
            if corpus["name"] == name:
                return source
    return None


def source_for_corpus_file(file: Path | str, path: Path | str | None = None) -> dict | None:
    target = Path(file).resolve()
    for source in sources(path):
        for corpus in source.get("corpora", []):
            if (ROOT / corpus["file"]).resolve() == target:
                return source
    return None


def aliases(path: Path | str | None = None) -> dict[str, Path]:
    """Short names usable with `--corpus`, mapped to the frozen file."""
    table: dict[str, Path] = {}
    for source in sources(path):
        for corpus in source.get("corpora", []):
            table[corpus["alias"]] = ROOT / corpus["file"]
    return table


def resolve_corpus(value: str | Path | None, path: Path | str | None = None) -> Path | None:
    """`--corpus` accepts a registered alias or a filesystem path.

    An alias that is not registered is an error rather than a silent fallback to the
    default corpus: reading the wrong records is worse than stopping.
    """
    if value is None:
        return None
    text = str(value)
    table = aliases(path)
    if text in table:
        return table[text]
    candidate = Path(text)
    if candidate.exists():
        return candidate
    known = ", ".join(sorted(table))
    raise ValueError(f"unknown corpus {text!r}: not a registered alias ({known}) and not a file")


def policy_for_corpus(corpus, path: Path | str | None = None) -> tuple[dict | None, dict]:
    """Return (source, policy) for a loaded corpus. Unknown corpora get the safe default."""
    source = source_for_corpus_name(corpus.meta.get("name", ""), path)
    if source is None:
        return None, dict(UNREGISTERED_POLICY)
    return source, dict(source["policy"])


def ai_input_allowed(corpus, path: Path | str | None = None) -> tuple[bool, dict | None, dict]:
    source, policy = policy_for_corpus(corpus, path)
    return bool(policy.get("ai_input")), source, policy


def provenance(corpus, path: Path | str | None = None) -> dict:
    """The block the result carries so a reader can see where the records came from.

    For an unregistered corpus the licence is `None`, not whatever the corpus file
    says about itself. A file's own claim is not a licence on file; it is a claim,
    and it is reported separately so the difference is visible.
    """
    source, policy = policy_for_corpus(corpus, path)
    if source is None:
        return {
            "id": None,
            "name": corpus.meta.get("source", "unknown"),
            "license": None,
            "license_claimed": corpus.meta.get("license"),
            "registered": False,
            "ai_input": policy["ai_input"],
        }
    return {
        "id": source["id"],
        "name": source["name"],
        "license": source["license"]["id"],
        "homepage": source["homepage"],
        "registered": True,
        "ai_input": policy["ai_input"],
        "robots_verdict": source["robots"]["verdict"],
        "decision": source["decision"]["status"],
    }


def format_table(path: Path | str | None = None) -> str:
    """One row per source, for `--sources`."""
    rows = [
        ("SOURCE", "ROBOTS", "LICENCE", "AI", "DECISION"),
    ]
    for source in sources(path):
        rows.append(
            (
                source["id"],
                source["robots"]["verdict"],
                source["license"]["id"],
                "yes" if source["policy"]["ai_input"] else "no",
                source["decision"]["status"],
            )
        )
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    lines = [
        "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip()
        for row in rows
    ]
    lines.insert(1, "  ".join("-" * width for width in widths))
    return "\n".join(lines)


__all__ = [
    "REGISTER_PATH",
    "UNREGISTERED_POLICY",
    "ai_input_allowed",
    "aliases",
    "format_table",
    "get_source",
    "load_register",
    "policy_for_corpus",
    "provenance",
    "resolve_corpus",
    "source_for_corpus_file",
    "source_for_corpus_name",
    "sources",
]
