import json
from pathlib import Path

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
