# ADR 0001: Use Planetary Computer for POC Development and Sentinel Hub for Production

## Status

Accepted

## Context

The POC needs repeated iteration over Sentinel-2 L2A scenes while the team debugs AOI
projection, fixed grids, cloud masks, vegetation masks, and time-series aggregation.
Running every retry through Sentinel Hub Process API can burn processing units before the
pipeline is validated.

## Decision

Use Planetary Computer + STAC + odc-stac as the default development provider for the
first six weeks. Keep Sentinel Hub as a first-class provider boundary for production and
final customer demos.

## Consequences

- Development iteration is cheaper and easier to reproduce.
- The processing core must stay provider-agnostic.
- Provider adapters must return data on a fixed grid so results remain comparable.
- Sentinel Hub integration still needs a production-readiness pass before launch.
