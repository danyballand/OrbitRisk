# ADR 0004: Use Seasonal Baselines and Explicit Trigger Reasons

## Status

Accepted

## Context

Raw NDVI or NDMI values are seasonal. A low value can mean drought, harvest, dormancy,
cloud contamination, or phenology. Parametric insurance needs a trigger that can be read,
audited, and reproduced.

## Decision

Score observations against a same-day-of-year seasonal baseline, smooth with EMA, and emit
explicit trigger reasons such as `ndmi_ema_below_p10_for_2_periods`.

## Consequences

- The score is easier for actuaries to inspect.
- The API must return rejected-observation reasons and quality metadata.
- Future smoothers such as Whittaker can be evaluated against EMA, but EMA is the POC
  default because it is transparent.
