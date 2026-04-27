from pathlib import Path

from orbitrisk.batch.manifest import load_aoi_batch_manifest, resolve_geojson_document
from orbitrisk.batch.quality import validate_aoi_manifest


def test_rpg_candidate_pack_has_real_vineyard_aois_and_crop_masks() -> None:
    manifest_path = Path("examples/rpg_2023_vineyard_candidate_manifest.json")

    manifest = load_aoi_batch_manifest(manifest_path)
    report = validate_aoi_manifest(manifest, manifest_path=manifest_path)

    assert manifest.name == "rpg-2023-vineyard-candidate-pack"
    assert len(manifest.aois) == 10
    assert {entry.region for entry in manifest.aois} == {"bordeaux", "languedoc"}
    assert all(entry.crop_mask_geojson_path is not None for entry in manifest.aois)
    assert report["summary"]["accepted_count"] == 10
    assert report["summary"]["has_external_crop_mask_count"] == 10

    first_aoi = manifest.aois[0]
    assert first_aoi.aoi_geojson_path is not None
    assert first_aoi.crop_mask_geojson_path is not None
    aoi = resolve_geojson_document(manifest_path.parent, first_aoi.aoi_geojson_path)
    crop_mask = resolve_geojson_document(
        manifest_path.parent,
        first_aoi.crop_mask_geojson_path,
    )
    assert aoi["properties"]["source"] == "IGN RPG 2023 WFS"
    assert crop_mask["properties"]["source_layer"] == "RPG.2023:parcelles_graphiques"
    assert crop_mask["properties"]["rpg_code_group"] == "21"
    assert crop_mask["properties"]["geometry_role"] == "crop_mask"
