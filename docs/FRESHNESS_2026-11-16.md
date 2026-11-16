# Museum freshness, 16 Nov 2026

Read-only. No frozen file was replaced. No checksum was edited. No model call was made.

## Shipped records

A rebuild through `tools/fetch_corpus.py`’s `build()` was compared in memory with the three shipped files. The shipped bytes were hashed before and after the fetches.

| Preset | Records fetched | Byte match | sha256 | File changed |
| --- | --- | --- | --- | --- |
| primary | 20 Met objects | yes | `bdb51f3a20aeefc83d592d958e9dfa53435001e08b676ba649664a0d3d851f07` | no |
| egyptian | 10 Met objects | yes | `878195ccdf83ae09c94d44f6ee626ca1c15a6fecfa5d21c960236421160edf8a` | no |
| cleveland | 10 Cleveland objects | yes | `144d59a46965693254eb7ec70bf0c977e7144c16a904c39c9c4e163859c8cab9` | no |

The pinned `fetched_at` dates (23 Oct and 1 Nov 2026) still reproduce today’s public records for these object IDs. That does not mean every other object at those museums is unchanged.

## Robots register

`tools/check_sources.py` did not use the project certificate bundle, so the first run failed TLS inside the Python 3.12 environment and proved nothing about the museums. It now uses `labeldesk.net.ssl_context`, the same verifying context as the corpus fetch.

After that fix, Met, Cleveland, the British Museum, the Palace Museum, and Wikidata matched the register. The Art Institute did not: `https://api.artic.edu/robots.txt` returned 200, prefix `e5c4b84484ee4216`. The register had said 403 from 1 Nov 2026. One GET of `https://api.artic.edu/api/v1/artworks?limit=1&fields=id` returned HTTP 200 and JSON. No artwork from that response was stored.

`data/sources.json` now records the 200 and the prefix. The decision stays `deferred`. `ai_input` stays false. Cleveland remains the frozen second museum. After that edit, `tools/check_sources.py` matched 7/7 sources and exited 0.

The British Museum and the Palace Museum are still refused. Their robots statuses matched the register.

## What this does not show

It does not show that a future fetch will match. It does not admit the Art Institute into the corpus. `tools/fetch_corpus.py` without `--check` still writes the corpus, so that form was not run.
