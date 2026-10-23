"""Label Desk: cited, plain-language exhibition labels from one frozen corpus.

Core path, standard library only:

    record -> validate -> fact sheet -> deterministic renderer -> grounding check
                                                                   |
                                                        drafted | refused
"""

from __future__ import annotations

__version__ = "1.0.0"

from .corpus import Corpus, load_corpus  # noqa: E402
from .pipeline import draft  # noqa: E402

__all__ = ["Corpus", "load_corpus", "draft", "__version__"]
