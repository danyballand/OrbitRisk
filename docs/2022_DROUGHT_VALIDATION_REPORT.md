# OrbitRisk 2022 Drought Validation Report

Date: 2026-04-28

## Executive Readout

OrbitRisk detects the July-August 2022 drought signal on real French vineyard AOIs, but
the v0 classifier is intentionally conservative:

| Region | AOIs | Accepted | Ambiguous | Rejected | Trigger candidates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bordeaux | 5 | 4 | 1 | 0 | 5 |
| Languedoc | 5 | 2 | 3 | 0 | 5 |
| Total | 10 | 6 | 4 | 0 | 10 |

The engine should not be pitched as a black-box semantic segmentation model. The
defensible claim is narrower and stronger: OrbitRisk produces an auditable drought-risk
time series with spatial masking, quality flags, seasonal baseline percentiles, explicit
trigger reasons, and accepted/ambiguous/rejected validation logic.

## Strongest AOI

Strongest accepted validation by classifier confidence:

| Field | Value |
| --- | --- |
| AOI | `FR_RPG23_PIC_SAINT_LOUP_02` |
| Region | Languedoc |
| Classification | `accepted` |
| Reason | `clear_drought_trigger` |
| Trigger | `ndmi_ema_below_0.15_for_2_periods` |
| Confidence | `0.7457` |
| Target periods | `6` |
| Baseline-supported periods | `5` |
| Minimum seasonal percentile | `0.0000` |
| Minimum valid pixels | `1193` |
| Mean cloud percentage | `0.0000` |

Why it matters: this AOI combines a clear absolute NDMI/EMA trigger, a same-season
baseline percentile at the bottom of the historical distribution, enough valid pixels,
and no cloud quality warning in the target window.

## Worst Failure Case

Worst customer-facing failure case:

| Field | Value |
| --- | --- |
| AOI | `FR_RPG23_BEZIERS_01` |
| Region | Languedoc |
| Classification | `ambiguous` |
| Reasons | `seasonal_percentile_not_low`, `quality_warnings_require_review` |
| Trigger | `ndmi_ema_below_0.15_for_2_periods` |
| Confidence | `0.7066` |
| Target periods | `6` |
| Baseline-supported periods | `6` |
| Minimum seasonal percentile | `0.6364` |
| Minimum valid pixels | `127` |
| Mean cloud percentage | `15.8424` |

This is the right failure. The absolute EMA trigger exists, but the parcel is not low
relative to its own seasonal baseline. One target period also has severe cloud
contamination: the final August composite has `95.0544%` cloud and only `127` valid
pixels. A naive absolute threshold would overclaim this AOI as a drought win; OrbitRisk
keeps it ambiguous.

The second important calibration failure is `FR_RPG23_MINERVOIS_02`: minimum NDMI EMA is
low (`-0.0321`), but the minimum target-period seasonal percentile is only `0.5556`, so
the low absolute value is not unusually low for that parcel and season.

## Basis-Risk Mask Benchmark Excerpt

The first real RPG crop-mask benchmark was run on
`FR_RPG23_BORDEAUX_RIGHT_BANK_01`.

| Variant | Mean valid px | Mean cloud % | Min NDMI EMA | Crop coverage % | Non-crop px | Assessment |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `raw_aoi` | 3341.0000 | 0.0000 | 0.0003 |  | 0 | baseline |
| `buffered_aoi` | 2989.0000 | 0.0000 | 0.0007 |  | 0 | comparison |
| `vector_crop_mask` | 2606.0000 | 0.0000 | 0.0025 | 87.1863 | 14937 | `improved` |

Interpretation: the vector crop mask removes measurable non-crop support while preserving
enough valid Sentinel-2 pixels for the drought signal. This supports the basis-risk
argument, but it is not yet a claim that OrbitRisk can reliably segment vine rows from
Sentinel-2 10 m pixels alone.

## Failure-Mode Appendix

| Failure mode | Current evidence | Product behavior |
| --- | --- | --- |
| Cloud gap | `FR_RPG23_BEZIERS_01` has a target period with `95.0544%` cloud and only `127` valid pixels. | Keep AOI `ambiguous`; expose `quality_warnings_require_review`. |
| Low valid-pixel support | `FR_RPG23_MINERVOIS_01` drops to `121` valid pixels and `FR_RPG23_BEZIERS_01` drops to `127`. | Surface `min_valid_pixel_count`; reject only below the configured `20` pixel floor. |
| Seasonal false positive | `FR_RPG23_MINERVOIS_02` has low absolute NDMI EMA but minimum seasonal percentile `0.5556`. | Keep AOI `ambiguous`; expose `seasonal_percentile_not_low`. |
| Mask instability or over-masking | The first real mask benchmark preserves enough pixels, but only one real AOI has a full raw/buffer/crop-mask comparison. | Do not claim a segmentation moat until broader crop-mask benchmarks beat the RPG/vector baseline. |

## Methodology

Data path:

- Sentinel-2 L2A loaded through Planetary Computer/STAC.
- Fixed local UTM raster grid per AOI.
- AOI negative buffer and optional external RPG-style vector crop mask.
- SCL-based cloud, shadow, and snow exclusion.
- P10D compositing for actuarial-style time series.
- NDMI primary water-stress index, with NDVI and NDWI available as supporting indices.
- EMA smoothing over the NDMI series.
- Same-day-of-year seasonal baseline metadata from previous years.
- Deterministic drought classifier with explicit reasons.

Chosen v0 trigger policy:

```text
accepted =
  ndmi_ema_below_0.15_for_2_periods
  AND min_target_ndmi_baseline_percentile <= 0.25
  AND confidence >= 0.35
  AND min_valid_pixel_count >= 20
  AND no cloud/clear-fraction/index quality warning
  AND at least one critical period exists
```

The calibration rationale is documented in `docs/NDMI_TRIGGER_CALIBRATION.md`.

## Reproducibility

Run Bordeaux validation:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region bordeaux \
  --max-items 40 \
  --output-json reports/bordeaux-2022-batch-validation.json \
  --output-md reports/bordeaux-2022-batch-validation.md
```

Run Languedoc validation:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region languedoc \
  --max-items 40 \
  --output-json reports/languedoc-2022-batch-validation.json \
  --output-md reports/languedoc-2022-batch-validation.md
```

Run the first real crop-mask benchmark:

```bash
orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 40 \
  --no-cache \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```

## Limitations

- Sentinel-2 10 m pixels are appropriate for parcel-level drought evidence on sufficiently
  large AOIs, not for reliable intra-row vine segmentation.
- Current crop masking is an external vector-mask and negative-buffer workflow. Any
  proprietary vegetation mask must beat the RPG/vector baseline before it becomes a moat
  claim.
- There are no supervised labels or loss-history labels in this repo. CatBoost remains
  blocked until labels exist.
- The current validation window is one known drought event: July-August 2022. A pilot
  should add non-drought and weak-drought windows to estimate false positives.
- The mask benchmark excerpt is one real AOI, not a full 10-AOI benchmark result.

## Decision

M3 is technically credible as a drought-validation POC once this report is paired with
the batch JSON/Markdown outputs. The next technical gap is not another model; it is
broader failure-mode coverage and pilot hardening: async jobs, provenance, API auth,
error models, and a design-partner review of the JSON contract.
