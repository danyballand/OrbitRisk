# Development Guide

Commands and configuration for working on OrbitRisk locally. The short version is in the
[README Quickstart](../README.md#quickstart); this page holds the full list.

## Setup

Python 3.11 or newer. `rasterio` needs a GDAL runtime; CI installs `gdal-bin` and
`libgdal-dev` on Ubuntu.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

```bash
ruff check .
pytest
```

Both run in CI on every push and pull request ([.github/workflows/ci.yml](../.github/workflows/ci.yml)).

## Environment

Copy `.env.example` to `.env` and fill the Sentinel Hub credentials when ready.

```bash
cp .env.example .env
```

The default POC provider is Planetary Computer/STAC to avoid burning Sentinel Hub
processing units during development. Sentinel Hub remains the intended production/demo
provider once the numerical pipeline is validated.

## Running the API

```bash
uvicorn orbitrisk.api.main:app --reload
curl http://127.0.0.1:8000/health
```

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
scenes. Increase it intentionally for multi-year validation runs. Live endpoints require
`X-API-Key`; configure allowed keys with `ORBITRISK_API_KEYS`.

For longer pilot-style requests, submit and poll an async quote job:

```text
POST /v1/risk/quote/jobs?max_items=80
GET /v1/risk/quote/jobs/{job_id}
GET /v1/risk/quote/jobs/{job_id}/result
```

The full request/response contract is in [API_CONTRACT.md](API_CONTRACT.md).

## CLI reference

All commands below are exposed by the `orbitrisk` entry point.

### Live smoke test

Run a tiny real-data smoke test through Planetary Computer:

```bash
orbitrisk smoke-pc tests/fixtures/sample_request.json --start 2022-07-01 --end 2022-07-10 --max-items 1
```

Use `--temporal P10D` or `--temporal P1M` to inspect the composited actuarial series.

### AOI batch validation (offline)

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

### 2022 drought validation

Run a first drought-2022 validation summary:

```bash
orbitrisk validate-2022 tests/fixtures/sample_request.json \
  --region bordeaux \
  --max-items 80 \
  --crop-mask-geojson data/rpg/vineyard-mask.geojson \
  --output-json reports/bordeaux-2022.json \
  --output-md reports/bordeaux-2022.md
```

Run an RPG drought-2022 validation batch:

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region bordeaux \
  --max-items 40 \
  --output-json reports/bordeaux-2022-batch-validation.json \
  --output-md reports/bordeaux-2022-batch-validation.md
```

Use `--region languedoc` with `reports/languedoc-2022-batch-validation.*` for the
Languedoc batch.

### Mask benchmarks

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
  --max-items 40 \
  --no-cache \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```

Validation responses are cached under `data/cache` by default. Use `--no-cache` when you
need to force a fresh Planetary Computer run.

### Demo pack and README figure

Build the offline MGA demo pack from tracked reports (no network access needed):

```bash
orbitrisk build-mga-demo-pack --output-dir demo/mga_pilot_2022
```

Regenerate the README results figure from the tracked batch reports (standard library only):

```bash
python scripts/render_readme_figure.py
```

It reads `reports/bordeaux-2022-batch-validation.json` and
`reports/languedoc-2022-batch-validation.json` and writes
`docs/images/drought-2022-results.svg`.
