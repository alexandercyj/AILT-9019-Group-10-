# Architecture notes

The first version of this file described a planned split across four local ports
(`server.py` 8000, `label_renderer.py` 8001, `grounding_check.py` 8002, `llm_adapter.py`
8003). None of those services exist. The core path is one Python package called
in-process, and the browser view is a thin client over it. This file records what is
actually there.

## One implementation, four entry points

```text
                      labeldesk/                     (standard library only)
  CLI  ──────────────►  corpus → validate → factsheet → render → grounding
  server.py /api/draft ┘        │           ▲                     │
  skills/labeldesk/SKILL.md     │           │                     ▼
                                │      sources.py            drafted | refused
                                │      (licence gate)              ▲
                                └─► llm.py (optional) ──► same grounding

  labeldesk.html  ──►  a build-time snapshot of the four entry points above
```

- `python3 -m labeldesk <catalogue number>` prints the result for a human.
- `server.py` serves `index.html` and exposes `POST /api/draft`, which calls the same
  `labeldesk.draft()` function and returns the same JSON. `POST /api/fetch` reads one
  record from a museum's open API at request time, wraps it in an ephemeral corpus that
  borrows the registered corpus name so provenance and the licence gate resolve
  unchanged, and drafts it through that same function. Nothing is written to disk.
- `skills/labeldesk/SKILL.md` documents that same command for another agent environment.
  It adds no code: the contract is the CLI's JSON.
- `labeldesk.html` is one file that opens in a browser with nothing installed.

`app.js` contains no renderer, no grounding rule and no refusal rule. If the browser view
and the CLI ever disagreed, that would be a bug in one call, not a divergence between two
implementations.

## Why the standalone file is a snapshot, not a port

The obvious way to ship a single HTML file is to reimplement the renderer and the four
checks in JavaScript. That would be a second implementation of the one thing this project
is about, and the two would drift — silently, because nothing would compare them.

So `tools/build_standalone.py` runs the real pipeline over every record in every corpus, in
both modes, and writes the results into the page as data. The page looks them up.

The consequence is worth stating plainly: **the standalone file cannot answer for a record
it was not built with.** Everything else it does answer correctly, because the input space
is finite. The two decisions the page does make for itself are membership tests over data
embedded in it:

| Decision | How the page makes it | Why that is safe |
| --- | --- | --- |
| is this catalogue number in this corpus? | array membership | the array *is* the corpus |
| does this question contain an out-of-scope term? | substring test over `meta.out_of_scope_terms` | the list is copied out of `labeldesk.pipeline`, not retyped |

The refusal wording comes from `REASON_TEXT` for the same reason: a page that invents its
own phrasing for a refusal would be a different tool with a familiar face.

`tests/test_standalone.py` closes the loop. It rebuilds the file and compares every embedded
result against a fresh `draft()` call, so a change to the renderer, the grounding rules or
the prompt fails the suite until the file is rebuilt. It also asserts the file has no
`<script src>`, no stylesheet link and no `fetch(`, which is what "open it and it works"
means mechanically.

The build is byte-reproducible — no timestamp, only corpus checksums and the prompt hash —
so `--check` is a real staleness test rather than a same-day coincidence.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | The single-page browser view. |
| GET | `/api/records` | Corpus metadata, all records with `missing` lists, and the `live_providers` offer (names, endpoints, example object IDs). |
| GET | `/api/record/<catalogue number>` | One record, or 404 `out_of_corpus`. |
| GET | `/api/llm` | Model endpoint, whether a key is set, default mode, prompt hash. |
| POST | `/api/draft` | `{"catalogue_number": "...", "question": "...", "llm": "auto"}` → the full result object. |
| POST | `/api/fetch` | `{"provider": "met" \| "cleveland", "object_id": N, "llm": "auto"}` → one live record plus the full result object for it. 400 on a bad provider or ID, 502 with the upstream status when the museum's API cannot be reached. |

No CORS headers: the page and the API are the same origin. The server binds to
`127.0.0.1` by default and has no write endpoints. `llm` is validated against the four
accepted values and defaults to off, so a page that does not ask never triggers a model
call. A live fetch is also a read: the record exists only in the response.

## Where the model layer sits

Behind `grounding.py`, not in front of it. `llm.py` is given the fact sheet and the offline
draft, and returns claims; `guard()` then runs structure, coverage, and the same four
checks the offline draft faces. A rewrite that fails any of them raises
`RewriteRejected`, `pipeline.draft()` keeps the offline result, and the reason lands in the
result's `llm` block.

That ordering is the whole design. Adding an `llm_adapter` port before the check was
enforced would have put unverified prose in the label; the layer exists now only because
there is a check for it to pass.

Two consequences worth stating:

- **`llm.py` never raises into the pipeline.** Transport failures, empty responses, prose
  instead of JSON, a stale transcript, a missing key — all become a reason string, and the
  offline draft prints.
- **The transcript is re-checked on replay.** `data/llm_transcripts.json` stores the raw
  model response, not an accepted result. Replay re-parses and re-runs the guardrail, so a
  transcript recorded under a weaker rule cannot smuggle in a rewrite the current rule
  would reject.

## Result object

Every drafted result carries `label`, `claims` (`text`, `source_field`, `value_span`),
`citations`, `padding`, `word_count`, `label_source` (`offline_template` or `llm_rewrite`),
`checks`, `llm`, `record`, and `provenance`. Every refusal carries `status`, `reason`,
`reason_text` and `missing_fields`, with `label: null` and `llm: null` — and `provenance`,
because a refusal should still say where the records came from. `--json`, `POST /api/draft`
and the skill contract all return the identical object.

`llm` is present on every drafted result, with `requested: false` when the model was not
asked for. That keeps the shape stable for callers and makes "the model was not used"
distinguishable from "the model was used and discarded".

`provenance` is the register's answer for this corpus: `id`, `license`, `robots_verdict`,
`decision`, `registered`, `ai_input`. For an unregistered corpus `license` is `null` and the
corpus's own claim is reported separately as `license_claimed` — a file's claim about itself
is not a licence on file.

## The licence gate, and why it is a separate step

`sources.py` answers one question before `llm.py` is reached: may this corpus's records be
sent to a model at all? Three outcomes:

| corpus | `ai_input` | `--llm` behaviour |
| --- | --- | --- |
| registered, `ai_input: true` | yes | normal: live or replay, guarded |
| registered, `ai_input: false` | no | `policy_block()`, reason `source_policy`, exit 4 |
| not in `data/sources.json` | no (default) | same as above, source reported as unregistered |

It is deliberately not inside `llm.py`. A guard that lives in the model layer can be
bypassed by a new entry point; a guard the *pipeline* calls cannot, because every entry point
already goes through the pipeline. The offline path never consults it, which is why a policy
refusal costs a draft nothing.

`policy_block()` is also deliberately distinct from a rejected rewrite. A rejection means the
model answered badly; a policy block means nothing was sent and nothing was attempted
(`attempts: 0`). The CLI prints different words for each, because "discarded" would
misdescribe an empty room.

## Two museums, three corpora, one pipeline

The corpus file carries its own `field_map`, because the sources disagree: the primary corpus
takes place from `culture`, Egyptian Art from `country`, and Cleveland from a list-shaped
`culture` joined with `; `. Records are normalised at build time (`tools/fetch_corpus.py`),
so `labeldesk/` only ever sees the five required field names. Nothing in the package knows
which museum a record came from, which is what `tests/test_second_corpus.py` and
`tests/test_third_corpus.py` assert.

The same is true of the transcripts. They are keyed `corpus::catalogue number`, because
catalogue numbers are unique inside a museum and not across museums — two collections can
both number something "1", and a flat key would let one corpus replay another's answer. The
plain key is still accepted on read, because the first transcripts were recorded before there
was a second museum; `tests/test_llm.py` asserts that none remain unscoped.

## Live fetch: a corpus of one

`POST /api/fetch` is the browser view's one door to the outside. It reuses
`tools/fetch_corpus.py` for the HTTP and the normalisation, builds a single-record
`Corpus` whose `meta.name` is the registered corpus name for that museum's frozen file,
and calls `labeldesk.draft()` — the same function the CLI and `/api/draft` call. Borrowing
the registered name is deliberate: `sources.py` resolves provenance and the `ai_input`
policy by it, so the licence gate applies to a live record exactly as it does to a frozen
one, with no new policy surface and no special cases. `Corpus.path` is never read during a
draft; it only satisfies the shape.

The field map for a live Met record reads `culture` first and falls back to `country`, so
any department works, not only the two that were frozen. Records that still come back
incomplete — the Met's European Paintings department leaves `culture` blank, for example —
hit the ordinary `missing_required_field` refusal. That is the grounding guarantee doing
its job on data nobody curated.

Two TLS notes. The project makes exactly two kinds of outbound call: the museum open APIs
and the optional model endpoint. Both verify through `labeldesk/net.py`, which uses
`certifi` when it is installed and the process default otherwise (so `SSL_CERT_FILE` still
works where a network needs its own store). The python.org macOS installer ships no root
store at all, which is why `certifi` is in `requirements.txt` rather than a preference.

## Versioning

`fetched_at` is pinned per corpus preset rather than read from the clock, so
`tools/fetch_corpus.py --check` rebuilds byte-identically and the checksum in the README is
a real claim about the file. The model prompt is versioned by sha256 instead of a version
number, because the hash is what the transcript is keyed against. The source register is
versioned by its own `updated` date plus a `robots.checked` date per source, because a
licence claim goes stale silently and a date is how it is made to say so.
