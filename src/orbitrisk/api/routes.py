from datetime import date, timedelta

from fastapi import APIRouter, Query

from orbitrisk.config import get_settings
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.providers.planetary_computer_client import PlanetaryComputerProvider
from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import (
    AoiMetrics,
    IndexStats,
    MaskCounts,
    Observation,
    RiskResponse,
    RiskSignal,
    SourceMetadata,
)
from orbitrisk.timeseries.smoothing import ema
from orbitrisk.timeseries.triggers import detect_water_stress_trigger

router = APIRouter(prefix="/v1")


@router.post("/risk/quote", response_model=RiskResponse)
def quote_risk(payload: RiskRequest) -> RiskResponse:
    """Validate the public contract and return a deterministic dry-run signal.

    The endpoint is intentionally wired through response objects now, so replacing this
    dry run with Sentinel Hub observations does not change the external API.
    """
    sample_dates = _sample_period_dates(payload.date_range.start, payload.date_range.end, limit=6)
    prepared_aoi = prepare_aoi(
        payload.aoi.model_dump(),
        source_crs=payload.crs,
        negative_buffer_m=payload.masking.negative_buffer_m,
    )
    ndmi_values = [0.29, 0.25, 0.21, 0.17, 0.13, 0.11][: len(sample_dates)]
    ndmi_ema = ema(ndmi_values, alpha=payload.time_series.smoothing.alpha)

    observations: list[Observation] = []
    for idx, observed_at in enumerate(sample_dates):
        ndmi_mean = ndmi_values[idx]
        ndvi_mean = min(0.78, ndmi_mean + 0.42)
        period_start = observed_at - timedelta(days=9)
        observations.append(
            Observation(
                date=observed_at,
                period=f"{period_start.isoformat()}/{observed_at.isoformat()}",
                valid_pixel_count=220 + idx * 7,
                cloud_pct=4.0 + idx,
                quality="good" if idx < 4 else "moderate",
                quality_flags=[],
                indices={
                    "ndvi": IndexStats(
                        mean=ndvi_mean,
                        median=ndvi_mean + 0.01,
                        p10=ndvi_mean - 0.08,
                        p90=ndvi_mean + 0.07,
                        std=0.04,
                        ema=ndvi_mean,
                        anomaly_z=-0.4 - idx * 0.1,
                    ),
                    "ndmi": IndexStats(
                        mean=ndmi_mean,
                        median=ndmi_mean + 0.005,
                        p10=ndmi_mean - 0.06,
                        p90=ndmi_mean + 0.05,
                        std=0.03,
                        ema=ndmi_ema[idx],
                        anomaly_z=-0.6 - idx * 0.35,
                    ),
                },
                mask_counts=MaskCounts(
                    valid=220 + idx * 7,
                    cloud=8 + idx,
                    shadow=3,
                    snow=0,
                    outside_aoi=140,
                    non_crop=24,
                ),
            )
        )

    trigger = detect_water_stress_trigger(
        values=[obs.indices["ndmi"].ema or obs.indices["ndmi"].mean for obs in observations],
        threshold=payload.trigger.ndmi_ema_threshold,
        min_consecutive=payload.trigger.min_consecutive_periods,
        dates=[obs.date for obs in observations],
    )

    return RiskResponse(
        request_id=payload.request_id,
        status="completed",
        source=SourceMetadata(
            provider="sentinel-hub",
            collection="sentinel-2-l2a",
            processing_crs=prepared_aoi.processing_crs.to_string(),
            resolution_m=payload.resolution_m,
        ),
        aoi_metrics=AoiMetrics(
            area_ha=prepared_aoi.area_ha,
            usable_area_ha=prepared_aoi.usable_area_ha,
            masked_area_pct=prepared_aoi.masked_area_pct,
        ),
        series=observations,
        risk_signal=RiskSignal(
            water_stress_score=78 if trigger.triggered else 34,
            trigger_candidate=trigger.triggered,
            trigger_reason=trigger.reason,
            confidence=0.72 if trigger.triggered else 0.44,
            critical_periods=trigger.periods,
        ),
    )


@router.post("/risk/quote/live", response_model=RiskResponse)
def quote_risk_live(
    payload: RiskRequest,
    max_items: int = Query(default=25, ge=1, le=500),
) -> RiskResponse:
    settings = get_settings()
    provider = PlanetaryComputerProvider(settings)
    engine = RiskEngine(
        provider,
        provider_name="planetary-computer",
        collection=settings.planetary_computer_collection,
    )
    return engine.quote(payload, max_items=max_items)


def _sample_period_dates(start: date, end: date, limit: int) -> list[date]:
    if start > end:
        return []
    span_days = max((end - start).days, 1)
    step_days = max(span_days // max(limit - 1, 1), 10)
    dates: list[date] = []
    current = start
    while current <= end and len(dates) < limit:
        dates.append(current)
        current += timedelta(days=step_days)
    return dates
