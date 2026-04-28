# POC Status

## Current State

OrbitRisk now has a working technical spine:

- strict API contract and dry-run endpoint,
- AOI preparation from GeoJSON,
- local UTM CRS selection,
- negative buffer handling,
- fixed raster grid generation,
- AOI raster mask,
- Planetary Computer/STAC provider,
- xarray datacube summarization,
- P10D/monthly observation compositing,
- live API endpoint backed by Planetary Computer,
- seasonal baseline metadata,
- drought-2022 validation summary runner,
- deterministic accepted/rejected/ambiguous classifier for drought-2022 validation,
- mask benchmark runner for raw AOI vs buffer vs external crop mask,
- batch mask benchmark runner for AOI manifests,
- deterministic basis-risk classifier for crop-mask benchmark outputs,
- optional SVG chart artifacts for NDMI, valid pixels, and cloud percentage,
- AOI batch manifest validation without network calls,
- local JSON response cache,
- JSON and Markdown validation exports,
- optional external vector crop mask for RPG-style masking,
- public RPG 2023 vineyard candidate pack with 10 accepted AOIs across Bordeaux and
  Languedoc,
- first real RPG mask benchmark showing `vector_crop_mask` as `improved` on
  `FR_RPG23_BORDEAUX_RIGHT_BANK_01`,
- Bordeaux July-August 2022 batch validation on five real RPG vineyard AOIs, with four
  `accepted`, one `ambiguous`, and same-season baseline support after year-stratified
  STAC sampling,
- Languedoc July-August 2022 batch validation on five real RPG vineyard AOIs, with two
  `accepted`, three `ambiguous`, and explicit cloud/calibration caveats,
- deterministic NDMI trigger calibration that keeps the absolute EMA threshold as a
  candidate generator and requires a same-season percentile guard for clean accepted
  validation,
- first customer-readable 2022 drought validation report with strongest AOI, worst
  ambiguous failure case, benchmark excerpt, methodology, limitations, and
  reproducibility commands,
- async quote job endpoints for submitting, polling, and fetching longer live risk
  requests,
- local artifact storage abstraction for JSON responses, Markdown reports, and chart
  artifacts with deterministic keys and content hashes,
- response provenance metadata with algorithm version, processing version, input hash,
  cache key, mask mode, and crop-mask hash when used,
- structured live quote error responses for invalid geometry, no scenes, cloud-only
  scenes, insufficient pixels, and provider failures,
- API key protection and in-memory per-key rate limiting for live quote and async job
  endpoints,
- OpenAPI request examples for dry-run, live quote, and crop-mask quote flows,
- reproducible MGA demo pack with requests, compact JSON summaries, validation reports,
  mask benchmark report, and chart artifacts,
- SCL cloud/shadow/snow masking,
- NDVI/NDMI/NDWI spatial statistics,
- real-data smoke command.

The first real smoke test runs against Planetary Computer Sentinel-2 L2A and returns
auditable observations with `valid_pixel_count`, `cloud_pct`, `quality`, `mask_counts`,
and index stats.

The live API smoke path also works:

```text
POST /v1/risk/quote/live?max_items=10
```

Longer pilot-style requests can use:

```text
POST /v1/risk/quote/jobs?max_items=80
GET /v1/risk/quote/jobs/{job_id}
GET /v1/risk/quote/jobs/{job_id}/result
```

For the July 2022 sample fixture, it returns three P10D composited observations and a
water-stress trigger.

## Distance to a Technical POC

Close, but not done.

The technical POC needs:

- full-batch observed raw-vs-buffer-vs-crop-mask benchmark outputs across all 10 RPG AOIs,
- mask coverage chart artifacts across AOIs.

The local AOI validation layer now rejects invalid geometries, empty negative buffers,
and insufficient Sentinel-2 pixel support before any live raster provider call.

Estimate: the engineering POC is roughly 92% complete. A rough demo can now run without
live coding; an actuary-grade POC still needs broader observed benchmark outputs, mask
coverage charts, and a design-partner review loop.

## Distance to a Sellable MGA POC

Further.

The sellable POC needs:

- 5-10 credible vineyard AOIs,
- 2022 drought validation report,
- naive mean vs buffer vs RPG/crop-mask comparison on real AOIs,
- one design partner conversation validating the JSON contract,
- a crisp explanation of basis-risk reduction and confidence metadata.

The product risk remains commercial, not only technical.
