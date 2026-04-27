# First Real Mask Benchmark

Run date: 2026-04-27

Input manifest:

- `examples/rpg_2023_first_real_benchmark_manifest.json`

Command:

```bash
orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 80 \
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
| Crop-mask non-crop pixel delta vs raw | 4596 |
| Crop-mask min NDMI EMA delta vs raw | 0.0019 |

Interpretation: the RPG crop mask beats buffer-only for measurable contamination removal
on this AOI, because buffer-only removes zero tracked non-crop pixels while the external
crop mask removes 4596. The tradeoff is a larger valid-pixel loss, but still far above
the `min_valid_pixels` threshold.

## Caveat

Do not use this run as drought-event proof. All variants were rejected by the drought
validation classifier because the July-August 2022 periods had no seasonal baseline
support (`no_baseline_support`). This is now tracked as a follow-up investigation before
closing the 2022 drought validation milestone.
