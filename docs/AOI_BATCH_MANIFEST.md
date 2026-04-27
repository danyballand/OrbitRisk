# AOI Batch Manifest

AOI batch manifests let OrbitRisk validate vineyard parcels before running expensive
Sentinel-2 history jobs. This is a local quality gate: it checks geometry, CRS,
negative-buffer survivability, raster pixel support, and optional crop-mask coverage
without calling Planetary Computer or Sentinel Hub.

## Command

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

## Minimal Inline Manifest

```json
{
  "version": "orbitrisk.aoi_batch.v1",
  "name": "bordeaux-demo-aoi-pack",
  "date_range": {
    "start": "2021-01-01",
    "end": "2022-08-31"
  },
  "aois": [
    {
      "aoi_id": "FR_BDX_SYNTH_001",
      "region": "bordeaux",
      "crop": "vineyard",
      "crs": "EPSG:4326",
      "aoi": {
        "type": "Feature",
        "properties": {
          "asset_id": "FR_BDX_SYNTH_001",
          "crop": "vineyard"
        },
        "geometry": {
          "type": "Polygon",
          "coordinates": [
            [
              [4.82, 45.73],
              [4.83, 45.73],
              [4.83, 45.74],
              [4.82, 45.74],
              [4.82, 45.73]
            ]
          ]
        }
      }
    }
  ]
}
```

## Path-Based Manifest

Use paths when AOIs or crop masks are stored as separate GeoJSON files. Relative paths
are resolved from the manifest directory.

```json
{
  "version": "orbitrisk.aoi_batch.v1",
  "name": "rpg-vineyard-pack",
  "date_range": {
    "start": "2021-01-01",
    "end": "2022-08-31"
  },
  "masking": {
    "negative_buffer_m": 10,
    "min_valid_pixels": 20
  },
  "aois": [
    {
      "aoi_id": "FR_BDX_REAL_001",
      "region": "bordeaux",
      "crop": "vineyard",
      "crs": "EPSG:4326",
      "aoi_geojson_path": "../data/aoi/fr_bdx_real_001.geojson",
      "crop_mask_geojson_path": "../data/rpg/fr_bdx_real_001_vineyard.geojson",
      "crop_mask_crs": "EPSG:2154"
    }
  ]
}
```

## Validation Output

Each AOI is classified as `accepted` or `rejected`.

Current rejection reasons:

- `invalid_crs`
- `invalid_geometry`
- `missing_geojson_file`
- `empty_negative_buffer`
- `insufficient_pixels`
- `empty_crop_mask`
- `validation_error`

Warnings do not reject an AOI. Today, `missing_crop_mask` is a warning because some AOIs
can still be used for raw-vs-buffer comparisons.

## Notes

- `crop` is intentionally restricted to `vineyard` for the first MGA POC.
- `EPSG:4326` and `EPSG:2154` are both valid as long as the corresponding CRS field is
  explicit.
- A small AOI can still be kept in the manifest, but it should be expected to fail the
  local quality gate when Sentinel-2 10 m pixel support is insufficient.
- `examples/rpg_2023_vineyard_candidate_manifest.json` is generated from public IGN RPG
  2023 WFS data. Its crop masks are the original RPG vineyard parcel geometries; its AOIs
  are 20 m outward buffers around those parcels to simulate contaminated insured
  boundaries for basis-risk benchmarking.
