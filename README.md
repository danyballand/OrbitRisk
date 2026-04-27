# OrbitRisk

API-first risk engine for parametric crop insurance.

OrbitRisk ingests a vineyard polygon and date range, fetches Sentinel-2 L2A observations,
applies spatial and atmospheric masks, computes vegetation and water-stress indices, and
returns an auditable JSON time series for actuarial workflows.

## What this POC is

- A strict FastAPI/Pydantic API contract for vineyard risk requests.
- A geospatial processing skeleton built around fixed raster grids and explicit CRS handling.
- NumPy implementations for NDVI, NDWI, NDMI, quality masking, robust spatial aggregation,
  EMA smoothing, anomaly scoring, and trigger detection.
- Provider boundaries for Planetary Computer/STAC development and Sentinel Hub production.

## What this POC is not

- A promise of reliable intra-row vineyard segmentation from Sentinel-2 alone. Sentinel-2
  10 m pixels are useful for parcel-level risk signals, but many French vineyard parcels
  contain mixed pixels at edges, roads, roofs, hedges, and bare inter-row soil.
- A supervised drought model. CatBoost belongs after we have labels, claims history, or
  trusted agronomic ground truth.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn orbitrisk.api.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Run tests:

```bash
pytest
```

Run a tiny real-data smoke test through Planetary Computer:

```bash
orbitrisk smoke-pc tests/fixtures/sample_request.json --start 2022-07-01 --end 2022-07-10 --max-items 1
```

## Environment

Copy `.env.example` to `.env` and fill the Sentinel Hub credentials when ready.

```bash
cp .env.example .env
```

The default POC provider is Planetary Computer/STAC to avoid burning Sentinel Hub
processing units during development. Sentinel Hub remains the intended production/demo
provider once the numerical pipeline is validated.

## API Shape

Primary endpoint:

```text
POST /v1/risk/quote
```

For the first POC pass, the endpoint validates the actuarial contract and returns a
deterministic dry-run response. The provider and processing modules are separated so the
dry run can be replaced by real Sentinel Hub observations without changing the public API.
