import json
from pathlib import Path

from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import (
    AoiMetrics,
    MaskCounts,
    Observation,
    RiskResponse,
    RiskSignal,
    SourceMetadata,
)
from orbitrisk.storage.cache import LocalRiskResponseCache, risk_response_cache_key

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_request.json"


def test_local_risk_response_cache_round_trips(tmp_path: Path) -> None:
    cache = LocalRiskResponseCache(tmp_path)
    response = _response()

    path = cache.set("abc", response)
    cached = cache.get("abc")

    assert path.exists()
    assert cached == response
    assert cache.get("missing") is None


def test_risk_response_cache_key_is_stable_and_scoped() -> None:
    payload = RiskRequest.model_validate(json.loads(FIXTURE.read_text()))

    first = risk_response_cache_key(
        payload,
        provider_name="planetary-computer",
        collection="sentinel-2-l2a",
        max_items=10,
    )
    second = risk_response_cache_key(
        payload,
        provider_name="planetary-computer",
        collection="sentinel-2-l2a",
        max_items=10,
    )
    different = risk_response_cache_key(
        payload,
        provider_name="planetary-computer",
        collection="sentinel-2-l2a",
        max_items=11,
    )

    assert first == second
    assert first != different

    masked = risk_response_cache_key(
        payload,
        provider_name="planetary-computer",
        collection="sentinel-2-l2a",
        max_items=10,
        extra={"crop_mask": {"type": "Polygon", "coordinates": []}},
    )
    assert masked != first


def _response() -> RiskResponse:
    return RiskResponse(
        request_id="cached",
        status="completed",
        source=SourceMetadata(
            provider="fake",
            collection="sentinel-2-l2a",
            processing_crs="EPSG:32631",
            resolution_m=10,
        ),
        aoi_metrics=AoiMetrics(area_ha=1, usable_area_ha=0.9, masked_area_pct=10),
        series=[
            Observation(
                date="2022-07-01",
                period="2022-07-01/2022-07-10",
                valid_pixel_count=10,
                cloud_pct=0,
                quality="good",
                indices={},
                mask_counts=MaskCounts(valid=10),
            )
        ],
        risk_signal=RiskSignal(
            water_stress_score=0,
            trigger_candidate=False,
            trigger_reason=None,
            confidence=1,
        ),
    )
