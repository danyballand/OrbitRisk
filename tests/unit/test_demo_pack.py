import json
from pathlib import Path

from orbitrisk.demo.pack import build_mga_demo_pack

ROOT = Path(__file__).resolve().parents[2]


def test_build_mga_demo_pack_writes_buyer_facing_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo"

    summary = build_mga_demo_pack(
        output_dir=output_dir,
        manifest_path=ROOT / "examples/rpg_2023_vineyard_candidate_manifest.json",
        validation_report_paths=[
            ROOT / "reports/bordeaux-2022-batch-validation.json",
            ROOT / "reports/languedoc-2022-batch-validation.json",
        ],
        benchmark_json_path=ROOT / "reports/rpg-2023-first-real-mask-benchmark.json",
        validation_memo_path=ROOT / "docs/2022_DROUGHT_VALIDATION_REPORT.md",
        benchmark_report_path=ROOT / "reports/rpg-2023-first-real-mask-benchmark.md",
        benchmark_charts_dir=ROOT / "reports/charts/rpg-2023-first-real-mask-benchmark",
    )

    assert summary["strongest_success_aoi"] == "FR_RPG23_PIC_SAINT_LOUP_02"
    assert summary["worst_failure_aoi"] == "FR_RPG23_BEZIERS_01"
    assert "MANIFEST.json" in summary["files"]
    assert "README.md" in summary["files"]
    assert (output_dir / "README.md").exists()
    assert (output_dir / "reports/2022_drought_validation_report.md").exists()
    assert (output_dir / "reports/mask_benchmark_report.md").exists()
    assert (output_dir / "charts/mask_benchmark").exists()

    strongest_request = _read_json(output_dir / "requests/strongest_success_request.json")
    worst_summary = _read_json(output_dir / "outputs/worst_failure_summary.json")
    benchmark_summary = _read_json(output_dir / "outputs/mask_benchmark_summary.json")

    assert strongest_request["request_id"] == "FR_RPG23_PIC_SAINT_LOUP_02"
    assert strongest_request["crop_mask"]["type"] in {"Feature", "FeatureCollection"}
    assert worst_summary["classification"] == "ambiguous"
    assert "seasonal_percentile_not_low" in worst_summary["reasons"]
    assert worst_summary["ndmi_periods"][0]["valid_pixel_count"] > 0
    assert "quality_flags" in worst_summary["ndmi_periods"][0]
    assert benchmark_summary["basis_risk_classification"] == "improved"
    assert {variant["variant"] for variant in benchmark_summary["variants"]} == {
        "raw_aoi",
        "buffered_aoi",
        "vector_crop_mask",
    }


def _read_json(path: Path) -> dict:
    document = json.loads(path.read_text())
    assert isinstance(document, dict)
    return document
