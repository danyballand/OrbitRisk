# NDMI Trigger Calibration

Date: 2026-04-28

## Scope

This note calibrates the deterministic v0 drought trigger for the M3 validation pack. It
uses the two live 2022 vineyard batches already generated with Planetary Computer
Sentinel-2 L2A, RPG-style crop masks, SCL masking, and same-day-of-year seasonal
baseline metadata:

- `reports/bordeaux-2022-batch-validation.json`
- `reports/languedoc-2022-batch-validation.json`

CatBoost is explicitly out of scope for this milestone. There are no loss labels, no
claim history, and no validated policy trigger labels yet. A supervised model would add
opacity before it adds actuarial evidence.

## Compared Rules

### 1. Absolute EMA Threshold

Current engine trigger:

```text
ndmi_ema_below_0.15_for_2_periods
```

Result on the 10 real RPG vineyard AOIs:

| Metric | Result |
| --- | ---: |
| AOIs with absolute trigger candidate | 10 / 10 |
| Bordeaux trigger candidates | 5 / 5 |
| Languedoc trigger candidates | 5 / 5 |

This has useful recall for the known 2022 drought, but it is too permissive as the only
customer-facing rule. In Languedoc, `FR_RPG23_MINERVOIS_02` has low absolute NDMI EMA
(`-0.0321`) while its target-period seasonal percentile never drops below `0.5556`.
That means the low absolute value is not unusually low for that parcel and season.

### 2. Seasonal Percentile Guard

Seasonal percentile is computed against previous-year observations in a day-of-year
window. For v0 validation, the guard is:

```text
min_target_ndmi_baseline_percentile <= 0.25
```

Sensitivity across the 10 AOIs:

| Percentile guard | AOIs passing guard | Notes |
| --- | ---: | --- |
| `<= P10` | 7 / 10 | Stricter, but brittle with short baselines. |
| `<= P25` | 8 / 10 | Keeps all clean accepted AOIs and flags the two Languedoc high-percentile cases. |
| `<= P50` | 8 / 10 | No extra useful separation on the current batch. |

Regional split at `P25`:

| Region | AOIs | Passing `P25` guard | Above `P25` |
| --- | ---: | ---: | ---: |
| Bordeaux | 5 | 5 | 0 |
| Languedoc | 5 | 3 | 2 |

### 3. Chosen v0 Classifier Rule

The v0 validation classifier keeps the absolute EMA trigger as the candidate generator
and uses the seasonal percentile as an acceptance guard:

```text
accepted =
  absolute_ndmi_ema_trigger
  AND baseline_supported_period_count >= 1
  AND min_target_ndmi_baseline_percentile <= 0.25
  AND confidence >= 0.35
  AND min_valid_pixel_count >= 20
  AND no cloud/clear-fraction/index quality warning
  AND at least one critical period exists
```

If the absolute trigger exists but the minimum seasonal percentile is above `P25`, the
AOI remains `ambiguous` with reason:

```text
seasonal_percentile_not_low
```

This is intentionally conservative. The API should not sell a low absolute NDMI value as
an insurance trigger if the same parcel is often that low during the same season.

## Current Evidence

Final v0 classification on the two validation batches:

| Region | Accepted | Ambiguous | Rejected | Trigger candidates |
| --- | ---: | ---: | ---: | ---: |
| Bordeaux | 4 | 1 | 0 | 5 |
| Languedoc | 2 | 3 | 0 | 5 |
| Total | 6 | 4 | 0 | 10 |

The two clearest percentile failures are:

| AOI | Region | Min baseline percentile | Min NDMI EMA | v0 reason |
| --- | --- | ---: | ---: | --- |
| `FR_RPG23_MINERVOIS_02` | Languedoc | 0.5556 | -0.0321 | `seasonal_percentile_not_low`, `quality_warnings_require_review` |
| `FR_RPG23_BEZIERS_01` | Languedoc | 0.6364 | 0.1332 | `seasonal_percentile_not_low`, `quality_warnings_require_review` |

## Decision

Use the combined deterministic rule for M3. Do not promote the raw absolute EMA trigger
as the actuarial trigger. Present it as a candidate signal that must survive seasonal
percentile and quality gates.

## Next Calibration Work

- Add true consecutive-period percentile logic once the trigger model supports percentile
  series directly, not only absolute EMA values.
- Validate at least one non-drought or weak-drought historical window to estimate false
  positives.
- Revisit `P25` only after a design partner confirms whether they want high recall
  screening or stricter payout-trigger evidence.
- Keep CatBoost blocked until loss labels or expert-reviewed trigger labels exist.
