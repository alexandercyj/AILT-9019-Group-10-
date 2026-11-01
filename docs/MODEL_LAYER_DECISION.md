# Decision note: the model layer stays

**Date:** 1 November 2026
**Owner:** 陈泳钧
**Item:** midterm status sheet, next two weeks, item 3
**Pre-agreed condition:** if the optional model layer is not passing the factual check
by the cut date, it is dropped and the offline renderer ships as the whole system.

## Decision

**The model layer stays, behind the guardrail, and the offline renderer remains the
default.** No change to the must-have path. `python3 -m labeldesk <number>` still runs
no model and makes no network call.

The cut was conditional on the model layer passing the factual check. It does, in
both of the two runs the proposal requires, on the same gates as the offline run.

## Evidence

All figures are reproducible with the three commands under "Reproduce" below.

| Run | Cases | Claim precision | Citation resolution | Readability | Restatements | Probes | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| model off | 17/17 | 100% | 100% | 100% | 72/72 | 12/12, 0 false accepts | PASS |
| model on, recorded (`--llm --replay`) | 17/17 | 100% | 100% | 100% | 72/72 | 12/12, 0 false accepts | PASS |
| model on, live call, 1 Nov | 17/17 | 100% | 100% | 100% | 72/72 | 12/12, 0 false accepts | PASS |

The gates are identical in all three runs, which is the point: turning the model on
did not move a single gate value.

What the model layer actually did, over the 13 golden cases that produce a label:

| Run | Rewrites accepted | Discarded | Reason for each discard |
| --- | --- | --- | --- |
| recorded | 11/13 (85%) | 2 | `drops_field_content` × 2 |
| live, 1 Nov | 12/13 (92%) | 1 | `drops_field_content` × 1 |

A discarded rewrite is not a failure. The offline draft is printed in its place, so
every case still passes every gate. The acceptance rate measures prose quality; the
gates measure correctness, and correctness did not move.

## What the discarded rewrites taught us

Both discards were the same failure, and it is not one the four checks could see. The model
truncated a multi-part medium value at a delimiter and cited the part it kept:

| Case | The record's medium | What the rewrite cited | What it lost |
| --- | --- | --- | --- |
| `1970.103a–e` | `Five-panel folding screen; lacquer on wood, colors and gold` | `lacquer on wood, colors and gold` | `five-panel folding screen` |
| `36.120.655` | `Clay; moulded frame and shaped supports glazed black; both faces of screen with ivory glaze, decorated with landscapes in black (Tokyo ware)` | `Clay; moulded frame and shaped supports glazed black` | `both faces of screen with ivory glaze, decorated with landscapes in black (Tokyo ware)` |

Nothing false was added. The citation resolved, the span was a real substring, and every
word in the sentence came from the cited slice — the rewrite is *shorter*, which is exactly
the direction the four checks do not police. The label simply lost the words that identify
what the object is made of and what is on it.

This is why the model layer now has a fifth rule, `validate_coverage`: a rewrite may reword
a field but may not retain less of it than the offline draft did. It is a coverage test, not
a factual one, and it is the only rule added to the guardrail for the model layer. Without
it, the honest acceptance rate would have read 13/13 while two labels were quietly worse
than the template they replaced — the most dangerous kind of model failure, because it looks
like success.

The general lesson, which belongs in the final report: a grounding check made of
"nothing false was added" rules is structurally blind to omission. Whatever the guardrail
covers, it needs a subtraction rule as well as an addition rule.

Two earlier prompt revisions were also rejected on evidence, and the reasons are
worth keeping:

- The first prompt let the model name the object type in any sentence ("the vase was
  dated 1713–22"), which pulls a fact out of the title field into the date claim.
  Rejected by value containment, as designed.
- The first assembly forced the model to pad each sentence to reach the word band,
  which produced "The medium field of the record states Ceramic, paint verbatim."
  The model now writes short sentences and the renderer appends its own fact-free
  framing sentences, exactly as the offline path does.

## Conditions attached to keeping it

1. **Off by default.** The model is reached only through `--llm`. A reader who never
   passes it never touches the network.
2. **No key, no failure.** Without a key `--llm` replays the recorded transcript in
   `data/llm_transcripts.json`, which is re-parsed and re-checked on every replay, so
   a transcript cannot smuggle in a rewrite the guardrail would now reject.
3. **The guardrail is not tuned to the model.** The one vocabulary change made for the
   model layer is a documented list of *reporting* words ("keeps", "states", "gives")
   that describe the record rather than the object; it cannot admit a number, date,
   place or name. The twelve boundary probes still agree 12/12 with 0 false accepts.
4. **Re-open the decision if** any model-on run produces a claim that fails
   grounding, or if the acceptance rate falls below half. Either would mean the
   guardrail is carrying the model rather than checking it.

## Reproduce

```bash
python3 eval/evaluate.py                 # model off  -> eval/reports/golden_report.md
python3 eval/evaluate.py --llm --replay  # model on   -> eval/reports/golden_report_llm.md
python3 eval/evaluate.py --compare       #            -> eval/reports/model_comparison.md
```

The live run of 1 November is kept as `eval/reports/golden_report_llm_live.*`. It is
not the committed default because a live call is not reproducible; the recorded run
is, and it passes the same gates.
