from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Literal
from uuid import uuid4

from orbitrisk.schemas.response import RiskResponse

QuoteJobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class QuoteJobRecord:
    job_id: str
    request_id: str
    status: QuoteJobStatus
    created_at: datetime
    updated_at: datetime
    result: RiskResponse | None = None
    error: str | None = None


class InMemoryQuoteJobStore:
    """Small POC job store; replace with durable storage before production."""

    def __init__(self) -> None:
        self._records: dict[str, QuoteJobRecord] = {}
        self._lock = RLock()

    def create(self, request_id: str) -> QuoteJobRecord:
        now = _now()
        record = QuoteJobRecord(
            job_id=uuid4().hex,
            request_id=request_id,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._records[record.job_id] = record
        return record

    def get(self, job_id: str) -> QuoteJobRecord | None:
        with self._lock:
            return self._records.get(job_id)

    def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running", result=None, error=None)

    def mark_completed(self, job_id: str, result: RiskResponse) -> None:
        self._update(job_id, status="completed", result=result, error=None)

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", result=None, error=error)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def _update(
        self,
        job_id: str,
        *,
        status: QuoteJobStatus,
        result: RiskResponse | None,
        error: str | None,
    ) -> None:
        with self._lock:
            record = self._records[job_id]
            record.status = status
            record.result = result
            record.error = error
            record.updated_at = _now()


def _now() -> datetime:
    return datetime.now(UTC)
