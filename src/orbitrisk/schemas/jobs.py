from datetime import datetime
from typing import Literal

from pydantic import BaseModel

QuoteJobStatus = Literal["queued", "running", "completed", "failed"]


class QuoteJobSubmitResponse(BaseModel):
    job_id: str
    request_id: str
    status: QuoteJobStatus
    status_url: str
    result_url: str


class QuoteJobStatusResponse(BaseModel):
    job_id: str
    request_id: str
    status: QuoteJobStatus
    created_at: datetime
    updated_at: datetime
    status_url: str
    result_url: str | None = None
    error: str | None = None
