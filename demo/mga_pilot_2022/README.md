# OrbitRisk MGA Pilot Demo Pack

This folder is the buyer-facing demo bundle for the July-August 2022 drought validation narrative.

## Talk Track

- Strongest accepted AOI: `FR_RPG23_PIC_SAINT_LOUP_02`.
- Worst ambiguous failure case: `FR_RPG23_BEZIERS_01`.
- Crop-mask benchmark: raw AOI vs negative buffer vs external RPG-style mask.
- Main claim: auditable parcel-level drought evidence, not black-box Sentinel-2 vine-row segmentation.

## Files

- `requests/strongest_success_request.json`: live API request for the clean accepted case.
- `requests/worst_failure_request.json`: live API request for the ambiguous case.
- `outputs/strongest_success_summary.json`: compact actuarial-readable response summary.
- `outputs/worst_failure_summary.json`: compact failure-mode summary.
- `outputs/mask_benchmark_summary.json`: compact basis-risk benchmark.
- `reports/2022_drought_validation_report.md`: full validation memo.
- `reports/mask_benchmark_report.md`: full mask benchmark report.
- `charts/mask_benchmark/`: SVG charts when source chart artifacts exist.

## Rebuild From A Clean Checkout

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
orbitrisk build-mga-demo-pack --output-dir demo/mga_pilot_2022
```

## Reproduce Live Source Reports

These commands hit Planetary Computer unless cached responses already exist under `data/cache`.

```bash
orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region bordeaux \
  --max-items 40 \
  --output-json reports/bordeaux-2022-batch-validation.json \
  --output-md reports/bordeaux-2022-batch-validation.md

orbitrisk validate-2022-batch examples/rpg_2023_vineyard_candidate_manifest.json \
  --region languedoc \
  --max-items 40 \
  --output-json reports/languedoc-2022-batch-validation.json \
  --output-md reports/languedoc-2022-batch-validation.md

orbitrisk benchmark-masks-batch-2022 examples/rpg_2023_first_real_benchmark_manifest.json \
  --max-items 40 \
  --output-json reports/rpg-2023-first-real-mask-benchmark.json \
  --output-md reports/rpg-2023-first-real-mask-benchmark.md \
  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark
```
