#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from orbitrisk.geo.crs import best_utm_crs_for_geometry

WFS_URL = "https://data.geopf.fr/wfs"
RPG_LAYER = "RPG.2023:parcelles_graphiques"
RPG_VINEYARD_GROUP_CODE = "21"
WGS84 = CRS.from_epsg(4326)


@dataclass(frozen=True)
class SeedArea:
    slug: str
    region: str
    bbox: tuple[float, float, float, float]
    target_count: int


SEED_AREAS = [
    SeedArea("bordeaux_right_bank", "bordeaux", (-0.25, 44.85, -0.05, 44.98), 2),
    SeedArea("medoc", "bordeaux", (-0.85, 44.95, -0.65, 45.25), 2),
    SeedArea("sauternes", "bordeaux", (-0.42, 44.48, -0.25, 44.62), 1),
    SeedArea("pic_saint_loup", "languedoc", (3.70, 43.68, 3.95, 43.88), 2),
    SeedArea("minervois", "languedoc", (2.65, 43.10, 2.95, 43.30), 2),
    SeedArea("beziers", "languedoc", (3.05, 43.25, 3.35, 43.50), 1),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a public RPG 2023 vineyard candidate AOI pack."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("."),
        help="Repository root where data/ and examples/ will be written.",
    )
    parser.add_argument("--max-features-per-seed", type=int, default=25)
    parser.add_argument("--min-surface-ha", type=float, default=1.0)
    parser.add_argument("--aoi-buffer-m", type=float, default=20.0)
    args = parser.parse_args()

    repo_root = args.output_root
    data_root = repo_root / "data"
    aoi_dir = data_root / "aoi" / "rpg_2023_vineyard_candidates"
    crop_mask_dir = data_root / "rpg" / "rpg_2023_vineyard_candidates"
    manifest_path = repo_root / "examples" / "rpg_2023_vineyard_candidate_manifest.json"
    aoi_dir.mkdir(parents=True, exist_ok=True)
    crop_mask_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    seen_parcel_ids: set[str] = set()
    for seed in SEED_AREAS:
        features = fetch_vineyard_features(seed, count=args.max_features_per_seed)
        accepted_for_seed = 0
        for feature in features:
            properties = feature.get("properties", {})
            parcel_id = str(properties.get("id_parcel") or feature.get("id"))
            if parcel_id in seen_parcel_ids:
                continue
            surface_ha = float(properties.get("surf_parc") or 0)
            if surface_ha < args.min_surface_ha:
                continue

            crop_geometry = shape(feature["geometry"])
            if crop_geometry.is_empty or not crop_geometry.is_valid:
                continue
            aoi_geometry = buffered_wgs84(crop_geometry, args.aoi_buffer_m)
            if aoi_geometry.is_empty or not aoi_geometry.is_valid:
                continue

            accepted_for_seed += 1
            seen_parcel_ids.add(parcel_id)
            aoi_id = f"FR_RPG23_{seed.slug.upper()}_{accepted_for_seed:02d}"
            crop_mask_feature = geojson_feature(
                crop_geometry,
                properties=source_properties(
                    aoi_id=aoi_id,
                    seed=seed,
                    rpg_properties=properties,
                    geometry_role="crop_mask",
                    derivation="original RPG 2023 vineyard parcel geometry",
                    approximate_area_ha=surface_ha,
                ),
            )
            aoi_feature = geojson_feature(
                aoi_geometry,
                properties=source_properties(
                    aoi_id=aoi_id,
                    seed=seed,
                    rpg_properties=properties,
                    geometry_role="aoi",
                    derivation=f"{args.aoi_buffer_m:g} m outward buffer around RPG parcel",
                    approximate_area_ha=projected_area_ha(aoi_geometry),
                ),
            )

            aoi_path = aoi_dir / f"{aoi_id.lower()}.geojson"
            crop_mask_path = crop_mask_dir / f"{aoi_id.lower()}_crop_mask.geojson"
            write_json(aoi_path, aoi_feature)
            write_json(crop_mask_path, crop_mask_feature)
            entries.append(
                {
                    "aoi_id": aoi_id,
                    "region": seed.region,
                    "crop": "vineyard",
                    "crs": "EPSG:4326",
                    "aoi_geojson_path": relative_to(manifest_path.parent, aoi_path),
                    "crop_mask_geojson_path": relative_to(manifest_path.parent, crop_mask_path),
                    "crop_mask_crs": "EPSG:4326",
                }
            )
            if accepted_for_seed >= seed.target_count:
                break

    manifest = {
        "version": "orbitrisk.aoi_batch.v1",
        "name": "rpg-2023-vineyard-candidate-pack",
        "date_range": {"start": "2019-06-01", "end": "2022-08-31"},
        "masking": {
            "negative_buffer_m": 10,
            "min_valid_pixels": 20,
            "exclude_scl_classes": [0, 1, 3, 7, 8, 9, 10, 11],
            "min_clear_fraction": 0.7,
        },
        "aois": entries,
    }
    write_json(manifest_path, manifest)
    print(f"Wrote {len(entries)} AOIs to {manifest_path}")
    return 0


def fetch_vineyard_features(seed: SeedArea, *, count: int) -> list[dict[str, Any]]:
    minx, miny, maxx, maxy = seed.bbox
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": RPG_LAYER,
        "COUNT": str(count),
        "OUTPUTFORMAT": "json",
        "SRSNAME": "EPSG:4326",
        "SORTBY": "surf_parc D",
        "CQL_FILTER": (
            f"code_group='{RPG_VINEYARD_GROUP_CODE}' "
            f"AND BBOX(geom,{minx},{miny},{maxx},{maxy},'EPSG:4326')"
        ),
    }
    url = f"{WFS_URL}?{urlencode(params)}"
    with urlopen(url, timeout=60) as response:
        document = json.loads(response.read().decode("utf-8"))
    features = document.get("features", [])
    if not isinstance(features, list):
        return []
    return [feature for feature in features if isinstance(feature, dict)]


def buffered_wgs84(geometry: BaseGeometry, distance_m: float) -> BaseGeometry:
    local_crs = best_utm_crs_for_geometry(geometry)
    to_local = Transformer.from_crs(WGS84, local_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(local_crs, WGS84, always_xy=True)
    projected = transform(to_local.transform, geometry)
    buffered = projected.buffer(distance_m)
    simplified = buffered.simplify(1.0, preserve_topology=True)
    return transform(to_wgs84.transform, simplified)


def projected_area_ha(geometry: BaseGeometry) -> float:
    local_crs = best_utm_crs_for_geometry(geometry)
    to_local = Transformer.from_crs(WGS84, local_crs, always_xy=True)
    return transform(to_local.transform, geometry).area / 10_000


def geojson_feature(geometry: BaseGeometry, *, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": mapping(geometry),
    }


def source_properties(
    *,
    aoi_id: str,
    seed: SeedArea,
    rpg_properties: dict[str, Any],
    geometry_role: str,
    derivation: str,
    approximate_area_ha: float,
) -> dict[str, Any]:
    return {
        "asset_id": aoi_id,
        "region": seed.region,
        "crop": "vineyard",
        "geometry_role": geometry_role,
        "geometry_derivation": derivation,
        "approximate_area_ha": round(approximate_area_ha, 4),
        "source": "IGN RPG 2023 WFS",
        "source_url": WFS_URL,
        "source_layer": RPG_LAYER,
        "source_license_note": "See IGN/cartes.gouv.fr RPG terms of use",
        "rpg_id_parcel": str(rpg_properties.get("id_parcel", "")),
        "rpg_code_cultu": str(rpg_properties.get("code_cultu", "")),
        "rpg_code_group": str(rpg_properties.get("code_group", "")),
        "rpg_surf_parc_ha": rpg_properties.get("surf_parc"),
        "seed_area": seed.slug,
    }


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def relative_to(base_dir: Path, target: Path) -> str:
    return os.path.relpath(target, start=base_dir)


if __name__ == "__main__":
    raise SystemExit(main())
