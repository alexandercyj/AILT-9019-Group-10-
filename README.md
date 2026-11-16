# Label Desk

A cited, plain-language exhibition label drafted from one frozen museum record — with a
machine check that every sentence in the label comes from a field of that record, and a
refusal path for records that cannot supply one.

AILT9019 Group 10. Midterm check, October 2026 · post-midterm work, November 2026.

---

## Six steps to one label

No API key and no environment variable. The core path uses the Python standard library.

1. Check the interpreter: `python3 --version` (3.10 or newer).
2. Clone the shared repository, not a personal copy: `git clone https://github.com/alexandercyj/AILT-9019-Group-10-.git`
3. Enter it: `cd AILT-9019-Group-10-`
4. Stay offline. Do not create a `.env` for this check.
5. Paste one command: `python3 -m labeldesk 14.40.377`
6. The process exits 0. The status line says `DRAFTED`. The corpus line shows `sha256 bdb51f3a20ae`. The label is 65 words and ends with `Draft for curator review, not an official record.`

Two further catalogue numbers show the other designed outcomes: `36.120.655` keeps the hedge `ca. 1740`, and `62.98.1` refuses because the object date is blank (exit 3).

## What works today

One command takes a catalogue number from a frozen corpus of Met Open Access (CC0)
objects and prints one of two things:

- **drafted** — a 60–80 word label, five claims, five citations, and four automatic
  checks that all pass;
- **refused** — a stated reason and no label text, for a record with a missing required
  field, a catalogue number outside the corpus, or an out-of-scope request.

The core path has no model in it and makes no network call at run time. The same record
always produces the same label.

Three corpora ship, from two museums, and nothing in the package knows which is which:
the field map and the licence live in the corpus file and in `data/sources.json`. Adding
a museum is a data change, not a code change.

An **optional model layer** sits behind the same check: `--llm` asks a model to reword
the five sentences, and the rewrite is printed only if it passes the identical four
checks and keeps at least as much of each field as the offline draft did. Otherwise the
offline draft is printed and the rejection reason is recorded. Turning the model on can
cost prose quality; it cannot cost a fact or a citation.

| | |
| --- | --- |
| Corpora | 20 records (Met, 4 departments) · 10 (Met, Egyptian Art) · 10 (Cleveland Museum of Art) |
| Sources checked | 7, of which 2 admitted, 2 refused, 1 deferred, 1 reference-only, 1 not frozen |
| Tests | 248 on Python 3.12.6 |
| Golden set | 18/18 cases, both model-off and model-on replay |
| Cross-corpus run | 40 records, 0 check failures, 35/37 rewrites accepted |
| Claim precision · citation resolution | 100% · 100%, every run |
| Network at run time | none, unless `--llm` or a live fetch is asked for |

---

## Open the offline collection without installing anything

`labeldesk.html` is a self-contained, English-language collection reader. Double-click
it, or drag it into a browser. No Python, server or key is needed. It contains all 40
records from all three corpora and their real pipeline output. The page looks results
up; it does not recompute or invent them. Museum images load from their open-access
URLs, so image display needs a network connection; all catalogue text remains available
offline.

The standalone reader deliberately does not pretend to offer live web research. Use
`server.py` for the full encyclopaedia experience, including whole-collection search,
web search, page extraction and paragraph-level citations.

```bash
python3 tools/build_standalone.py          # rebuild labeldesk.html
python3 tools/build_standalone.py --check  # is the shipped file stale?
```

The build is byte-reproducible: no timestamp goes into the file, only the corpus
checksums and the prompt hash.

---

## Setup

Requires Python 3.12 or newer, as the proposal specifies. Verified on 16 Nov 2026 with Python 3.12.6 (and earlier the same day with 3.15.2). The core path needs no third-party package.

```bash
git clone https://github.com/alexandercyj/AILT-9019-Group-10-.git
cd AILT-9019-Group-10-
python3 --version          # 3.10 or newer
python3 -m pip install -r requirements.txt   # pytest, and the optional model SDK
```

Nothing to configure for the core path: no environment variables, no API key.

**Only** if you want live model rewrites, put a key in `.env` (copied from
`.env.example`, and git-ignored):

```bash
cp .env.example .env
# then edit .env and set LABELDESK_API_KEY
python3 -m labeldesk --status      # shows the endpoint, the model, and whether a key is set
```

Without a key, `--llm` replays the recorded responses in `data/llm_transcripts.json`.
The model path is therefore demonstrable offline, which is the pre-agreed fallback.

---

## Run the core path

One command, no arguments to remember beyond the catalogue number:

```bash
python3 -m labeldesk 14.40.377
```

Expected output (this is the whole result, not an extract):

```text
Label Desk 1.1.0 · offline draft
Corpus  labeldesk-frozen-corpus v1.0.0 · 20 records · sha256 bdb51f3a20ae
Source  met · CC0-1.0 · robots no_restriction_published · ai_input yes
Record  14.40.377 · Vase · object 42229 · Asian Art

STATUS  DRAFTED
Label   65 words (band 60–80)

  The object is titled "Vase". The catalogue dates it to 1713–22. The
  medium is recorded as "Porcelain with peach-bloom glaze (Jingdezhen
  ware)". Its place or culture is given as China. The credit line reads:
  Bequest of Benjamin Altman, 1913. Every sentence above restates one
  field of the catalogue record. No fact outside that record has been
  added. Draft for curator review, not an official record.

Claims
  c1  title             -> "Vase"
  c2  object date       -> "1713–22"
  c3  medium            -> "Porcelain with peach-bloom glaze (Jingdezhen ware)"
  c4  place or culture  -> "China"
  c5  credit line       -> "Bequest of Benjamin Altman, 1913"

Checks
  PASS  Field existence       5/5 claims pass
  PASS  Value containment     5/5 claims pass
  PASS  Citation resolution   5/5 citations pass
  PASS  Readability           1/1 label pass
  claim precision 100% · citation resolution 100% · average sentence 8.12 words
```

Exit codes: `0` drafted and every check passed, `1` drafted but a check failed,
`3` refused, `4` the model layer was asked for and could not run. Refusal is a
designed outcome, so it gets its own code rather than an error.

### Three sample catalogue numbers

| Command | What it shows |
| --- | --- |
| `python3 -m labeldesk 14.40.377` | Well-formed record, plain draft. |
| `python3 -m labeldesk 36.120.655` | Hedged date: the label keeps `ca. 1740`. |
| `python3 -m labeldesk 62.98.1` | Refusal: the record has no object date. |

Other entry points:

```bash
python3 -m labeldesk --list                          # the catalogue numbers in the corpus
python3 -m labeldesk --info                          # corpus metadata, checksum, source policy
python3 -m labeldesk --sources                       # the source register, and the corpus aliases
python3 -m labeldesk 14.40.377 --json                # full machine-readable result
python3 -m labeldesk 14.40.377 --ask "what is it worth?"   # out-of-scope refusal
python3 -m labeldesk 29.3.1 --corpus egyptian        # second department (Met, Egyptian Art)
python3 -m labeldesk 1970.36 --corpus cleveland      # second museum (Cleveland Museum of Art)
```

`--corpus` takes a registered alias or a path. An alias that is not in
`data/sources.json` is an error rather than a silent fallback to the default
corpus, because reading the wrong records is worse than stopping.

### Model layer (optional)

```bash
python3 -m labeldesk 14.40.377 --llm            # live call if a key is set, else replay
python3 -m labeldesk 14.40.377 --llm --replay   # recorded response, no network, no key
python3 -m labeldesk 1970.36 --corpus cleveland --llm --replay   # the model path on a third museum
python3 -m labeldesk --status                   # endpoint, model, prompt hash, transcript count
```

The tail of a model-on run says what happened to the rewrite:

```text
  Model   deepseek-v4.1-flash · live · rewrite accepted (1 call)
```

or, when the guardrail fired:

```text
  Model   deepseek-v4.1-flash · replay · rewrite discarded: drops_field_content
          {"reason": "drops_field_content", "field": "medium", "missing": ["both", "decorated", "faces", "glaz
          offline draft printed instead (no-regression rule)
```

That example is real. The record's medium is a four-part description
(`Clay; moulded frame and shaped supports glazed black; both faces of screen with ivory
glaze, decorated with landscapes in black (Tokyo ware)`); the rewrite kept the first two
parts, stopped at a semicolon, and cited what it kept. Every word it printed was true, the
citation resolved, and the label had lost the ware. The `drops_field_content` rule is what
catches that.

### Browser encyclopaedia (optional)

```bash
python3 server.py            # http://127.0.0.1:8000
```

The English-language page searches the complete Met and Cleveland open collections in
parallel, returns real CC0/public-domain images, and opens a wiki-style object entry.
Museum fields remain visibly separate from external research. There are no Google
redirects, object-ID forms, checksum panels, model switches or debugging controls in the
reader interface.

After an object is selected, `labeldesk/research.py` calls the provider's OpenAI-compatible
Responses API with the built-in `web_search` and `web_extractor` tools. The separate
`LABELDESK_RESEARCH_MODEL` defaults to `deepseek-v4.1-flash-1017`, because the older
rewrite model is not documented as supporting page extraction. Research output is English
JSON with a lead, sections and an evidence-to-conclusion note. Every paragraph must cite
a URL actually returned by `web_extractor` (search-result links alone are insufficient); otherwise the
whole research answer is withheld and only the museum record remains. The page presents
actual searches, pages read and a concise evidence explanation, not a raw hidden
chain-of-thought.

When no museum record matches, the same research path can produce a web-only entry.
It does not use arbitrary hotlinked images: without a confirmed open image, the entry
honestly shows no image. Research requires `LABELDESK_API_KEY`, network access and a root
certificate store. Failures never become unsourced prose. Successful responses are cached
in memory for 30 minutes to avoid repeated model and search charges; nothing is written
to disk.

HTTPS verification note: direct outbound calls use the museum open APIs and the model
endpoint through `labeldesk/net.py`, which prefers `certifi`. Web pages used by the
research layer are retrieved by the model provider's built-in tools. The python.org macOS
installer ships without a root store, so `certifi` is listed in `requirements.txt`.

---

## Check the result

Three independent ways, from cheapest to strictest.

### 1. The four checks, printed with the label

Every run prints field existence, value containment, citation resolution and readability
with a pass count. A drafted label that fails any of them exits `1`.

### 2. The test suite

```bash
python3 -m pytest -q
```

Expected: `248 passed` on 16 Nov 2026, Python 3.12.6, pytest 9.1.1. The suite is not a smoke test — it breaks the output on purpose
and requires the check to catch it:

| Test file | What it proves |
| --- | --- |
| `tests/test_corpus.py` | 20 records, checksum matches `data/frozen_corpus.sha256`, lookups resolve. |
| `tests/test_core_path.py` | Five claims, word band, notice, determinism, hedges kept. |
| `tests/test_refusal.py` | Missing field, unknown number and out-of-scope questions all refuse. |
| `tests/test_grounding.py` | Invented place, narrowed date, dropped hedge and dropped `or` are rejected. |
| `tests/test_render.py` | Long values are shortened to a prefix that still resolves. |
| `tests/test_golden.py` | The evaluation below passes, and the CLI exit codes are right. |
| `tests/test_llm.py` | 43 tests: every way a rewrite is discarded, transcript replay and scoping, stale prompt, no key, and that a refusal never reaches the model. |
| `tests/test_second_corpus.py` | The second department drafts and refuses with no new code. |
| `tests/test_third_corpus.py` | The second museum does too, on dates the team did not phrase. |
| `tests/test_sources.py` | Every shipped corpus is registered, and the pipeline refuses the model for one that is not. |
| `tests/test_import.py` | A CSV with an unquoted comma is refused rather than silently misaligned. |
| `tests/test_server.py` | Real-socket drafts, combined museum search, image policy, research cache and refusal paths, all offline-mocked. |
| `tests/test_research.py` | Retrieved-URL citations, readable research steps, source-policy filtering and safe failure without a key. |
| `tests/test_standalone.py` | Every label in `labeldesk.html` equals a fresh pipeline run; no external code assets are loaded. |
| `tests/test_skill.py` | The skill file describes the program that actually runs. |
| `tests/test_repro.py` | Offline and replay results do not change when a key is present, and the key text is absent. |
| `tests/test_contrast.py` | The muted and empty-state colours meet the WCAG AA 4.5:1 threshold on their backgrounds. |

### 3. The golden set, run twice

```bash
python3 eval/evaluate.py                 # model off
python3 eval/evaluate.py --llm --replay  # model on
python3 eval/evaluate.py --compare       # the two side by side
```

Expected, both runs:

```text
Golden set · 18/18 cases passed
  claim precision        100%  citation resolution   100%  readability 100%
  restatements           72/72  probe agreement 100%  (false accepts 0, spurious rejections 0)
```

The model-on run adds one line:

```text
  rewrites               11/13 accepted  (85%), 2 discarded -> offline draft
        - drops_field_content x 2
```

`data/golden_set.json` holds 15 record cases (10 well formed, 5 boundary) and 3 request
cases, each with the record values a correct label must restate and the outcome it must
produce. `eval/probes.json` holds 12 single sentences labelled pass or fail, which test the
grounding rule rather than the templates.

Reports land in `eval/reports/`:

| File | What it is |
| --- | --- |
| `golden_report.md` / `.json` | model off |
| `golden_report_llm.md` / `.json` | model on, recorded — reproducible by anyone, no key |
| `golden_report_llm_live.md` / `.json` | model on, live call on 1 Nov 2026, kept as evidence |
| `model_comparison.md` | the two runs side by side, gate by gate |

The committed model-on report is the recorded run, not the live one, because a live call
is not reproducible. Both pass the same gates; the live run accepted one rewrite more.

To reproduce any corpus byte for byte:

```bash
python3 tools/fetch_corpus.py --check
python3 tools/fetch_corpus.py --preset egyptian --check
python3 tools/fetch_corpus.py --preset cleveland --check
```

### 4. Every record in every corpus

```bash
python3 eval/cross_corpus.py
```

The golden set is 17 hand-picked cases with expectations the team wrote while looking at
the same records. This is the other test: all 40 records across all three corpora, no
per-record expectations, reporting only what the pipeline says about itself.

```text
cleveland  10 records · 10 drafted · 0 refused · 10/10 checks pass · rewrite 10 accepted, 0 discarded
egyptian   10 records · 10 drafted · 0 refused · 10/10 checks pass · rewrite 10 accepted, 0 discarded
primary    20 records · 17 drafted · 3 refused · 17/17 checks pass · rewrite 15 accepted, 2 discarded
```

Report: `eval/reports/cross_corpus.md`. Exit `1` if any drafted label fails a check in either
mode, which makes it usable as a regression gate rather than only as a table.

---

## The core path, in five steps

1. **Look up** the catalogue number in the frozen corpus. Not found → refused as
   `out_of_corpus`; the system never describes a similar object instead.
2. **Validate** the record against the five required fields: title, object date, medium,
   place or culture, credit line. Any blank → refused as `missing_required_field`, naming
   the field.
3. **Build a fact sheet** where every value keeps a pointer to the field it came from.
4. **Render** five fixed sentences, one per field, so the offline path is deterministic.
   Every sentence is emitted as a claim: a span of label text plus one source field plus
   the exact slice of that field it cites.
5. **Check** every claim: the cited field exists and is non-empty; every fact-carrying word
   in the claim comes from that slice; no hedge is dropped and no new number appears; every
   printed citation resolves; the label is 60–80 words with sentences under 20 words.

### What counts as a fact

The check compares claims, not prose. A claim may restate a field, including the museum's
own hedges (`ca.`, `probably`, `(?)`, `or`), but may not sharpen, narrow, date or relocate
it. Concretely, for the record value `probably Iran`:

| Claim | Result | Why |
| --- | --- | --- |
| `probably made in Iran` | pass | hedge kept, place restated |
| `made in Iran` | fail | the stated uncertainty was dropped |
| `made in Egypt` | fail | names a place the cited field does not contain |

`eval/probes.json` holds these and nine more.

The comparison is token-level, which is stricter than "no new facts" and has two
consequences worth knowing. A word may be added only if it is on a short, documented
**free-word list**: function words, field names, the verbs of the templates, and a
reporting vocabulary (`keeps`, `states`, `gives`, `lists`) that describes the record
rather than the object. And an apostrophe leaves a stray `s` token, so "the record's
wording" is rejected where "the wording of the record" passes.

---

## The model layer

```text
record ──► source register: may these records be sent to a model at all?
                    │
        no ─────────┴─────────► policy_block, exit 4, nothing sent
                    │ yes
fact sheet + offline draft ──► model (temperature 0, prompt in prompts/rewrite.txt)
                                        │
                                        ▼
                         claims + one source field each
                                        │
              ┌─────────────────────────┴──────────────────────────┐
              ▼                                                    ▼
     structure: 5 claims, one per field,       coverage: keeps at least as much
     span occurs verbatim in the value         of each field as the offline draft
              └─────────────────────────┬──────────────────────────┘
                                        ▼
                   the same four checks the offline draft faces
                                        │
                            accepted ───┴─── discarded → offline draft, reason logged
```

Why the layer is built this way:

- **The licence is read before the call, not after it.** `sources.py` answers whether this
  corpus's source permits `ai_input`. A corpus that is unregistered, or whose source says
  no, never reaches the network — `attempts: 0`, reason `source_policy`, exit `4`. See
  "Where the data comes from" above.
- **The model returns structure, not prose.** It must answer with one claim per field and
  the exact slice of that field each sentence restates. Prose alone is not accepted, so
  there is nothing to re-check by hand.
- **A fifth rule exists only for the model.** `drops_field_content` catches the one failure
  the four checks cannot see: a rewrite that cites a *narrower* slice than the draft did.
  Nothing false was added and the citation resolved — and the label quietly lost half of a
  four-part medium description. Factual grounding cannot detect a subtraction; coverage can.
- **The prompt is a file, and it is hashed.** `prompts/rewrite.txt` is the system message.
  Each transcript entry stores the sha256 of the prompt that produced it, so editing the
  prompt marks the transcript stale instead of silently replaying an answer to a question
  that is no longer being asked.
- **Record values are data, never instructions.** The fact sheet is sent as JSON in the
  user message, and the prompt says so too. A field reading "ignore the rules" arrives
  inside a string.
- **The model reasons by default; it is switched off.** `deepseek-v4.1-flash` spends
  tokens on a hidden reasoning trace before answering, and with a 900-token budget it
  spent all of them there and returned an empty string. `enable_thinking: false` makes the
  same request cost six completion tokens and makes temperature 0 mean something.

What it actually buys, measured rather than claimed: 11 of 13 golden cases accepted on
replay, 12 of 13 live, and 35 of 37 across all three corpora. The prose is a little more
fluent ("The title given for the object is Vase" against the template's
`The object is titled "Vase"`), and the structural constraint leaves little room for more.
The full argument for keeping the layer, with the numbers and the conditions, is in
`docs/MODEL_LAYER_DECISION.md`.

---

## Refusals

| Input | Reason | What it prints |
| --- | --- | --- |
| `62.98.1` | `missing_required_field` | "Record 62.98.1 has no object date. No label was drafted: a blank field is not filled from outside the record." |
| `09.13.5` | `missing_required_field` | Same, for place or culture. |
| `99.99.99` | `out_of_corpus` | "… is not in the frozen corpus … the system does not describe a similar object from memory." |
| `--ask "what is it worth?"` | `out_of_scope` | Valuation, authentication, insurance and rights are declined. |
| `--ask "who made this?"` | `unknown_maker` | No artist is named. The cited fields do not identify a maker. |

A refusal never reaches the model: the look-up and validation steps run first, so there is
nothing for a model to be asked about.

---

## A second department, and a second museum

`data/frozen_corpus_egyptian.json` holds 10 Egyptian Art records. The point is not the
records but the field map: that department leaves `culture` blank and records place in
`country`, so its corpus declares `"place_or_culture": ["country", "culture"]`. Nothing in
`labeldesk/` knows this — the mapping lives in the corpus file, which is what makes the
pipeline data-agnostic rather than Met-Asian-Art-shaped.

```bash
python3 -m labeldesk 29.3.1 --corpus egyptian
python3 -m labeldesk 26.7.1460 --corpus egyptian --llm --replay
```

One record carries a `(?)` doubt marker and a disjunctive title ("Part (?) of a bracelet or
armlet with uraei"), so the hedge rule is exercised on this data too.

`data/frozen_corpus_cleveland.json` is the harder test: a different museum, a different
API, and dates phrased by someone else. The team did not write `c. 1050`, `1100s` or
`1800s, before 1896`; Cleveland did. A hedge rule that only works on phrasings we chose is
not a rule, so this corpus is the check on it.

```bash
python3 -m labeldesk 1970.36 --corpus cleveland            # c. 1050 survives
python3 -m labeldesk 1926.428 --corpus cleveland --llm --replay  # recorded rewrite, not a live call
python3 -m labeldesk --corpus cleveland --list
```

All 10 records draft with the four checks passing, and all 10 rewrites are accepted on
replay. `eval/cross_corpus.py` runs every record in every corpus and writes
`eval/reports/cross_corpus.md`:

| corpus | records | drafted | refused | checks pass | rewrite accepted |
| --- | --- | --- | --- | --- | --- |
| cleveland | 10 | 10 | 0 | 10/10 | 10 |
| egyptian | 10 | 10 | 0 | 10/10 | 10 |
| primary | 20 | 17 | 3 | 17/17 | 15 (2 discarded) |

Re-run on 16 Nov 2026 with offline drafting and replay, no live call. Same counts.
The three refusals are the frozen records with a blank required field (`62.98.1` and
`14.40.372` have no object date; `09.13.5` has no place or culture). Replay discarded
`1970.103a–e` and `36.120.655` for `drops_field_content` and kept the offline draft.
That replay discard is not the separate live rewrite of `36.120.655` recorded in
`docs/live_run_2026-11-16.json`.

---

## Where the data comes from, and what the sources allow

`data/sources.json` is a register of every source that was examined, not only the ones
that were used. Each entry records what the host publishes about automated access (the
file, its HTTP status, a sha256 prefix, and the verdict drawn from it), the terms for the
records as distinct from the terms for the website, and whether a record may be used as
label input at all.

```bash
python3 -m labeldesk --sources          # the register as a table, plus the corpus aliases
python3 tools/check_sources.py          # re-fetch every robots.txt and report drift
```

```text
SOURCE          ROBOTS                    LICENCE                    AI   DECISION
met             no_restriction_published  CC0-1.0                    yes  admitted
cleveland       allowed                   CC0-1.0                    yes  admitted
british-museum  restricted                no-open-licence-published  no   refused
palace-museum   not_published             no-open-licence-published  no   refused
artic           reachable                 CC0-1.0                    no   deferred
wikidata        allowed                   CC0-1.0                    yes  reference_only
nga             not_applicable            CC0-1.0                    yes  admitted_not_frozen
```

Two of these are refusals, and they are refusals of the brief: the post-midterm note asked
for the Palace Museum and the British Museum specifically. Both were checked, both were
rejected, and neither was worked around.

- **The British Museum** serves `Content-Signal: search=yes, ai-train=no, use=reference`
  and disallows the major training crawlers, publishes no open licence for collection
  records, and answers non-browser clients with a Cloudflare challenge. Getting past that
  challenge would be evasion, not permission.
- **The Palace Museum** returns a 70-byte meta refresh where `robots.txt` should be, has no
  open data licence, no API, and no reachable collection endpoint. A missing `robots.txt`
  is not a grant.

The register is not decoration. `pipeline.draft()` asks `sources.ai_input_allowed()`
*before* the model step, so a corpus whose source forbids `ai_input` — or which is not
registered at all — cannot reach the network through `--llm`, whichever entry point is
used. The offline draft is unaffected; the request loses its rewrite and exits `4`.

```bash
python3 -m labeldesk 1970.36 --corpus cleveland --llm --replay
#   Model   deepseek-v4.1-flash · replay · rewrite accepted (1 call)

python3 -m labeldesk 1970.36 --corpus /tmp/unregistered.json --llm --replay
#   Model   … · refused before sending: source_policy
#           source unregistered · licence not on file · ai_input not granted
#           offline draft printed instead; no record left this machine
```

Records from a refused source can still be used by someone entitled to hold them, through
`tools/import_records.py`: a CSV of the five fields plus the licence the importer asserts
and the basis on which they hold it. `--ai-input` is off by default there too — asserting a
licence to read records is not asserting a licence to send them to a model.

`docs/DATA_SOURCES.md` records the full reasoning, source by source.

---

## Calling it from another agent environment

`skills/labeldesk/SKILL.md` is a single-file contract for another agent: the invocation,
the result shape, the three refusal reasons, and six guardrails the caller must keep (never
turn a refusal into prose, never fill a blank field, check `checks.passed` before quoting,
always print the notice). The document is tested against the program, so it cannot drift
into describing a tool that does not exist.

---

## Curator review

`docs/REVIEW_CHECKLIST.md` is the human half of the system: six groups of yes/no questions
covering traceability, hedges, wording, readability, framing and sign-off. The tool can
prove a label is grounded; it cannot prove it is good, and the checklist is where that
judgement is recorded.

---

## Repository map

```text
labeldesk.html        the whole thing in one file: open it, no install, no server
standalone/
  template.html       the page shell, with three inline markers
  standalone.css      the styles the standalone page adds to styles.css
  standalone.js       presentation only: it looks results up, it does not compute them
labeldesk/            core pipeline, standard library only
  corpus.py           loading, checksum, required-field list
  validate.py         missing-field detection
  factsheet.py        fact sheet with a pointer per value
  render.py           deterministic renderer and claim emission
  grounding.py        the four checks
  llm.py              optional label rewrite, behind the same checks
  research.py         built-in web search/extraction and citation validation
  sources.py          the source register: what may be done with a corpus
  pipeline.py         draft / refuse orchestration, including the licence gate
  cli.py              command-line entry point
prompts/rewrite.txt   the label guardrail prompt, hashed into every transcript
prompts/research.txt  the web-research and structured-citation prompt
server.py             local server for collection search and encyclopaedia research
index.html            English wiki-style browser view
app.js                browser presentation; no drafting or grounding logic
styles.css            styling
skills/labeldesk/     single-file skill contract for other agent environments
data/
  frozen_corpus.json            20 Met Open Access records, values copied verbatim
  frozen_corpus.sha256
  frozen_corpus_egyptian.json   10 Egyptian Art records, second department
  frozen_corpus_egyptian.sha256
  frozen_corpus_cleveland.json  10 Cleveland Museum of Art records, second museum
  frozen_corpus_cleveland.sha256
  sources.json                  every source examined: robots, licence, policy, decision
  golden_set.json               15 record cases + 3 request cases, hand-written expectations
  llm_transcripts.json          37 recorded model responses, keyed by corpus
eval/
  evaluate.py         golden-set scorer, --llm and --compare, writes eval/reports/
  cross_corpus.py     every record in every corpus, both modes, no per-record expectations
  probes.json         12 hand-labelled sentences for the grounding rule
tests/                pytest suite (248 tests on 16 Nov 2026, Python 3.12.6)
tools/
  fetch_corpus.py     rebuild any corpus from its museum API (--preset, --check)
  check_sources.py    re-fetch every robots.txt and report drift against the register
  import_records.py   bring in records by hand and register the licence asserted
  build_standalone.py build labeldesk.html from a fresh run of the pipeline
  record_transcripts.py  record or verify the model transcripts
docs/
  DATA_SOURCES.md     why each source was admitted, refused or deferred
  DEMO_SCRIPT.md      shot list for the 60-second recording
  REVIEW_CHECKLIST.md the curator's half of the system
  MODEL_LAYER_DECISION.md  the Week 10 keep-or-cut decision, with evidence
```

## Data

- Sources: The Metropolitan Museum of Art Open Access and The Cleveland Museum of Art Open
  Access, both CC0 1.0. Field values in the corpus files are copied verbatim from the object
  records; blanks are the museum's own blanks, not missing data introduced by the team.
- Primary corpus checksum: `bdb51f3a20aeefc83d592d958e9dfa53435001e08b676ba649664a0d3d851f07`
- Egyptian corpus checksum: `878195ccdf83ae09c94d44f6ee626ca1c15a6fecfa5d21c960236421160edf8a`
- Cleveland corpus checksum: `144d59a46965693254eb7ec70bf0c977e7144c16a904c39c9c4e163859c8cab9`
- Records now also carry `image_url` and `image_thumbnail`. These are populated only for
  public-domain/CC0 objects; closed-licence records have blank image fields.
- Frozen 2026-10-23 (primary) and 2026-11-01 (Egyptian, Cleveland). Six of the primary
  records are boundary cases, kept on purpose so the refusal path can be demonstrated
  without inventing a broken record.
- `fetched_at` is pinned per preset, not read from the clock, so `--check` is a real test
  rather than a same-day coincidence. All three corpora rebuild byte-identically.
- The Cleveland corpus is filtered to `share_license_status == "CC0"` at fetch time, so
  nothing outside the open-access set can reach the file.

## What this does not do

It does not authenticate, appraise, price, insure or clear rights for any object. It does
not replace the curator's judgement or the museum's record. It does not process personal
data — the corpora contain none. It does not crawl a museum that has not granted access:
two were asked and refused, and the refusal is recorded rather than routed around. Every
label ends with the same notice: *draft for curator review, not an official record*.

## Known limitations

- **The word band is met partly with framing sentences.** A record with short field values
  would render under 60 words, so the renderer appends one or two carrier-only sentences
  ("No fact outside that record has been added."). They add no facts and are listed in the
  output as `padding`, but they are not exhibition prose. Egyptian records, whose medium is
  one word ("Granite"), lean on this most.
- **The check is conservative.** It can reject a sentence a curator would accept — a
  paraphrase that reorders a value, or a possessive. Rejections are returned with a reason
  and counted in the evaluation rather than tuned away.
- **Five fields, one claim each.** The renderer has no grammar of its own, and the model may
  not merge two fields into one sentence, so the prose ceiling is low by construction. That
  constraint is what makes the check exact.
- **The model is accepted on most records, not all.** 11 of 13 on the recorded golden run,
  35 of 37 across all three corpora. A discarded rewrite costs nothing but fluency; the
  label that prints is the offline draft.
- **`--llm` is not the default and should not be.** A reader who never passes it never
  touches the network, and the offline path is the one the evaluation treats as canonical.
- **Three corpora is not a survey.** They were chosen because their sources permit the use,
  which is a selection effect: a museum that refuses automated access also tends not to
  publish the kind of record this tool needs. The pipeline is museum-agnostic; the evidence
  is two museums wide.
- **The frozen corpus is 40 records, not a collection.** It remains the deterministic CLI
  and regression baseline. The browser is not limited to it: live search covers both museums,
  and web-only research covers themes without a museum match.
- **Citation resolution is not a factual proof.** The research layer verifies that every
  paragraph cites a page actually returned by the tools, but readers and curators must still
  judge whether the source adequately supports the wording. The UI therefore labels this
  material as AI-organised and keeps the original links visible.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: labeldesk` | Run from the repository root, or use `python3 -m labeldesk`. |
| `pytest: command not found` | `python3 -m pytest -q` after `python3 -m pip install -r requirements.txt`. |
| Browser search or research is unavailable | Check network access and `LABELDESK_API_KEY`; the museum record remains readable without research. |
| Port 8000 already in use | `python3 server.py --port 8080`. |
| `--llm` says `rewrite discarded: no_key` | No key in `.env` and no live call attempted. Drop `--llm`, or add a key, or use `--llm --replay`. |
| `--llm` says `transcript_stale` | `prompts/rewrite.txt` changed after the transcript was recorded. Re-record with `python3 tools/record_transcripts.py --force`. |
| `--llm` says `not_json` | The model answered in prose. It is a rejection by design, not a crash; the offline draft prints. |
| `--llm` is slow the first time | A live call with a cold prompt cache. `--llm --replay` is instant. |
