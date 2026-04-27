import json
from datetime import date
from pathlib import Path

import numpy as np

from orbitrisk.engine import prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.masking.vector_mask import crop_mask_from_geojson, polygonal_geometries

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


def test_crop_mask_from_geojson_rasterizes_crop_subset() -> None:
    payload = json.loads(FIXTURE.read_text())
    prepared = prepare_aoi(payload["aoi"], source_crs=payload["crs"], negative_buffer_m=10)
    job = prepare_raster_job(
        prepared,
        date_start=date(2022, 7, 1),
        date_end=date(2022, 7, 31),
        resolution_m=10,
    )

    crop_mask = crop_mask_from_geojson(
        _left_half_crop_mask(),
        source_crs="EPSG:4326",
        grid=job.grid,
        clip_geometry=prepared.analysis_geometry,
    )

    assert crop_mask.geometry_count == 1
    assert crop_mask.mask.dtype == np.bool_
    assert 0 < crop_mask.crop_pixel_count < int(job.aoi_mask.sum())
    assert 0 < crop_mask.crop_coverage_fraction < 1


def test_polygonal_geometries_accepts_feature_collection() -> None:
    geometries = polygonal_geometries(
        {
            "type": "FeatureCollection",
            "features": [_left_half_crop_mask()],
        }
    )

    assert len(geometries) == 1


def _left_half_crop_mask() -> dict:
    return {
        "type": "Feature",
        "properties": {"source": "synthetic-rpg"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.825, 45.73],
                    [4.825, 45.74],
                    [4.82, 45.74],
                    [4.82, 45.73],
                ]
            ],
        },
    }
