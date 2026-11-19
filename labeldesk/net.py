"""TLS for the few HTTPS calls this project makes.

The core path is fully offline; the only outbound requests are the museum open
APIs (`tools/fetch_corpus.py`), the robots re-check (`tools/check_sources.py`),
and the optional model endpoint (`labeldesk/llm.py`). Those calls go through
:func:`ssl_context`.

Python installs that ship without a root store — the python.org macOS
installer is the common case, with an empty ``etc/openssl`` — cannot verify
any host until one is supplied. When ``certifi`` is installed its bundle is
used; otherwise the process default applies, which honours ``SSL_CERT_FILE``
for anyone whose network or platform needs a different store. Nothing here
weakens verification: no unverified contexts, no per-call overrides.
"""

from __future__ import annotations

import ssl


def ssl_context() -> ssl.SSLContext:
    """A verifying context with certifi's roots when certifi is available."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
