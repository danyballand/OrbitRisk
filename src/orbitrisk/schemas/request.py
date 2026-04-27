from datetime import date
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IndexName = Literal["ndvi", "ndwi", "ndmi", "ndre"]
SpatialStat = Literal["mean", "median", "p10", "p90", "std"]


def default_indices() -> list[IndexName]:
    return ["ndvi", "ndmi", "ndwi"]


def default_spatial_stats() -> list[SpatialStat]:
    return ["mean", "median", "p10", "p90", "std"]


class GeoJSONPolygonalGeometry(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: list[Any]) -> list[Any]:
        if not value:
            raise ValueError("GeoJSON geometry coordinates are required")
        return value


class GeoJSONFeature(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["Feature"]
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: GeoJSONPolygonalGeometry


class GeoJSONFeatureCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["FeatureCollection"]
    features: list[GeoJSONFeature] = Field(min_length=1)


CropMaskGeoJSON: TypeAlias = (
    GeoJSONFeature | GeoJSONFeatureCollection | GeoJSONPolygonalGeometry
)


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> "DateRange":
        if self.start > self.end:
            raise ValueError("date_range.start must be before or equal to date_range.end")
        return self


class AggregationOptions(BaseModel):
    temporal: str = Field(default="P10D", pattern=r"^P(\d+D|1M)$")
    spatial_stats: list[SpatialStat] = Field(default_factory=default_spatial_stats)


class MaskingOptions(BaseModel):
    cloud_mask: bool = True
    shadow_mask: bool = True
    snow_mask: bool = True
    negative_buffer_m: float = Field(default=10.0, ge=0.0, le=100.0)
    min_valid_pixels: int = Field(default=20, ge=1)
    exclude_scl_classes: list[int] = Field(default_factory=lambda: [0, 1, 3, 7, 8, 9, 10, 11])
    min_clear_fraction: float = Field(default=0.7, ge=0.0, le=1.0)


class SmoothingOptions(BaseModel):
    method: Literal["ema"] = "ema"
    alpha: float = Field(default=0.35, gt=0.0, le=1.0)


class BaselineOptions(BaseModel):
    method: Literal["day_of_year_percentile"] = "day_of_year_percentile"
    years: int = Field(default=5, ge=1, le=10)


class TimeSeriesOptions(BaseModel):
    smoothing: SmoothingOptions = Field(default_factory=SmoothingOptions)
    baseline: BaselineOptions = Field(default_factory=BaselineOptions)


class TriggerOptions(BaseModel):
    ndmi_ema_threshold: float = Field(default=0.15, ge=-1.0, le=1.0)
    min_consecutive_periods: int = Field(default=2, ge=1, le=8)


class RiskRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    aoi: GeoJSONFeature
    crop_mask: CropMaskGeoJSON | None = None
    crs: str = "EPSG:4326"
    crop_mask_crs: str = "EPSG:4326"
    date_range: DateRange
    indices: list[IndexName] = Field(default_factory=default_indices)
    aggregation: AggregationOptions = Field(default_factory=AggregationOptions)
    masking: MaskingOptions = Field(default_factory=MaskingOptions)
    time_series: TimeSeriesOptions = Field(default_factory=TimeSeriesOptions)
    trigger: TriggerOptions = Field(default_factory=TriggerOptions)
    resolution_m: int = Field(default=10, ge=10, le=60)

    @field_validator("crs", "crop_mask_crs")
    @classmethod
    def validate_crs_name(cls, value: str) -> str:
        if not value.upper().startswith("EPSG:"):
            raise ValueError("Only EPSG CRS identifiers are supported in the public API")
        return value.upper()
