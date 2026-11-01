# Model off vs model on

Both runs are the same 15 record cases, 2 request cases and 12 boundary probes,
scored by the same gates. The point of the comparison is that turning the model
on changes the prose and nothing else: the gates below must be identical.

| Run | Cases | Claim precision | Citation resolution | Readability | Probe agreement | False accepts | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| model off | 17/17 | 100% | 100% | 100% | 100% | 0 | PASS |
| model on | 17/17 | 100% | 100% | 100% | 100% | 0 | PASS |

## Label source per case

| Case | Catalogue | Model off | Model on | Words off → on |
| --- | --- | --- | --- | --- |
| g01 | 14.40.377 | offline_template | llm_rewrite | 65 → 61 |
| g02 | 20.45 | offline_template | llm_rewrite | 60 → 66 |
| g03 | 93.3.115 | offline_template | llm_rewrite | 67 → 61 |
| g04 | 65.1.2 | offline_template | llm_rewrite | 60 → 64 |
| g05 | 1999.247.1 | offline_template | llm_rewrite | 63 → 67 |
| g06 | 1970.103a–e | offline_template | offline (discarded: drops_field_content) | 63 → 63 |
| g07 | 2001.732 | offline_template | llm_rewrite | 67 → 63 |
| g08 | 74.51.524 | offline_template | llm_rewrite | 63 → 67 |
| g09 | 1978.11.10 | offline_template | llm_rewrite | 66 → 62 |
| g10 | 62.173.7 | offline_template | llm_rewrite | 64 → 60 |
| g11 | 36.120.655 | offline_template | offline (discarded: drops_field_content) | 69 → 69 |
| g12 | 2013.872 | offline_template | llm_rewrite | 60 → 65 |
| g13 | 67.182.1 | offline_template | llm_rewrite | 66 → 62 |
| g14 | 62.98.1 | none | none | 0 → 0 |
| g15 | 09.13.5 | none | none | 0 → 0 |

## Model layer in the on-run

- attempted **13**, accepted **11** (85%), discarded **2**
- discard reasons: `drops_field_content` × 2

A discarded rewrite is not a failure. The offline draft is printed in its
place, which is why every gate above still passes in the on-run. The
acceptance rate measures prose quality, not correctness.

**Gate values identical across both runs: yes.**
