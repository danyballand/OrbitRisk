import json
from pathlib import Path

import numpy as np
import xarray as xr

from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.request import RiskRequest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


class FakeProvider:
    def __init__(self) -> None:
        self.calls = []

    def load_datacube(self, query, *, geobox=None):
        self.calls.append((query, geobox))
        return _dataset(tuple(geobox.shape))


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


def _dataset(grid_shape: tuple[int, int]) -> xr.Dataset:
    height, width = grid_shape
    shape = (3, height, width)
    coords = {
        "time": np.array(["2022-07-01", "2022-07-11", "2022-07-21"], dtype="datetime64[D]"),
        "y": np.arange(height),
        "x": np.arange(width),
    }
    return xr.Dataset(
        {
            "B03": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B04": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B05": (("time", "y", "x"), np.full(shape, 0.30, dtype=np.float32)),
            "B08": (("time", "y", "x"), np.full(shape, 0.60, dtype=np.float32)),
            "B11": (("time", "y", "x"), np.full(shape, 0.30, dtype=np.float32)),
            "SCL": (("time", "y", "x"), np.full(shape, 4, dtype=np.uint8)),
        },
        coords=coords,
    )
