import argparse
import copy
import json
import statistics
from datetime import date
from pathlib import Path
from typing import Any

from orbitrisk.batch.basis_risk import BasisRiskInputs, classify_basis_risk
from orbitrisk.batch.manifest import AoiBatchManifest, load_aoi_batch_manifest
from orbitrisk.batch.quality import render_aoi_validation_markdown, validate_aoi_manifest
from orbitrisk.batch.requests import (
    resolve_crop_mask_document,
    risk_request_payload_from_manifest_entry,
)
from orbitrisk.config import get_settings
from orbitrisk.engine import prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.processing.datacube import summarize_datacube
from orbitrisk.providers.planetary_computer_client import PlanetaryComputerProvider
from orbitrisk.reporting.charts import (
    write_mask_benchmark_batch_charts,
    write_mask_benchmark_charts,
)
from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import RiskResponse
from orbitrisk.storage.cache import LocalRiskResponseCache, risk_response_cache_key
from orbitrisk.timeseries.compositing import composite_observations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orbitrisk")
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke = subparsers.add_parser("smoke-pc", help="Run a Planetary Computer smoke test")
    smoke.add_argument("request_json", type=Path)
    smoke.add_argument("--start", type=date.fromisoformat)
    smoke.add_argument("--end", type=date.fromisoformat)
    smoke.add_argument("--resolution-m", type=int, default=10)
    smoke.add_argument("--max-items", type=int, default=2)
    smoke.add_argument("--max-cloud-cover-pct", type=float, default=80.0)
    smoke.add_argument("--temporal", default=None, help="Aggregation period, e.g. P10D or P1M")
    validate_batch = subparsers.add_parser(
        "validate-aoi-batch",
        help="Validate an AOI batch manifest without loading Sentinel scenes",
    )
    validate_batch.add_argument("manifest_json", type=Path)
    validate_batch.add_argument("--output-json", type=Path, default=None)
    validate_batch.add_argument("--output-md", type=Path, default=None)
    validate = subparsers.add_parser("validate-2022", help="Run a drought-2022 validation")
    validate.add_argument("request_json", type=Path)
    validate.add_argument("--region", default="unknown")
    validate.add_argument("--baseline-start", type=date.fromisoformat, default=date(2019, 6, 1))
    validate.add_argument("--end", type=date.fromisoformat, default=date(2022, 8, 31))
    validate.add_argument("--max-items", type=int, default=80)
    validate.add_argument("--cache", action=argparse.BooleanOptionalAction, default=True)
    validate.add_argument("--cache-dir", type=Path, default=None)
    validate.add_argument("--output-json", type=Path, default=None)
    validate.add_argument("--output-md", type=Path, default=None)
    validate.add_argument("--crop-mask-geojson", type=Path, default=None)
    validate.add_argument("--crop-mask-crs", default="EPSG:4326")
    benchmark = subparsers.add_parser(
        "benchmark-masks-2022",
        help="Compare raw AOI, buffered AOI, and vector crop-mask drought signals",
    )
    benchmark.add_argument("request_json", type=Path)
    benchmark.add_argument("--region", default="unknown")
    benchmark.add_argument("--baseline-start", type=date.fromisoformat, default=date(2019, 6, 1))
    benchmark.add_argument("--end", type=date.fromisoformat, default=date(2022, 8, 31))
    benchmark.add_argument("--max-items", type=int, default=80)
    benchmark.add_argument("--buffer-m", type=float, default=None)
    benchmark.add_argument("--cache", action=argparse.BooleanOptionalAction, default=True)
    benchmark.add_argument("--cache-dir", type=Path, default=None)
    benchmark.add_argument("--output-json", type=Path, default=None)
    benchmark.add_argument("--output-md", type=Path, default=None)
    benchmark.add_argument("--charts-dir", type=Path, default=None)
    benchmark.add_argument("--crop-mask-geojson", type=Path, default=None)
    benchmark.add_argument("--crop-mask-crs", default="EPSG:4326")
    benchmark_batch = subparsers.add_parser(
        "benchmark-masks-batch-2022",
        help="Run mask benchmarks for every accepted AOI in a batch manifest",
    )
    benchmark_batch.add_argument("manifest_json", type=Path)
    benchmark_batch.add_argument(
        "--baseline-start",
        type=date.fromisoformat,
        default=date(2019, 6, 1),
    )
    benchmark_batch.add_argument("--end", type=date.fromisoformat, default=date(2022, 8, 31))
    benchmark_batch.add_argument("--max-items", type=int, default=80)
    benchmark_batch.add_argument("--buffer-m", type=float, default=None)
    benchmark_batch.add_argument("--cache", action=argparse.BooleanOptionalAction, default=True)
    benchmark_batch.add_argument("--cache-dir", type=Path, default=None)
    benchmark_batch.add_argument("--output-json", type=Path, default=None)
    benchmark_batch.add_argument("--output-md", type=Path, default=None)
    benchmark_batch.add_argument("--charts-dir", type=Path, default=None)
    benchmark_batch.add_argument(
        "--include-without-crop-mask",
        action="store_true",
        help="Run partial raw/buffer benchmarks for AOIs missing crop masks",
    )

    args = parser.parse_args(argv)
    if args.command == "smoke-pc":
        result = run_planetary_computer_smoke(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "validate-aoi-batch":
        result = run_aoi_batch_validation(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "validate-2022":
        result = run_2022_validation(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "benchmark-masks-2022":
        result = run_mask_benchmark_2022(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "benchmark-masks-batch-2022":
        result = run_mask_benchmark_batch_2022(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    return 1


def run_aoi_batch_validation(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_aoi_batch_manifest(args.manifest_json)
    report = validate_aoi_manifest(manifest, manifest_path=args.manifest_json)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True))
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_aoi_validation_markdown(report))
    return report


def run_planetary_computer_smoke(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.loads(args.request_json.read_text())
    date_range = payload["date_range"]
    date_start = args.start or date.fromisoformat(date_range["start"])
    date_end = args.end or date.fromisoformat(date_range["end"])
    prepared_aoi = prepare_aoi(
        payload["aoi"],
        source_crs=payload.get("crs", "EPSG:4326"),
        negative_buffer_m=payload.get("masking", {}).get("negative_buffer_m", 10.0),
    )
    job = prepare_raster_job(
        prepared_aoi,
        date_start=date_start,
        date_end=date_end,
        resolution_m=args.resolution_m,
        max_cloud_cover_pct=args.max_cloud_cover_pct,
        max_items=args.max_items,
    )

    provider = PlanetaryComputerProvider(get_settings())
    dataset = provider.load_datacube(job.query, geobox=job.grid.to_odc_geobox())
    observations = summarize_datacube(
        dataset,
        aoi_mask=job.aoi_mask,
        requested_indices=payload.get("indices", ["ndvi", "ndmi", "ndwi"]),
        min_valid_pixels=payload.get("masking", {}).get("min_valid_pixels", 20),
        min_clear_fraction=payload.get("masking", {}).get("min_clear_fraction", 0.7),
        exclude_scl_classes=set(payload.get("masking", {}).get("exclude_scl_classes", [])) or None,
    )
    temporal = args.temporal or payload.get("aggregation", {}).get("temporal", "P10D")
    composites = composite_observations(
        observations,
        temporal=temporal,
        start=date_start,
        end=date_end,
    )

    return {
        "request_id": payload["request_id"],
        "provider": "planetary-computer",
        "processing_crs": prepared_aoi.processing_crs.to_string(),
        "temporal": temporal,
        "grid": {
            "height": job.grid.height,
            "width": job.grid.width,
            "resolution_m": job.grid.resolution_m,
            "aoi_pixels": int(job.aoi_mask.sum()),
        },
        "observations": [
            {
                "date": observation.observed_at.isoformat(),
                "quality": observation.stats.quality,
                "quality_flags": observation.stats.quality_flags,
                "valid_pixel_count": observation.stats.valid_pixel_count,
                "cloud_pct": observation.stats.cloud_pct,
                "indices": observation.stats.index_stats,
                "mask_counts": observation.stats.mask_counts,
            }
            for observation in observations
        ],
        "composites": [
            {
                "period": composite.period,
                "selected_date": composite.selected.observed_at.isoformat(),
                "candidate_count": composite.candidate_count,
                "accepted_candidate_count": composite.accepted_candidate_count,
                "rejected_candidate_count": composite.rejected_candidate_count,
                "quality": composite.selected.stats.quality,
                "quality_flags": composite.selected.stats.quality_flags,
                "valid_pixel_count": composite.selected.stats.valid_pixel_count,
                "cloud_pct": composite.selected.stats.cloud_pct,
                "indices": composite.selected.stats.index_stats,
                "mask_counts": composite.selected.stats.mask_counts,
            }
            for composite in composites
        ],
    }


def run_2022_validation(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.loads(args.request_json.read_text())
    request = RiskRequest.model_validate(
        _validation_payload(payload, baseline_start=args.baseline_start, end=args.end)
    )
    crop_mask_geojson = (
        _read_crop_mask_document(args.crop_mask_geojson)
        if args.crop_mask_geojson is not None
        else None
    )
    settings = get_settings()
    provider_name = "planetary-computer"
    collection = settings.planetary_computer_collection
    engine = RiskEngine(
        PlanetaryComputerProvider(settings),
        provider_name=provider_name,
        collection=collection,
    )
    response = _quote_with_cache(
        engine,
        request,
        provider_name=provider_name,
        collection=collection,
        max_items=args.max_items,
        enabled=args.cache,
        cache_dir=args.cache_dir or settings.cache_dir,
        crop_mask_geojson=crop_mask_geojson,
        crop_mask_crs=args.crop_mask_crs,
    )
    summary = summarize_2022_validation(response, region=args.region)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_validation_markdown(summary))
    return summary


def run_mask_benchmark_2022(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.loads(args.request_json.read_text())
    crop_mask_geojson = _benchmark_crop_mask(payload, args.crop_mask_geojson)
    crop_mask_crs = str(
        args.crop_mask_crs
        if args.crop_mask_geojson is not None
        else payload.get("crop_mask_crs", args.crop_mask_crs)
    )
    settings = get_settings()
    provider_name = "planetary-computer"
    collection = settings.planetary_computer_collection
    engine = RiskEngine(
        PlanetaryComputerProvider(settings),
        provider_name=provider_name,
        collection=collection,
    )
    summary = _run_mask_benchmark_payload(
        payload,
        region=args.region,
        baseline_start=args.baseline_start,
        end=args.end,
        max_items=args.max_items,
        buffer_m=args.buffer_m,
        cache_enabled=args.cache,
        cache_dir=args.cache_dir or settings.cache_dir,
        crop_mask_geojson=crop_mask_geojson,
        crop_mask_crs=crop_mask_crs,
        engine=engine,
        provider_name=provider_name,
        collection=collection,
    )
    if args.charts_dir is not None:
        _attach_chart_artifacts(
            summary,
            write_mask_benchmark_charts(
                summary,
                args.charts_dir,
                aoi_id=str(payload.get("request_id") or args.region),
            ),
        )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_mask_benchmark_markdown(summary))
    return summary


def run_mask_benchmark_batch_2022(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_aoi_batch_manifest(args.manifest_json)
    settings = get_settings()
    provider_name = "planetary-computer"
    collection = settings.planetary_computer_collection
    engine = RiskEngine(
        PlanetaryComputerProvider(settings),
        provider_name=provider_name,
        collection=collection,
    )
    summary = _run_mask_benchmark_batch(
        manifest,
        manifest_path=args.manifest_json,
        baseline_start=args.baseline_start,
        end=args.end,
        max_items=args.max_items,
        buffer_m=args.buffer_m,
        cache_enabled=args.cache,
        cache_dir=args.cache_dir or settings.cache_dir,
        include_without_crop_mask=args.include_without_crop_mask,
        engine=engine,
        provider_name=provider_name,
        collection=collection,
    )
    if args.charts_dir is not None:
        _attach_chart_artifacts(
            summary,
            write_mask_benchmark_batch_charts(summary, args.charts_dir),
        )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_mask_benchmark_batch_markdown(summary))
    return summary


def _run_mask_benchmark_payload(
    payload: dict[str, Any],
    *,
    region: str,
    baseline_start: date,
    end: date,
    max_items: int,
    buffer_m: float | None,
    cache_enabled: bool,
    cache_dir: Path,
    crop_mask_geojson: dict[str, Any] | None,
    crop_mask_crs: str,
    engine: RiskEngine,
    provider_name: str,
    collection: str,
) -> dict[str, Any]:
    base_masking = payload.get("masking", {})
    buffered_m = (
        buffer_m
        if buffer_m is not None
        else base_masking.get("negative_buffer_m", 10.0)
    )

    variants: list[tuple[str, str, RiskResponse | None]] = []
    for variant, label, negative_buffer_m, crop_mask in [
        ("raw_aoi", "Raw AOI mean", 0.0, None),
        ("buffered_aoi", f"AOI mean with {buffered_m:g} m negative buffer", buffered_m, None),
        ("vector_crop_mask", "External crop mask + buffer", buffered_m, crop_mask_geojson),
    ]:
        if variant == "vector_crop_mask" and crop_mask is None:
            variants.append((variant, label, None))
            continue
        request = RiskRequest.model_validate(
            _validation_payload(
                payload,
                baseline_start=baseline_start,
                end=end,
                negative_buffer_m=negative_buffer_m,
                include_crop_mask=False,
            )
        )
        response = _quote_with_cache(
            engine,
            request,
            provider_name=provider_name,
            collection=collection,
            max_items=max_items,
            enabled=cache_enabled,
            cache_dir=cache_dir,
            crop_mask_geojson=crop_mask,
            crop_mask_crs=crop_mask_crs,
        )
        variants.append((variant, label, response))

    return summarize_mask_benchmark(variants, region=region)


def _run_mask_benchmark_batch(
    manifest: AoiBatchManifest,
    *,
    manifest_path: Path,
    baseline_start: date,
    end: date,
    max_items: int,
    buffer_m: float | None,
    cache_enabled: bool,
    cache_dir: Path,
    include_without_crop_mask: bool,
    engine: RiskEngine,
    provider_name: str,
    collection: str,
) -> dict[str, Any]:
    base_dir = manifest_path.parent
    quality_report = validate_aoi_manifest(manifest, manifest_path=manifest_path)
    quality_by_aoi_id = {result["aoi_id"]: result for result in quality_report["aois"]}
    aoi_results: list[dict[str, Any]] = []

    for entry in manifest.aois:
        quality = quality_by_aoi_id[entry.aoi_id]
        if quality["status"] == "rejected":
            aoi_results.append(
                {
                    "aoi_id": entry.aoi_id,
                    "region": entry.region,
                    "status": "rejected",
                    "reasons": quality["reasons"],
                    "quality_gate": quality,
                }
            )
            continue

        try:
            crop_mask = resolve_crop_mask_document(entry, base_dir=base_dir)
            if crop_mask is None and not include_without_crop_mask:
                aoi_results.append(
                    {
                        "aoi_id": entry.aoi_id,
                        "region": entry.region,
                        "status": "skipped",
                        "reasons": ["missing_crop_mask"],
                        "quality_gate": quality,
                    }
                )
                continue

            payload = risk_request_payload_from_manifest_entry(
                manifest,
                entry,
                base_dir=base_dir,
                date_start=baseline_start,
                date_end=end,
                include_crop_mask=False,
            )
            benchmark = _run_mask_benchmark_payload(
                payload,
                region=entry.region,
                baseline_start=baseline_start,
                end=end,
                max_items=max_items,
                buffer_m=buffer_m,
                cache_enabled=cache_enabled,
                cache_dir=cache_dir,
                crop_mask_geojson=crop_mask,
                crop_mask_crs=entry.crop_mask_crs,
                engine=engine,
                provider_name=provider_name,
                collection=collection,
            )
            aoi_results.append(
                {
                    "aoi_id": entry.aoi_id,
                    "region": entry.region,
                    "status": "success",
                    "quality_gate": quality,
                    "benchmark": benchmark,
                }
            )
        except Exception as exc:
            aoi_results.append(
                {
                    "aoi_id": entry.aoi_id,
                    "region": entry.region,
                    "status": "failed",
                    "reasons": ["benchmark_failed"],
                    "error": str(exc),
                    "quality_gate": quality,
                }
            )

    return summarize_mask_benchmark_batch(
        manifest,
        aoi_results,
        baseline_start=baseline_start,
        end=end,
        buffer_m=buffer_m,
        max_items=max_items,
        cache_enabled=cache_enabled,
        provider_name=provider_name,
        collection=collection,
    )


def _validation_payload(
    payload: dict[str, Any],
    *,
    baseline_start: date,
    end: date,
    negative_buffer_m: float | None = None,
    include_crop_mask: bool = True,
) -> dict[str, Any]:
    prepared = copy.deepcopy(payload)
    prepared["date_range"] = {
        "start": baseline_start.isoformat(),
        "end": end.isoformat(),
    }
    prepared["aggregation"] = {
        "temporal": prepared.get("aggregation", {}).get("temporal", "P10D"),
        "spatial_stats": prepared.get("aggregation", {}).get(
            "spatial_stats",
            ["mean", "median", "p10", "p90", "std"],
        ),
    }
    if negative_buffer_m is not None:
        masking = dict(prepared.get("masking", {}))
        masking["negative_buffer_m"] = negative_buffer_m
        prepared["masking"] = masking
    if not include_crop_mask:
        prepared.pop("crop_mask", None)
        prepared.pop("crop_mask_crs", None)
    return prepared


def _benchmark_crop_mask(
    payload: dict[str, Any],
    crop_mask_path: Path | None,
) -> dict[str, Any] | None:
    if crop_mask_path is not None:
        return _read_crop_mask_document(crop_mask_path)
    embedded_crop_mask = payload.get("crop_mask")
    if isinstance(embedded_crop_mask, dict):
        return embedded_crop_mask
    return None


def _read_crop_mask_document(crop_mask_path: Path) -> dict[str, Any]:
    document: Any = json.loads(crop_mask_path.read_text())
    if not isinstance(document, dict):
        raise ValueError("Crop mask GeoJSON root must be an object")
    return document


def _quote_with_cache(
    engine: RiskEngine,
    request: RiskRequest,
    *,
    provider_name: str,
    collection: str,
    max_items: int,
    enabled: bool,
    cache_dir: Path,
    crop_mask_geojson: dict[str, Any] | None = None,
    crop_mask_crs: str = "EPSG:4326",
) -> RiskResponse:
    if not enabled:
        return engine.quote(
            request,
            max_items=max_items,
            crop_mask_geojson=crop_mask_geojson,
            crop_mask_crs=crop_mask_crs,
        )
    cache = LocalRiskResponseCache(cache_dir)
    cache_key = risk_response_cache_key(
        request,
        provider_name=provider_name,
        collection=collection,
        max_items=max_items,
        extra={
            "crop_mask": crop_mask_geojson,
            "crop_mask_crs": crop_mask_crs if crop_mask_geojson is not None else None,
        },
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    response = engine.quote(
        request,
        max_items=max_items,
        crop_mask_geojson=crop_mask_geojson,
        crop_mask_crs=crop_mask_crs,
    )
    cache.set(cache_key, response)
    return response


def summarize_2022_validation(response: RiskResponse, *, region: str) -> dict[str, Any]:
    target_series = [
        observation
        for observation in response.series
        if observation.date.year == 2022 and observation.date.month in {7, 8}
    ]
    ndmi_periods = [
        {
            "period": observation.period,
            "date": observation.date.isoformat(),
            "quality": observation.quality,
            "quality_flags": observation.quality_flags,
            "valid_pixel_count": observation.valid_pixel_count,
            "cloud_pct": observation.cloud_pct,
            "ndmi_mean": observation.indices["ndmi"].mean,
            "ndmi_ema": observation.indices["ndmi"].ema,
            "ndmi_anomaly_z": observation.indices["ndmi"].anomaly_z,
            "ndmi_baseline_percentile": observation.indices["ndmi"].baseline_percentile,
            "ndmi_baseline_count": observation.indices["ndmi"].baseline_count,
        }
        for observation in target_series
        if "ndmi" in observation.indices
    ]
    baseline_supported = [
        period for period in ndmi_periods if period["ndmi_baseline_count"] is not None
    ]
    detected = response.risk_signal.trigger_candidate and bool(baseline_supported)
    return {
        "request_id": response.request_id,
        "region": region,
        "status": response.status,
        "detected": detected,
        "detection_reason": response.risk_signal.trigger_reason,
        "confidence": response.risk_signal.confidence,
        "target_period_count": len(target_series),
        "baseline_supported_period_count": len(baseline_supported),
        "critical_periods": [
            period.model_dump(mode="json") for period in response.risk_signal.critical_periods
        ],
        "ndmi_periods": ndmi_periods,
    }


def summarize_mask_benchmark(
    variants: list[tuple[str, str, RiskResponse | None]],
    *,
    region: str,
) -> dict[str, Any]:
    variant_summaries = [
        _summarize_benchmark_variant(variant, label, response, region=region)
        for variant, label, response in variants
    ]
    completed = [
        summary for summary in variant_summaries if summary["status"] != "skipped"
    ]
    raw = next(
        (summary for summary in completed if summary["variant"] == "raw_aoi"),
        completed[0] if completed else None,
    )
    comparisons = [
        _compare_benchmark_variants(raw, summary)
        for summary in completed
        if raw is not None and summary["variant"] != raw["variant"]
    ]
    return {
        "region": region,
        "variant_count": len(variant_summaries),
        "completed_variant_count": len(completed),
        "variants": variant_summaries,
        "comparisons": comparisons,
    }


def summarize_mask_benchmark_batch(
    manifest: AoiBatchManifest,
    aoi_results: list[dict[str, Any]],
    *,
    baseline_start: date,
    end: date,
    buffer_m: float | None,
    max_items: int,
    cache_enabled: bool,
    provider_name: str,
    collection: str,
) -> dict[str, Any]:
    enriched_results = [_enrich_batch_aoi_result(result) for result in aoi_results]
    return {
        "manifest": {
            "name": manifest.name,
            "version": manifest.version,
            "aoi_count": len(manifest.aois),
            "date_range": manifest.date_range.model_dump(mode="json"),
            "resolution_m": manifest.resolution_m,
        },
        "run": {
            "baseline_start": baseline_start.isoformat(),
            "end": end.isoformat(),
            "buffer_m": buffer_m,
            "max_items": max_items,
            "cache_enabled": cache_enabled,
            "provider": provider_name,
            "collection": collection,
        },
        "summary": {
            "success_count": _count_aoi_status(enriched_results, "success"),
            "skipped_count": _count_aoi_status(enriched_results, "skipped"),
            "rejected_count": _count_aoi_status(enriched_results, "rejected"),
            "failed_count": _count_aoi_status(enriched_results, "failed"),
            "aoi_count": len(enriched_results),
        },
        "aggregate": _batch_aggregate_metrics(enriched_results),
        "aois": enriched_results,
    }


def _count_aoi_status(aoi_results: list[dict[str, Any]], status: str) -> int:
    return sum(1 for result in aoi_results if result["status"] == status)


def _enrich_batch_aoi_result(result: dict[str, Any]) -> dict[str, Any]:
    if result["status"] != "success":
        return {
            **result,
            "basis_risk_assessment": {
                "classification": "not_run",
                "reasons": result.get("reasons", []),
            },
        }

    benchmark = result["benchmark"]
    raw = _benchmark_variant(benchmark, "raw_aoi")
    buffered = _benchmark_variant(benchmark, "buffered_aoi")
    vector = _benchmark_variant(benchmark, "vector_crop_mask")
    vector_comparison = _benchmark_comparison(benchmark, "vector_crop_mask")
    buffered_comparison = _benchmark_comparison(benchmark, "buffered_aoi")
    min_valid_pixels = _optional_int(
        _nested_get(result, "quality_gate", "metrics", "min_valid_pixels")
    )
    return {
        **result,
        "key_metrics": {
            "raw_median_valid_pixel_count": _nested_get(
                raw,
                "aggregate_metrics",
                "median_valid_pixel_count",
            ),
            "buffered_median_valid_pixel_count": _nested_get(
                buffered,
                "aggregate_metrics",
                "median_valid_pixel_count",
            ),
            "crop_mask_median_valid_pixel_count": _nested_get(
                vector,
                "aggregate_metrics",
                "median_valid_pixel_count",
            ),
            "crop_mask_coverage_pct": _nested_get(
                vector,
                "aoi_metrics",
                "crop_mask_coverage_pct",
            ),
            "crop_mask_non_crop_pixel_delta": vector_comparison.get("non_crop_pixel_delta"),
            "crop_mask_valid_pixel_delta_pct": vector_comparison.get(
                "median_valid_pixel_delta_pct"
            ),
            "crop_mask_min_ndmi_ema_delta": vector_comparison.get("min_ndmi_ema_delta"),
            "buffered_valid_pixel_delta_pct": buffered_comparison.get(
                "median_valid_pixel_delta_pct"
            ),
        },
        "basis_risk_assessment": _basis_risk_assessment(
            vector,
            vector_comparison,
            min_valid_pixels=min_valid_pixels,
        ),
    }


def _basis_risk_assessment(
    vector_variant: dict[str, Any],
    vector_comparison: dict[str, Any],
    *,
    min_valid_pixels: int | None,
) -> dict[str, Any]:
    return classify_basis_risk(
        BasisRiskInputs(
            vector_status=vector_variant.get("status") if vector_variant else None,
            crop_mask_coverage_pct=_optional_float(
                _nested_get(vector_variant, "aoi_metrics", "crop_mask_coverage_pct")
            ),
            crop_mask_median_valid_pixel_count=_optional_int(
                _nested_get(
                    vector_variant,
                    "aggregate_metrics",
                    "median_valid_pixel_count",
                )
            ),
            min_valid_pixels=min_valid_pixels,
            non_crop_pixel_delta=_optional_int(vector_comparison.get("non_crop_pixel_delta")),
            valid_pixel_delta_pct=_optional_float(
                vector_comparison.get("median_valid_pixel_delta_pct")
            ),
            min_ndmi_ema_delta=_optional_float(vector_comparison.get("min_ndmi_ema_delta")),
        )
    )


def _batch_aggregate_metrics(aoi_results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [result for result in aoi_results if result["status"] == "success"]
    return {
        "basis_risk_classification_counts": {
            "improved": _count_assessment(successful, "improved"),
            "degraded": _count_assessment(successful, "degraded"),
            "ambiguous": _count_assessment(successful, "ambiguous"),
            "not_run": len(aoi_results) - len(successful),
        },
        "variant_rollups": {
            variant_name: _variant_rollup(successful, variant_name)
            for variant_name in ["raw_aoi", "buffered_aoi", "vector_crop_mask"]
        },
        "comparison_rollups": {
            "buffered_aoi_vs_raw_aoi": _comparison_rollup(successful, "buffered_aoi"),
            "vector_crop_mask_vs_raw_aoi": _comparison_rollup(
                successful,
                "vector_crop_mask",
            ),
        },
    }


def _count_assessment(aoi_results: list[dict[str, Any]], classification: str) -> int:
    return sum(
        1
        for result in aoi_results
        if result["basis_risk_assessment"]["classification"] == classification
    )


def _variant_rollup(aoi_results: list[dict[str, Any]], variant_name: str) -> dict[str, Any]:
    variants = [
        _benchmark_variant(result["benchmark"], variant_name)
        for result in aoi_results
    ]
    completed = [variant for variant in variants if variant and variant["status"] != "skipped"]
    return {
        "aoi_count": len(completed),
        "detected_count": sum(1 for variant in completed if variant["detected"]),
        "mean_confidence": _mean_optional([variant.get("confidence") for variant in completed]),
        "mean_median_valid_pixel_count": _mean_optional(
            [
                _nested_get(variant, "aggregate_metrics", "median_valid_pixel_count")
                for variant in completed
            ]
        ),
        "mean_cloud_pct": _mean_optional(
            [_nested_get(variant, "aggregate_metrics", "mean_cloud_pct") for variant in completed]
        ),
        "min_ndmi_ema": _min_optional(
            [_nested_get(variant, "aggregate_metrics", "min_ndmi_ema") for variant in completed]
        ),
        "mean_crop_mask_coverage_pct": _mean_optional(
            [_nested_get(variant, "aoi_metrics", "crop_mask_coverage_pct") for variant in completed]
        ),
        "total_non_crop_pixels": sum(
            int(_nested_get(variant, "aggregate_metrics", "total_non_crop_pixels") or 0)
            for variant in completed
        ),
    }


def _comparison_rollup(aoi_results: list[dict[str, Any]], candidate_variant: str) -> dict[str, Any]:
    comparisons = [
        _benchmark_comparison(result["benchmark"], candidate_variant)
        for result in aoi_results
    ]
    completed = [comparison for comparison in comparisons if comparison]
    return {
        "aoi_count": len(completed),
        "mean_valid_pixel_delta_pct": _mean_optional(
            [comparison.get("median_valid_pixel_delta_pct") for comparison in completed]
        ),
        "mean_cloud_delta_pct_points": _mean_optional(
            [comparison.get("mean_cloud_delta_pct_points") for comparison in completed]
        ),
        "mean_min_ndmi_mean_delta": _mean_optional(
            [comparison.get("min_ndmi_mean_delta") for comparison in completed]
        ),
        "mean_min_ndmi_ema_delta": _mean_optional(
            [comparison.get("min_ndmi_ema_delta") for comparison in completed]
        ),
        "mean_confidence_delta": _mean_optional(
            [comparison.get("confidence_delta") for comparison in completed]
        ),
        "total_non_crop_pixel_delta": sum(
            int(comparison.get("non_crop_pixel_delta") or 0) for comparison in completed
        ),
    }


def _summarize_benchmark_variant(
    variant: str,
    label: str,
    response: RiskResponse | None,
    *,
    region: str,
) -> dict[str, Any]:
    if response is None:
        return {
            "variant": variant,
            "label": label,
            "status": "skipped",
            "skip_reason": "crop_mask_geojson_not_provided",
        }

    summary = summarize_2022_validation(response, region=region)
    ndmi_periods = summary["ndmi_periods"]
    valid_counts = [
        int(period["valid_pixel_count"])
        for period in ndmi_periods
        if period["valid_pixel_count"] is not None
    ]
    cloud_values = [
        float(period["cloud_pct"]) for period in ndmi_periods if period["cloud_pct"] is not None
    ]
    ndmi_mean_values = _period_float_values(ndmi_periods, "ndmi_mean")
    ndmi_ema_values = _period_float_values(ndmi_periods, "ndmi_ema")
    flag_counts = _quality_flag_counts(response)
    summary.update(
        {
            "variant": variant,
            "label": label,
            "aoi_metrics": response.aoi_metrics.model_dump(mode="json"),
            "aggregate_metrics": {
                "median_valid_pixel_count": _median_int(valid_counts),
                "mean_cloud_pct": _mean_float(cloud_values),
                "min_ndmi_mean": _min_float(ndmi_mean_values),
                "min_ndmi_ema": _min_float(ndmi_ema_values),
                "total_non_crop_pixels": sum(
                    observation.mask_counts.non_crop for observation in response.series
                ),
                "quality_flag_counts": flag_counts,
            },
        }
    )
    return summary


def _period_float_values(periods: list[dict[str, Any]], key: str) -> list[float]:
    return [float(period[key]) for period in periods if period.get(key) is not None]


def _median_int(values: list[int]) -> int | None:
    if not values:
        return None
    return int(statistics.median(values))


def _mean_float(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.fmean(values)


def _min_float(values: list[float]) -> float | None:
    if not values:
        return None
    return min(values)


def _quality_flag_counts(response: RiskResponse) -> dict[str, int]:
    counts: dict[str, int] = {}
    for observation in response.series:
        for flag in observation.quality_flags:
            counts[flag] = counts.get(flag, 0) + 1
    return counts


def _compare_benchmark_variants(
    raw: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    raw_metrics = raw["aggregate_metrics"]
    candidate_metrics = candidate["aggregate_metrics"]
    return {
        "baseline_variant": raw["variant"],
        "candidate_variant": candidate["variant"],
        "median_valid_pixel_delta_pct": _pct_delta(
            raw_metrics["median_valid_pixel_count"],
            candidate_metrics["median_valid_pixel_count"],
        ),
        "mean_cloud_delta_pct_points": _numeric_delta(
            raw_metrics["mean_cloud_pct"],
            candidate_metrics["mean_cloud_pct"],
        ),
        "min_ndmi_mean_delta": _numeric_delta(
            raw_metrics["min_ndmi_mean"],
            candidate_metrics["min_ndmi_mean"],
        ),
        "min_ndmi_ema_delta": _numeric_delta(
            raw_metrics["min_ndmi_ema"],
            candidate_metrics["min_ndmi_ema"],
        ),
        "confidence_delta": _numeric_delta(raw["confidence"], candidate["confidence"]),
        "non_crop_pixel_delta": (
            candidate_metrics["total_non_crop_pixels"]
            - raw_metrics["total_non_crop_pixels"]
        ),
    }


def _numeric_delta(baseline: float | int | None, candidate: float | int | None) -> float | None:
    if baseline is None or candidate is None:
        return None
    return float(candidate) - float(baseline)


def _pct_delta(baseline: float | int | None, candidate: float | int | None) -> float | None:
    if baseline is None or candidate is None or float(baseline) == 0:
        return None
    return (float(candidate) - float(baseline)) / float(baseline) * 100


def render_validation_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# OrbitRisk 2022 Drought Validation: {summary['region']}",
        "",
        f"- Request: `{summary['request_id']}`",
        f"- Status: `{summary['status']}`",
        f"- Detected: `{summary['detected']}`",
        f"- Detection reason: `{summary['detection_reason']}`",
        f"- Confidence: `{summary['confidence']:.2f}`",
        f"- Target periods: `{summary['target_period_count']}`",
        f"- Baseline-supported periods: `{summary['baseline_supported_period_count']}`",
        "",
        "## NDMI Periods",
        "",
        "| Period | Date | Quality | Valid px | Cloud % | NDMI mean | EMA | z | "
        "baseline pctl | n |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for period in summary["ndmi_periods"]:
        lines.append(
            "| {period} | {date} | {quality} | {valid} | {cloud:.1f} | {mean:.4f} | "
            "{ema} | {z} | {pctl} | {count} |".format(
                period=period["period"],
                date=period["date"],
                quality=period["quality"],
                valid=period["valid_pixel_count"],
                cloud=period["cloud_pct"],
                mean=period["ndmi_mean"],
                ema=_format_optional(period["ndmi_ema"]),
                z=_format_optional(period["ndmi_anomaly_z"]),
                pctl=_format_optional(period["ndmi_baseline_percentile"]),
                count=period["ndmi_baseline_count"] or "",
            )
        )
    lines.append("")
    lines.append("## Critical Periods")
    lines.append("")
    if summary["critical_periods"]:
        for period in summary["critical_periods"]:
            lines.append(f"- {period['start']} to {period['end']}: {period['severity']}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def render_mask_benchmark_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# OrbitRisk 2022 Mask Benchmark: {summary['region']}",
        "",
        "- Completed variants: `{completed}` / `{total}`".format(
            completed=summary["completed_variant_count"],
            total=summary["variant_count"],
        ),
        "",
        "## Variant Summary",
        "",
        "| Variant | Status | Detected | Confidence | Target periods | Baseline periods | "
        "Median valid px | Mean cloud % | Min NDMI mean | Min NDMI EMA | Crop coverage % | "
        "Non-crop px |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in summary["variants"]:
        if variant["status"] == "skipped":
            lines.append(
                f"| {variant['label']} | skipped |  |  |  |  |  |  |  |  |  |  |"
            )
            continue
        metrics = variant["aggregate_metrics"]
        aoi_metrics = variant["aoi_metrics"]
        lines.append(
            "| {label} | {status} | {detected} | {confidence:.2f} | {target} | "
            "{baseline} | {valid} | {cloud} | {mean} | {ema} | {coverage} | {non_crop} |".format(
                label=variant["label"],
                status=variant["status"],
                detected=variant["detected"],
                confidence=variant["confidence"],
                target=variant["target_period_count"],
                baseline=variant["baseline_supported_period_count"],
                valid=metrics["median_valid_pixel_count"] or "",
                cloud=_format_optional(metrics["mean_cloud_pct"]),
                mean=_format_optional(metrics["min_ndmi_mean"]),
                ema=_format_optional(metrics["min_ndmi_ema"]),
                coverage=_format_optional(aoi_metrics["crop_mask_coverage_pct"]),
                non_crop=metrics["total_non_crop_pixels"],
            )
        )

    lines.extend(
        [
            "",
            "## Comparison vs Raw AOI",
            "",
            "| Candidate | Valid px delta % | Cloud delta pp | Min NDMI mean delta | "
            "Min NDMI EMA delta | Confidence delta | Non-crop px delta |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for comparison in summary["comparisons"]:
        lines.append(
            "| {candidate} | {valid} | {cloud} | {mean} | {ema} | {confidence} | "
            "{non_crop} |".format(
                candidate=comparison["candidate_variant"],
                valid=_format_optional(comparison["median_valid_pixel_delta_pct"]),
                cloud=_format_optional(comparison["mean_cloud_delta_pct_points"]),
                mean=_format_optional(comparison["min_ndmi_mean_delta"]),
                ema=_format_optional(comparison["min_ndmi_ema_delta"]),
                confidence=_format_optional(comparison["confidence_delta"]),
                non_crop=comparison["non_crop_pixel_delta"],
            )
        )

    _append_chart_artifact_section(lines, summary)
    lines.append("")
    return "\n".join(lines)


def render_mask_benchmark_batch_markdown(summary: dict[str, Any]) -> str:
    manifest = summary["manifest"]
    counts = summary["summary"]
    lines = [
        f"# OrbitRisk 2022 Batch Mask Benchmark: {manifest['name']}",
        "",
        f"- AOIs: `{counts['aoi_count']}`",
        f"- Success: `{counts['success_count']}`",
        f"- Skipped: `{counts['skipped_count']}`",
        f"- Rejected: `{counts['rejected_count']}`",
        f"- Failed: `{counts['failed_count']}`",
        "",
        "## Basis-Risk Summary",
        "",
        "| Improved | Degraded | Ambiguous | Not run |",
        "| ---: | ---: | ---: | ---: |",
        "| {improved} | {degraded} | {ambiguous} | {not_run} |".format(
            improved=summary["aggregate"]["basis_risk_classification_counts"]["improved"],
            degraded=summary["aggregate"]["basis_risk_classification_counts"]["degraded"],
            ambiguous=summary["aggregate"]["basis_risk_classification_counts"]["ambiguous"],
            not_run=summary["aggregate"]["basis_risk_classification_counts"]["not_run"],
        ),
        "",
        "## AOI Summary",
        "",
        "| AOI | Region | Status | Completed variants | Detected | Confidence | "
        "Crop coverage % | Assessment | Reasons |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for result in summary["aois"]:
        benchmark = result.get("benchmark", {})
        vector_variant = _benchmark_variant(benchmark, "vector_crop_mask")
        assessment = result.get("basis_risk_assessment", {})
        lines.append(
            "| {aoi_id} | {region} | {status} | {variants} | {detected} | {confidence} | "
            "{coverage} | {assessment} | {reasons} |".format(
                aoi_id=result["aoi_id"],
                region=result["region"],
                status=result["status"],
                variants=benchmark.get("completed_variant_count", ""),
                detected=vector_variant.get("detected", ""),
                confidence=_format_optional(vector_variant.get("confidence")),
                coverage=_format_optional(
                    vector_variant.get("aoi_metrics", {}).get("crop_mask_coverage_pct")
                ),
                assessment=assessment.get("classification", ""),
                reasons=", ".join(result.get("reasons", [])),
            )
        )
    lines.extend(
        [
            "",
            "## Variant Rollup",
            "",
            "| Variant | AOIs | Detected | Mean confidence | Mean valid px | Mean cloud % | "
            "Min NDMI EMA | Crop coverage % | Non-crop px |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for variant_name, rollup in summary["aggregate"]["variant_rollups"].items():
        lines.append(
            "| {variant} | {aois} | {detected} | {confidence} | {valid} | {cloud} | "
            "{ndmi} | {coverage} | {non_crop} |".format(
                variant=variant_name,
                aois=rollup["aoi_count"],
                detected=rollup["detected_count"],
                confidence=_format_optional(rollup["mean_confidence"]),
                valid=_format_optional(rollup["mean_median_valid_pixel_count"]),
                cloud=_format_optional(rollup["mean_cloud_pct"]),
                ndmi=_format_optional(rollup["min_ndmi_ema"]),
                coverage=_format_optional(rollup["mean_crop_mask_coverage_pct"]),
                non_crop=rollup["total_non_crop_pixels"],
            )
        )
    _append_chart_artifact_section(lines, summary)
    lines.append("")
    return "\n".join(lines)


def _benchmark_variant(benchmark: dict[str, Any], variant_name: str) -> dict[str, Any]:
    for variant in benchmark.get("variants", []):
        if isinstance(variant, dict) and variant.get("variant") == variant_name:
            return variant
    return {}


def _benchmark_comparison(benchmark: dict[str, Any], candidate_variant: str) -> dict[str, Any]:
    for comparison in benchmark.get("comparisons", []):
        if (
            isinstance(comparison, dict)
            and comparison.get("candidate_variant") == candidate_variant
        ):
            return comparison
    return {}


def _attach_chart_artifacts(
    summary: dict[str, Any],
    charts: list[dict[str, str]],
) -> None:
    artifacts = summary.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
        summary["artifacts"] = artifacts
    artifacts["charts"] = charts


def _append_chart_artifact_section(lines: list[str], summary: dict[str, Any]) -> None:
    artifacts = summary.get("artifacts", {})
    charts = artifacts.get("charts", []) if isinstance(artifacts, dict) else []
    if not isinstance(charts, list) or not charts:
        return

    lines.extend(
        [
            "",
            "## Chart Artifacts",
            "",
            "| AOI | Variant | Metric | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        lines.append(
            "| {aoi} | {variant} | {metric} | `{path}` |".format(
                aoi=chart.get("aoi_id", ""),
                variant=chart.get("variant", ""),
                metric=chart.get("metric", ""),
                path=chart.get("path", ""),
            )
        )


def _nested_get(document: dict[str, Any], *keys: str) -> Any:
    current: Any = document
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _mean_optional(values: list[Any]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return statistics.fmean(numeric)


def _min_optional(values: list[Any]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return min(numeric)


def _format_optional(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
