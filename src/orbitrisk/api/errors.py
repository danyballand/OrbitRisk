from fastapi import HTTPException, status

from orbitrisk.schemas.errors import RiskError, RiskErrorCode, RiskErrorResponse
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import Observation, RiskResponse


def live_quote_exception(exc: Exception, *, request_id: str | None) -> HTTPException:
    message = str(exc) or exc.__class__.__name__
    if isinstance(exc, ValueError):
        if "No Sentinel-2 items found" in message:
            return risk_http_exception(
                "no_scenes",
                message,
                request_id=request_id,
                status_code=status.HTTP_404_NOT_FOUND,
                retryable=False,
            )
        if "AOI" in message or "geometry" in message.lower():
            return risk_http_exception(
                "invalid_geometry",
                message,
                request_id=request_id,
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                retryable=False,
            )

    return risk_http_exception(
        "provider_failure",
        message,
        request_id=request_id,
        status_code=status.HTTP_502_BAD_GATEWAY,
        retryable=True,
    )


def validate_live_quote_response(response: RiskResponse, request: RiskRequest) -> None:
    if not response.series:
        raise risk_http_exception(
            "no_scenes",
            "No usable observations were produced for the requested AOI and date range",
            request_id=request.request_id,
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
        )
    if _all_cloud_blocked(response.series):
        raise risk_http_exception(
            "cloud_only_scenes",
            "All observations are cloud blocked and have no usable index statistics",
            request_id=request.request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            retryable=True,
        )
    if _all_too_few_pixels(response.series, request.masking.min_valid_pixels):
        raise risk_http_exception(
            "insufficient_pixels",
            "All observations are below the configured min_valid_pixels threshold",
            request_id=request.request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            retryable=False,
        )


def risk_http_exception(
    code: RiskErrorCode,
    message: str,
    *,
    request_id: str | None,
    status_code: int,
    retryable: bool,
) -> HTTPException:
    detail = RiskErrorResponse(
        error=RiskError(
            code=code,
            message=message,
            request_id=request_id,
            retryable=retryable,
        )
    ).model_dump(mode="json")
    return HTTPException(status_code=status_code, detail=detail)


def _all_too_few_pixels(observations: list[Observation], min_valid_pixels: int) -> bool:
    return all(
        observation.valid_pixel_count < min_valid_pixels
        or "too_few_valid_pixels" in observation.quality_flags
        for observation in observations
    )


def _all_cloud_blocked(observations: list[Observation]) -> bool:
    return all(
        not observation.indices
        and (
            "high_cloud_fraction" in observation.quality_flags
            or "low_clear_fraction" in observation.quality_flags
            or "no_index_stats" in observation.quality_flags
        )
        for observation in observations
    )
