from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Quality = Literal["good", "moderate", "poor", "rejected"]


class SourceMetadata(BaseModel):
    provider: str
    collection: str
    processing_crs: str
    resolution_m: int


class AoiMetrics(BaseModel):
    area_ha: float | None = None
    usable_area_ha: float | None = None
    masked_area_pct: float | None = None


class IndexStats(BaseModel):
    mean: float
    median: float
    p10: float
    p90: float
    std: float | None = None
    ema: float | None = None
    anomaly_z: float | None = None
    baseline_percentile: float | None = Field(default=None, ge=0.0, le=1.0)
    baseline_count: int | None = Field(default=None, ge=0)


class MaskCounts(BaseModel):
    valid: int
    cloud: int = 0
    shadow: int = 0
    snow: int = 0
    outside_aoi: int = 0
    non_crop: int = 0


class Observation(BaseModel):
    date: date
    period: str
    valid_pixel_count: int = Field(ge=0)
    cloud_pct: float = Field(ge=0.0, le=100.0)
    quality: Quality
    quality_flags: list[str] = Field(default_factory=list)
    indices: dict[str, IndexStats]
    mask_counts: MaskCounts


class CriticalPeriod(BaseModel):
    start: date
    end: date
    severity: Literal["low", "medium", "high"]


class RiskSignal(BaseModel):
    water_stress_score: int = Field(ge=0, le=100)
    trigger_candidate: bool
    trigger_reason: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    critical_periods: list[CriticalPeriod] = Field(default_factory=list)


class RiskResponse(BaseModel):
    request_id: str
    status: Literal["completed", "partial", "failed"]
    source: SourceMetadata
    aoi_metrics: AoiMetrics
    series: list[Observation]
    risk_signal: RiskSignal
