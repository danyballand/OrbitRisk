# Bordeaux 2022 Batch Validation

Run date: 2026-04-27

Input manifest:

- `examples/rpg_2023_vineyard_candidate_manifest.json`
- Region filter: `bordeaux`

Command:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region bordeaux \
  --max-items 40 \
  --output-json reports/bordeaux-2022-batch-validation.json \
  --output-md reports/bordeaux-2022-batch-validation.md
```

## Result

The Bordeaux batch completed all five RPG vineyard AOIs with crop masks enabled:

| Metric | Value |
| --- | ---: |
| AOIs | 5 |
| Successful live validations | 5 |
| Accepted | 4 |
| Ambiguous | 1 |
| Rejected | 0 |
| Failed | 0 |
| Triggered AOIs | 5 |
| Crop-mask AOIs | 5 |
| Target periods | 34 |
| Baseline-supported periods | 26 |

AOI outcomes:

| AOI | Assessment | Reason | Baseline periods | Min valid px | Mean cloud % |
| --- | --- | --- | ---: | ---: | ---: |
| `FR_RPG23_BORDEAUX_RIGHT_BANK_01` | accepted | clear_drought_trigger | 6 | 2606 | 0.0000 |
| `FR_RPG23_BORDEAUX_RIGHT_BANK_02` | ambiguous | quality_warnings_require_review | 6 | 1312 | 6.1741 |
| `FR_RPG23_MEDOC_01` | accepted | clear_drought_trigger | 4 | 7411 | 0.0000 |
| `FR_RPG23_MEDOC_02` | accepted | clear_drought_trigger | 5 | 3009 | 0.4301 |
| `FR_RPG23_SAUTERNES_01` | accepted | clear_drought_trigger | 5 | 4468 | 0.0000 |

## Interpretation

This closes the first Bordeaux validation pass: the engine sees the July-August 2022
water-stress event on five real RPG vineyard AOIs, and the classifier does not count the
cloud-flagged right-bank AOI as a clean win.

The ambiguous AOI is useful, not embarrassing: it proves the report can surface a real
quality caveat (`low_clear_fraction` and `high_cloud_fraction`) instead of flattening
everything into a binary success claim.

## Caveat

This is not yet the final M3 validation report. It still needs Languedoc coverage,
threshold calibration, and a failure-mode appendix before it becomes customer-facing.
