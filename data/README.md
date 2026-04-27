# OrbitRisk Data Packs

This directory stores small, versioned validation fixtures that are safe to commit.

## RPG 2023 Vineyard Candidate Pack

Generated files:

- `examples/rpg_2023_vineyard_candidate_manifest.json`
- `data/aoi/rpg_2023_vineyard_candidates/*.geojson`
- `data/rpg/rpg_2023_vineyard_candidates/*_crop_mask.geojson`

Source:

- Producer/service: IGN Géoplateforme WFS
- Endpoint: `https://data.geopf.fr/wfs`
- Layer: `RPG.2023:parcelles_graphiques`
- Crop filter: `code_group = 21`, labelled `Vignes` in `RPG.2023:codes_cultures`
- CRS written to files: `EPSG:4326`

Generation command:

```bash
PYTHONPATH=src python scripts/build_rpg_vineyard_pack.py --output-root .
```

Important caveat: the `crop_mask` GeoJSON is the original RPG 2023 vineyard parcel. The
AOI GeoJSON is a 20 m outward buffer around that same RPG parcel, used to simulate a
contaminated insured boundary for raw-vs-buffer-vs-crop-mask benchmarking. This makes
non-crop pixel removal measurable without using private customer parcel data.

These AOIs are public-data candidates for engineering validation, not an underwriting
portfolio.
