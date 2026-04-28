import hashlib
import json
from typing import Any, Literal

from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import ProvenanceMetadata, RiskResponse, SourceMetadata

ALGORITHM_VERSION = "orbitrisk.ndmi_ema_threshold.v0"
PROCESSING_VERSION = "orbitrisk.sentinel2_l2a_p10d.v0"


def response_provenance(
    payload: RiskRequest,
    *,
    source: SourceMetadata,
    cache_key: str | None = None,
    crop_mask_geojson: dict[str, Any] | None = None,
    crop_mask_crs: str | None = None,
    max_items: int | None = None,
) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        algorithm_version=ALGORITHM_VERSION,
        processing_version=PROCESSING_VERSION,
        provider=source.provider,
        collection=source.collection,
        processing_crs=source.processing_crs,
        resolution_m=source.resolution_m,
        input_hash=input_hash(
            payload,
            crop_mask_geojson=crop_mask_geojson,
            crop_mask_crs=crop_mask_crs,
            max_items=max_items,
        ),
        cache_key=cache_key,
        mask_mode=mask_mode(payload, crop_mask_geojson=crop_mask_geojson),
        crop_mask_hash=crop_mask_hash(payload, crop_mask_geojson=crop_mask_geojson),
    )


def attach_cache_key(response: RiskResponse, cache_key: str) -> RiskResponse:
    return response.model_copy(
        update={
            "provenance": response.provenance.model_copy(update={"cache_key": cache_key}),
        }
    )


def input_hash(
    payload: RiskRequest,
    *,
    crop_mask_geojson: dict[str, Any] | None = None,
    crop_mask_crs: str | None = None,
    max_items: int | None = None,
) -> str:
    return stable_json_hash(
        {
            "payload": payload.model_dump(mode="json"),
            "external_crop_mask": crop_mask_geojson,
            "external_crop_mask_crs": crop_mask_crs if crop_mask_geojson is not None else None,
            "max_items": max_items,
            "version": "risk-input-v1",
        }
    )


def crop_mask_hash(
    payload: RiskRequest,
    *,
    crop_mask_geojson: dict[str, Any] | None = None,
) -> str | None:
    if crop_mask_geojson is not None:
        return stable_json_hash(crop_mask_geojson)
    if payload.crop_mask is not None:
        return stable_json_hash(payload.crop_mask.model_dump(mode="json"))
    return None


def mask_mode(
    payload: RiskRequest,
    *,
    crop_mask_geojson: dict[str, Any] | None = None,
) -> Literal["raw_aoi", "negative_buffer", "vector_crop_mask"]:
    if crop_mask_geojson is not None or payload.crop_mask is not None:
        return "vector_crop_mask"
    if payload.masking.negative_buffer_m > 0:
        return "negative_buffer"
    return "raw_aoi"


def stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
