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
