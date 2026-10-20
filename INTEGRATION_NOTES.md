# Label Desk — UI Integration Notes

## What is included

- `index.html`: single-page browser view for the proposal prototype.
- `styles.css`: responsive CSS layout and visual system.
- `app.js`: local interaction logic for drafting labels and exercising the refusal path.
- All visible guidance, inline suggestions, and backend integration notes are written in English.

## Current local preview

The UI is being served locally for preview at:

```text
http://127.0.0.1:4173/
```

This is a static prototype server. It is for local preview only.

## Suggested backend file connections

| File | Suggested local service | Why it belongs there |
| --- | --- | --- |
| `server.py` | `http://127.0.0.1:8000` | Main API and static entry point for the browser view. |
| `label_renderer.py` | `http://127.0.0.1:8001` | Offline deterministic label rendering endpoint. |
| `grounding_check.py` | `http://127.0.0.1:8002` | Fact containment and citation resolution checks. |
| `llm_adapter.py` | `http://127.0.0.1:8003` | Optional model pass behind the same guardrails. |
| `frozen_corpus.json` | no port | Local read-only data file used by the backend services. |

## Inline recommendation

Keep the browser UI on port `8000` and proxy backend requests through `server.py` only. The frontend should not connect directly to the checker or model adapter services. This makes refusal handling, grounding checks, and fallbacks easier to enforce in one place.

## UI behavior implemented

- Fill or edit the record fields.
- Generate a grounded draft.
- Trigger a safe refusal when a required field is missing.
- Show claim tags, citation tags, and grounding status.

## Accessibility and review notes

- Semantic sections and headings are used.
- Form controls have labels.
- The page is keyboard-friendly and remains readable at narrow widths.
- The output keeps the proposal’s review wording: draft for curator review, not an official record.
