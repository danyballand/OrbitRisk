from datetime import date
from pathlib import Path

from orbitrisk.cli import (
    _quote_with_cache,
    render_validation_markdown,
    summarize_2022_validation,
)
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import (
    AoiMetrics,
    CriticalPeriod,
    IndexStats,
    MaskCounts,
    Observation,
    RiskResponse,
    RiskSignal,
    SourceMetadata,
)


def test_summarize_2022_validation_requires_trigger_and_baseline_support() -> None:
    response = _response(trigger=True, baseline_count=3)

    summary = summarize_2022_validation(response, region="bordeaux")

    assert summary["region"] == "bordeaux"
    assert summary["detected"] is True
    assert summary["baseline_supported_period_count"] == 1
    assert summary["ndmi_periods"][0]["ndmi_baseline_percentile"] == 0.0


def test_summarize_2022_validation_does_not_detect_without_baseline() -> None:
    response = _response(trigger=True, baseline_count=None)

    summary = summarize_2022_validation(response, region="languedoc")

    assert summary["detected"] is False
    assert summary["baseline_supported_period_count"] == 0


def test_render_validation_markdown_includes_key_fields() -> None:
    summary = summarize_2022_validation(
        _response(trigger=True, baseline_count=3),
        region="bordeaux",
    )

    rendered = render_validation_markdown(summary)

    assert "# OrbitRisk 2022 Drought Validation: bordeaux" in rendered
    assert "Baseline-supported periods" in rendered
    assert "2022-07-01/2022-07-10" in rendered


def test_quote_with_cache_avoids_recomputing(tmp_path: Path) -> None:
    request = RiskRequest.model_validate(
        {
            "request_id": "cache-test",
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
            "date_range": {"start": "2022-07-01", "end": "2022-07-31"},
        }
    )
    engine = FakeEngine()

    first = _quote_with_cache(
        engine,
        request,
        provider_name="fake",
        collection="sentinel-2-l2a",
        max_items=1,
        enabled=True,
        cache_dir=tmp_path,
    )
    second = _quote_with_cache(
        engine,
        request,
        provider_name="fake",
        collection="sentinel-2-l2a",
        max_items=1,
        enabled=True,
        cache_dir=tmp_path,
    )

    assert first == second
    assert engine.calls == 1


def _response(*, trigger: bool, baseline_count: int | None) -> RiskResponse:
    return RiskResponse(
        request_id="validation",
        status="completed",
        source=SourceMetadata(
            provider="fake",
            collection="sentinel-2-l2a",
            processing_crs="EPSG:32631",
            resolution_m=10,
        ),
        aoi_metrics=AoiMetrics(area_ha=1.0, usable_area_ha=0.9, masked_area_pct=10),
        series=[
            Observation(
                date=date(2022, 7, 11),
                period="2022-07-01/2022-07-10",
                valid_pixel_count=500,
                cloud_pct=0,
                quality="good",
                quality_flags=[],
                indices={
                    "ndmi": IndexStats(
                        mean=0.1,
                        median=0.1,
                        p10=0.05,
                        p90=0.2,
                        std=0.03,
                        ema=0.1,
                        anomaly_z=-2.0,
                        baseline_percentile=0.0 if baseline_count else None,
                        baseline_count=baseline_count,
                    )
                },
                mask_counts=MaskCounts(valid=500),
            )
        ],
        risk_signal=RiskSignal(
            water_stress_score=80,
            trigger_candidate=trigger,
            trigger_reason="ndmi_ema_below_0.15_for_2_periods" if trigger else None,
            confidence=0.9,
            critical_periods=[
                CriticalPeriod(start=date(2022, 7, 1), end=date(2022, 7, 20), severity="high")
            ]
            if trigger
            else [],
        ),
    )


class FakeEngine:
    def __init__(self) -> None:
        self.calls = 0

    def quote(
        self,
        request: RiskRequest,
        *,
        max_items: int,
        crop_mask_geojson=None,
        crop_mask_crs: str = "EPSG:4326",
    ) -> RiskResponse:
        self.calls += 1
        return _response(trigger=False, baseline_count=None)
