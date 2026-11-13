# 4-6 Week POC Plan

## Week 1: Contract, Raster Core, and Commercial Reality Check

- Freeze request/response schemas.
- Implement CRS normalization and AOI reprojection.
- Implement fixed raster grid creation for a single AOI.
- Implement local GeoTIFF reader and mask/stat pipeline.
- Add unit tests using synthetic chips.
- Start 10-15 MGA / parametric insurance discovery calls in parallel.
- Write initial ADRs for data access, masking baseline, deterministic-first modeling, and trigger logic.

## Week 2: Data Access and Baseline Masking

- Implement Planetary Computer + STAC + odc-stac access for Sentinel-2 L2A.
- Keep Sentinel Hub Process API as the production/demo provider boundary.
- Load bands: B03, B04, B05, B08, B11, SCL, dataMask.
- Enforce identical grid/transform per AOI across observations.
- Add cloud/shadow/snow quality summaries.
- Implement negative AOI buffer before any time-series run.
- Implement baseline vegetation mask.
- Add RPG IGN cross-reference as the free French parcel/crop baseline to beat.
- Cache raw observations locally or in object storage.

## Week 3: Time Series and Trigger Logic

- Build P10D or monthly compositing.
- Add EMA, percentile baseline, anomaly z-score, and basic trigger detection.
- Add rejected-observation reasons.
- Return full audit trail in JSON.

## Week 4: Basis-Risk Benchmark

- Compare naive parcel mean vs RPG + negative buffer vs OrbitRisk vegetation mask.
- Produce before/after basis-risk examples on 5-10 French vineyard AOIs.
- Measure whether the proprietary mask beats RPG + buffer on contamination reduction.
- Reject "semantic segmentation" claims unless the proprietary mask wins on measurable AOIs.

## Week 5: 2022 Drought Validation

- Build a validation run for Bordeaux and Languedoc vineyard AOIs.
- Use the July-August 2022 drought as the reference event.
- Require a clear NDMI anomaly/crash against the 2017-2021 or available same-DOY baseline.
- Produce a notebook/report with accepted, rejected, and ambiguous AOIs.
- Convert discovery-call feedback into API contract changes before hardening.

## Week 6: Product Hardening

- Add async jobs for multi-year requests.
- Add object storage and metadata table.
- Add API auth and rate limits.
- Add benchmark report for actuarial conversations.
- Add CatBoost only if credible labels are available.
