# Report scaffold

This is evidence for the final report. It is not the submitted PDF. It does not replace `AILT9019_Final_Report_Group10.docx`, `AILT9019_Final_Report_Template.docx`, or `report.pdf` from commit `836f232`. Those files were left as the teammate committed them. A person on the team still has to reconcile this scaffold with that draft, fill Section 6, and export the PDF.

Team ID: G10. Project: Label Desk. Repository: https://github.com/alexandercyj/AILT-9019-Group-10-

Public webpage: not published. Presentation video: not recorded. Demo video: not recorded. See `links.txt`.

## 1. Background

Label Desk drafts a short exhibition label from one frozen museum record and cites the fields it used. It is for a curator reviewing a draft. It does not value an object, authenticate it, or name a maker the record does not name.

Scope change already recorded by the repository, not decided in this pass: the Art Institute of Chicago is `deferred` in `data/sources.json`. Cleveland was admitted instead. See `docs/DATA_SOURCES.md` and `docs/PROGRESS_2026-11-01.md`.

## 2. Pipeline

Input is a catalogue number, or a question about one record. Processing loads the frozen corpus, checks the request, renders an offline label, and runs grounding checks. Output is a drafted label with claims, or a refusal. An optional rewrite can run in replay mode; the same checks keep or discard it. The optional research layer stays separate and was not called against the network in this pass.

## 3. Evaluation

Question: does every golden case draft or refuse as specified, with claim precision and citation resolution at 100% both with the model off and with recorded model replies?

Method: `python3 eval/evaluate.py` and `python3 eval/evaluate.py --llm --replay` on 16 Nov 2026. No live model call. Replay is recorded output, not a new API call.

| Run | When | Cases | Claim precision | Citation resolution | Readability | Probe agreement | False accepts | Spurious rejections |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| model off | 2026-11-16 after r03 | 18/18 | 100% | 100% | 100% | 100% | 0 | 0 |
| model replay | 2026-11-16 after r03 | 18/18 | 100% | 100% | 100% | 100% | 0 | 0 |

Corpus checksum on both reports: `bdb51f3a20ae`. Restatements 72/72. Replay accepted 11 of 13 rewrites and discarded 2 for `drops_field_content`; those two cases kept the offline draft. Reports: `eval/reports/golden_report.md`, `eval/reports/golden_report_llm.md`, `eval/reports/model_comparison.md`.

Pytest the same day: 252 passed, 0 failed, on Python 3.12.6 (pytest 9.1.1). That count includes the cross-corpus and draft-package tests. An earlier run the same evening, before those tests, was 248. The proposal names Python 3.12+. Replay above is recorded transcripts. A separate live run the same evening made 2 requests, not replay: see `docs/live_run_2026-11-16.json`.

CLI the same day, primary corpus:

| Command | Exit | Observed |
| --- | --- | --- |
| `python3 -m labeldesk 14.40.377` | 0 | DRAFTED, 65 words, checksum `bdb51f3a20ae`, notice “Draft for curator review, not an official record.” |
| `python3 -m labeldesk 36.120.655` | 0 | DRAFTED, 69 words, date kept as `ca. 1740` |
| `python3 -m labeldesk 62.98.1` | 3 | REFUSED, `missing_required_field`, “Record 62.98.1 has no object date.” |
| `python3 -m labeldesk --ask "who made this?" 14.40.377` | 3 | REFUSED, `unknown_maker`. No artist name was added. |

## 4. Reproducibility and limitations

The README section “Six steps to one label” is the install path. No `.env` was present. `labeldesk.html` was rebuilt with `python3 tools/build_standalone.py` and `--check` matched. Embedded `has_key` is false in all 74 result blocks. A key on the build machine no longer changes the offline page.

Failure kept on purpose: record `62.98.1` has no object date, so the pipeline refuses instead of filling one in.

Limitations:

- The Week 2 Build Start brief was not accessible. See `docs/SOURCE_COVERAGE.md`. Requirements used here are the two submitted proposals, the midterm requirements, and the final rubric, template, and GitHub guide.
- Golden model-on numbers above are replay. Two live rewrites are a separate file, `docs/live_run_2026-11-16.json`.
- Cross-corpus on 16 Nov 2026: 37 drafted, 3 expected refusals, 35 replay rewrites kept, 2 discarded. See `eval/reports/cross_corpus.md`.
- The three frozen corpora still match a read-only rebuild. See `docs/FRESHNESS_2026-11-16.md`. The Art Institute answered on 16 Nov and was not frozen.
- Weekly report marks are course records and are not in this repository.
- Section 6 below is empty of member claims because this pass did not observe who did which course task.
- `export_pdf.applescript` no longer contains a personal Desktop path. It was not run. Running it would overwrite `report.pdf`.

## 5. Ethics and AI-use disclosure

Data: frozen Met, Egyptian, and Cleveland records already in the repository, with the licences and statuses in `data/sources.json` and `docs/DATA_SOURCES.md`. A read-only rebuild on 16 Nov 2026 matched those files and did not save new records. The sponsored key stayed outside the repository. No personal data was added.

Does not: value, authenticate, or name a maker the cited fields do not name.

Risk: a fluent rewrite can drop a hedge or a field. Mitigation already in the pipeline: grounding discards the rewrite and the golden replay discarded 2 of 13 for `drops_field_content`.

Tools/models used: Cursor agent (Grok 4.7) on 16 Nov 2026, for the local code, tests, and this scaffold. Replay uses `deepseek-v4.1-flash`. Two live rewrites used `deepseek-v4.1-flash-1017`. See `docs/proposed/REPORT_CANDIDATE.md`.

Tasks supported: repair of clean-checkout `has_key` leakage into offline results; `unknown_maker` refusal; proposal boundary regression; contrast colours; README checksum and test count; English integration notes; evaluation rerun; this scaffold.

Representative prompts / interactions: the session instruction to implement against the two proposals, midterm requirements, and final rubric, and to mark the Week 2 brief as inaccessible.

Material outputs retained: the files in the local commits on `cursor/ailt9019-local-product-69c3`. Those commits are not a team member’s authorship.

Verification performed: pytest 252 passed on Python 3.12.6; model-off and replay evaluations exited 0 at 18/18. Two live rewrites on `deepseek-v4.1-flash-1017` were accepted by the same checks (`docs/live_run_2026-11-16.json`). Replay rows are recorded output, not those live calls. A team member still has to review the diff before any submission. This agent is not a member of Group 10.

Known limitations: Week 2 brief unread; public page not hosted; videos not recorded; member contributions not observed. The draft ZIP is not final-ready.

Team members responsible: not this agent. The people who submit the work remain responsible. Section 6 is unfinished until they write it.

## 6. Individual contributions

HUMAN REQUIRED. Do not copy this scaffold into the report as if the names below did the work listed here. Git history before this session is authored by 陈泳钧. The 19 Sep 2026 team list names Chen Yongjun, Cheng Chi Man, Gunawan Alexander, and Sheikh Mohammad Saarim. The status sheet still has members 2–4 bracketed. This pass did not observe each person’s completed work.

| Member | Sections 1–7 and other work |
| --- | --- |
| Chen Yongjun | HUMAN REQUIRED |
| Cheng Chi Man | HUMAN REQUIRED |
| Gunawan Alexander | HUMAN REQUIRED |
| Sheikh Mohammad Saarim | HUMAN REQUIRED |

Commits on `cursor/ailt9019-local-product-69c3` made in this session are AI-assisted local edits. They must not be counted as one of those four members’ contributions.

## 7. References

- Repository: https://github.com/alexandercyj/AILT-9019-Group-10-
- Corpus register: `data/sources.json`, `docs/DATA_SOURCES.md`
- Measured reports: `eval/reports/golden_report.md`, `eval/reports/golden_report_llm.md`
- Course files used: the two Group 10 proposals, the midterm requirements, the final rubric, the final report template, and the GitHub collaboration guide. The Week 2 brief was not available.
