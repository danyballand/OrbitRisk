# OrbitRisk 2022 Batch Drought Validation: rpg-2023-vineyard-candidate-pack-languedoc

- AOIs: `5`
- Success: `5`
- Rejected before live load: `0`
- Failed: `0`

## Validation Summary

| Accepted | Rejected | Ambiguous | Not run |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 3 | 0 |

## AOI Summary

| AOI | Region | Status | Assessment | Detected | Confidence | Target periods | Baseline periods | Min baseline pctl | Min valid px | Mean cloud % | Reasons |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| FR_RPG23_PIC_SAINT_LOUP_01 | languedoc | success | accepted | True | 0.7118 | 6 | 6 | 0.1000 | 1563 | 0.4393 | clear_drought_trigger |
| FR_RPG23_PIC_SAINT_LOUP_02 | languedoc | success | accepted | True | 0.7457 | 6 | 5 | 0.0000 | 1193 | 0.0000 | clear_drought_trigger |
| FR_RPG23_MINERVOIS_01 | languedoc | success | ambiguous | True | 0.6278 | 6 | 6 | 0.2500 | 121 | 15.8646 | quality_warnings_require_review |
| FR_RPG23_MINERVOIS_02 | languedoc | success | ambiguous | True | 0.7538 | 6 | 6 | 0.5556 | 1274 | 9.5816 | seasonal_percentile_not_low, quality_warnings_require_review |
| FR_RPG23_BEZIERS_01 | languedoc | success | ambiguous | True | 0.7066 | 6 | 6 | 0.6364 | 127 | 15.8424 | seasonal_percentile_not_low, quality_warnings_require_review |
