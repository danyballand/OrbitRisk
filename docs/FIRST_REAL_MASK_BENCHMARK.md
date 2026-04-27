# First Real Mask Benchmark

Run date: 2026-04-27

Input manifest:

- `examples/rpg_2023_first_real_benchmark_manifest.json`

Command:

```bash
orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 40 \
  --no-cache \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```

AOI:

- `FR_RPG23_BORDEAUX_RIGHT_BANK_01`
- Source: IGN RPG 2023 WFS, `RPG.2023:parcelles_graphiques`
- Crop: vineyard, `code_group=21`
- Region: Bordeaux
- Crop-mask coverage: `87.1863%`

## Result

The first real benchmark completed all three variants:

- `raw_aoi`
- `buffered_aoi`
- `vector_crop_mask`

Basis-risk classification: `improved`

Reason: `non_crop_pixels_removed`

Key metrics:

| Metric | Value |
| --- | ---: |
| Raw median valid pixels | 3341 |
| Buffered median valid pixels | 2989 |
| Crop-mask median valid pixels | 2606 |
| Buffered valid-pixel delta vs raw | -10.5358% |
| Crop-mask valid-pixel delta vs raw | -21.9994% |
| Crop-mask non-crop pixel delta vs raw | 14937 |
| Crop-mask min NDMI EMA delta vs raw | 0.0022 |
| Raw drought validation assessment | accepted |
| Crop-mask drought validation assessment | accepted |
| Baseline-supported target periods | 6 |

Interpretation: the RPG crop mask beats buffer-only for measurable contamination removal
on this AOI, because buffer-only removes zero tracked non-crop pixels while the external
crop mask removes 14937. The tradeoff is a larger valid-pixel loss, but still far above
the `min_valid_pixels` threshold.

## Baseline Fix

The first live run exposed a sampling bug: a global `--max-items` budget could be consumed
by recent 2022 scenes before enough 2019-2021 same-season scenes reached the seasonal
baseline calculator. The Planetary Computer provider now stratifies multi-year seasonal
queries by year and samples each June-August slice chronologically.

With `--max-items 40`, each target period now has baseline support (`ndmi_baseline_count`
from 6 to 9), all three variants produce a clear drought trigger
(`ndmi_ema_below_0.15_for_2_periods`), and the drought validation classifier marks the
AOI as `accepted`.

## Caveat

The `--max-items 80` rerun proved the stratified search distribution in a live diagnostic
(`20` items per year from 2019 through 2022), but the full raster benchmark timed out on
Planetary Computer. `--max-items 40` is the current reproducible live budget for this
single-AOI benchmark until the pipeline moves to async jobs or chunked artifact storage.
