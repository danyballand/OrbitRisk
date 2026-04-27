from datetime import date
from pathlib import Path

from orbitrisk.batch.manifest import AoiBatchManifest
from orbitrisk.cli import _run_mask_benchmark_batch, render_mask_benchmark_batch_markdown
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


def test_run_mask_benchmark_batch_handles_success_and_rejected_aoi(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "batch",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "valid-with-mask",
                    "region": "bordeaux",
                    "aoi": _feature(),
                    "crop_mask": _left_half_crop_mask(),
                },
                {
                    "aoi_id": "too-small",
                    "region": "bordeaux",
                    "aoi": _tiny_feature(),
                },
            ],
        }
    )
    engine = FakeEngine()

    report = _run_mask_benchmark_batch(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        baseline_start=date(2019, 6, 1),
        end=date(2022, 8, 31),
        max_items=5,
        buffer_m=None,
        cache_enabled=False,
        cache_dir=tmp_path,
        include_without_crop_mask=False,
        engine=engine,
        provider_name="fake",
        collection="sentinel-2-l2a",
    )

    assert report["summary"]["success_count"] == 1
    assert report["summary"]["rejected_count"] == 1
    assert report["aggregate"]["basis_risk_classification_counts"]["improved"] == 1
    assert report["aggregate"]["basis_risk_classification_counts"]["not_run"] == 1
    assert (
        report["aggregate"]["comparison_rollups"]["vector_crop_mask_vs_raw_aoi"][
            "total_non_crop_pixel_delta"
        ]
        == 100
    )
    assert report["aois"][0]["benchmark"]["completed_variant_count"] == 3
    assert report["aois"][0]["basis_risk_assessment"]["classification"] == "improved"
    assert report["aois"][0]["key_metrics"]["crop_mask_non_crop_pixel_delta"] == 100
    assert report["aois"][1]["status"] == "rejected"
    assert "insufficient_pixels" in report["aois"][1]["reasons"]
    assert [call["request_id"] for call in engine.calls] == [
        "valid-with-mask",
        "valid-with-mask",
        "valid-with-mask",
    ]


def test_run_mask_benchmark_batch_skips_aoi_without_crop_mask(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "batch",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "valid-no-mask",
                    "region": "bordeaux",
                    "aoi": _feature(),
                },
            ],
        }
    )
    engine = FakeEngine()

    report = _run_mask_benchmark_batch(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        baseline_start=date(2019, 6, 1),
        end=date(2022, 8, 31),
        max_items=5,
        buffer_m=None,
        cache_enabled=False,
        cache_dir=tmp_path,
        include_without_crop_mask=False,
        engine=engine,
        provider_name="fake",
        collection="sentinel-2-l2a",
    )

    assert report["summary"]["skipped_count"] == 1
    assert report["aois"][0]["status"] == "skipped"
    assert report["aois"][0]["reasons"] == ["missing_crop_mask"]
    assert engine.calls == []


def test_run_mask_benchmark_batch_isolates_failed_aoi(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "batch",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "ok",
                    "region": "bordeaux",
                    "aoi": _feature(),
                    "crop_mask": _left_half_crop_mask(),
                },
                {
                    "aoi_id": "boom",
                    "region": "languedoc",
                    "aoi": _shifted_feature(),
                    "crop_mask": _shifted_crop_mask(),
                },
            ],
        }
    )
    engine = FakeEngine(fail_request_ids={"boom"})

    report = _run_mask_benchmark_batch(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        baseline_start=date(2019, 6, 1),
        end=date(2022, 8, 31),
        max_items=5,
        buffer_m=None,
        cache_enabled=False,
        cache_dir=tmp_path,
        include_without_crop_mask=False,
        engine=engine,
        provider_name="fake",
        collection="sentinel-2-l2a",
    )

    assert report["summary"]["success_count"] == 1
    assert report["summary"]["failed_count"] == 1
    assert report["aois"][1]["status"] == "failed"
    assert report["aois"][1]["reasons"] == ["benchmark_failed"]


def test_render_mask_benchmark_batch_markdown_includes_status_table(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "batch-md",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "valid-with-mask",
                    "region": "bordeaux",
                    "aoi": _feature(),
                    "crop_mask": _left_half_crop_mask(),
                },
            ],
        }
    )
    report = _run_mask_benchmark_batch(
        manifest,
        manifest_path=tmp_path / "manifest.json",
        baseline_start=date(2019, 6, 1),
        end=date(2022, 8, 31),
        max_items=5,
        buffer_m=None,
        cache_enabled=False,
        cache_dir=tmp_path,
        include_without_crop_mask=False,
        engine=FakeEngine(),
        provider_name="fake",
        collection="sentinel-2-l2a",
    )

    rendered = render_mask_benchmark_batch_markdown(report)

    assert "# OrbitRisk 2022 Batch Mask Benchmark: batch-md" in rendered
    assert "## Basis-Risk Summary" in rendered
    assert "## Variant Rollup" in rendered
    assert "| valid-with-mask | bordeaux | success | 3 |" in rendered


class FakeEngine:
    def __init__(self, fail_request_ids: set[str] | None = None) -> None:
        self.fail_request_ids = fail_request_ids or set()
        self.calls: list[dict[str, object]] = []

    def quote(
        self,
        request: RiskRequest,
        *,
        max_items: int,
        crop_mask_geojson=None,
        crop_mask_crs: str = "EPSG:4326",
    ) -> RiskResponse:
        self.calls.append(
            {
                "request_id": request.request_id,
                "max_items": max_items,
                "has_crop_mask": crop_mask_geojson is not None,
                "crop_mask_crs": crop_mask_crs,
            }
        )
        if request.request_id in self.fail_request_ids:
            raise RuntimeError("synthetic provider failure")
        return _response(
            request_id=request.request_id,
            crop_mask_used=crop_mask_geojson is not None,
        )


def _response(*, request_id: str, crop_mask_used: bool) -> RiskResponse:
    return RiskResponse(
        request_id=request_id,
        status="completed",
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
            crop_mask_area_ha=0.5 if crop_mask_used else None,
            crop_mask_coverage_pct=55.0 if crop_mask_used else None,
            crop_mask_geometry_count=1 if crop_mask_used else None,
        ),
        series=[
            Observation(
                date=date(2022, 7, 11),
                period="2022-07-01/2022-07-10",
                valid_pixel_count=500,
                cloud_pct=1.0,
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
                        baseline_percentile=0.0,
                        baseline_count=3,
                    )
                },
                mask_counts=MaskCounts(valid=500, non_crop=100 if crop_mask_used else 0),
            )
        ],
        risk_signal=RiskSignal(
            water_stress_score=80,
            trigger_candidate=True,
            trigger_reason="ndmi_ema_below_0.15_for_2_periods",
            confidence=0.9,
            critical_periods=[
                CriticalPeriod(start=date(2022, 7, 1), end=date(2022, 7, 20), severity="high")
            ],
        ),
    )


def _feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"asset_id": "FR_VINEYARD_TEST", "crop": "vineyard"},
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
    }


def _shifted_feature() -> dict:
    feature = _feature()
    feature["geometry"]["coordinates"] = [
        [
            [4.84, 45.73],
            [4.85, 45.73],
            [4.85, 45.74],
            [4.84, 45.74],
            [4.84, 45.73],
        ]
    ]
    return feature


def _tiny_feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"asset_id": "TOO_SMALL", "crop": "vineyard"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.82001, 45.73],
                    [4.82001, 45.73001],
                    [4.82, 45.73001],
                    [4.82, 45.73],
                ]
            ],
        },
    }


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


def _shifted_crop_mask() -> dict:
    return {
        "type": "Feature",
        "properties": {"source": "synthetic-rpg"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.84, 45.73],
                    [4.845, 45.73],
                    [4.845, 45.74],
                    [4.84, 45.74],
                    [4.84, 45.73],
                ]
            ],
        },
    }
