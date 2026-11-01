# Curator review checklist

The proposal's Risk 3 promises that "a human review checklist ships with the
README". This is that checklist. It exists because the tool can prove a label is
*grounded* and cannot prove it is *good*: taste, emphasis and audience stay with
the curator.

Ten minutes per label, in this order. Each item is a question with a yes/no answer,
and a "no" is not a defect in the tool unless the item says so.

## 1. Is every sentence traceable?

- [ ] Read the label next to the `Claims` block. For each sentence, find its
      `source_field` and `value_span`. A sentence with no claim is a defect.
- [ ] For each claim, confirm the `value_span` is still present, verbatim, in the
      catalogue record you hold. If the record changed after the corpus was frozen,
      the label is stale — re-freeze rather than editing the label.
- [ ] Confirm `checks.passed` is `true` in the run that produced this label. If it is
      `false`, the label is not reviewable: report the failing check instead.

## 2. Are the record's own hedges still there?

- [ ] `ca.` / `circa` / `around` — still approximate? The tool may reword a hedge but
      may not remove it.
- [ ] `probably` / `possibly` / `presumably` — still a probability, not a statement?
- [ ] `(?)` — still printed? It is the museum saying it is unsure, and it is the
      first thing a fluent rewrite tends to drop.
- [ ] `or` in a culture field ("Seleucid or Parthian") — still disjunctive? Collapsing
      it picks a side the record did not pick.

If any of these was resolved into a firmer statement, the tool has failed and the
failure should be reported, not edited around.

## 3. Is the wording the record's wording?

- [ ] Place and culture names come from the record's own fields, not replaced with
      generic terms ("the ancient world", "Asia").
- [ ] The credit line is reproduced, not paraphrased. It is a legal statement about
      ownership and it is the one field that must be verbatim.
- [ ] The medium is quoted or truncated at a real boundary, never summarised into a
      category ("stone" for "Green porphyry").

## 4. Does it read as a label?

- [ ] 60–80 words, average sentence under 20 words — already checked, but read it.
- [ ] No sentence opens with the same words as the one before it. The templates are
      fixed, so this is the most common cosmetic problem.
- [ ] No claim sounds like a database report ("The place or culture field of the
      record states China"). Rewrite for the wall; the claim structure survives
      rewording, and the tool will check it again.
- [ ] The `padding` sentences, if any, are carrier-only. If a padding sentence has
      started to say something about the object, that is a defect: padding must
      add no facts.

## 5. Is the framing right?

- [ ] The notice is present: *Draft for curator review, not an official record.*
- [ ] Nothing in the label asserts authenticity, value, date of acquisition, rights
      status or attribution beyond what the record states.
- [ ] If the record was refused (`out_of_corpus`, `missing_required_field`,
      `out_of_scope`), the correct action is to supply the missing catalogue
      information or to decline — never to write the label by hand and file it as
      tool output.

## 6. Sign-off

- [ ] Reviewer name and date recorded next to the label.
- [ ] Any rejected label kept, with the reason. Rejections are the evaluation's
      diagnostic data; a rejection rate of zero usually means nobody is reading.

---

### What to send back to the team

One line per rejected label: the catalogue number, the item above that failed, and
the sentence. That is enough to tell a template problem from a corpus problem from a
reviewer's taste, and it is what the spurious-rejection log in
`eval/reports/` is meant to be read against.
