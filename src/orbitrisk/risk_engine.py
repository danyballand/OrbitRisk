from datetime import date
from typing import Any, Literal, Protocol, cast

from orbitrisk.engine import prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.masking.vector_mask import VectorCropMask, crop_mask_from_geojson
from orbitrisk.processing.datacube import summarize_datacube
from orbitrisk.processing.observation import ObservationStats
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import (
    AoiMetrics,
    IndexStats,
    MaskCounts,
    Observation,
    Quality,
    RiskResponse,
    RiskSignal,
    SourceMetadata,
)
from orbitrisk.timeseries.anomalies import z_scores
from orbitrisk.timeseries.baseline import seasonal_baseline
from orbitrisk.timeseries.compositing import CompositeObservation, composite_observations
from orbitrisk.timeseries.smoothing import ema
from orbitrisk.timeseries.triggers import detect_water_stress_trigger


class RasterProvider(Protocol):
    def load_datacube(self, query: Any, *, geobox: Any | None = None) -> Any: ...


IndexEnrichment = dict[int, tuple[float | None, float | None, float | None, int | None]]


class RiskEngine:
    def __init__(
        self,
        provider: RasterProvider,
        *,
        provider_name: str,
        collection: str,
    ) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.collection = collection

    def quote(
        self,
        payload: RiskRequest,
        *,
        max_items: int | None = None,
        crop_mask_geojson: dict[str, Any] | None = None,
        crop_mask_crs: str = "EPSG:4326",
    ) -> RiskResponse:
        prepared_aoi = prepare_aoi(
            payload.aoi.model_dump(),
            source_crs=payload.crs,
            negative_buffer_m=payload.masking.negative_buffer_m,
        )
        job = prepare_raster_job(
            prepared_aoi,
            date_start=payload.date_range.start,
            date_end=payload.date_range.end,
            resolution_m=payload.resolution_m,
            max_cloud_cover_pct=100.0,
            max_items=max_items,
        )

        crop_mask = None
        crop_mask_result: VectorCropMask | None = None
        crop_mask_document = None
        crop_mask_source_crs = crop_mask_crs
        if crop_mask_geojson is not None:
            crop_mask_document = crop_mask_geojson
        elif payload.crop_mask is not None:
            crop_mask_document = payload.crop_mask.model_dump(mode="json")
            crop_mask_source_crs = payload.crop_mask_crs
        if crop_mask_document is not None:
            crop_mask_result = crop_mask_from_geojson(
                crop_mask_document,
                source_crs=crop_mask_source_crs,
                grid=job.grid,
                clip_geometry=prepared_aoi.analysis_geometry,
            )
            crop_mask = crop_mask_result.mask

        dataset = self.provider.load_datacube(job.query, geobox=job.grid.to_odc_geobox())
        observations = summarize_datacube(
            dataset,
            aoi_mask=job.aoi_mask,
            crop_mask=crop_mask,
            requested_indices=list(payload.indices),
            min_valid_pixels=payload.masking.min_valid_pixels,
            min_clear_fraction=payload.masking.min_clear_fraction,
            exclude_scl_classes=set(payload.masking.exclude_scl_classes),
        )
        composites = composite_observations(
            observations,
            temporal=payload.aggregation.temporal,
            start=payload.date_range.start,
            end=payload.date_range.end,
        )
        series = _build_observation_series(
            composites,
            indices=list(payload.indices),
            smoothing_alpha=payload.time_series.smoothing.alpha,
        )
        ndmi_values = [
            observation.indices["ndmi"].ema or observation.indices["ndmi"].mean
            for observation in series
            if "ndmi" in observation.indices
        ]
        ndmi_dates = [observation.date for observation in series if "ndmi" in observation.indices]
        trigger = detect_water_stress_trigger(
            ndmi_values,
            threshold=payload.trigger.ndmi_ema_threshold,
            min_consecutive=payload.trigger.min_consecutive_periods,
            dates=ndmi_dates,
        )

        return RiskResponse(
            request_id=payload.request_id,
            status=_response_status(series),
            source=SourceMetadata(
                provider=self.provider_name,
                collection=self.collection,
                processing_crs=prepared_aoi.processing_crs.to_string(),
                resolution_m=payload.resolution_m,
            ),
            aoi_metrics=AoiMetrics(
                area_ha=prepared_aoi.area_ha,
                usable_area_ha=prepared_aoi.usable_area_ha,
                masked_area_pct=prepared_aoi.masked_area_pct,
                crop_mask_area_ha=_crop_mask_area_ha(
                    crop_mask_result,
                    resolution_m=payload.resolution_m,
                ),
                crop_mask_coverage_pct=_crop_mask_coverage_pct(
                    crop_mask_result,
                    aoi_mask=job.aoi_mask,
                ),
                crop_mask_geometry_count=(
                    crop_mask_result.geometry_count if crop_mask_result is not None else None
                ),
            ),
            series=series,
            risk_signal=RiskSignal(
                water_stress_score=_water_stress_score(series),
                trigger_candidate=trigger.triggered,
                trigger_reason=trigger.reason,
                confidence=_confidence(series),
                critical_periods=trigger.periods,
            ),
        )


def _crop_mask_area_ha(
    crop_mask: VectorCropMask | None,
    *,
    resolution_m: int,
) -> float | None:
    if crop_mask is None:
        return None
    return crop_mask.crop_pixel_count * resolution_m * resolution_m / 10_000


def _crop_mask_coverage_pct(
    crop_mask: VectorCropMask | None,
    *,
    aoi_mask: Any,
) -> float | None:
    if crop_mask is None:
        return None
    aoi_pixel_count = int(aoi_mask.sum())
    if aoi_pixel_count == 0:
        return 0.0
    return crop_mask.crop_pixel_count / aoi_pixel_count * 100


def _build_observation_series(
    composites: list[CompositeObservation],
    *,
    indices: list[str],
    smoothing_alpha: float,
) -> list[Observation]:
    enrichment = _index_enrichment(composites, indices=indices, smoothing_alpha=smoothing_alpha)
    return [
        Observation(
            date=composite.selected.observed_at,
            period=composite.period,
            valid_pixel_count=composite.selected.stats.valid_pixel_count,
            cloud_pct=composite.selected.stats.cloud_pct,
            quality=cast(Quality, composite.selected.stats.quality),
            quality_flags=composite.selected.stats.quality_flags,
            indices=_index_models(
                composite.selected.stats,
                index_enrichment=enrichment,
                observation_index=idx,
            ),
            mask_counts=MaskCounts(**composite.selected.stats.mask_counts),
        )
        for idx, composite in enumerate(composites)
    ]


def _index_enrichment(
    composites: list[CompositeObservation],
    *,
    indices: list[str],
    smoothing_alpha: float,
) -> dict[str, IndexEnrichment]:
    enrichment: dict[str, IndexEnrichment] = {}
    for index_name in indices:
        positions: list[int] = []
        dates: list[date] = []
        values: list[float] = []
        for position, composite in enumerate(composites):
            stats = composite.selected.stats.index_stats.get(index_name)
            if stats is None:
                continue
            positions.append(position)
            dates.append(composite.selected.observed_at)
            values.append(stats["mean"])

        if not values:
            continue
        smoothed = ema(values, alpha=smoothing_alpha)
        fallback_anomalies = z_scores(values)
        baseline = seasonal_baseline(dates, values, window_days=20, min_samples=3, max_years=5)
        enrichment[index_name] = {
            position: (
                smoothed[idx],
                baseline[idx].z_score if idx in baseline else fallback_anomalies[idx],
                baseline[idx].percentile if idx in baseline else None,
                baseline[idx].baseline_count if idx in baseline else None,
            )
            for idx, position in enumerate(positions)
        }
    return enrichment


def _index_models(
    stats: ObservationStats,
    *,
    index_enrichment: dict[str, IndexEnrichment],
    observation_index: int,
) -> dict[str, IndexStats]:
    models: dict[str, IndexStats] = {}
    for index_name, raw_stats in stats.index_stats.items():
        smoothed, anomaly, baseline_percentile, baseline_count = index_enrichment.get(
            index_name,
            {},
        ).get(
            observation_index,
            (None, None, None, None),
        )
        models[index_name] = IndexStats(
            mean=raw_stats["mean"],
            median=raw_stats["median"],
            p10=raw_stats["p10"],
            p90=raw_stats["p90"],
            std=raw_stats["std"],
            ema=smoothed,
            anomaly_z=anomaly,
            baseline_percentile=baseline_percentile,
            baseline_count=baseline_count,
        )
    return models


def _response_status(series: list[Observation]) -> Literal["completed", "partial", "failed"]:
    if not series:
        return "failed"
    if any(observation.quality == "rejected" for observation in series):
        return "partial"
    return "completed"


def _water_stress_score(series: list[Observation]) -> int:
    ndmi_values = [
        observation.indices["ndmi"].ema
        for observation in series
        if "ndmi" in observation.indices
    ]
    finite = [value for value in ndmi_values if value is not None]
    if not finite:
        return 0
    latest = finite[-1]
    score = round((0.35 - latest) / 0.5 * 100)
    return max(0, min(100, score))


def _confidence(series: list[Observation]) -> float:
    if not series:
        return 0.0
    quality_score = {
        "good": 1.0,
        "moderate": 0.75,
        "poor": 0.35,
        "rejected": 0.0,
    }
    scores = [
        quality_score.get(observation.quality, 0.0)
        * min(1.0, observation.valid_pixel_count / 500)
        for observation in series
    ]
    return sum(scores) / len(scores)
