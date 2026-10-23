# Golden-set evaluation

Generated 2026-10-23 06:27 UTC · Label Desk 1.0.0 · corpus sha256 `962e03aba0b6`

## Gates

| Gate | Result | Required | Status |
| --- | --- | --- | --- |
| outcome_accuracy | 100% | 100% | PASS |
| claim_precision | 100% | 100% | PASS |
| citation_resolution_rate | 100% | 100% | PASS |
| readability_pass_rate | 100% | 100% | PASS |
| restatement_coverage | 100% | 100% | PASS |

- cases passed: **17/17**
- restatements matched: 72/72
- probe agreement: 100% (false accepts 0, spurious rejections 0)

## Record cases

| Case | Catalogue | Expected | Actual | Words | Claim precision | Citations | Restatements | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| g01 | 14.40.377 | drafted | drafted | 65 | 100% | 100% | 7/7 | PASS |
| g02 | 20.45 | drafted | drafted | 60 | 100% | 100% | 6/6 | PASS |
| g03 | 93.3.115 | drafted | drafted | 67 | 100% | 100% | 6/6 | PASS |
| g04 | 65.1.2 | drafted | drafted | 60 | 100% | 100% | 6/6 | PASS |
| g05 | 1999.247.1 | drafted | drafted | 63 | 100% | 100% | 5/5 | PASS |
| g06 | 1970.103a–e | drafted | drafted | 63 | 100% | 100% | 6/6 | PASS |
| g07 | 2001.732 | drafted | drafted | 67 | 100% | 100% | 5/5 | PASS |
| g08 | 74.51.524 | drafted | drafted | 63 | 100% | 100% | 5/5 | PASS |
| g09 | 1978.11.10 | drafted | drafted | 66 | 100% | 100% | 5/5 | PASS |
| g10 | 62.173.7 | drafted | drafted | 64 | 100% | 100% | 5/5 | PASS |
| g11 | 36.120.655 | drafted | drafted | 69 | 100% | 100% | 6/6 | PASS |
| g12 | 2013.872 | drafted | drafted | 60 | 100% | 100% | 5/5 | PASS |
| g13 | 67.182.1 | drafted | drafted | 66 | 100% | 100% | 5/5 | PASS |
| g14 | 62.98.1 | refused | refused | 0 | — | — | 0/0 | PASS |
| g15 | 09.13.5 | refused | refused | 0 | — | — | 0/0 | PASS |

## Request cases

| Case | Request | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| r01 | How much is this vase worth, and is it authentic? | refused | refused (out_of_scope) | PASS |
| r02 | 99.99.99 | refused | refused (out_of_corpus) | PASS |

## Boundary probes

| Probe | Field | Sentence | Expected | Accepted | Rule fired |
| --- | --- | --- | --- | --- | --- |
| p01 | object_date | made around 1750 | pass | yes | — |
| p02 | object_date | made in the mid-18th century | fail | no | unsupported_word |
| p03 | object_date | made in the 18th century | pass | yes | — |
| p04 | object_date | made in 1750 | fail | no | unsupported_word |
| p05 | place_or_culture | probably made in Iran | pass | yes | — |
| p06 | place_or_culture | made in Iran | fail | no | dropped_hedge |
| p07 | place_or_culture | made in Egypt | fail | no | unsupported_word |
| p08 | credit_line | The credit line reads: Rogers Fund, 1920. | pass | yes | — |
| p09 | place_or_culture | made in Hittite | fail | no | dropped_hedge |
| p10 | object_date | The catalogue dates it to late 18th century. | fail | no | dropped_hedge |
| p11 | medium | The medium is recorded as "Porcelain with peach-bloom glaze (Jingdezhen ware)". | pass | yes | — |
| p12 | title | The object is titled "Vase". | pass | yes | — |
