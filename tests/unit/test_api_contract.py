import json
from pathlib import Path

import numpy as np
import xarray as xr
from fastapi.testclient import TestClient

from orbitrisk.api.main import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


def test_quote_endpoint_returns_auditable_aoi_metadata() -> None:
    client = TestClient(app)
    payload = json.loads(FIXTURE.read_text())

    response = client.post("/v1/risk/quote", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == payload["request_id"]
    assert body["source"]["processing_crs"] == "EPSG:32631"
    assert body["aoi_metrics"]["area_ha"] > body["aoi_metrics"]["usable_area_ha"]
    assert body["series"][0]["mask_counts"]["valid"] > 0
    assert "trigger_candidate" in body["risk_signal"]


def test_live_quote_endpoint_uses_provider(monkeypatch) -> None:
    calls = {}

    class FakeProvider:
        def __init__(self, settings) -> None:
            calls["settings"] = settings

        def load_datacube(self, query, *, geobox=None):
            calls["query"] = query
            calls["geobox"] = geobox
            return _dataset(tuple(geobox.shape))

    monkeypatch.setattr("orbitrisk.api.routes.PlanetaryComputerProvider", FakeProvider)
    client = TestClient(app)
    payload = json.loads(FIXTURE.read_text())
    payload["date_range"] = {"start": "2022-07-01", "end": "2022-07-31"}

    response = client.post("/v1/risk/quote/live?max_items=3&use_cache=false", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert calls["query"].max_items == 3
    assert calls["geobox"] is not None
    assert body["source"]["provider"] == "planetary-computer"
    assert body["series"][0]["indices"]["ndmi"]["ema"] is not None
    assert body["series"][0]["quality_flags"] == []


def test_live_quote_endpoint_accepts_feature_collection_crop_mask(monkeypatch) -> None:
    class FakeProvider:
        def __init__(self, settings) -> None:
            self.settings = settings

        def load_datacube(self, query, *, geobox=None):
            return _dataset(tuple(geobox.shape))

    monkeypatch.setattr("orbitrisk.api.routes.PlanetaryComputerProvider", FakeProvider)
    client = TestClient(app)
    payload = json.loads(FIXTURE.read_text())
    payload["date_range"] = {"start": "2022-07-01", "end": "2022-07-31"}
    payload["crop_mask"] = {
        "type": "FeatureCollection",
        "features": [_left_half_crop_mask()],
    }
    payload["crop_mask_crs"] = "EPSG:4326"

    response = client.post("/v1/risk/quote/live?max_items=3&use_cache=false", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["aoi_metrics"]["crop_mask_area_ha"] > 0
    assert 0 < body["aoi_metrics"]["crop_mask_coverage_pct"] < 100
    assert body["aoi_metrics"]["crop_mask_geometry_count"] == 1
    assert body["series"][0]["mask_counts"]["non_crop"] > 0


def _dataset(grid_shape: tuple[int, int]) -> xr.Dataset:
    height, width = grid_shape
    shape = (2, height, width)
    coords = {
        "time": np.array(["2022-07-01", "2022-07-11"], dtype="datetime64[D]"),
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
