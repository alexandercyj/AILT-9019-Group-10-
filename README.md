# Label Desk UI

A local single-page browser interface for the Label Desk prototype described in the AILT9019 project proposal.

The UI helps turn one catalogue record into a reviewable exhibition label draft. It shows the record fields, the generated label, claim-to-field links, citation tags, grounding checks, and a safe refusal path when a required field is missing.

## Files

- `index.html` — main single-page browser view
- `styles.css` — responsive CSS layout and visual styling
- `app.js` — local interaction logic for label drafting and refusal testing
- `INTEGRATION_NOTES.md` — English notes on backend file-to-port connections
- `README.md` — this file

## Current local preview

The UI was tested through a local static preview server at:

```text
http://127.0.0.1:4173/
```

That address is for local preview only. If the preview server is not running, open `index.html` directly in a browser or serve the folder again with a simple local static server.

## Features

- English-only visible guidance and inline suggestions
- Catalogue record form with editable fields
- Grounded label draft output
- Claim and citation tags for traceability
- Grounding checks panel
- Safe refusal path for a missing required field
- Responsive layout for smaller screens

## Suggested backend integration

See `INTEGRATION_NOTES.md` for the suggested mapping between backend files and local ports.

At a glance:

- `server.py` → `:8000`
- `label_renderer.py` → `:8001`
- `grounding_check.py` → `:8002`
- `llm_adapter.py` → `:8003`
- `frozen_corpus.json` → local read-only data file

## Notes

This interface is a prototype. It is designed as a drafting aid, not as an authoritative museum record.
