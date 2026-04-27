from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from orbitrisk.batch.manifest import (
    AoiBatchManifest,
    AoiManifestEntry,
)
from orbitrisk.batch.requests import resolve_aoi_feature, resolve_crop_mask_document
from orbitrisk.engine import prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.masking.vector_mask import crop_mask_from_geojson

AoiValidationStatus = Literal["accepted", "rejected"]


@dataclass(frozen=True)
class AoiValidationResult:
    aoi_id: str
    region: str
    crop: str
    status: AoiValidationStatus
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "aoi_id": self.aoi_id,
            "region": self.region,
            "crop": self.crop,
            "status": self.status,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


def validate_aoi_manifest(
    manifest: AoiBatchManifest,
    *,
    manifest_path: Path,
) -> dict[str, Any]:
    base_dir = manifest_path.parent
    results = [
        validate_aoi_entry(manifest, entry, base_dir=base_dir)
        for entry in manifest.aois
    ]
    accepted = [result for result in results if result.status == "accepted"]
    rejected = [result for result in results if result.status == "rejected"]
    return {
        "manifest": {
            "name": manifest.name,
            "version": manifest.version,
            "aoi_count": len(manifest.aois),
            "date_range": manifest.date_range.model_dump(mode="json"),
            "resolution_m": manifest.resolution_m,
        },
        "summary": {
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "has_external_crop_mask_count": sum(
                1 for result in results if result.metrics.get("has_crop_mask")
            ),
        },
        "aois": [result.to_dict() for result in results],
    }


def validate_aoi_entry(
    manifest: AoiBatchManifest,
    entry: AoiManifestEntry,
    *,
    base_dir: Path,
) -> AoiValidationResult:
    reasons: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    masking = entry.masking or manifest.masking
    resolution_m = entry.resolution_m or manifest.resolution_m

    try:
        aoi_feature = resolve_aoi_feature(entry, base_dir=base_dir)
        crop_mask = resolve_crop_mask_document(entry, base_dir=base_dir)
        prepared_raw = prepare_aoi(
            aoi_feature.model_dump(mode="json"),
            source_crs=entry.crs,
            negative_buffer_m=0,
        )
        negative_buffer_empty = _negative_buffer_is_empty(
            prepared_raw.geometry_projected,
            masking.negative_buffer_m,
        )
        prepared = prepare_aoi(
            aoi_feature.model_dump(mode="json"),
            source_crs=entry.crs,
            negative_buffer_m=masking.negative_buffer_m,
        )
        job = prepare_raster_job(
            prepared,
            date_start=manifest.date_range.start,
            date_end=manifest.date_range.end,
            resolution_m=resolution_m,
            max_cloud_cover_pct=100.0,
            max_items=1,
        )
        aoi_pixels = int(job.aoi_mask.sum())
        crop_mask_metrics = _crop_mask_metrics(
            crop_mask,
            crop_mask_crs=entry.crop_mask_crs,
            prepared=prepared,
            job=job,
            resolution_m=resolution_m,
        )
        metrics.update(
            {
                "area_ha": prepared.area_ha,
                "usable_area_ha": prepared.usable_area_ha,
                "masked_area_pct": prepared.masked_area_pct,
                "processing_crs": prepared.processing_crs.to_string(),
                "resolution_m": resolution_m,
                "grid_height": job.grid.height,
                "grid_width": job.grid.width,
                "aoi_pixel_count": aoi_pixels,
                "min_valid_pixels": masking.min_valid_pixels,
                "negative_buffer_m": masking.negative_buffer_m,
                "negative_buffer_empty": negative_buffer_empty,
                **crop_mask_metrics,
            }
        )
        if negative_buffer_empty:
            reasons.append("empty_negative_buffer")
        if aoi_pixels < masking.min_valid_pixels:
            reasons.append("insufficient_pixels")
        if crop_mask is None:
            warnings.append("missing_crop_mask")
        elif crop_mask_metrics["crop_mask_pixel_count"] == 0:
            reasons.append("empty_crop_mask")
    except (ValueError, ValidationError, OSError) as exc:
        reasons.append(_reason_from_exception(exc))
        metrics["error"] = str(exc)

    return AoiValidationResult(
        aoi_id=entry.aoi_id,
        region=entry.region,
        crop=entry.crop,
        status="rejected" if reasons else "accepted",
        reasons=reasons,
        warnings=warnings,
        metrics=metrics,
    )


def render_aoi_validation_markdown(report: dict[str, Any]) -> str:
    manifest = report["manifest"]
    summary = report["summary"]
    lines = [
        f"# OrbitRisk AOI Batch Validation: {manifest['name']}",
        "",
        f"- Version: `{manifest['version']}`",
        f"- AOIs: `{manifest['aoi_count']}`",
        f"- Accepted: `{summary['accepted_count']}`",
        f"- Rejected: `{summary['rejected_count']}`",
        f"- With crop mask: `{summary['has_external_crop_mask_count']}`",
        "",
        "| AOI | Region | Status | Area ha | Usable ha | Pixels | Crop mask % | "
        "Reasons | Warnings |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for result in report["aois"]:
        metrics = result["metrics"]
        lines.append(
            "| {aoi_id} | {region} | {status} | {area} | {usable} | {pixels} | "
            "{coverage} | {reasons} | {warnings} |".format(
                aoi_id=result["aoi_id"],
                region=result["region"],
                status=result["status"],
                area=_format_optional(metrics.get("area_ha")),
                usable=_format_optional(metrics.get("usable_area_ha")),
                pixels=metrics.get("aoi_pixel_count", ""),
                coverage=_format_optional(metrics.get("crop_mask_coverage_pct")),
                reasons=", ".join(result["reasons"]),
                warnings=", ".join(result["warnings"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _negative_buffer_is_empty(geometry: Any, negative_buffer_m: float) -> bool:
    if negative_buffer_m <= 0:
        return False
    return bool(geometry.buffer(-negative_buffer_m).is_empty)


def _crop_mask_metrics(
    crop_mask: dict[str, Any] | None,
    *,
    crop_mask_crs: str,
    prepared: Any,
    job: Any,
    resolution_m: int,
) -> dict[str, Any]:
    if crop_mask is None:
        return {
            "has_crop_mask": False,
            "crop_mask_pixel_count": None,
            "crop_mask_area_ha": None,
            "crop_mask_coverage_pct": None,
            "crop_mask_geometry_count": None,
        }
    mask = crop_mask_from_geojson(
        crop_mask,
        source_crs=crop_mask_crs,
        grid=job.grid,
        clip_geometry=prepared.analysis_geometry,
    )
    aoi_pixels = max(int(job.aoi_mask.sum()), 1)
    return {
        "has_crop_mask": True,
        "crop_mask_pixel_count": mask.crop_pixel_count,
        "crop_mask_area_ha": mask.crop_pixel_count * resolution_m * resolution_m / 10_000,
        "crop_mask_coverage_pct": mask.crop_pixel_count / aoi_pixels * 100,
        "crop_mask_geometry_count": mask.geometry_count,
    }


def _reason_from_exception(exc: Exception) -> str:
    text = str(exc).lower()
    if "crs" in text or "epsg" in text:
        return "invalid_crs"
    if "geometry" in text or "polygon" in text:
        return "invalid_geometry"
    if "no such file" in text or "not found" in text:
        return "missing_geojson_file"
    return "validation_error"


def _format_optional(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
