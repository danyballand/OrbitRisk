from orbitrisk.batch.basis_risk import BasisRiskInputs, classify_basis_risk


def test_basis_risk_classifier_marks_clear_non_crop_removal_as_improved() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="completed",
            crop_mask_coverage_pct=50.0,
            crop_mask_median_valid_pixel_count=100,
            min_valid_pixels=20,
            non_crop_pixel_delta=10,
            valid_pixel_delta_pct=-20.0,
            min_ndmi_ema_delta=0.02,
        )
    )

    assert assessment["classification"] == "improved"
    assert assessment["reasons"] == ["non_crop_pixels_removed"]


def test_basis_risk_classifier_degrades_excessive_valid_pixel_loss() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="completed",
            crop_mask_coverage_pct=50.0,
            crop_mask_median_valid_pixel_count=100,
            min_valid_pixels=20,
            non_crop_pixel_delta=10,
            valid_pixel_delta_pct=-90.0,
            min_ndmi_ema_delta=0.02,
        )
    )

    assert assessment["classification"] == "degraded"
    assert "excessive_valid_pixel_loss" in assessment["reasons"]


def test_basis_risk_classifier_degrades_insufficient_crop_mask_pixels() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="completed",
            crop_mask_coverage_pct=50.0,
            crop_mask_median_valid_pixel_count=5,
            min_valid_pixels=20,
            non_crop_pixel_delta=10,
            valid_pixel_delta_pct=-20.0,
            min_ndmi_ema_delta=0.02,
        )
    )

    assert assessment["classification"] == "degraded"
    assert "insufficient_crop_mask_valid_pixels" in assessment["reasons"]


def test_basis_risk_classifier_keeps_no_non_crop_delta_ambiguous() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="completed",
            crop_mask_coverage_pct=50.0,
            crop_mask_median_valid_pixel_count=100,
            min_valid_pixels=20,
            non_crop_pixel_delta=0,
            valid_pixel_delta_pct=-20.0,
            min_ndmi_ema_delta=0.02,
        )
    )

    assert assessment["classification"] == "ambiguous"
    assert assessment["reasons"] == ["no_measurable_non_crop_delta"]


def test_basis_risk_classifier_keeps_large_ndmi_shift_ambiguous() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="completed",
            crop_mask_coverage_pct=50.0,
            crop_mask_median_valid_pixel_count=100,
            min_valid_pixels=20,
            non_crop_pixel_delta=10,
            valid_pixel_delta_pct=-20.0,
            min_ndmi_ema_delta=0.3,
        )
    )

    assert assessment["classification"] == "ambiguous"
    assert "large_ndmi_shift_requires_review" in assessment["reasons"]


def test_basis_risk_classifier_marks_missing_vector_mask_as_not_run() -> None:
    assessment = classify_basis_risk(
        BasisRiskInputs(
            vector_status="skipped",
            crop_mask_coverage_pct=None,
            crop_mask_median_valid_pixel_count=None,
            min_valid_pixels=20,
            non_crop_pixel_delta=None,
            valid_pixel_delta_pct=None,
            min_ndmi_ema_delta=None,
        )
    )

    assert assessment["classification"] == "not_run"
    assert assessment["reasons"] == ["missing_crop_mask"]
