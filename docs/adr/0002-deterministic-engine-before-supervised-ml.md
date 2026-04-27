# ADR 0002: Build a Deterministic Risk Engine Before Supervised ML

## Status

Accepted

## Context

CatBoost or another supervised model is only defensible with credible labels: claim
history, agronomic ground truth, or a trusted drought/loss proxy. Without labels, model
complexity increases audit risk and creates a black-box sales liability.

## Decision

The POC will ship deterministic logic first: NDVI/NDMI/NDWI, robust spatial aggregation,
EMA smoothing, seasonal baselines, anomaly scoring, and explicit trigger reasons.

## Consequences

- Every output can be inspected and challenged by an actuary.
- The API can expose quality metadata natively.
- ML remains available after validation data exists, but it is not on the critical path.
