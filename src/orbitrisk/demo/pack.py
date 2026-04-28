import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any, cast

from orbitrisk.batch.manifest import AoiManifestEntry, load_aoi_batch_manifest
from orbitrisk.batch.requests import risk_request_payload_from_manifest_entry

DEFAULT_BASELINE_START = date(2019, 6, 1)
DEFAULT_END = date(2022, 8, 31)


def build_mga_demo_pack(
    *,
    output_dir: Path,
    manifest_path: Path,
    validation_report_paths: list[Path],
    benchmark_json_path: Path,
    validation_memo_path: Path,
    benchmark_report_path: Path,
    benchmark_charts_dir: Path | None = None,
    baseline_start: date = DEFAULT_BASELINE_START,
    end: date = DEFAULT_END,
) -> dict[str, Any]:
    """Build a compact, reproducible demo folder from existing validation artifacts."""
    manifest = load_aoi_batch_manifest(manifest_path)
    validation_reports = [_read_json_object(path) for path in validation_report_paths]
    benchmark = _read_json_object(benchmark_json_path)

    strongest = _select_strongest_success(validation_reports)
    worst_failure = _select_worst_failure(validation_reports)
    entries_by_id = {entry.aoi_id: entry for entry in manifest.aois}

    output_dir.mkdir(parents=True, exist_ok=True)
    request_dir = output_dir / "requests"
    output_summary_dir = output_dir / "outputs"
    report_dir = output_dir / "reports"
    chart_dir = output_dir / "charts"
    for directory in (request_dir, output_summary_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    strongest_id = str(strongest["aoi_id"])
    worst_failure_id = str(worst_failure["aoi_id"])
    _write_json(
        request_dir / "strongest_success_request.json",
        _request_payload_for_aoi(
            entries_by_id,
            strongest_id,
            manifest_path=manifest_path,
            manifest=manifest,
            baseline_start=baseline_start,
            end=end,
        ),
    )
    _write_json(
        request_dir / "worst_failure_request.json",
        _request_payload_for_aoi(
            entries_by_id,
            worst_failure_id,
            manifest_path=manifest_path,
            manifest=manifest,
            baseline_start=baseline_start,
            end=end,
        ),
    )
    _write_json(
        output_summary_dir / "strongest_success_summary.json",
        _compact_validation_result(strongest),
    )
    _write_json(
        output_summary_dir / "worst_failure_summary.json",
        _compact_validation_result(worst_failure),
    )
    _write_json(
        output_summary_dir / "mask_benchmark_summary.json",
        _compact_benchmark_result(benchmark),
    )

    shutil.copyfile(validation_memo_path, report_dir / "2022_drought_validation_report.md")
    shutil.copyfile(benchmark_report_path, report_dir / "mask_benchmark_report.md")
    if benchmark_charts_dir is not None and benchmark_charts_dir.exists():
        if chart_dir.exists():
            shutil.rmtree(chart_dir)
        shutil.copytree(benchmark_charts_dir, chart_dir / "mask_benchmark")

    manifest_summary = {
        "demo": "mga_pilot_2022",
        "baseline_start": baseline_start.isoformat(),
        "end": end.isoformat(),
        "source_manifest": str(manifest_path),
        "source_validation_reports": [str(path) for path in validation_report_paths],
        "source_benchmark_json": str(benchmark_json_path),
        "strongest_success_aoi": strongest_id,
        "worst_failure_aoi": worst_failure_id,
        "files": [],
    }
    _write_demo_readme(output_dir / "README.md", manifest_summary)
    manifest_summary["files"] = sorted(
        {*_demo_file_manifest(output_dir), "MANIFEST.json"}
    )
    _write_json(output_dir / "MANIFEST.json", manifest_summary)
    return manifest_summary


def _request_payload_for_aoi(
    entries_by_id: dict[str, AoiManifestEntry],
    aoi_id: str,
    *,
    manifest_path: Path,
    manifest: Any,
    baseline_start: date,
    end: date,
) -> dict[str, Any]:
    entry = entries_by_id.get(aoi_id)
    if entry is None:
        raise ValueError(f"AOI {aoi_id} is missing from {manifest_path}")
    return risk_request_payload_from_manifest_entry(
        manifest,
        entry,
        base_dir=manifest_path.parent,
        date_start=baseline_start,
        date_end=end,
        include_crop_mask=True,
    )


def _select_strongest_success(reports: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [
        result
        for result in _validation_results(reports)
        if _classification(result) == "accepted"
    ]
    if not accepted:
        raise ValueError("No accepted validation result found")
    return max(accepted, key=_confidence)


def _select_worst_failure(reports: list[dict[str, Any]]) -> dict[str, Any]:
    ambiguous = [
        result
        for result in _validation_results(reports)
        if _classification(result) == "ambiguous"
    ]
    if not ambiguous:
        raise ValueError("No ambiguous validation result found")
    return max(ambiguous, key=_failure_score)


def _validation_results(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for report in reports:
        aois = report.get("aois", [])
        if not isinstance(aois, list):
            continue
        for result in aois:
            if isinstance(result, dict) and isinstance(result.get("validation"), dict):
                results.append(result)
    return results


def _classification(result: dict[str, Any]) -> str:
    classification = _assessment(result).get("classification")
    return str(classification or "not_run")


def _confidence(result: dict[str, Any]) -> float:
    validation = _validation(result)
    return _float(validation.get("confidence")) or 0.0


def _failure_score(result: dict[str, Any]) -> float:
    assessment = _assessment(result)
    inputs = _assessment_inputs(result)
    reasons = {str(reason) for reason in assessment.get("reasons", [])}
    score = 0.0
    if "seasonal_percentile_not_low" in reasons:
        score += 200.0
    if "quality_warnings_require_review" in reasons:
        score += 100.0
    mean_cloud_pct = _float(inputs.get("mean_cloud_pct"))
    if mean_cloud_pct is not None:
        score += mean_cloud_pct
    min_valid_pixel_count = _float(inputs.get("min_valid_pixel_count"))
    if min_valid_pixel_count is not None:
        score += max(0.0, 500.0 - min_valid_pixel_count) / 10.0
    min_baseline_percentile = _float(inputs.get("min_baseline_percentile"))
    if min_baseline_percentile is not None:
        score += min_baseline_percentile
    return score


def _compact_validation_result(result: dict[str, Any]) -> dict[str, Any]:
    validation = _validation(result)
    assessment = _assessment(result)
    inputs = _assessment_inputs(result)
    return {
        "aoi_id": result["aoi_id"],
        "region": result["region"],
        "classification": assessment["classification"],
        "reasons": assessment["reasons"],
        "detected": validation["detected"],
        "trigger": validation["detection_reason"],
        "confidence": validation["confidence"],
        "quality": {
            "target_period_count": validation["target_period_count"],
            "baseline_supported_period_count": validation[
                "baseline_supported_period_count"
            ],
            "min_valid_pixel_count": inputs.get("min_valid_pixel_count"),
            "mean_cloud_pct": inputs.get("mean_cloud_pct"),
            "min_baseline_percentile": inputs.get("min_baseline_percentile"),
            "quality_flag_counts": validation["quality_flag_counts"],
        },
        "critical_periods": validation["critical_periods"],
        "ndmi_periods": [
            _compact_ndmi_period(period) for period in validation["ndmi_periods"]
        ],
    }


def _compact_ndmi_period(period: dict[str, Any]) -> dict[str, Any]:
    return {
        "period": period["period"],
        "date": period["date"],
        "quality": period["quality"],
        "quality_flags": period["quality_flags"],
        "valid_pixel_count": period["valid_pixel_count"],
        "cloud_pct": period["cloud_pct"],
        "ndmi_mean": period["ndmi_mean"],
        "ndmi_ema": period["ndmi_ema"],
        "ndmi_baseline_percentile": period["ndmi_baseline_percentile"],
        "ndmi_baseline_count": period["ndmi_baseline_count"],
    }


def _compact_benchmark_result(benchmark: dict[str, Any]) -> dict[str, Any]:
    first_aoi = _first_successful_benchmark_aoi(benchmark)
    basis_risk = first_aoi["basis_risk_assessment"]
    benchmark_result = first_aoi["benchmark"]
    return {
        "aoi_id": first_aoi["aoi_id"],
        "basis_risk_classification": basis_risk["classification"],
        "basis_risk_reasons": basis_risk["reasons"],
        "variant_count": benchmark_result["variant_count"],
        "completed_variant_count": benchmark_result["completed_variant_count"],
        "variants": [
            _compact_benchmark_variant(variant)
            for variant in benchmark_result["variants"]
        ],
        "comparisons": benchmark_result["comparisons"],
    }


def _first_successful_benchmark_aoi(benchmark: dict[str, Any]) -> dict[str, Any]:
    aois = benchmark.get("aois", [])
    if not isinstance(aois, list):
        raise ValueError("Benchmark JSON does not contain an AOI list")
    for result in aois:
        if isinstance(result, dict) and result.get("status") == "success":
            return result
    raise ValueError("Benchmark JSON does not contain a successful AOI")


def _compact_benchmark_variant(variant: dict[str, Any]) -> dict[str, Any]:
    aggregate = variant["aggregate_metrics"]
    aoi_metrics = variant["aoi_metrics"]
    return {
        "variant": variant["variant"],
        "label": variant["label"],
        "status": variant["status"],
        "detected": variant["detected"],
        "confidence": variant["confidence"],
        "mean_cloud_pct": aggregate["mean_cloud_pct"],
        "median_valid_pixel_count": aggregate["median_valid_pixel_count"],
        "min_ndmi_ema": aggregate["min_ndmi_ema"],
        "total_non_crop_pixels": aggregate["total_non_crop_pixels"],
        "crop_mask_coverage_pct": aoi_metrics["crop_mask_coverage_pct"],
    }


def _validation(result: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], result["validation"])


def _assessment(result: dict[str, Any]) -> dict[str, Any]:
    validation = _validation(result)
    return cast(dict[str, Any], validation["validation_assessment"])


def _assessment_inputs(result: dict[str, Any]) -> dict[str, Any]:
    assessment = _assessment(result)
    return cast(dict[str, Any], assessment["inputs"])


def _float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _read_json_object(path: Path) -> dict[str, Any]:
    document: Any = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return document


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _demo_file_manifest(output_dir: Path) -> list[str]:
    return [
        str(path.relative_to(output_dir))
        for path in sorted(output_dir.rglob("*"))
        if path.is_file()
    ]


def _write_demo_readme(path: Path, manifest_summary: dict[str, Any]) -> None:
    strongest = manifest_summary["strongest_success_aoi"]
    worst = manifest_summary["worst_failure_aoi"]
    path.write_text(
        "\n".join(
            [
                "# OrbitRisk MGA Pilot Demo Pack",
                "",
                "This folder is the buyer-facing demo bundle for the July-August 2022 "
                "drought validation narrative.",
                "",
                "## Talk Track",
                "",
                f"- Strongest accepted AOI: `{strongest}`.",
                f"- Worst ambiguous failure case: `{worst}`.",
                "- Crop-mask benchmark: raw AOI vs negative buffer vs external RPG-style mask.",
                "- Main claim: auditable parcel-level drought evidence, not black-box "
                "Sentinel-2 vine-row segmentation.",
                "",
                "## Files",
                "",
                "- `requests/strongest_success_request.json`: live API request for the "
                "clean accepted case.",
                "- `requests/worst_failure_request.json`: live API request for the "
                "ambiguous case.",
                "- `outputs/strongest_success_summary.json`: compact actuarial-readable "
                "response summary.",
                "- `outputs/worst_failure_summary.json`: compact failure-mode summary.",
                "- `outputs/mask_benchmark_summary.json`: compact basis-risk benchmark.",
                "- `reports/2022_drought_validation_report.md`: full validation memo.",
                "- `reports/mask_benchmark_report.md`: full mask benchmark report.",
                "- `charts/mask_benchmark/`: SVG charts when source chart artifacts exist.",
                "",
                "## Rebuild From A Clean Checkout",
                "",
                "```bash",
                "python -m venv .venv",
                "source .venv/bin/activate",
                "pip install -e \".[dev]\"",
                "orbitrisk build-mga-demo-pack --output-dir demo/mga_pilot_2022",
                "```",
                "",
                "## Reproduce Live Source Reports",
                "",
                "These commands hit Planetary Computer unless cached responses already "
                "exist under `data/cache`.",
                "",
                "```bash",
                "orbitrisk validate-2022-batch "
                "examples/rpg_2023_vineyard_candidate_manifest.json \\",
                "  --region bordeaux \\",
                "  --max-items 40 \\",
                "  --output-json reports/bordeaux-2022-batch-validation.json \\",
                "  --output-md reports/bordeaux-2022-batch-validation.md",
                "",
                "orbitrisk validate-2022-batch "
                "examples/rpg_2023_vineyard_candidate_manifest.json \\",
                "  --region languedoc \\",
                "  --max-items 40 \\",
                "  --output-json reports/languedoc-2022-batch-validation.json \\",
                "  --output-md reports/languedoc-2022-batch-validation.md",
                "",
                "orbitrisk benchmark-masks-batch-2022 "
                "examples/rpg_2023_first_real_benchmark_manifest.json \\",
                "  --max-items 40 \\",
                "  --output-json reports/rpg-2023-first-real-mask-benchmark.json \\",
                "  --output-md reports/rpg-2023-first-real-mask-benchmark.md \\",
                "  --charts-dir reports/charts/rpg-2023-first-real-mask-benchmark",
                "```",
                "",
            ]
        )
    )
