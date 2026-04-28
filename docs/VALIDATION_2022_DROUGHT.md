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

For M3, an AOI counts as accepted validation evidence only when all conditions are met:

- The absolute NDMI EMA trigger fires: `ndmi_ema_below_0.15_for_2_periods`.
- At least one target-period NDMI seasonal percentile is at or below `P25`.
- `valid_pixel_count` is above the request threshold for each triggering period.
- Cloud/shadow/snow masks do not explain the signal.
- The result includes a clear `trigger_reason` and mask-count audit trail.

The percentile guard is documented in `docs/NDMI_TRIGGER_CALIBRATION.md`. It is a v0
calibration rule, not a supervised payout model.

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
critical periods. The JSON and Markdown outputs also include a deterministic validation
assessment: `accepted`, `rejected`, or `ambiguous`.

Results are cached under `data/cache` by default. Use `--no-cache` to force a fresh run.

`--crop-mask-geojson` accepts a Polygon, MultiPolygon, Feature, or FeatureCollection and
is intended for RPG IGN or other parcel/crop masks. The vector mask is reprojected onto
the fixed Sentinel grid and affects `valid_pixel_count` and `mask_counts.non_crop`.

## Batch Drought Validation Runner

Use the batch runner once AOIs are listed in an AOI manifest:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region bordeaux \
  --max-items 40 \
  --output-json reports/bordeaux-2022-batch-validation.json \
  --output-md reports/bordeaux-2022-batch-validation.md
```

The batch runner validates AOI geometry first, uses crop masks when they are present in
the manifest, isolates provider failures per AOI, and reports an `accepted`, `rejected`,
`ambiguous`, or `not_run` assessment for each AOI.

The first Bordeaux batch is summarized in `docs/BORDEAUX_2022_BATCH_VALIDATION.md`:
five live AOIs completed, four were `accepted`, and one was `ambiguous` because cloud
quality warnings require manual review.

The first Languedoc batch is summarized in `docs/LANGUEDOC_2022_BATCH_VALIDATION.md`:
five live AOIs completed, two were `accepted`, and three were `ambiguous` because cloud
quality warnings or percentile/threshold calibration questions require review.

## Drought Validation Classifier

The drought-event classifier is separate from the basis-risk masking classifier. It
answers a different question: can this AOI honestly be counted as evidence that the
engine detected the July-August 2022 drought?

Default thresholds:

- `min_valid_pixels`: `20`
- `min_baseline_supported_periods`: `1`
- `min_confidence`: `0.35`
- `max_clear_signal_percentile`: `0.25`
- `max_mean_cloud_pct`: `70.0`
- `max_rejected_period_fraction`: `0.5`

Classification rules:

- `accepted`: clear drought trigger, baseline support, enough valid pixels, critical
  periods, target-period seasonal percentile at or below `P25`, and no quality warnings
  requiring review.
- `rejected`: failed response, no July-August target periods, no NDMI periods, no
  seasonal baseline support, insufficient valid pixels, too many rejected periods, or
  cloud gap.
- `ambiguous`: enough data to inspect, but weak/no drought signal, low confidence, no
  critical periods, seasonal percentile not low enough, or quality warnings that make the
  trigger non-decisive.

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
  --charts-dir reports/charts/bordeaux-mask-benchmark \
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
  --charts-dir reports/charts/batch-mask-benchmark \
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

First real RPG benchmark command:

```bash
orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 40 \
  --no-cache \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```

The first real run is summarized in `docs/FIRST_REAL_MASK_BENCHMARK.md`. It shows
`vector_crop_mask` as `improved` for basis-risk contamination removal on
`FR_RPG23_BORDEAUX_RIGHT_BANK_01`. After year-stratified seasonal STAC sampling, the same
run also has baseline-supported July-August 2022 target periods and an `accepted`
drought-event validation assessment.

When `--charts-dir` is provided, the runner writes SVG chart artifacts for every
completed AOI/variant pair:

- NDMI mean and EMA;
- valid pixel count;
- cloud percentage.

Chart generation is disabled by default for fast CI and dry benchmark runs.

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
