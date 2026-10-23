"""Loading and checksum verification for the frozen corpus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "data" / "frozen_corpus.json"

# The five fields the label may cite. A record missing any of them is refused.
REQUIRED_FIELDS: tuple[str, ...] = (
    "title",
    "object_date",
    "medium",
    "place_or_culture",
    "credit_line",
)

# Human wording used in refusals and in the printed citation list.
FIELD_LABELS: dict[str, str] = {
    "title": "title",
    "object_date": "object date",
    "medium": "medium",
    "place_or_culture": "place or culture",
    "credit_line": "credit line",
}


def file_checksum(path: Path | str) -> str:
    """SHA-256 of the corpus file exactly as it sits on disk."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Corpus:
    """The frozen record set, indexed by catalogue number."""

    meta: dict
    records: tuple[dict, ...]
    path: Path

    @property
    def checksum(self) -> str:
        return file_checksum(self.path)

    @property
    def short_checksum(self) -> str:
        return self.checksum[:12]

    def __len__(self) -> int:
        return len(self.records)

    def get(self, catalogue_number: str) -> dict | None:
        """Look a record up by catalogue number, ignoring case and spacing."""
        key = _key(catalogue_number)
        for record in self.records:
            if _key(record.get("catalogue_number", "")) == key:
                return record
        return None

    def catalogue_numbers(self) -> list[str]:
        return [record["catalogue_number"] for record in self.records]


def _key(value: str) -> str:
    return "".join(str(value).split()).casefold()


def load_corpus(path: Path | str | None = None) -> Corpus:
    """Read the frozen corpus from disk. No network access, ever."""
    target = Path(path) if path else DEFAULT_CORPUS
    payload = json.loads(target.read_text(encoding="utf-8"))
    records = tuple(payload["records"])
    if not records:
        raise ValueError(f"corpus at {target} contains no records")
    return Corpus(meta=payload["corpus"], records=records, path=target)
