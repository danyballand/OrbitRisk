from typing import Literal

from pydantic import BaseModel

RiskErrorCode = Literal[
    "invalid_geometry",
    "no_scenes",
    "cloud_only_scenes",
    "insufficient_pixels",
    "provider_failure",
]


class RiskError(BaseModel):
    code: RiskErrorCode
    message: str
    request_id: str | None = None
    retryable: bool = False


class RiskErrorResponse(BaseModel):
    error: RiskError
