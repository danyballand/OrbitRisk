# OrbitRisk 2022 Batch Mask Benchmark: rpg-2023-first-real-benchmark-aoi

- AOIs: `1`
- Success: `1`
- Skipped: `0`
- Rejected: `0`
- Failed: `0`

## Basis-Risk Summary

| Improved | Degraded | Ambiguous | Not run |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 0 | 0 |

## AOI Summary

| AOI | Region | Status | Completed variants | Detected | Confidence | Crop coverage % | Assessment | Reasons |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | bordeaux | success | 3 | False | 0.8185 | 87.1863 | improved |  |

## Variant Rollup

| Variant | AOIs | Detected | Mean confidence | Mean valid px | Mean cloud % | Min NDMI EMA | Crop coverage % | Non-crop px |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| raw_aoi | 1 | 0 | 0.8753 | 3341.0000 | 0.0000 | -0.0166 |  | 0 |
| buffered_aoi | 1 | 0 | 0.8739 | 2989.0000 | 0.0000 | -0.0162 |  | 0 |
| vector_crop_mask | 1 | 0 | 0.8185 | 2606.0000 | 0.0000 | -0.0147 | 87.1863 | 4596 |

## Chart Artifacts

| AOI | Variant | Metric | Path |
| --- | --- | --- | --- |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | raw_aoi | ndmi | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__raw_aoi__ndmi.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | raw_aoi | valid_pixels | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__raw_aoi__valid_pixels.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | raw_aoi | cloud_pct | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__raw_aoi__cloud_pct.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | buffered_aoi | ndmi | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__buffered_aoi__ndmi.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | buffered_aoi | valid_pixels | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__buffered_aoi__valid_pixels.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | buffered_aoi | cloud_pct | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__buffered_aoi__cloud_pct.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | vector_crop_mask | ndmi | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__vector_crop_mask__ndmi.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | vector_crop_mask | valid_pixels | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__vector_crop_mask__valid_pixels.svg` |
| FR_RPG23_BORDEAUX_RIGHT_BANK_01 | vector_crop_mask | cloud_pct | `reports/charts/rpg-2023-first-real-mask-benchmark/FR_RPG23_BORDEAUX_RIGHT_BANK_01/FR_RPG23_BORDEAUX_RIGHT_BANK_01__vector_crop_mask__cloud_pct.svg` |
