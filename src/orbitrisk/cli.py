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

    args = parser.parse_args(argv)
    if args.command == "smoke-pc":
        result = run_planetary_computer_smoke(args)
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

    return {
        "request_id": payload["request_id"],
        "provider": "planetary-computer",
        "processing_crs": prepared_aoi.processing_crs.to_string(),
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
                "valid_pixel_count": observation.stats.valid_pixel_count,
                "cloud_pct": observation.stats.cloud_pct,
                "indices": observation.stats.index_stats,
                "mask_counts": observation.stats.mask_counts,
            }
            for observation in observations
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
