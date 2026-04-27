import json
from pathlib import Path

import numpy as np

from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.geo.raster_grid import grid_from_geometry

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


def test_prepare_aoi_projects_to_local_utm_and_buffers() -> None:
    payload = json.loads(FIXTURE.read_text())

    prepared = prepare_aoi(payload["aoi"], source_crs=payload["crs"], negative_buffer_m=10)

    assert prepared.processing_crs.to_epsg() == 32631
    assert prepared.area_ha > prepared.usable_area_ha
    assert prepared.masked_area_pct > 0


def test_grid_from_geometry_rasterizes_analysis_area() -> None:
    payload = json.loads(FIXTURE.read_text())
    prepared = prepare_aoi(payload["aoi"], source_crs=payload["crs"], negative_buffer_m=10)

    grid = grid_from_geometry(
        prepared.geometry_projected,
        crs=prepared.processing_crs,
        resolution_m=10,
    )
    mask = grid.mask(prepared.analysis_geometry)

    assert grid.shape[0] > 0
    assert grid.shape[1] > 0
    west, south, east, north = grid.bounds
    assert west < east
    assert south < north
    assert 600_000 < west < 700_000
    assert 5_000_000 < south < 5_100_000
    assert mask.dtype == np.bool_
    assert 0 < int(mask.sum()) < mask.size
