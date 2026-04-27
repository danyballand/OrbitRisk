from datetime import date
from pathlib import Path

from orbitrisk.cli import (
    _quote_with_cache,
    _validation_payload,
    render_mask_benchmark_markdown,
    render_validation_markdown,
    summarize_2022_validation,
    summarize_mask_benchmark,
)
from orbitrisk.reporting.charts import write_mask_benchmark_charts
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
    assert summary["validation_assessment"]["classification"] == "accepted"
    assert summary["baseline_supported_period_count"] == 1
    assert summary["ndmi_periods"][0]["ndmi_baseline_percentile"] == 0.0


def test_summarize_2022_validation_does_not_detect_without_baseline() -> None:
    response = _response(trigger=True, baseline_count=None)

    summary = summarize_2022_validation(response, region="languedoc")

    assert summary["detected"] is False
    assert summary["validation_assessment"]["classification"] == "rejected"
    assert "no_baseline_support" in summary["validation_assessment"]["reasons"]
    assert summary["baseline_supported_period_count"] == 0


def test_render_validation_markdown_includes_key_fields() -> None:
    summary = summarize_2022_validation(
        _response(trigger=True, baseline_count=3),
        region="bordeaux",
    )

    rendered = render_validation_markdown(summary)

    assert "# OrbitRisk 2022 Drought Validation: bordeaux" in rendered
    assert "Assessment: `accepted`" in rendered
    assert "Baseline-supported periods" in rendered
    assert "2022-07-01/2022-07-10" in rendered


def test_summarize_2022_validation_marks_weak_supported_signal_ambiguous() -> None:
    summary = summarize_2022_validation(
        _response(trigger=False, baseline_count=3),
        region="bordeaux",
    )

    assert summary["validation_assessment"]["classification"] == "ambiguous"
    assert "weak_or_no_drought_signal" in summary["validation_assessment"]["reasons"]


def test_summarize_2022_validation_rejects_insufficient_pixels() -> None:
    summary = summarize_2022_validation(
        _response(
            trigger=True,
            baseline_count=3,
            valid_pixel_count=5,
            quality="rejected",
            quality_flags=["too_few_valid_pixels", "no_index_stats"],
            status="partial",
        ),
        region="bordeaux",
    )

    assert summary["validation_assessment"]["classification"] == "rejected"
    assert "insufficient_valid_pixels" in summary["validation_assessment"]["reasons"]
    assert summary["quality_flag_counts"]["too_few_valid_pixels"] == 1


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


def test_validation_payload_can_strip_embedded_crop_mask_for_benchmark() -> None:
    payload = {
        "request_id": "benchmark",
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
        "crop_mask": {"type": "Polygon", "coordinates": []},
        "crop_mask_crs": "EPSG:4326",
        "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
    }

    prepared = _validation_payload(
        payload,
        baseline_start=date(2019, 6, 1),
        end=date(2022, 8, 31),
        negative_buffer_m=0,
        include_crop_mask=False,
    )

    assert "crop_mask" not in prepared
    assert "crop_mask_crs" not in prepared
    assert prepared["masking"]["negative_buffer_m"] == 0


def test_summarize_mask_benchmark_compares_against_raw_aoi() -> None:
    raw = _response(
        trigger=True,
        baseline_count=3,
        valid_pixel_count=600,
        non_crop=0,
        confidence=0.5,
        ndmi_mean=0.18,
    )
    crop_mask = _response(
        trigger=True,
        baseline_count=3,
        valid_pixel_count=420,
        non_crop=180,
        confidence=0.8,
        ndmi_mean=0.12,
        crop_mask_coverage_pct=70.0,
    )

    summary = summarize_mask_benchmark(
        [
            ("raw_aoi", "Raw AOI mean", raw),
            ("vector_crop_mask", "External crop mask + buffer", crop_mask),
            ("missing_crop_mask", "Skipped crop mask", None),
        ],
        region="bordeaux",
    )

    assert summary["completed_variant_count"] == 2
    assert summary["variants"][2]["status"] == "skipped"
    assert summary["comparisons"][0]["candidate_variant"] == "vector_crop_mask"
    assert summary["comparisons"][0]["median_valid_pixel_delta_pct"] == -30.0
    assert summary["comparisons"][0]["non_crop_pixel_delta"] == 180


def test_render_mask_benchmark_markdown_includes_comparison_table() -> None:
    summary = summarize_mask_benchmark(
        [
            ("raw_aoi", "Raw AOI mean", _response(trigger=True, baseline_count=3)),
            (
                "buffered_aoi",
                "AOI mean with 10 m negative buffer",
                _response(trigger=True, baseline_count=3, valid_pixel_count=450),
            ),
        ],
        region="bordeaux",
    )

    rendered = render_mask_benchmark_markdown(summary)

    assert "# OrbitRisk 2022 Mask Benchmark: bordeaux" in rendered
    assert "Comparison vs Raw AOI" in rendered
    assert "AOI mean with 10 m negative buffer" in rendered


def test_write_mask_benchmark_charts_generates_svg_artifacts(tmp_path: Path) -> None:
    summary = summarize_mask_benchmark(
        [
            ("raw_aoi", "Raw AOI mean", _response(trigger=True, baseline_count=3)),
            (
                "buffered_aoi",
                "AOI mean with 10 m negative buffer",
                _response(trigger=True, baseline_count=3, valid_pixel_count=450),
            ),
            ("vector_crop_mask", "External crop mask + buffer", None),
        ],
        region="bordeaux",
    )

    artifacts = write_mask_benchmark_charts(
        summary,
        tmp_path / "charts",
        aoi_id="bordeaux-aoi-1",
    )
    summary["artifacts"] = {"charts": artifacts}
    rendered = render_mask_benchmark_markdown(summary)

    assert len(artifacts) == 6
    assert {artifact["metric"] for artifact in artifacts} == {
        "ndmi",
        "valid_pixels",
        "cloud_pct",
    }
    assert (tmp_path / "charts" / "bordeaux-aoi-1__raw_aoi__ndmi.svg").exists()
    assert "<svg" in (tmp_path / "charts" / "bordeaux-aoi-1__raw_aoi__ndmi.svg").read_text()
    assert "## Chart Artifacts" in rendered


def _response(
    *,
    trigger: bool,
    baseline_count: int | None,
    valid_pixel_count: int = 500,
    cloud_pct: float = 0.0,
    quality: str = "good",
    quality_flags: list[str] | None = None,
    status: str = "completed",
    non_crop: int = 0,
    confidence: float = 0.9,
    ndmi_mean: float = 0.1,
    crop_mask_coverage_pct: float | None = None,
) -> RiskResponse:
    return RiskResponse(
        request_id="validation",
        status=status,
        source=SourceMetadata(
            provider="fake",
            collection="sentinel-2-l2a",
            processing_crs="EPSG:32631",
            resolution_m=10,
        ),
        aoi_metrics=AoiMetrics(
            area_ha=1.0,
            usable_area_ha=0.9,
            masked_area_pct=10,
            crop_mask_area_ha=0.7 if crop_mask_coverage_pct is not None else None,
            crop_mask_coverage_pct=crop_mask_coverage_pct,
            crop_mask_geometry_count=1 if crop_mask_coverage_pct is not None else None,
        ),
        series=[
            Observation(
                date=date(2022, 7, 11),
                period="2022-07-01/2022-07-10",
                valid_pixel_count=valid_pixel_count,
                cloud_pct=cloud_pct,
                quality=quality,
                quality_flags=quality_flags or [],
                indices={
                    "ndmi": IndexStats(
                        mean=ndmi_mean,
                        median=ndmi_mean,
                        p10=ndmi_mean - 0.05,
                        p90=ndmi_mean + 0.1,
                        std=0.03,
                        ema=ndmi_mean,
                        anomaly_z=-2.0,
                        baseline_percentile=0.0 if baseline_count else None,
                        baseline_count=baseline_count,
                    )
                },
                mask_counts=MaskCounts(valid=valid_pixel_count, non_crop=non_crop),
            )
        ],
        risk_signal=RiskSignal(
            water_stress_score=80,
            trigger_candidate=trigger,
            trigger_reason="ndmi_ema_below_0.15_for_2_periods" if trigger else None,
            confidence=confidence,
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
