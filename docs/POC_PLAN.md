# 4-6 Week POC Plan

## Week 1: Contract and Raster Core

- Freeze request/response schemas.
- Implement CRS normalization and AOI reprojection.
- Implement fixed raster grid creation for a single AOI.
- Implement local GeoTIFF reader and mask/stat pipeline.
- Add unit tests using synthetic chips.

## Week 2: Sentinel Hub Integration

- Implement Process API download for Sentinel-2 L2A bands: B03, B04, B05, B08, B11, SCL, dataMask.
- Enforce identical grid/transform per AOI across observations.
- Add cloud/shadow/snow quality summaries.
- Cache raw observations locally or in object storage.

## Week 3: Time Series and Trigger Logic

- Build P10D or monthly compositing.
- Add EMA, percentile baseline, anomaly z-score, and basic trigger detection.
- Add rejected-observation reasons.
- Return full audit trail in JSON.

## Week 4: Vineyard Masking Baseline

- Add conservative parcel edge buffer.
- Add vegetation mask baseline.
- Evaluate external crop/parcel layers before claiming semantic segmentation.
- Produce before/after basis-risk examples on 5-10 French vineyard AOIs.

## Weeks 5-6: Product Hardening

- Add async jobs for multi-year requests.
- Add object storage and metadata table.
- Add API auth and rate limits.
- Add benchmark notebook/report for actuarial conversations.
- Add CatBoost only if credible labels are available.
