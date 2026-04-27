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

## Roadmap

The detailed build roadmap is tracked in [docs/ROADMAP.md](docs/ROADMAP.md) and mirrored
as GitHub milestones/issues.

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

Use `--temporal P10D` or `--temporal P1M` to inspect the composited actuarial series.

Validate an AOI batch locally before live Sentinel-2 runs:

```bash
orbitrisk validate-aoi-batch examples/aoi_batch_manifest.json \
  --output-json reports/aoi-batch-validation.json \
  --output-md reports/aoi-batch-validation.md
```

Validate the public RPG 2023 vineyard candidate pack:

```bash
orbitrisk validate-aoi-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --output-json reports/rpg-2023-aoi-validation.json \
  --output-md reports/rpg-2023-aoi-validation.md
```

Run a first drought-2022 validation summary:

```bash
orbitrisk validate-2022 tests/fixtures/sample_request.json \
  --region bordeaux \
  --max-items 80 \
  --crop-mask-geojson data/rpg/vineyard-mask.geojson \
  --output-json reports/bordeaux-2022.json \
  --output-md reports/bordeaux-2022.md
```

Compare raw AOI, negative-buffer, and external crop-mask variants:

```bash
orbitrisk benchmark-masks-2022 tests/fixtures/sample_request.json \
  --region bordeaux \
  --max-items 80 \
  --crop-mask-geojson data/rpg/vineyard-mask.geojson \
  --output-json reports/bordeaux-mask-benchmark.json \
  --output-md reports/bordeaux-mask-benchmark.md
```

Run the same mask benchmark across every accepted AOI in a manifest:

```bash
orbitrisk benchmark-masks-batch-2022 examples/aoi_batch_manifest.json \
  --max-items 80 \
  --output-json reports/batch-mask-benchmark.json \
  --output-md reports/batch-mask-benchmark.md
```

Run the first real RPG crop-mask benchmark:

```bash
orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 80 \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```

Validation responses are cached under `data/cache` by default. Use `--no-cache` when you
need to force a fresh Planetary Computer run.

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

The default endpoint validates the actuarial contract and returns a deterministic dry-run
response. A live Planetary Computer-backed endpoint is also available:

```text
POST /v1/risk/quote/live?max_items=25
```

`max_items` protects development calls from accidentally loading hundreds of Sentinel-2
scenes. Increase it intentionally for multi-year validation runs.
