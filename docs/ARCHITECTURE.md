# Architecture

## Processing Flow

```text
GeoJSON AOI
  -> validate public contract
  -> infer local UTM CRS
  -> negative buffer to reduce mixed edge pixels
  -> fixed raster grid
  -> Planetary Computer STAC observations in dev
  -> Sentinel Hub observations for production/demo
  -> SCL/cloud/shadow/snow mask
  -> optional vegetation/non-crop mask
  -> NDVI/NDMI/NDWI arrays
  -> robust spatial aggregation
  -> temporal smoothing/anomaly scoring
  -> insurance trigger JSON
```

## Package Boundaries

```text
api/          FastAPI routes and dependency wiring
schemas/      Public Pydantic request/response models
providers/    Planetary Computer and Sentinel Hub IO boundaries
geo/          CRS, AOI, raster grid, rasterization utilities
processing/   Band math, cloud masks, quality control, spatial stats
masking/      Parcel edge, vector, and vegetation masking strategies
timeseries/   EMA, anomaly scoring, extrema and trigger logic
models/       Future supervised feature extraction and model adapters
jobs/         Async/background execution boundary
storage/      Raster artifact and metadata persistence boundary
```

## Technical Stance

Sentinel-2 can support a parcel-level parametric risk signal, but not a clean promise of
intra-row vineyard segmentation at 10 m. OrbitRisk should expose confidence and quality
metadata as product features, not hide them behind a single score.

The first reliable moat is not a neural network. It is a reproducible index with:

- fixed grids across time,
- explicit atmospheric masking,
- conservative edge handling,
- robust statistics instead of naive means,
- seasonal baseline comparisons,
- full audit metadata for every returned value.

## Data Access Strategy

During the POC, the default provider is Planetary Computer + STAC + odc-stac. That keeps
iteration cheap and reproducible while the team debugs grids, masks, and time-series logic.

Sentinel Hub remains in the architecture as the production/demo provider because it gives
strong operational controls, consistent APIs, and clean deployment ergonomics for B2B use.
