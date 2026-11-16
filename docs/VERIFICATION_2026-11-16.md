# Verification, 16 Nov 2026

Local branch `cursor/ailt9019-local-product-69c3`. No push. The measurements below are the afternoon verification. They are not the evening live run.

The Week 2 Build Start brief was not available. Presentation speaking and Section 6 contributions are human-only.

## Later the same evening

Ed credit rules were read. The sponsored key file outside the repo is mode 600 and was not copied into the tree. Two live rewrites used `deepseek-v4.1-flash-1017` at temperature 0, 800 output tokens, no retries, thinking off. Both were kept by the checks. A third draft, “Who made this?” on `14.40.377`, refused `unknown_maker` with no extra request. Usage and outcomes are in `docs/live_run_2026-11-16.json`. That file is live evidence. The 18/18 replay report is still recorded transcripts. Python 3.12.6 then passed 248 tests. Search and record selection do not call research unless the server is started with `--allow-research`, and a live draft is refused unless the server is started with `--allow-live`.

## Python 3.12

Interpreter already installed: `/usr/local/bin/python3.12`, version 3.12.6. Isolated environment: `/tmp/labeldesk-py312` (not installed into the system site-packages).

On a clean worktree of `e6d8dbd` (before this hardening commit):

- `pytest`: 241 passed in 1.41s
- `tools/build_standalone.py --check`: matched sha256 `c08f6d1a3229cb03f6364f1ef4778b7b43a5163cba664367e5a4da4f73eaf8ad`
- `python3 -m labeldesk 14.40.377`: exit 0
- `python3 -m labeldesk 62.98.1`: exit 3
- `eval/evaluate.py --llm --replay --quiet`: 17/17, claim precision 100%, citation resolution 100%, 11/13 rewrites kept, 2 discarded for `drops_field_content`

That pytest rewrote only the timestamps in `eval/reports/golden_report.md` and `.json`. Those files were restored. The suite now writes test reports to a temporary directory (`--reports`) so a later pytest does not do that.

After the hardening edits, the same 3.12.6 environment in the feature worktree: 245 passed.

`tools/fetch_corpus.py --check` was not run. Its rebuild fetches museum records.

## Browser

Headless Chrome, throwaway profile `/tmp/ld-chrome-profile`, not the signed-in profile. Screenshots:

- `docs/verification/standalone-draft.png` — `labeldesk.html` opened as a file. DOM title: Fragment of a Processional Cross. DOM label begins “The object is titled…” and the page text includes “Draft for curator review”.
- `docs/verification/standalone-refusal.png` — same file, Metropolitan tab, catalogue `62.98.1`. The summary reads: “Record 62.98.1 has no object date. No label was drafted…” The date row reads “Not supplied by the museum”.
- `docs/verification/local-landing.png` — `site/index.html`. Visible text: “This file is a local page. It is not a published URL.” and “Nothing here claims a host.”
- `docs/verification/server-home.png` — `http://127.0.0.1:8765/` from `server.py` bound to 127.0.0.1. The search box was not submitted. Resource URLs loaded by that page: `/styles.css` and `/app.js` only.

The refusal screenshot’s object image was requested by the browser from the museum image URL already stored in the frozen record. That is a public image GET. `/api/search`, `/api/fetch`, and `/api/research` were not called. `GET /api/llm` returned `has_key: false`. `POST /api/draft` for `62.98.1` returned `refused` / `missing_required_field`.

## What the tests do not prove

- `tests/test_standalone.py` checks that `labeldesk.html` matches a fresh `draft()` from the same code. It proves the file was rebuilt. It does not use a second implementation as an oracle. The golden set’s expected statuses are the separate check.
- At the 245-test tree the golden set had no `unknown_maker` case. Request case `r03` was added later. The CLI and `tests/test_refusal.py` already covered that reason.
- `tests/test_contrast.py` locks colour literals in `styles.css`. It does not measure pixels in a browser.
- Server tests monkeypatch museum providers. They do not prove a live museum response.
- Pytest used to rewrite the dated golden reports. It no longer does.

## Release batches, still local

1. This branch. Code, tests, and the notes above. Not pushed.
2. A team member reconciles `report.pdf` with `docs/REPORT_DISCREPANCIES.md`, fills Section 6 from work they actually did, and adds this session to the AI-use fields if the commits are kept.
3. Host the page, record the presentation (every member speaks, name visible) and the demo, then replace the placeholders in `links.txt`.
4. Live model calls only after the Ed credit rules are verified. Until then, replay stays labeled as not live.
5. A coordinator confirms, then someone with the shared repo pushes. This pass does not.

## `.impeccable`

`.impeccable/config.json` records design-hook exceptions for the existing Inter face, the CSS type scale, and the existing paper colour. Nothing in `labeldesk` or `requirements.txt` imports it. `.impeccable/hook.cache.json` is gitignored because it stores this machine’s paths.
