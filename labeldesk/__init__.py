"""Label Desk: cited, plain-language exhibition labels from one frozen corpus.

Core path, standard library only:

    record -> validate -> fact sheet -> deterministic renderer -> grounding check
                                                                   |
                                                        drafted | refused

Optional model layer, behind the same check:

    fact sheet + draft -> model -> claims -> the same four checks -> kept | dropped

`draft(corpus, number)` never touches the network. Pass `llm="live"` (or
`--llm` on the command line) to add the rewrite step.
"""

from __future__ import annotations

__version__ = "1.1.0"

from .corpus import Corpus, load_corpus  # noqa: E402
from .pipeline import draft  # noqa: E402

__all__ = ["Corpus", "load_corpus", "draft", "__version__"]
