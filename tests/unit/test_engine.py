import json
from datetime import date
from pathlib import Path

from orbitrisk.engine import SENTINEL2_L2A_BANDS, prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


def test_prepare_raster_job_builds_query_and_mask() -> None:
    payload = json.loads(FIXTURE.read_text())
    prepared_aoi = prepare_aoi(
        payload["aoi"],
        source_crs=payload["crs"],
        negative_buffer_m=10,
    )

    job = prepare_raster_job(
        prepared_aoi,
        date_start=date.fromisoformat(payload["date_range"]["start"]),
        date_end=date.fromisoformat(payload["date_range"]["end"]),
        resolution_m=10,
        max_items=3,
    )

    assert job.query.output_crs == "EPSG:32631"
    assert job.query.bands == SENTINEL2_L2A_BANDS
    assert job.query.max_items == 3
    assert job.aoi_mask.shape == job.grid.shape
    assert job.aoi_mask.sum() > 0
