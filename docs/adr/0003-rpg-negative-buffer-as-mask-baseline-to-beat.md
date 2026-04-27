# ADR 0003: Treat RPG Plus Negative Buffer as the Baseline to Beat

## Status

Accepted

## Context

Sentinel-2 10 m pixels are often mixed inside French vineyard parcels. Roads, roofs,
hedges, bare soil, and parcel edges can contaminate naive means. A proprietary CV mask is
not a moat unless it outperforms a strong free baseline.

## Decision

Use RPG IGN parcel/crop cross-reference plus a negative AOI buffer as the baseline mask.
OrbitRisk masking must be compared against this baseline before claiming semantic
segmentation value.

## Consequences

- Week 2 includes baseline masking, not only data access.
- Week 4 explicitly benchmarks naive mean vs RPG + buffer vs OrbitRisk mask.
- Marketing language should emphasize auditability until the proprietary mask wins on
  measured AOIs.
