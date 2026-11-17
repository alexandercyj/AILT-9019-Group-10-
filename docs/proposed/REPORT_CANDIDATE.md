# Final report candidate — Group 10 · Label Desk

This file is a proposed replacement for the measured sentences in the teammate draft. It is not the submitted PDF. It has not been reviewed by Chen Yongjun, Cheng Chi Man, Gunawan Alexander, or Sheikh Mohammad Saarim. `report.pdf` and `AILT9019_Final_Report_Group10.docx` were not edited.

Team ID: G10. Project: Label Desk. Repository: https://github.com/alexandercyj/AILT-9019-Group-10-

Public webpage: not published. Presentation video: not recorded. Demo video: not recorded. See `links.txt`. Do not describe `site/index.html` or `labeldesk.html` as a hosted page.

Status on 18 Nov 2026: the 16 Nov measurements in this candidate still stand. After the 03:50 HKT publish of `e3e84a6e72885e1920e043ad196f2cd57d3c3a09`, the feature branch `cursor/ailt9019-release-69c3` is at that commit. The earlier 01:42 HKT publish was `b326b98086baa13876661a30901dc73a11f99100`, after the 23:45 HKT publish of `11b1d96c32b7673ad2a8562dede2da34d1d6e561` on 17 Nov 2026. `main` remains `836f232a44565e087b304b04c3e453def2e189ce`. No pull request was opened. This file is not a Moodle submission.

GitHub Actions workflow "Python 3.12 offline tests" completed successfully on `e3e84a6`: https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44163068879

The earlier publishes also have successful Actions runs: `b326b98` at https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44139989242 and `11b1d96` at https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44117984127

The final project rubric states the Moodle deadline as 23:59, 20 November 2026 (UTC+8). The late cutoff is 23:59, 25 November 2026 (UTC+8).

GitHub Pages is not enabled on the repository. The GitHub identity that can push this branch has no admin or maintain permission, so Pages was not turned on here. `site/index.html` is now a local public landing page with a skip link, a drafted label, and a refusal, but it is still a local file, as is `labeldesk.html`. Do not treat a github.io URL as a published page.

`tools/package_submission.py` still reports `final_ready: false` because the public https webpage, both YouTube links, `docs/CONTRIBUTION_APPROVAL.txt`, and an updated report PDF are missing. It also refuses a guessed github.io URL while this tree still says GitHub Pages is not enabled, a raw.githubusercontent.com URL, and a loopback or private host.

## 1. Background

Label Desk drafts a short exhibition label from one frozen museum record and cites the fields it used. It refuses when a required field is blank, when the object is outside the corpus, when the question asks for a value or an authentication, and when the question asks who made an object the record does not name.

The five required fields are unchanged. The named fallback, the Art Institute of Chicago, is still not a frozen corpus. Cleveland was frozen instead. On 16 Nov 2026 the Art Institute API answered again; that observation is in `docs/FRESHNESS_2026-11-16.md` and did not add records.

The Week 2 Build Start brief was not available. Requirements used here are the two submitted proposals, the midterm requirements, the final rubric, the final report template, and the GitHub collaboration guide.

## 2. Pipeline

Input is a catalogue number, or a question about one record. The offline path loads the frozen corpus, checks the request, renders a label, and runs the grounding checks. A rewrite is optional. Replay uses `data/llm_transcripts.json` and does not call a model. A live rewrite is refused by `server.py` unless the process was started with `--allow-live`. Web research is refused unless it was started with `--allow-research`. Ordinary search does not call research.

## 3. Evaluation

Question: does every golden case draft or refuse as specified, with claim precision and citation resolution at 100% both with the model off and with recorded replies?

Method on 16 Nov 2026, Python 3.12.6: `python3 eval/evaluate.py` and `python3 eval/evaluate.py --llm --replay`. No key was set for those two commands.

| Gate | Model off | Replay | Required |
| --- | --- | --- | --- |
| Cases | 18/18 | 18/18 | all |
| Claim precision | 100% | 100% | 100% |
| Citation resolution | 100% | 100% | 100% |
| Readability | 100% | 100% | 100% |
| Restatements | 72/72 | 72/72 | all |
| Probe agreement | 100% (0 / 0) | 100% (0 / 0) | 100% |
| Rewrites kept | — | 11/13 | no-regression only |

The eighteenth case is request `r03`: “Who made this?” on `14.40.377` must refuse `unknown_maker` and must not say “attributed to”, “painted by”, or “the artist is”. Replay is recorded output. The two discarded golden rewrites used `drops_field_content` and the offline draft was kept.

Cross-corpus, the same day, offline and replay, no live call: 40 records, 37 drafted, 3 refused, 0 check failures, 35 rewrites kept, 2 discarded. The refusals are the blank fields: `62.98.1` and `14.40.372` have no object date; `09.13.5` has no place or culture. The discarded replay rewrites are `1970.103a–e` and `36.120.655`, both `drops_field_content`.

Separate from that replay, two live requests on 16 Nov 2026 used `deepseek-v4.1-flash-1017`, temperature 0, max output 800, retries 0, thinking off. Both were kept by the same checks: `14.40.377` (66 words; prompt 2346, completion 201, total 2547) and `36.120.655` (69 words; prompt 2399, completion 237, total 2636). A third draft, “Who made this?” on `14.40.377`, refused `unknown_maker` and made no request. Evidence: `docs/live_run_2026-11-16.json`. The live acceptance of `36.120.655` is not the replay discard of the older transcript for that record.

Pytest the same day: 252 passed, 0 failed, Python 3.12.6, pytest 9.1.1. The 248 figure was the suite before the cross-corpus and package tests. The same 252-test suite was run again on 17 Nov 2026, 17:51 HKT, Python 3.12.6, pytest 9.1.1, with model keys unset: 252 passed, 0 failed. `python3 tools/build_standalone.py --check` on that tree reported that the shipped file matches a fresh build. The later landing-page and packager tests brought the suite to 257. GitHub Actions run 44078196868 ran that 257-test suite on `47fb841` and succeeded on 17 Nov 2026 at 19:54 HKT. The same 257-test suite was run again on 17 Nov 2026, 21:50 HKT, Python 3.12.6, pytest 9.1.1, with model keys unset: 257 passed, 0 failed. `python3 tools/build_standalone.py --check` reported that the shipped file still matches a fresh build (sha256 2c329428645479d3d69779e319246319fb854a7069afbed80231934c8030f28b). The later github.io packager test brought the suite to 258. GitHub Actions run 44117984127 ran that 258-test suite on `11b1d96` and succeeded on 17 Nov 2026 at 23:46 HKT. The same 258-test suite was run again on 18 Nov 2026, 01:42 HKT, Python 3.12.6, pytest 9.1.1, with model keys unset: 258 passed, 0 failed. `python3 tools/build_standalone.py --check` reported that the shipped file still matches a fresh build (sha256 2c329428645479d3d69779e319246319fb854a7069afbed80231934c8030f28b). The later raw GitHub and loopback packager tests brought the suite to 260. GitHub Actions run 44163068879 ran that 260-test suite on `e3e84a6` and succeeded on 18 Nov 2026 at 03:51 HKT. The same 260-test suite was run again on 18 Nov 2026, 05:44 HKT, Python 3.12.6, pytest 9.1.1, with model keys unset: 260 passed, 0 failed. `python3 tools/build_standalone.py --check` reported that the shipped file still matches a fresh build (sha256 2c329428645479d3d69779e319246319fb854a7069afbed80231934c8030f28b).

## 4. Reproducibility and limitations

A classmate clones the repository, checks out `cursor/ailt9019-release-69c3`, installs `requirements.txt`, and runs `python3 -m labeldesk 14.40.377` with no API key. `python3 -m pytest -q` is the check. `python3 eval/evaluate.py --reports /tmp/labeldesk-reports` writes reports outside the committed files. A clone that stays on the default branch lands on `main` at `836f232a44565e087b304b04c3e453def2e189ce`, which is the earlier teammate snapshot and does not contain this tree.

`tools/fetch_corpus.py --check` was not used to replace the corpora. A separate read-only rebuild on 16 Nov 2026 matched the shipped bytes. Checksums stayed `bdb51f3a20aeefc83d592d958e9dfa53435001e08b676ba649664a0d3d851f07`, `878195ccdf83ae09c94d44f6ee626ca1c15a6fecfa5d21c960236421160edf8a`, and `144d59a46965693254eb7ec70bf0c977e7144c16a904c39c9c4e163859c8cab9`.

Limitations: the Week 2 brief is unread; the public page is still not hosted, even though `site/index.html` is now a local landing page; the two YouTube recordings do not exist; Section 6 is not approved; the Art Institute was not frozen; `docs/demo.mp4` was not played in this pass and is not a YouTube upload. The Moodle ZIP has not been submitted. The rubric deadline is 23:59, 20 November 2026 (UTC+8).

## 5. Ethics and AI-use disclosure

Data are the frozen Metropolitan and Cleveland records already in the repository, CC0, copied verbatim. This candidate does not add personal data. The product does not value an object, authenticate it, or name a maker the cited fields do not name.

Tools and models: Cursor agent (Grok 4.7) on 16 Nov 2026, for local code, tests, the scaffold, and the first form of this candidate. Cursor agent (Grok Bot) on 17 Nov 2026, for the earlier accuracy updates, the local landing-page update, and the packager change that refuses unhosted github.io URLs. Cursor agent (Grok Bot) on 18 Nov 2026, for the earlier accuracy update after the 23:45 HKT publish, the packager change that refuses raw.githubusercontent.com URLs and loopback or private hosts, and this later accuracy update after the 03:50 HKT publish. Product replay model `deepseek-v4.1-flash`. Two live rewrites used `deepseek-v4.1-flash-1017` through the group’s sponsored endpoint. The key file stayed outside the repository at mode 600 and is not in this text. No new live model call was made for this update.

Tasks supported: opt-in gates for live rewrites and research; the unknown-maker golden case; the cross-corpus re-run; the read-only museum compare; this candidate; local packaging that stays unready until the missing items exist, and that does not treat the GitHub repository URL, a guessed github.io URL while Pages is not enabled, a raw.githubusercontent.com URL, or a loopback or private host as a public webpage; the 17 Nov accuracy pass that records the published feature-branch SHA, the Actions run, the rubric deadline, and the checkout required to reproduce this tree; the local landing page in `site/index.html` and the tests that keep it from claiming a host or a video; the 18 Nov accuracy pass that records the 23:45 HKT feature-branch SHA, the 258-test suite, and Actions run 44117984127; the packager change that refuses raw GitHub and loopback URLs; and this later accuracy pass that records the 03:50 HKT feature-branch SHA, the 260-test suite, and Actions run 44163068879.

Representative prompt: the instruction to finish the local project against the proposals, midterm requirements, and final rubric, to use the sponsored key only for a bounded live check, and not to invent the Week 2 brief or member contributions.

Material outputs retained: the local commits on `cursor/ailt9019-local-product-69c3`, the published copies of that tree on `cursor/ailt9019-release-69c3` through `e3e84a6e72885e1920e043ad196f2cd57d3c3a09`, `docs/live_run_2026-11-16.json`, `eval/reports/cross_corpus.md`, `site/index.html`, and this candidate. Those commits are not a member’s contribution. The private product branch is not a public upstream and is not required for reproduction.

Verification: pytest 252 passed on Python 3.12.6 on 16 Nov 2026; golden 18/18 off and replay; cross-corpus 37 drafted and 3 expected refusals; two live rewrites kept. The 252-test suite was re-run on 17 Nov 2026, 17:51 HKT: 252 passed, 0 failed, Python 3.12.6, pytest 9.1.1, keys unset, and the standalone check matched. The published tree at `47fb841` has 257 tests. GitHub Actions run 44078196868 succeeded on that SHA on 17 Nov 2026 at 19:54 HKT. The 257-test suite was re-run on 17 Nov 2026, 21:50 HKT: 257 passed, 0 failed, Python 3.12.6, pytest 9.1.1, keys unset, and the standalone check matched. The published tree at `11b1d96` has 258 tests. GitHub Actions run 44117984127 succeeded on that SHA on 17 Nov 2026 at 23:46 HKT. The 258-test suite was re-run on 18 Nov 2026, 01:42 HKT: 258 passed, 0 failed, Python 3.12.6, pytest 9.1.1, keys unset, and the standalone check matched. The published tree at `e3e84a6` has 260 tests. GitHub Actions run 44163068879 succeeded on that SHA on 18 Nov 2026 at 03:51 HKT. The 260-test suite was re-run on 18 Nov 2026, 05:44 HKT: 260 passed, 0 failed, Python 3.12.6, pytest 9.1.1, keys unset, and the standalone check matched. Earlier Actions runs 44139989242, 44117984127, 44096943198 and 44078196868 succeeded on `b326b98`, `11b1d96`, `439a700` and `47fb841`. A team member still has to review the diff. This agent is not a member of Group 10. The sentence “reviewed by Chen Yongjun” in the earlier draft was not observed here and is not repeated as fact.

Known limitations: Week 2 unread; page unhosted; videos unrecorded; contributions unapproved.

Team members responsible: not assigned by this candidate.

## 6. Individual contributions

Not approved. The 19 Sep 2026 team list names Chen Yongjun, Cheng Chi Man, Gunawan Alexander, and Sheikh Mohammad Saarim. Git history before 16 Nov 2026 is authored by 陈泳钧. This candidate does not assign sections, does not say that anyone spoke, and does not say that a statement was agreed on 13 Nov 2026. The four people have to write `docs/CONTRIBUTION_APPROVAL.txt` themselves. Until that file exists, `tools/package_submission.py` reports `final_ready: false`.

## 7. References

- Repository: https://github.com/alexandercyj/AILT-9019-Group-10-
- The Metropolitan Museum of Art Open Access and the Cleveland Museum of Art Open Access, both CC0. Frozen files and checksums are in `data/`.
- Source register: `data/sources.json`, `docs/DATA_SOURCES.md`, `docs/FRESHNESS_2026-11-16.md`
- Measured reports: `eval/reports/golden_report.md`, `eval/reports/golden_report_llm.md`, `eval/reports/cross_corpus.md`, `docs/live_run_2026-11-16.json`
- Course files used: the two Group 10 proposals, the midterm requirements, the final rubric, the final report template, and the GitHub collaboration guide. The Week 2 brief was not available. The rubric names the Moodle deadline as 23:59, 20 November 2026 (UTC+8).
- Feature branch published 18 Nov 2026, 03:50 HKT: `e3e84a6e72885e1920e043ad196f2cd57d3c3a09`. Actions run: https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44163068879. The earlier 01:42 HKT publish was `b326b98086baa13876661a30901dc73a11f99100`, Actions run https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44139989242. The 23:45 HKT publish was `11b1d96c32b7673ad2a8562dede2da34d1d6e561`, Actions run https://github.com/alexandercyj/AILT-9019-Group-10-/actions/runs/44117984127
