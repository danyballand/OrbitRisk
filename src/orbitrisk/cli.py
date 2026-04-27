import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from orbitrisk.config import get_settings
from orbitrisk.engine import prepare_raster_job
from orbitrisk.geo.aoi import prepare_aoi
from orbitrisk.processing.datacube import summarize_datacube
from orbitrisk.providers.planetary_computer_client import PlanetaryComputerProvider
from orbitrisk.risk_engine import RiskEngine
from orbitrisk.schemas.request import RiskRequest
from orbitrisk.schemas.response import RiskResponse
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
    validate = subparsers.add_parser("validate-2022", help="Run a drought-2022 validation")
    validate.add_argument("request_json", type=Path)
    validate.add_argument("--region", default="unknown")
    validate.add_argument("--baseline-start", type=date.fromisoformat, default=date(2019, 6, 1))
    validate.add_argument("--end", type=date.fromisoformat, default=date(2022, 8, 31))
    validate.add_argument("--max-items", type=int, default=80)

    args = parser.parse_args(argv)
    if args.command == "smoke-pc":
        result = run_planetary_computer_smoke(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "validate-2022":
        result = run_2022_validation(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    return 1


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
    payload["date_range"] = {
        "start": args.baseline_start.isoformat(),
        "end": args.end.isoformat(),
    }
    payload["aggregation"] = {
        "temporal": payload.get("aggregation", {}).get("temporal", "P10D"),
        "spatial_stats": payload.get("aggregation", {}).get(
            "spatial_stats",
            ["mean", "median", "p10", "p90", "std"],
        ),
    }
    request = RiskRequest.model_validate(payload)
    settings = get_settings()
    response = RiskEngine(
        PlanetaryComputerProvider(settings),
        provider_name="planetary-computer",
        collection=settings.planetary_computer_collection,
    ).quote(request, max_items=args.max_items)
    return summarize_2022_validation(response, region=args.region)


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


if __name__ == "__main__":
    raise SystemExit(main())
