# Label Desk

A cited, plain-language exhibition label drafted from one frozen museum record — with a
machine check that every sentence in the label comes from a field of that record, and a
refusal path for records that cannot supply one.

AILT9019 Group 10. Midterm check, October 2026.

---

## What works today

One command takes a catalogue number from a frozen 20-record corpus of Met Open Access
(CC0) objects and prints one of two things:

- **drafted** — a 60–80 word label, five claims, five citations, and four automatic checks
  that all pass;
- **refused** — a stated reason and no label text, for a record with a missing required
  field, a catalogue number outside the corpus, or an out-of-scope request.

There is no model in the core path and no network call at run time. The same record always
produces the same label.

---

## Setup

Requires Python 3.10 or newer. No third-party package is needed for the core path.

```bash
git clone https://github.com/alexandercyj/AILT-9019-Group-10-.git
cd AILT-9019-Group-10-
python3 --version          # 3.10 or newer
```

`pytest` is the only dependency, and only for the test suite:

```bash
python3 -m pip install -r requirements.txt
```

Nothing to configure, no environment variables, no API key.

---

## Run the core path

One command, no arguments to remember beyond the catalogue number:

```bash
python3 -m labeldesk 14.40.377
```

Expected output (this is the whole result, not an extract):

```text
Label Desk 1.0.0 · offline draft
Corpus  labeldesk-frozen-corpus v1.0.0 · 20 records · sha256 962e03aba0b6
Record  14.40.377 · Vase · Met object 42229 · Asian Art

STATUS  DRAFTED
Label   65 words (band 60–80)

  The object is titled "Vase". The catalogue dates it to 1713–22. The medium is
  recorded as "Porcelain with peach-bloom glaze (Jingdezhen ware)". Its place or
  culture is given as China. The credit line reads: Bequest of Benjamin Altman,
  1913. Every sentence above restates one field of the catalogue record. No fact
  outside that record has been added. Draft for curator review, not an official
  record.

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

  Draft for curator review, not an official record.
```

Exit codes: `0` drafted and every check passed, `1` drafted but a check failed,
`3` refused. Refusal is a designed outcome, so it gets its own code rather than an error.

### Three sample catalogue numbers

| Command | What it shows |
| --- | --- |
| `python3 -m labeldesk 14.40.377` | Well-formed record, plain draft. |
| `python3 -m labeldesk 36.120.655` | Hedged date: the label keeps `ca. 1740`. |
| `python3 -m labeldesk 62.98.1` | Refusal: the record has no object date. |

Other entry points:

```bash
python3 -m labeldesk --list                          # the 20 catalogue numbers
python3 -m labeldesk --info                          # corpus metadata and checksum
python3 -m labeldesk 14.40.377 --json                # full machine-readable result
python3 -m labeldesk 14.40.377 --ask "what is it worth?"   # out-of-scope refusal
```

### Browser view (optional)

```bash
python3 server.py            # http://127.0.0.1:8000
```

The page posts the selected catalogue number to the same Python pipeline and draws the
result. It contains no second implementation of the renderer or the check, so the two
paths cannot disagree. Add `#refuse` to the URL (`http://127.0.0.1:8000/#refuse`) to open
on the refusal path.

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

Expected: `51 passed`. The suite is not a smoke test — it breaks the output on purpose and
requires the check to catch it:

| Test file | What it proves |
| --- | --- |
| `tests/test_corpus.py` | 20 records, checksum matches `data/frozen_corpus.sha256`, lookups resolve. |
| `tests/test_core_path.py` | Five claims, word band, notice, determinism, hedges kept. |
| `tests/test_refusal.py` | Missing field, unknown number and out-of-scope questions all refuse. |
| `tests/test_grounding.py` | Invented place, narrowed date, dropped hedge and dropped `or` are rejected. |
| `tests/test_render.py` | Long values are shortened to a prefix that still resolves. |
| `tests/test_golden.py` | The evaluation below passes, and the CLI exit codes are right. |

### 3. The golden set

```bash
python3 eval/evaluate.py
```

Expected:

```text
Golden set · 17/17 cases passed
  claim precision        100%  citation resolution   100%  readability 100%
  restatements           72/72  probe agreement 100%  (false accepts 0, spurious rejections 0)
```

`data/golden_set.json` holds 15 record cases (10 well formed, 5 boundary) and 2 request
cases, each with the record values a correct label must restate and the outcome it must
produce. `eval/probes.json` holds 12 single sentences labelled pass or fail, which test the
grounding rule rather than the templates. The script writes
`eval/reports/golden_report.md` and `.json`; it exits `1` if any gate is missed.

To reproduce the corpus byte for byte:

```bash
python3 tools/fetch_corpus.py --check
```

---

## The core path, in five steps

1. **Look up** the catalogue number in `data/frozen_corpus.json`. Not found → refused as
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

---

## Refusals

| Input | Reason | What it prints |
| --- | --- | --- |
| `62.98.1` | `missing_required_field` | "Record 62.98.1 has no object date. No label was drafted: a blank field is not filled from outside the record." |
| `09.13.5` | `missing_required_field` | Same, for place or culture. |
| `99.99.99` | `out_of_corpus` | "… is not in the frozen corpus … the system does not describe a similar object from memory." |
| `--ask "what is it worth?"` | `out_of_scope` | Valuation, authentication, insurance and rights are declined. |

---

## Repository map

```text
labeldesk/            core pipeline, standard library only
  corpus.py           loading, checksum, required-field list
  validate.py         missing-field detection
  factsheet.py        fact sheet with a pointer per value
  render.py           deterministic renderer and claim emission
  grounding.py        the four checks
  pipeline.py         draft / refuse orchestration
  cli.py              command-line entry point
server.py             local server for the browser view
index.html            browser view (one page)
app.js                browser view logic: calls /api/draft, no logic of its own
styles.css            styling
data/
  frozen_corpus.json  20 Met Open Access records, values copied verbatim
  frozen_corpus.sha256
  golden_set.json     15 record cases + 2 request cases, hand-written expectations
eval/
  evaluate.py         golden-set scorer, writes eval/reports/
  probes.json         12 hand-labelled sentences for the grounding rule
tests/                pytest suite (51 tests)
tools/fetch_corpus.py rebuild the corpus from the Met API (not needed to run)
docs/DEMO_SCRIPT.md   shot list for the 60-second recording
```

## Data

- Source: The Metropolitan Museum of Art Open Access, CC0 1.0. Field values in
  `data/frozen_corpus.json` are copied verbatim from the object records; blanks are the
  museum's own blanks, not missing data introduced by the team.
- Corpus checksum: `962e03aba0b6ff94b53a7822f0c59f2e1c2b6157a58586664df4dfa3a1e97158`
- Frozen on 2026-10-23. Six of the 20 records are boundary cases, kept on purpose so the
  refusal path can be demonstrated without inventing a broken record.

## What this does not do

It does not authenticate, appraise, price, insure or clear rights for any object. It does
not replace the curator's judgement or the museum's record. It does not process personal
data — the corpus contains none. Every label ends with the same notice: *draft for curator
review, not an official record*.

## Known limitations

- **The word band is met partly with framing sentences.** A record with short field values
  would render under 60 words, so the renderer appends one or two carrier-only sentences
  ("No fact outside that record has been added."). They add no facts and are listed in the
  output as `padding`, but they are not exhibition prose.
- **The check is conservative.** It can reject a sentence a curator would accept, for
  example a paraphrase that reorders a value. Rejections are returned with a reason and
  counted in the evaluation rather than tuned away.
- **Five fields, one template set.** The renderer has no grammar of its own; a record whose
  medium is a long list is quoted, not summarised.
- **No model layer yet.** The optional LLM pass in the proposal is not built. The offline
  draft is the whole system, which is the pre-agreed fallback.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: labeldesk` | Run from the repository root, or use `python3 -m labeldesk`. |
| `pytest: command not found` | `python3 -m pytest -q` after `python3 -m pip install -r requirements.txt`. |
| Browser view says "Pipeline not reachable" | `python3 server.py` in another terminal, then reload. |
| Port 8000 already in use | `python3 server.py --port 8080`. |
