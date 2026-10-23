# Architecture notes

The previous version of this file described a planned split across four local ports
(`server.py` 8000, `label_renderer.py` 8001, `grounding_check.py` 8002, `llm_adapter.py`
8003). None of those services exist. The core path is one Python package called in-process,
and the browser view is a thin client over it. This file now records what is actually
there.

## One implementation, two entry points

```text
                      labeldesk/                     (standard library only)
  CLI  ──────────────►  corpus → validate → factsheet → render → grounding
  server.py /api/draft ┘                                        │
                                                                ▼
                                                     drafted | refused
```

- `python3 -m labeldesk <catalogue number>` prints the result for a human.
- `server.py` serves `index.html` and exposes `POST /api/draft`, which calls the same
  `labeldesk.draft()` function and returns the same JSON.

`app.js` contains no renderer, no grounding rule and no refusal rule. If the browser view
and the CLI ever disagreed, that would be a bug in one call, not a divergence between two
implementations.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | The single-page browser view. |
| GET | `/api/records` | Corpus metadata and all 20 records, each with a `missing` field list. |
| GET | `/api/record/<catalogue number>` | One record, or 404 `out_of_corpus`. |
| POST | `/api/draft` | `{"catalogue_number": "...", "question": "..."}` → the full result object. |

No CORS headers: the page and the API are the same origin. The server binds to
`127.0.0.1` by default and has no write endpoints.

## Why there is no model service yet

The proposal keeps the LLM pass optional and behind the same guardrails. When it is built,
it belongs *behind* `grounding.py`: a rewrite is accepted only if it passes the same four
checks and returns the same claim-to-field structure, with the offline draft as the
fallback. That is why there is no `llm_adapter` port to wire up now — adding one before the
check is enforced would put unverified prose in the label.

## Result object

Every drafted result carries `label`, `claims` (`text`, `source_field`, `value_span`),
`citations`, `padding`, `word_count` and `checks`. Every refusal carries `status`,
`reason`, `reason_text` and `missing_fields`, with `label: null`. `--json` and
`POST /api/draft` return the identical object.
