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
- SCL cloud/shadow/snow masking,
- NDVI/NDMI/NDWI spatial statistics,
- real-data smoke command.

The first real smoke test runs against Planetary Computer Sentinel-2 L2A and returns
auditable observations with `valid_pixel_count`, `cloud_pct`, `quality`, `mask_counts`,
and index stats.

## Distance to a Technical POC

Close, but not done.

The technical POC needs:

- period compositing: choose the best observation per P10D/monthly bucket,
- API route backed by the real provider instead of dry-run values,
- persistence/caching for raw and summarized observations,
- clear rejected-observation reasons,
- baseline seasonal anomaly scoring,
- a Bordeaux/Languedoc July-August 2022 validation run.

Estimate: the engineering POC is roughly 40-50% complete. A rough demo is close; an
actuary-grade POC still needs the validation and compositing layers.

## Distance to a Sellable MGA POC

Further.

The sellable POC needs:

- 5-10 credible vineyard AOIs,
- 2022 drought validation report,
- naive mean vs RPG + buffer vs OrbitRisk mask comparison,
- one design partner conversation validating the JSON contract,
- a crisp explanation of basis-risk reduction and confidence metadata.

The product risk remains commercial, not only technical.
