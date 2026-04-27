import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from orbitrisk.batch.manifest import AoiBatchManifest, load_aoi_batch_manifest
from orbitrisk.batch.quality import render_aoi_validation_markdown, validate_aoi_manifest
from orbitrisk.cli import run_aoi_batch_validation


def test_manifest_accepts_inline_and_path_geojson(tmp_path: Path) -> None:
    aoi_path = tmp_path / "vineyard.geojson"
    aoi_path.write_text(json.dumps(_feature()))
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "m1-test",
                "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
                "aois": [
                    {
                        "aoi_id": "inline-aoi",
                        "region": "bordeaux",
                        "crop": "vineyard",
                        "aoi": _feature(),
                    },
                    {
                        "aoi_id": "path-aoi",
                        "region": "languedoc",
                        "crop": "vineyard",
                        "aoi_geojson_path": "vineyard.geojson",
                    },
                ],
            }
        )
    )

    manifest = load_aoi_batch_manifest(manifest_path)

    assert manifest.name == "m1-test"
    assert len(manifest.aois) == 2
    assert manifest.aois[1].aoi_geojson_path == Path("vineyard.geojson")


def test_manifest_rejects_duplicate_ids_and_unsupported_crop() -> None:
    with pytest.raises(ValidationError, match="Duplicate AOI ids"):
        AoiBatchManifest.model_validate(
            {
                "name": "duplicates",
                "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
                "aois": [
                    {"aoi_id": "same", "region": "bordeaux", "aoi": _feature()},
                    {"aoi_id": "same", "region": "bordeaux", "aoi": _feature()},
                ],
            }
        )

    with pytest.raises(ValidationError):
        AoiBatchManifest.model_validate(
            {
                "name": "bad-crop",
                "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
                "aois": [
                    {
                        "aoi_id": "corn",
                        "region": "bordeaux",
                        "crop": "corn",
                        "aoi": _feature(),
                    }
                ],
            }
        )

    with pytest.raises(ValidationError, match="Only EPSG CRS identifiers"):
        AoiBatchManifest.model_validate(
            {
                "name": "bad-crs",
                "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
                "aois": [
                    {
                        "aoi_id": "bad-crs",
                        "region": "bordeaux",
                        "crs": "WGS84",
                        "aoi": _feature(),
                    }
                ],
            }
        )


def test_validate_aoi_manifest_reports_accepts_rejects_and_crop_mask(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "quality-gates",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "valid-with-mask",
                    "region": "bordeaux",
                    "aoi": _feature(),
                    "crop_mask": _left_half_crop_mask(),
                },
                {
                    "aoi_id": "too-small",
                    "region": "bordeaux",
                    "aoi": _tiny_feature(),
                },
            ],
        }
    )

    report = validate_aoi_manifest(manifest, manifest_path=tmp_path / "manifest.json")

    assert report["summary"]["accepted_count"] == 1
    assert report["summary"]["rejected_count"] == 1
    assert report["summary"]["has_external_crop_mask_count"] == 1
    assert report["aois"][0]["metrics"]["crop_mask_pixel_count"] > 0
    assert report["aois"][1]["status"] == "rejected"
    assert "insufficient_pixels" in report["aois"][1]["reasons"]
    assert "empty_negative_buffer" in report["aois"][1]["reasons"]


def test_validate_aoi_manifest_rejects_invalid_geometry(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "invalid-geometry",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "bowtie",
                    "region": "bordeaux",
                    "aoi": _invalid_feature(),
                },
            ],
        }
    )

    report = validate_aoi_manifest(manifest, manifest_path=tmp_path / "manifest.json")

    assert report["summary"]["rejected_count"] == 1
    assert report["aois"][0]["status"] == "rejected"
    assert "invalid_geometry" in report["aois"][0]["reasons"]


def test_render_aoi_validation_markdown_includes_status_table(tmp_path: Path) -> None:
    manifest = AoiBatchManifest.model_validate(
        {
            "name": "markdown",
            "date_range": {"start": "2021-01-01", "end": "2022-08-31"},
            "aois": [
                {
                    "aoi_id": "valid",
                    "region": "bordeaux",
                    "aoi": _feature(),
                }
            ],
        }
    )
    report = validate_aoi_manifest(manifest, manifest_path=tmp_path / "manifest.json")

    rendered = render_aoi_validation_markdown(report)

    assert "# OrbitRisk AOI Batch Validation: markdown" in rendered
    assert "| valid | bordeaux | accepted |" in rendered
    assert "missing_crop_mask" in rendered


def test_run_aoi_batch_validation_writes_json_and_markdown(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "cli",
                "date_range": {
                    "start": date(2021, 1, 1).isoformat(),
                    "end": date(2022, 8, 31).isoformat(),
                },
                "aois": [
                    {
                        "aoi_id": "valid",
                        "region": "bordeaux",
                        "aoi": _feature(),
                    }
                ],
            }
        )
    )

    report = run_aoi_batch_validation(
        SimpleNamespace(
            manifest_json=manifest_path,
            output_json=output_json,
            output_md=output_md,
        )
    )

    assert report["summary"]["accepted_count"] == 1
    assert json.loads(output_json.read_text())["summary"]["accepted_count"] == 1
    assert "OrbitRisk AOI Batch Validation" in output_md.read_text()


def _feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"asset_id": "FR_VINEYARD_TEST", "crop": "vineyard"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.83, 45.73],
                    [4.83, 45.74],
                    [4.82, 45.74],
                    [4.82, 45.73],
                ]
            ],
        },
    }


def _tiny_feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"asset_id": "TOO_SMALL", "crop": "vineyard"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.82001, 45.73],
                    [4.82001, 45.73001],
                    [4.82, 45.73001],
                    [4.82, 45.73],
                ]
            ],
        },
    }


def _invalid_feature() -> dict:
    return {
        "type": "Feature",
        "properties": {"asset_id": "BOWTIE", "crop": "vineyard"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.83, 45.74],
                    [4.83, 45.73],
                    [4.82, 45.74],
                    [4.82, 45.73],
                ]
            ],
        },
    }


def _left_half_crop_mask() -> dict:
    return {
        "type": "Feature",
        "properties": {"source": "synthetic-rpg"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [4.82, 45.73],
                    [4.825, 45.73],
                    [4.825, 45.74],
                    [4.82, 45.74],
                    [4.82, 45.73],
                ]
            ],
        },
    }
