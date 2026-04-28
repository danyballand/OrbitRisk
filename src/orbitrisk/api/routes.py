from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status

from orbitrisk.api.auth import require_api_key
from orbitrisk.api.errors import live_quote_exception, validate_live_quote_response
from orbitrisk.config import get_settings
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.jobs.store import InMemoryQuoteJobStore, QuoteJobRecord
from orbitrisk.provenance import attach_cache_key, response_provenance
from orbitrisk.providers.planetary_computer_client import PlanetaryComputerProvider
from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.jobs import QuoteJobStatusResponse, QuoteJobSubmitResponse
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
from orbitrisk.storage.cache import LocalRiskResponseCache, risk_response_cache_key
from orbitrisk.timeseries.smoothing import ema
from orbitrisk.timeseries.triggers import detect_water_stress_trigger

router = APIRouter(prefix="/v1")
quote_job_store = InMemoryQuoteJobStore()

RISK_REQUEST_OPENAPI_EXAMPLES: dict[str, dict[str, Any]] = {
    "dry_run": {
        "summary": "Dry-run vineyard quote",
        "description": "Minimal contract-validation request without live provider cost.",
        "value": {
            "request_id": "quote_dry_run_001",
            "aoi": {
                "type": "Feature",
                "properties": {"asset_id": "FR_VINEYARD_DEMO"},
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
            "date_range": {"start": "2022-07-01", "end": "2022-08-31"},
        },
    },
    "live_quote": {
        "summary": "Live Sentinel-2 quote",
        "description": "Planetary Computer-backed live quote for a short date range.",
        "value": {
            "request_id": "quote_live_001",
            "aoi": {
                "type": "Feature",
                "properties": {"asset_id": "FR_VINEYARD_LIVE"},
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
            "aggregation": {"temporal": "P10D"},
            "trigger": {"ndmi_ema_threshold": 0.15, "min_consecutive_periods": 2},
        },
    },
    "crop_mask_quote": {
        "summary": "Live quote with crop mask",
        "description": "External RPG-style vector crop mask for basis-risk reduction.",
        "value": {
            "request_id": "quote_crop_mask_001",
            "aoi": {
                "type": "Feature",
                "properties": {"asset_id": "FR_VINEYARD_MASKED"},
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
            "crop_mask": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"source": "RPG_IGN", "crop": "vineyard"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [4.821, 45.731],
                                    [4.829, 45.731],
                                    [4.829, 45.739],
                                    [4.821, 45.739],
                                    [4.821, 45.731],
                                ]
                            ],
                        },
                    }
                ],
            },
            "crop_mask_crs": "EPSG:4326",
            "date_range": {"start": "2022-07-01", "end": "2022-08-31"},
        },
    },
}


@router.post("/risk/quote", response_model=RiskResponse)
def quote_risk(
    payload: Annotated[
        RiskRequest,
        Body(openapi_examples=RISK_REQUEST_OPENAPI_EXAMPLES),
    ],
) -> RiskResponse:
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

    source = SourceMetadata(
        provider="sentinel-hub",
        collection="sentinel-2-l2a",
        processing_crs=prepared_aoi.processing_crs.to_string(),
        resolution_m=payload.resolution_m,
    )
    return RiskResponse(
        request_id=payload.request_id,
        status="completed",
        source=source,
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
        provenance=response_provenance(payload, source=source),
    )


@router.post("/risk/quote/live", response_model=RiskResponse)
def quote_risk_live(
    payload: Annotated[
        RiskRequest,
        Body(openapi_examples=RISK_REQUEST_OPENAPI_EXAMPLES),
    ],
    max_items: int = Query(default=25, ge=1, le=500),
    use_cache: bool = Query(default=True),
    _api_key: str = Depends(require_api_key),
) -> RiskResponse:
    return _quote_live(payload, max_items=max_items, use_cache=use_cache)


@router.post(
    "/risk/quote/jobs",
    response_model=QuoteJobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_quote_job(
    payload: Annotated[
        RiskRequest,
        Body(openapi_examples=RISK_REQUEST_OPENAPI_EXAMPLES),
    ],
    background_tasks: BackgroundTasks,
    max_items: int = Query(default=80, ge=1, le=1000),
    use_cache: bool = Query(default=True),
    _api_key: str = Depends(require_api_key),
) -> QuoteJobSubmitResponse:
    record = quote_job_store.create(payload.request_id)
    background_tasks.add_task(
        _run_quote_job,
        record.job_id,
        payload,
        max_items,
        use_cache,
    )
    return QuoteJobSubmitResponse(
        job_id=record.job_id,
        request_id=record.request_id,
        status=record.status,
        status_url=_job_status_url(record.job_id),
        result_url=_job_result_url(record.job_id),
    )


@router.get("/risk/quote/jobs/{job_id}", response_model=QuoteJobStatusResponse)
def get_quote_job_status(
    job_id: str,
    _api_key: str = Depends(require_api_key),
) -> QuoteJobStatusResponse:
    return _job_status_response(_get_job_or_404(job_id))


@router.get("/risk/quote/jobs/{job_id}/result", response_model=RiskResponse)
def get_quote_job_result(
    job_id: str,
    _api_key: str = Depends(require_api_key),
) -> RiskResponse:
    record = _get_job_or_404(job_id)
    if record.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "job_id": record.job_id,
                "status": record.status,
                "error": record.error,
            },
        )
    if record.status != "completed" or record.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "job_id": record.job_id,
                "status": record.status,
                "error": "job_result_not_ready",
            },
        )
    return record.result


def _quote_live(
    payload: RiskRequest,
    *,
    max_items: int,
    use_cache: bool,
) -> RiskResponse:
    try:
        settings = get_settings()
        provider_name = "planetary-computer"
        provider = PlanetaryComputerProvider(settings)
        engine = RiskEngine(
            provider,
            provider_name=provider_name,
            collection=settings.planetary_computer_collection,
        )
        cache = LocalRiskResponseCache(settings.cache_dir)
        cache_key = risk_response_cache_key(
            payload,
            provider_name=provider_name,
            collection=settings.planetary_computer_collection,
            max_items=max_items,
        )
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return attach_cache_key(cached, cache_key)

        response = engine.quote(payload, max_items=max_items)
        validate_live_quote_response(response, payload)
        response = attach_cache_key(response, cache_key)
        if use_cache:
            cache.set(cache_key, response)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise live_quote_exception(exc, request_id=payload.request_id) from exc


def _run_quote_job(
    job_id: str,
    payload: RiskRequest,
    max_items: int,
    use_cache: bool,
) -> None:
    quote_job_store.mark_running(job_id)
    try:
        response = _quote_live(payload, max_items=max_items, use_cache=use_cache)
    except Exception as exc:
        quote_job_store.mark_failed(job_id, str(exc))
        return
    quote_job_store.mark_completed(job_id, response)


def _get_job_or_404(job_id: str) -> QuoteJobRecord:
    record = quote_job_store.get(job_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"job_id": job_id, "error": "job_not_found"},
        )
    return record


def _job_status_response(record: QuoteJobRecord) -> QuoteJobStatusResponse:
    return QuoteJobStatusResponse(
        job_id=record.job_id,
        request_id=record.request_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        status_url=_job_status_url(record.job_id),
        result_url=_job_result_url(record.job_id) if record.status == "completed" else None,
        error=record.error,
    )


def _job_status_url(job_id: str) -> str:
    return f"/v1/risk/quote/jobs/{job_id}"


def _job_result_url(job_id: str) -> str:
    return f"/v1/risk/quote/jobs/{job_id}/result"


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
