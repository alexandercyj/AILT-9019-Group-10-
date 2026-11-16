# Report discrepancies

Read-only comparison on 16 Nov 2026 of `report.pdf` and `AILT9019_Final_Report_Group10.docx` from commit `836f232` against the code and the evaluations run that day. Neither file was edited. The PDF and the docx say the same things (word overlap about 0.99). `tools_build_report.py` is the generator that produced those sentences. It was not run.

These are suggested edits for a person on the team. They are not filled-in contributions.

## Matches

- Team ID G10, repository `https://github.com/alexandercyj/AILT-9019-Group-10-`.
- Public webpage and both YouTube links are still `[add URL before submission]`. That matches `links.txt`: nothing is hosted and no video has been uploaded.
- Golden gates in the report (17/17, claim precision 100%, citation resolution 100%, 72/72, probes 100% with 0 false accepts, 11/13 rewrites) match `eval/evaluate.py` and `eval/evaluate.py --llm --replay` on 16 Nov 2026. Replay was recorded output.
- Record `62.98.1` refusal text matches the CLI and the offline page.
- Cleveland is named as admitted. The Art Institute of Chicago is named as deferred. That matches `data/sources.json`.
- The report says replayed transcripts are not live execution. Keep that sentence.

## Update before submission

| Report text | What the current tree shows | Suggested edit |
| --- | --- | --- |
| “224 passed” and “224-test suite”, including the verification field | Python 3.12.6, pytest 9.1.1: 245 passed on 16 Nov 2026 | Replace 224 with 245 and name Python 3.12.6. The proposal asks for 3.12+. |
| Refusal reasons: missing field, out of corpus, out of scope | A fourth reason, `unknown_maker`, refuses “who made this?” on `14.40.377` and does not invent an artist | Add that case. It is not in the 17-case golden set. |
| “The must-have scope is unchanged” | The five fields are unchanged. The named fallback, the Art Institute of Chicago, is deferred; Cleveland was used | Say that in the same sentence so “unchanged” is not read as “no dataset change”. |
| No Python version | Verified on 3.12.6 | State it in the reproducibility section. |
| No Week 2 brief | The detailed Week 2 Build Start file was not accessible | One sentence in limitations. Do not invent the brief. |
| `tools/fetch_corpus.py --check` as a verification step | Not run on 16 Nov. The command refetches museum records | Say it was not re-run in this pass, or run it later when a network fetch is intended. |
| Cross-corpus “35/37 rewrites accepted” | Not re-run on 16 Nov | Leave the number only if someone re-runs `eval/cross_corpus.py` offline or on replay and gets it again. This pass does not confirm it. |
| “PDF export was dropped” | `export_pdf.applescript` still exports the course report. It no longer contains a personal Desktop path. It was not executed | Say the product does not export labels to PDF, and that the script only exports this course report beside itself. |

## Do not treat as verified

- Section 6 assigns specific work to Chen Yongjun, Cheng Chi Man, Gunawan Alexander, and Sheikh Mohammad Saarim, says all four spoke, and says the statement was agreed on 13 Nov 2026. Git history before this session has one author, 陈泳钧. Review work would not have to appear as a commit. This pass did not watch anyone speak and did not see a Moodle receipt. Leave those sentences for the people named to confirm or correct.
- “58-second demo recording”: `docs/demo.mp4` is 4,986,215 bytes and Spotlight reports 58 seconds. The file was not played. Speakers, captions, and whether it shows a real failure were not checked.
- “AI-assisted code and report text reviewed by Chen Yongjun” and the other members checking their entries: not observed here.
- This session’s code and scaffold were written with a Cursor agent (Grok 4.7) on 16 Nov 2026. The committed PDF does not mention that, because the PDF predates it. Add it to the seven AI-use fields if those outputs are kept. Do not count the local commits as a member’s contribution.

`docs/REPORT_SCAFFOLD.md` has the measured numbers and blank contribution rows. It does not replace the PDF.
