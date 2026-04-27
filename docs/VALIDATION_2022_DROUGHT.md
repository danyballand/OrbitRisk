# 2022 Drought Validation Protocol

## Goal

Use the July-August 2022 drought as the first hard validation event. If the engine cannot
surface a clear water-stress signal on known vineyard regions, the product claim is too
weak for actuarial conversations.

## Regions

- Bordeaux vineyard AOIs.
- Languedoc vineyard AOIs.

The first run should use 5-10 AOIs with enough Sentinel-2 pixels after masking. Tiny AOIs
with fewer than the configured `min_valid_pixels` should be rejected rather than forced
into the benchmark.

## Signal

Primary index:

- NDMI: `(B08 - B11) / (B08 + B11)`

Supporting indices:

- NDVI: `(B08 - B04) / (B08 + B04)`
- NDWI: `(B03 - B08) / (B03 + B08)`

## Baseline

Compare July-August 2022 against a same-day-of-year baseline from the available previous
years. Prefer a 5-year baseline where coverage exists; otherwise report the shortened
baseline explicitly.

## Acceptance Criteria

An AOI counts as detected when all conditions are met:

- At least two consecutive accepted periods have NDMI EMA below the configured seasonal
  percentile threshold.
- `valid_pixel_count` is above the request threshold for each triggering period.
- Cloud/shadow/snow masks do not explain the signal.
- The result includes a clear `trigger_reason` and mask-count audit trail.

The validation report must list:

- accepted AOIs,
- rejected AOIs with rejection reasons,
- ambiguous AOIs,
- naive parcel mean vs RPG + buffer vs OrbitRisk mask comparison,
- charts for NDMI, NDVI, valid pixel count, and cloud percentage.

## Current Runner

OrbitRisk includes a first JSON validation runner:

```bash
orbitrisk validate-2022 tests/fixtures/sample_request.json \
  --region bordeaux \
  --max-items 80 \
  --crop-mask-geojson data/rpg/vineyard-mask.geojson \
  --output-json reports/bordeaux-2022.json \
  --output-md reports/bordeaux-2022.md
```

The runner executes the live Planetary Computer path, filters July-August 2022, and reports
NDMI mean, EMA, anomaly z-score, baseline percentile, baseline count, quality flags, and
critical periods.

Results are cached under `data/cache` by default. Use `--no-cache` to force a fresh run.

`--crop-mask-geojson` accepts a Polygon, MultiPolygon, Feature, or FeatureCollection and
is intended for RPG IGN or other parcel/crop masks. The vector mask is reprojected onto
the fixed Sentinel grid and affects `valid_pixel_count` and `mask_counts.non_crop`.

## Mask Benchmark Runner

The benchmark runner executes three comparable variants:

- `raw_aoi`: no negative buffer, no crop mask.
- `buffered_aoi`: AOI mean with the configured or supplied negative buffer.
- `vector_crop_mask`: external crop mask plus buffer. If no crop mask is provided, this
  variant is marked as skipped rather than silently degraded.

```bash
orbitrisk benchmark-masks-2022 tests/fixtures/sample_request.json \
  --region bordeaux \
  --max-items 80 \
  --crop-mask-geojson data/rpg/vineyard-mask.geojson \
  --crop-mask-crs EPSG:4326 \
  --output-json reports/bordeaux-mask-benchmark.json \
  --output-md reports/bordeaux-mask-benchmark.md
```

The output reports per-variant detection status, confidence, baseline support, median
valid pixels, cloud percentage, minimum NDMI mean/EMA, crop-mask coverage, and deltas
against the raw AOI baseline.

## Batch Mask Benchmark Runner

Use the batch runner once AOIs are listed in an AOI manifest:

```bash
orbitrisk benchmark-masks-batch-2022 examples/aoi_batch_manifest.json \
  --max-items 80 \
  --output-json reports/batch-mask-benchmark.json \
  --output-md reports/batch-mask-benchmark.md
```

The batch runner validates the manifest first, rejects AOIs that fail local geometry or
pixel-support checks, skips accepted AOIs without crop masks by default, and isolates
provider failures so one AOI does not crash the full run. Use
`--include-without-crop-mask` to run partial raw/buffer benchmarks for AOIs that do not
yet have crop masks.

The batch report includes:

- per-AOI status: `success`, `skipped`, `rejected`, or `failed`;
- basis-risk classification counts: `improved`, `degraded`, `ambiguous`, `not_run`;
- per-AOI key metrics for crop-mask coverage, valid-pixel delta, non-crop delta, and
  NDMI EMA delta;
- variant rollups for `raw_aoi`, `buffered_aoi`, and `vector_crop_mask`;
- comparison rollups for buffer-vs-raw and crop-mask-vs-raw.

## Basis-Risk Classifier

The batch classifier is deterministic and intentionally conservative. A crop mask is
classified as `improved` only when it removes measurable non-crop pixels while preserving
enough valid Sentinel-2 support and without materially rewriting the NDMI signal.

Default thresholds:

- `min_crop_coverage_pct`: `5.0`
- `min_non_crop_pixel_delta`: `1`
- `max_valid_pixel_loss_pct`: `75.0`
- `max_abs_ndmi_ema_delta`: `0.15`

Classification rules:

- `not_run`: vector crop mask was missing or skipped.
- `degraded`: empty/low crop-mask coverage, insufficient crop-mask valid pixels versus
  `min_valid_pixels`, or more than 75% median valid-pixel loss.
- `ambiguous`: no measurable non-crop removal, or absolute NDMI EMA shift above `0.15`
  that requires human review.
- `improved`: non-crop pixels were removed and no degraded/ambiguous rule fired.
