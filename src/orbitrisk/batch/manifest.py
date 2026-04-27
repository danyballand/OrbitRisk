import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from orbitrisk.schemas.request import (
    AggregationOptions,
    CropMaskGeoJSON,
    DateRange,
    GeoJSONFeature,
    IndexName,
    MaskingOptions,
    TimeSeriesOptions,
    TriggerOptions,
    default_indices,
)

ManifestVersion = Literal["orbitrisk.aoi_batch.v1"]
SupportedCrop = Literal["vineyard"]


class AoiManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aoi_id: str = Field(min_length=1, max_length=128)
    region: str = Field(min_length=1, max_length=128)
    crop: SupportedCrop = "vineyard"
    crs: str = "EPSG:4326"
    aoi: GeoJSONFeature | None = None
    aoi_geojson_path: Path | None = None
    crop_mask: CropMaskGeoJSON | None = None
    crop_mask_geojson_path: Path | None = None
    crop_mask_crs: str = "EPSG:4326"
    resolution_m: int | None = Field(default=None, ge=10, le=60)
    masking: MaskingOptions | None = None

    @field_validator("crs", "crop_mask_crs")
    @classmethod
    def validate_crs_name(cls, value: str) -> str:
        if not value.upper().startswith("EPSG:"):
            raise ValueError("Only EPSG CRS identifiers are supported")
        return value.upper()

    @model_validator(mode="after")
    def validate_geometry_source(self) -> "AoiManifestEntry":
        if (self.aoi is None) == (self.aoi_geojson_path is None):
            raise ValueError("Provide exactly one of aoi or aoi_geojson_path")
        if self.crop_mask is not None and self.crop_mask_geojson_path is not None:
            raise ValueError("Provide at most one of crop_mask or crop_mask_geojson_path")
        return self


class AoiBatchManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: ManifestVersion = "orbitrisk.aoi_batch.v1"
    name: str = Field(min_length=1, max_length=128)
    date_range: DateRange
    indices: list[IndexName] = Field(default_factory=default_indices)
    aggregation: AggregationOptions = Field(default_factory=AggregationOptions)
    masking: MaskingOptions = Field(default_factory=MaskingOptions)
    time_series: TimeSeriesOptions = Field(default_factory=TimeSeriesOptions)
    trigger: TriggerOptions = Field(default_factory=TriggerOptions)
    resolution_m: int = Field(default=10, ge=10, le=60)
    aois: list[AoiManifestEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_aoi_ids(self) -> "AoiBatchManifest":
        seen: set[str] = set()
        duplicates: list[str] = []
        for aoi in self.aois:
            if aoi.aoi_id in seen:
                duplicates.append(aoi.aoi_id)
            seen.add(aoi.aoi_id)
        if duplicates:
            duplicate_list = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"Duplicate AOI ids in manifest: {duplicate_list}")
        return self


def load_aoi_batch_manifest(path: Path) -> AoiBatchManifest:
    document = _read_json_object(path)
    return AoiBatchManifest.model_validate(document)


def resolve_geojson_document(base_dir: Path, path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else base_dir / path
    return _read_json_object(resolved)


def _read_json_object(path: Path) -> dict[str, Any]:
    document: Any = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return document
