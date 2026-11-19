# Staged release, 16–19 Nov 2026

Local only. This file does not push, open a pull request, merge, or deploy. Nothing here is a grade.

No file on this machine states a rule of 10 commits a day. If the GitHub collaboration guide requires that, this branch does not earn it. Empty or padded commits will not be added to make the number. The commits below are real changes by `AI-assisted local edit`. They are not member contributions.

The offline suite and `requirements.txt` stay the gate for every batch. The core path does not gain a required network call. Live model calls are not part of the remaining batches.

## 16 Nov — done locally, not released

Product fixes, two live rewrites, opt-in spend gates, the cross-corpus re-run, the read-only museum compare, the report candidate, and the draft packager. The branch is `cursor/ailt9019-local-product-69c3`. It has no upstream from this run.

`tools/package_submission.py` writes a draft ZIP and exits 1. `final_ready` stays false while the webpage, both YouTube links, the contribution approval, and an updated PDF are missing.

## 17 Nov — first batch that could be pushed

Only after the user asks for the push. Contents would be the commits already tested on Python 3.12.6, including `.github/workflows/py312.yml`. No merge to `main` unless the team says so. No new model call. If there is no further code defect to fix, this day does not get extra commits, and a 10-commit minimum cannot be earned.

## 18 Nov — human items

The four named members record the presentation and the demo, and they write Section 6. This agent does not invent speaking or contributions. Code changes on this day are only fixes for a failing test. If the team does not record the videos, the day has no genuine code commit from this work, and a 10-commit minimum cannot be earned.

## 19 Nov — package, still not submitted by this agent

A person exports the updated PDF without overwriting `report.pdf` until they choose to replace it, fills `links.txt` with real https URLs, and adds `docs/CONTRIBUTION_APPROVAL.txt`. Then they re-run `python3 tools/package_submission.py`. Exit 0 is possible only after those items exist. This agent does not upload the ZIP.

If 17–19 Nov produce no new tested change, say so in the next note. Do not backfill commits.
