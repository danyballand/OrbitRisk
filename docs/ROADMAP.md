# OrbitRisk Roadmap

This roadmap starts from the current state on 2026-04-27: the repo already has the
FastAPI contract, Planetary Computer provider, fixed raster grid, SCL masking, NDVI/NDMI
statistics, seasonal baseline metadata, local response cache, vector crop-mask support,
and a mask benchmark CLI.

The target is not a generic climate platform. The target is a sellable MGA-facing POC:
an auditable drought-risk API for French vineyard AOIs with evidence that masking reduces
basis risk compared with naive parcel means.

## North Star Demo

By 2026-05-31, OrbitRisk should produce a defensible demo pack for 5-10 vineyard AOIs:

- [ ] one API request per AOI with strict input contract,
- [ ] one JSON risk response per AOI,
- [x] one raw-vs-buffer-vs-crop-mask benchmark report,
- [x] one 2022 drought validation report for Bordeaux and/or Languedoc,
- [x] explicit accepted/rejected/ambiguous AOI classification logic,
- [ ] observed accepted/rejected/ambiguous classification on real AOIs,
- [x] clear reasons when the signal is weak, cloudy, under-sampled, or not benchmarkable,
- [ ] a technical explanation an actuary can audit without trusting a black box.

## P0 Exit Criteria

The POC is considered technically demoable only when all P0 criteria are true:

- [x] AOIs can be versioned as manifests or fixtures, with CRS and crop metadata.
- [x] Each AOI can be locally accepted or rejected before live Sentinel-2 loading.
- [x] 5-10 real vineyard AOIs are versioned in a validation manifest.
- [x] `benchmark-masks-2022` has been run on the AOI batch.
- [x] The benchmark compares `raw_aoi`, `buffered_aoi`, and `vector_crop_mask`.
- [x] At least one real crop/RPG-style mask is used, not only synthetic geometry.
- [x] The validation report includes July-August 2022 NDMI/EMA/baseline evidence.
- [ ] Every reported trigger has `valid_pixel_count`, `cloud_pct`, `mask_counts`, and
  `quality_flags`.
- [ ] The demo can be reproduced from documented CLI commands.

## Non-Goals Before First MGA Demo

- [x] No supervised CatBoost trigger unless credible labels or loss history exist.
- [x] No claim of reliable intra-row segmentation from Sentinel-2 10 m pixels alone.
- [x] No production billing, self-serve dashboard, or multi-tenant admin UI.
- [x] No Sentinel Hub migration until the Planetary Computer numerical path is stable.

## Milestones

GitHub tracking:

- [M1: AOI Data Pack and Quality Gates](https://github.com/danyballand/OrbitRisk/milestone/1)
  tracks issues [#1](https://github.com/danyballand/OrbitRisk/issues/1) through
  [#5](https://github.com/danyballand/OrbitRisk/issues/5).
- [M2: Basis-Risk Mask Benchmark](https://github.com/danyballand/OrbitRisk/milestone/2)
  tracks issues [#6](https://github.com/danyballand/OrbitRisk/issues/6) through
  [#10](https://github.com/danyballand/OrbitRisk/issues/10).
- [M3: 2022 Drought Validation](https://github.com/danyballand/OrbitRisk/milestone/3)
  tracks issues [#11](https://github.com/danyballand/OrbitRisk/issues/11) through
  [#15](https://github.com/danyballand/OrbitRisk/issues/15), plus the baseline-support
  follow-up [#25](https://github.com/danyballand/OrbitRisk/issues/25).
- [M4: API Hardening for Pilot Use](https://github.com/danyballand/OrbitRisk/milestone/4)
  tracks issues [#16](https://github.com/danyballand/OrbitRisk/issues/16) through
  [#20](https://github.com/danyballand/OrbitRisk/issues/20).
- [M5: MGA Demo Pack](https://github.com/danyballand/OrbitRisk/milestone/5)
  tracks issues [#21](https://github.com/danyballand/OrbitRisk/issues/21) through
  [#24](https://github.com/danyballand/OrbitRisk/issues/24).

### M1: AOI Data Pack and Quality Gates

Due: 2026-05-03

Goal: make the input dataset real enough to expose geospatial failure modes.

Deliverables:

- [x] AOI batch manifest schema for vineyard test parcels.
- [x] 5-10 candidate AOIs across Bordeaux and/or Languedoc.
- [x] Crop-mask/RPG input convention and CRS handling documented.
- [x] Geometry and raster support checks for min area, min pixels, CRS, and invalid shapes.
- [x] Rejection reasons surfaced before expensive Sentinel-2 loads where possible.

Exit criteria:

- [x] `orbitrisk` can validate a batch manifest locally.
- [x] Tiny or invalid AOIs fail with actionable reasons.
- [x] At least one real AOI has an external crop mask ready for the benchmark.

### M2: Basis-Risk Mask Benchmark

Due: 2026-05-10

Goal: turn the masking moat into measurable evidence.

Deliverables:

- [x] Batch wrapper for `benchmark-masks-2022`.
- [x] JSON and Markdown aggregate reports across AOIs.
- [x] Metrics for crop coverage, non-crop pixels, valid pixel deltas, cloud deltas, and NDMI
  deltas.
- [x] Deterministic basis-risk classifier with auditable thresholds and reasons.
- [x] Explicit comparison of naive AOI mean vs negative buffer vs external crop mask.
- [x] Chart artifacts for NDMI, valid pixels, and cloud percentage.
- [ ] Mask coverage chart artifact across AOIs.

Exit criteria:

- [x] The report identifies which AOIs improve, degrade, or remain ambiguous after masking.
- [x] The report can be shown in a discovery call without hand-editing.
- [ ] Any proprietary vegetation mask is benchmarked against RPG/crop-mask baseline before
  being described as a moat.

### M3: 2022 Drought Validation

Due: 2026-05-17

Goal: prove the engine sees a known historical drought event.

Deliverables:

- [x] Bordeaux and/or Languedoc July-August 2022 validation run.
- [x] Same-day-of-year seasonal baseline metadata for each accepted period.
- [x] Accepted/rejected/ambiguous AOI classifier.
- [ ] NDMI threshold and percentile calibration note.
- [x] Investigation of missing seasonal baseline support in the first real RPG benchmark.
- [ ] Failure-mode appendix covering cloud gaps, insufficient pixels, and unstable masks.

Exit criteria:

- [x] At least one known drought AOI shows a clear NDMI/EMA crash in July-August 2022.
- [ ] Rejected AOIs have explicit non-handwavy rejection reasons.
- [x] Ambiguous AOIs are not counted as wins.

### M4: API Hardening for Pilot Use

Due: 2026-05-24

Goal: make the API reliable enough for a design partner pilot.

Deliverables:

- [ ] Async job submission and polling endpoints for multi-year requests.
- [ ] Artifact storage abstraction for reports and cached responses.
- [ ] API key auth and basic rate limiting.
- [ ] Algorithm/version provenance in every response.
- [ ] OpenAPI examples for dry-run, live quote, and crop-mask quote.
- [ ] Error model for invalid geometry, no scenes, cloud-only scenes, and insufficient pixels.

Exit criteria:

- [ ] Multi-year requests no longer require synchronous HTTP completion.
- [ ] A failed quote returns a structured error that can be logged in an actuarial workflow.
- [ ] Responses contain enough provenance to reproduce or dispute a result.

### M5: MGA Demo Pack

Due: 2026-05-31

Goal: package the technical work into a buyer-facing proof.

Deliverables:

- [ ] One reproducible demo folder with requests, outputs, and reports.
- [ ] Short technical memo explaining basis-risk reduction and current limitations.
- [ ] Contract-ready JSON examples for actuaries.
- [ ] Design-partner discovery summary with objections and API changes.
- [ ] Go/no-go note for CatBoost, Sentinel Hub production path, and pilot deployment.

Exit criteria:

- [ ] A 30-minute MGA demo can be run without live coding.
- [ ] The strongest result and the worst failure case are both documented.
- [ ] The next build step is driven by customer feedback, not by speculative ML.

## GitHub Issue Labels

Recommended labels:

- `roadmap`: roadmap-tracked work.
- `p0`: required for first credible demo.
- `p1`: important but not blocking first demo.
- `p2`: follow-up or polish.
- `geo`: geospatial/raster/CRS work.
- `validation`: drought validation and benchmark evidence.
- `api`: API contract, endpoints, auth, async jobs.
- `product`: MGA/customer-facing work.
- `docs`: documentation, memo, reports.

## Risk Register

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Sentinel-2 10 m mixed pixels make small vineyard AOIs unreliable | High | Reject small AOIs, expose valid pixels, use crop masks and confidence flags |
| Cloud cover creates false drought signals or sparse baselines | High | Keep SCL quality flags, baseline counts, accepted/rejected classification |
| RPG/crop mask does not improve over buffer-only | High | Benchmark honestly; pitch auditability rather than CV magic |
| No MGA design partner feedback | High | Run discovery calls in parallel with M1-M3 |
| Multi-year requests are too slow synchronously | Medium | Add async jobs and artifact storage in M4 |
| CatBoost becomes a distraction without labels | Medium | Gate supervised ML behind explicit label/loss-data availability |
