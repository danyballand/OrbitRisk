from datetime import date
from pathlib import Path
from typing import Any

from orbitrisk.batch.manifest import (
    AoiBatchManifest,
    AoiManifestEntry,
    resolve_geojson_document,
)
from orbitrisk.schemas.request import GeoJSONFeature


def risk_request_payload_from_manifest_entry(
    manifest: AoiBatchManifest,
    entry: AoiManifestEntry,
    *,
    base_dir: Path,
    date_start: date | None = None,
    date_end: date | None = None,
    negative_buffer_m: float | None = None,
    include_crop_mask: bool = True,
) -> dict[str, Any]:
    masking = (entry.masking or manifest.masking).model_dump(mode="json")
    if negative_buffer_m is not None:
        masking["negative_buffer_m"] = negative_buffer_m

    payload: dict[str, Any] = {
        "request_id": entry.aoi_id,
        "aoi": resolve_aoi_feature(entry, base_dir=base_dir).model_dump(mode="json"),
        "crs": entry.crs,
        "crop_mask_crs": entry.crop_mask_crs,
        "date_range": {
            "start": (date_start or manifest.date_range.start).isoformat(),
            "end": (date_end or manifest.date_range.end).isoformat(),
        },
        "indices": list(manifest.indices),
        "aggregation": manifest.aggregation.model_dump(mode="json"),
        "masking": masking,
        "time_series": manifest.time_series.model_dump(mode="json"),
        "trigger": manifest.trigger.model_dump(mode="json"),
        "resolution_m": entry.resolution_m or manifest.resolution_m,
    }
    crop_mask = resolve_crop_mask_document(entry, base_dir=base_dir)
    if include_crop_mask and crop_mask is not None:
        payload["crop_mask"] = crop_mask
    return payload


def resolve_aoi_feature(entry: AoiManifestEntry, *, base_dir: Path) -> GeoJSONFeature:
    if entry.aoi is not None:
        return entry.aoi
    if entry.aoi_geojson_path is None:
        raise ValueError("AOI geometry source is missing")
    return GeoJSONFeature.model_validate(
        resolve_geojson_document(base_dir, entry.aoi_geojson_path)
    )


def resolve_crop_mask_document(
    entry: AoiManifestEntry,
    *,
    base_dir: Path,
) -> dict[str, Any] | None:
    if entry.crop_mask is not None:
        return entry.crop_mask.model_dump(mode="json")
    if entry.crop_mask_geojson_path is None:
        return None
    return resolve_geojson_document(base_dir, entry.crop_mask_geojson_path)
