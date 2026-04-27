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
- mask benchmark runner for raw AOI vs buffer vs external crop mask,
- AOI batch manifest validation without network calls,
- local JSON response cache,
- JSON and Markdown validation exports,
- optional external vector crop mask for RPG-style masking,
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

For the July 2022 sample fixture, it returns three P10D composited observations and a
water-stress trigger.

## Distance to a Technical POC

Close, but not done.

The technical POC needs:

- a 5-10 AOI Bordeaux/Languedoc July-August 2022 validation batch,
- observed raw-vs-buffer-vs-crop-mask benchmark outputs,
- explicit accepted/rejected/ambiguous AOI classification,
- charts for NDMI, valid pixels, and cloud percentage.

The local AOI validation layer now rejects invalid geometries, empty negative buffers,
and insufficient Sentinel-2 pixel support before any live raster provider call.

Estimate: the engineering POC is roughly 55-65% complete. A rough demo is close; an
actuary-grade POC still needs real AOI batches, observed benchmark outputs, and a
clear accepted/rejected/ambiguous AOI review loop.

## Distance to a Sellable MGA POC

Further.

The sellable POC needs:

- 5-10 credible vineyard AOIs,
- 2022 drought validation report,
- naive mean vs buffer vs RPG/crop-mask comparison on real AOIs,
- one design partner conversation validating the JSON contract,
- a crisp explanation of basis-risk reduction and confidence metadata.

The product risk remains commercial, not only technical.
