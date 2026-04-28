# Languedoc 2022 Batch Validation

Run date: 2026-04-28

Input manifest:

- `examples/rpg_2023_vineyard_candidate_manifest.json`
- Region filter: `languedoc`

Command:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region languedoc \
  --max-items 40 \
  --output-json reports/languedoc-2022-batch-validation.json \
  --output-md reports/languedoc-2022-batch-validation.md
```

## Result

The Languedoc batch completed all five RPG vineyard AOIs with crop masks enabled:

| Metric | Value |
| --- | ---: |
| AOIs | 5 |
| Successful live validations | 5 |
| Accepted | 2 |
| Ambiguous | 3 |
| Rejected | 0 |
| Failed | 0 |
| Triggered AOIs | 5 |
| Crop-mask AOIs | 5 |
| Target periods | 30 |
| Baseline-supported periods | 29 |

AOI outcomes:

| AOI | Assessment | Reason | Baseline periods | Min valid px | Mean cloud % | Min baseline percentile |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `FR_RPG23_PIC_SAINT_LOUP_01` | accepted | clear_drought_trigger | 6 | 1563 | 0.4393 | 0.1000 |
| `FR_RPG23_PIC_SAINT_LOUP_02` | accepted | clear_drought_trigger | 5 | 1193 | 0.0000 | 0.0000 |
| `FR_RPG23_MINERVOIS_01` | ambiguous | quality_warnings_require_review | 6 | 121 | 15.8646 | 0.2500 |
| `FR_RPG23_MINERVOIS_02` | ambiguous | quality_warnings_require_review | 6 | 1274 | 9.5816 | 0.5556 |
| `FR_RPG23_BEZIERS_01` | ambiguous | quality_warnings_require_review | 6 | 127 | 15.8424 | 0.6364 |

## Interpretation

The Languedoc batch gives a useful stress test of the deterministic trigger. The engine
finds water-stress trigger candidates on all five AOIs, but only two are clean validation
wins. Three AOIs remain `ambiguous` because at least one target period has high cloud or
low clear-fraction warnings, with valid-pixel counts dropping as low as `121` and `127`.

This is the right behavior for a POC: the report keeps the signal inspectable without
counting cloudy or unstable periods as clean actuarial proof.

## Calibration Notes

No Languedoc-specific parameters were used in this run. The same `--max-items 40`,
seasonal sampling, crop-mask, SCL masking, and drought classifier thresholds were used as
the Bordeaux run.

The batch does reveal a calibration question for `#14`: some Languedoc target periods
have low absolute NDMI/EMA values but high same-season baseline percentiles. That means
the current absolute threshold (`ndmi_ema_below_0.15_for_2_periods`) should be compared
against a percentile-aware rule before the final M3 customer-facing report.

## Caveat

This is not yet the final M3 validation report. It still needs NDMI threshold calibration
and a failure-mode appendix before it becomes customer-facing.
