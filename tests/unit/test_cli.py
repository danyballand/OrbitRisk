import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from orbitrisk.cli import run_planetary_computer_smoke


def test_smoke_runner_uses_fixed_geobox(monkeypatch, tmp_path: Path) -> None:
    payload = {
        "request_id": "smoke",
        "aoi": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [4.82, 45.73],
                        [4.83, 45.73],
                        [4.83, 45.74],
                        [4.82, 45.74],
                        [4.82, 45.73],
                    ]
                ],
            },
        },
        "crs": "EPSG:4326",
        "date_range": {"start": "2022-07-01", "end": "2022-07-10"},
        "indices": ["ndvi"],
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(payload))
    calls = {}

    class FakeProvider:
        def __init__(self, settings) -> None:
            calls["settings"] = settings

        def load_datacube(self, query, *, geobox):
            calls["query"] = query
            calls["geobox"] = geobox
            return "dataset"

    def fake_summarize_datacube(dataset, **kwargs):
        calls["dataset"] = dataset
        calls["summary_kwargs"] = kwargs
        return []

    monkeypatch.setattr("orbitrisk.cli.PlanetaryComputerProvider", FakeProvider)
    monkeypatch.setattr("orbitrisk.cli.summarize_datacube", fake_summarize_datacube)

    result = run_planetary_computer_smoke(
        SimpleNamespace(
            request_json=request_path,
            start=date(2022, 7, 1),
            end=date(2022, 7, 10),
            resolution_m=10,
            max_items=1,
            max_cloud_cover_pct=80.0,
            temporal=None,
        )
    )

    assert result["request_id"] == "smoke"
    assert calls["query"].max_items == 1
    assert calls["geobox"] is not None
    assert calls["summary_kwargs"]["requested_indices"] == ["ndvi"]
    assert result["temporal"] == "P10D"
    assert result["composites"] == []
