from pathlib import Path

from orbitrisk.schemas.response import (
    AoiMetrics,
    MaskCounts,
    Observation,
    RiskResponse,
    RiskSignal,
    SourceMetadata,
)
from orbitrisk.storage.artifacts import LocalArtifactStore, artifact_key, content_hash


def test_local_artifact_store_round_trips_json_markdown_and_chart(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    key = artifact_key("validation-report", payload={"request_id": "artifact-test"})
    response = _response()

    json_meta = store.write_json_response(key, response)
    markdown_meta = store.write_markdown_report(key, "# Report\n\nAccepted.\n")
    chart_meta = store.write_chart_artifact(key, "ndmi chart", b"<svg></svg>")

    assert json_meta.path.exists()
    assert json_meta.kind == "json_response"
    assert json_meta.content_hash == content_hash(json_meta.path.read_bytes())
    assert store.read_json_response(key) == response

    assert markdown_meta.path.exists()
    assert markdown_meta.kind == "markdown_report"
    assert store.read_markdown_report(key) == "# Report\n\nAccepted.\n"

    assert chart_meta.path.exists()
    assert chart_meta.kind == "chart_artifact"
    assert chart_meta.content_type == "image/svg+xml"
    assert store.read_chart_artifact(key, "ndmi chart") == b"<svg></svg>"


def test_local_artifact_store_returns_none_for_missing_artifacts(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)

    assert store.read_json_response("missing") is None
    assert store.read_markdown_report("missing") is None
    assert store.read_chart_artifact("missing", "chart") is None


def test_artifact_key_is_deterministic_and_scoped() -> None:
    first = artifact_key("report", payload={"aoi_id": "FR_TEST", "kind": "json"})
    second = artifact_key("report", payload={"kind": "json", "aoi_id": "FR_TEST"})
    different_namespace = artifact_key("chart", payload={"aoi_id": "FR_TEST", "kind": "json"})
    different_payload = artifact_key("report", payload={"aoi_id": "FR_TEST", "kind": "md"})

    assert first == second
    assert first != different_namespace
    assert first != different_payload


def _response() -> RiskResponse:
    return RiskResponse(
        request_id="artifact-test",
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
