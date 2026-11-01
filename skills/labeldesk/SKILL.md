---
name: labeldesk
description: >
  Draft a cited, plain-language exhibition label from one frozen museum catalogue
  record, or refuse with a named reason. Use when an agent is asked to write a wall
  label, object caption or collection blurb from a record it has been given, and the
  requirement is that every sentence must be traceable to one field of that record.
  Runs offline, standard library only, no key needed. Refuses valuation,
  authentication, insurance and rights questions by design.
---

# Label Desk

One record in, one of two things out: a **drafted** label with five claims and five
citations that pass four automatic checks, or a **refused** result with a named
reason and no label text. There is no third outcome and no free prose.

## Call it

```bash
python3 -m labeldesk <catalogue number> --json
```

Run it from the repository root. `--json` is the contract below; without it the same
result is printed for a human and you would have to parse prose.

Optional, and never required:

| Flag | Effect |
| --- | --- |
| `--llm` | let the model rewrite the draft. A rewrite is kept only if it passes the same four checks; otherwise the offline draft is printed. |
| `--llm --replay` | same, using the recorded response. No key, no network. |
| `--corpus <alias or path>` | use another frozen corpus. Aliases: `primary`, `egyptian`, `cleveland`. |
| `--list` | the catalogue numbers this corpus can answer for. |
| `--ask "<question>"` | route a question through the out-of-scope check. |
| `--sources` | print the source register: what each source allows, and what it was decided. |

`--corpus` takes a registered alias or a path, and an alias that is not registered is an
error rather than a fallback to the default. Reading the wrong records is worse than
stopping.

## Read the result

```json
{
  "status": "drafted",
  "label": "…",
  "claims": [{"id": "c1", "text": "…", "source_field": "title", "value_span": "Vase"}],
  "citations": [{"field": "title", "value_span": "Vase", "label": "title"}],
  "padding": ["…"],
  "notice": "Draft for curator review, not an official record.",
  "word_count": 65,
  "label_source": "offline_template",
  "checks": {"passed": true, "claim_precision": 1.0, "citation_resolution_rate": 1.0, "…": "…"},
  "llm": {"requested": false, "applied": false, "reason": null},
  "record": {"catalogue_number": "14.40.377", "…": "…"},
  "provenance": {"id": "met", "license": "CC0-1.0", "registered": true, "ai_input": true}
}
```

A refusal carries `"status": "refused"`, `"label": null`, and one of three reasons:

| `reason` | Meaning | What you must do |
| --- | --- | --- |
| `out_of_corpus` | the catalogue number is not in the frozen corpus | tell the user the record is not in the corpus. Do not describe a similar object. |
| `missing_required_field` | the record itself is blank in a required field | name the missing field. Do not fill it from memory or from another source. |
| `out_of_scope` | the request asks for value, authenticity, insurance or rights | decline and say why. The tool has no data for any of these. |

A refusal still carries `provenance`, so you can say which corpus was consulted.

## If `--llm` is refused

`llm.reason == "source_policy"` means the corpus's source does not permit its records to
be sent to a model, so nothing was sent and nothing was attempted (`llm.attempts == 0`).
The process exits `4`. The label in the result is the offline draft and is still valid —
report it, and say that the rewrite was not attempted rather than that it failed. Check
`provenance.ai_input` if you need to explain why.

## Guardrails the caller must keep

1. **Never post-process a refusal into prose.** If `status` is `refused`, the answer
   to the user is the refusal, not a label you write yourself.
2. **Never fill a blank field.** A record with no object date is not an invitation to
   infer one.
3. **Check `checks.passed` before quoting the label.** A `false` there means a claim
   failed grounding; report it instead of the text.
4. **Quote `notice` with the label, every time.** It says the label is a draft for
   curator review, not an official record.
5. **Do not summarise a `value_span`.** The span is the exact slice of the record the
   claim cites; shortening it breaks the citation.
6. **Do not add facts of your own** when presenting the result — no style, date,
   origin, provenance or significance that is not in `record`.
7. **Do not route around a policy refusal.** If `llm.reason` is `source_policy`, do not
   try another corpus, another flag or another endpoint to get the same records to a
   model. The refusal is the answer.

## What it is not

Not an authentication, appraisal, valuation, insurance or rights-clearance service.
Not a replacement for a curator or for the museum's own record. It processes no
personal data — the corpora contain none. Its worst case is a draft a curator
rejects, which is why it produces drafts and refusals rather than decisions.

## Where the guardrail lives

The claim structure is emitted by `labeldesk/render.py` and checked by
`labeldesk/grounding.py`: field existence, value containment, citation resolution
and readability. The model layer (`labeldesk/llm.py`) sits behind that check, not in
front of it. `labeldesk/sources.py` sits before it and answers a different question —
whether the corpus's source permits the model at all — which is why `--llm` can be
refused without anything leaving the machine. An agent environment calling this skill
therefore inherits the same guarantee the command line has: there is no second code
path to keep in sync.
