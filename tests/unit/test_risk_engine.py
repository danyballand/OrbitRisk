import json
from pathlib import Path

import numpy as np
import xarray as xr

from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.request import RiskRequest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


class FakeProvider:
    def __init__(self, dates: list[str] | None = None, *, drought_last: bool = False) -> None:
        self.calls = []
        self.dates = dates or ["2022-07-01", "2022-07-11", "2022-07-21"]
        self.drought_last = drought_last

    def load_datacube(self, query, *, geobox=None):
        self.calls.append((query, geobox))
        return _dataset(tuple(geobox.shape), dates=self.dates, drought_last=self.drought_last)


def test_risk_engine_builds_live_response_from_provider_datacube() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["date_range"] = {"start": "2022-07-01", "end": "2022-07-31"}
    payload["aggregation"] = {
        "temporal": "P10D",
        "spatial_stats": ["mean", "median", "p10", "p90", "std"],
    }
    request = RiskRequest.model_validate(payload)
    provider = FakeProvider()

    response = RiskEngine(
        provider,
        provider_name="fake-provider",
        collection="sentinel-2-l2a",
    ).quote(request, max_items=10)

    assert provider.calls[0][0].max_items == 10
    assert provider.calls[0][1] is not None
    assert response.source.provider == "fake-provider"
    assert response.source.processing_crs == "EPSG:32631"
    assert response.status == "completed"
    assert [observation.period for observation in response.series] == [
        "2022-07-01/2022-07-10",
        "2022-07-11/2022-07-20",
        "2022-07-21/2022-07-30",
    ]
    assert response.series[0].indices["ndmi"].ema is not None
    assert response.risk_signal.confidence > 0


def test_risk_engine_adds_seasonal_baseline_metadata() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["date_range"] = {"start": "2020-07-01", "end": "2023-07-31"}
    request = RiskRequest.model_validate(payload)
    provider = FakeProvider(
        dates=["2020-07-11", "2021-07-11", "2022-07-11", "2023-07-11"],
        drought_last=True,
    )

    response = RiskEngine(
        provider,
        provider_name="fake-provider",
        collection="sentinel-2-l2a",
    ).quote(request, max_items=20)

    latest_ndmi = response.series[-1].indices["ndmi"]
    assert latest_ndmi.baseline_count == 3
    assert latest_ndmi.baseline_percentile == 0.0
    assert latest_ndmi.anomaly_z is not None


def test_risk_engine_applies_crop_mask_geojson() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["date_range"] = {"start": "2022-07-01", "end": "2022-07-31"}
    request = RiskRequest.model_validate(payload)
    provider = FakeProvider()

    response = RiskEngine(
        provider,
        provider_name="fake-provider",
        collection="sentinel-2-l2a",
    ).quote(request, max_items=10, crop_mask_geojson=_left_half_crop_mask())

    assert response.series[0].mask_counts.non_crop > 0
    assert response.aoi_metrics.crop_mask_area_ha is not None
    assert response.aoi_metrics.crop_mask_coverage_pct is not None
    assert response.aoi_metrics.crop_mask_geometry_count == 1
    full_grid_pixels = provider.calls[0][1].shape.y * provider.calls[0][1].shape.x
    assert response.series[0].valid_pixel_count < full_grid_pixels


def _dataset(
    grid_shape: tuple[int, int],
    *,
    dates: list[str],
    drought_last: bool,
) -> xr.Dataset:
    height, width = grid_shape
    shape = (len(dates), height, width)
    swir = np.full(shape, 0.30, dtype=np.float32)
    if drought_last:
        swir[-1] = 0.52
    coords = {
        "time": np.array(dates, dtype="datetime64[D]"),
        "y": np.arange(height),
        "x": np.arange(width),
    }
    return xr.Dataset(
        {
            "B03": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B04": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B05": (("time", "y", "x"), np.full(shape, 0.30, dtype=np.float32)),
            "B08": (("time", "y", "x"), np.full(shape, 0.60, dtype=np.float32)),
            "B11": (("time", "y", "x"), swir),
            "SCL": (("time", "y", "x"), np.full(shape, 4, dtype=np.uint8)),
        },
        coords=coords,
    )


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
