from orbitrisk.validation.drought import (
    DroughtValidationInputs,
    classify_drought_validation,
)


def test_drought_validation_classifier_accepts_clear_historical_trigger() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="completed",
            trigger_candidate=True,
            detection_reason="ndmi_ema_below_0.15_for_2_periods",
            confidence=0.8,
            target_period_count=4,
            baseline_supported_period_count=4,
            critical_period_count=1,
            min_valid_pixel_count=80,
            mean_cloud_pct=5.0,
            rejected_period_count=0,
            quality_flag_counts={},
        )
    )

    assert assessment["classification"] == "accepted"
    assert assessment["reasons"] == ["clear_drought_trigger"]


def test_drought_validation_classifier_rejects_no_baseline_support() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="completed",
            trigger_candidate=True,
            detection_reason="ndmi_ema_below_0.15_for_2_periods",
            confidence=0.8,
            target_period_count=4,
            baseline_supported_period_count=0,
            critical_period_count=1,
            min_valid_pixel_count=80,
            mean_cloud_pct=5.0,
            rejected_period_count=0,
            quality_flag_counts={},
        )
    )

    assert assessment["classification"] == "rejected"
    assert "no_baseline_support" in assessment["reasons"]


def test_drought_validation_classifier_rejects_insufficient_pixels() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="partial",
            trigger_candidate=True,
            detection_reason="ndmi_ema_below_0.15_for_2_periods",
            confidence=0.8,
            target_period_count=4,
            baseline_supported_period_count=4,
            critical_period_count=1,
            min_valid_pixel_count=5,
            mean_cloud_pct=5.0,
            rejected_period_count=1,
            quality_flag_counts={"too_few_valid_pixels": 1},
        )
    )

    assert assessment["classification"] == "rejected"
    assert "insufficient_valid_pixels" in assessment["reasons"]


def test_drought_validation_classifier_rejects_cloud_gap() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="completed",
            trigger_candidate=False,
            detection_reason=None,
            confidence=0.2,
            target_period_count=4,
            baseline_supported_period_count=4,
            critical_period_count=0,
            min_valid_pixel_count=80,
            mean_cloud_pct=90.0,
            rejected_period_count=0,
            quality_flag_counts={"high_cloud_fraction": 4},
        )
    )

    assert assessment["classification"] == "rejected"
    assert "cloud_gap" in assessment["reasons"]


def test_drought_validation_classifier_rejects_preflight_geometry_failure() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="failed",
            trigger_candidate=False,
            detection_reason=None,
            confidence=0.0,
            target_period_count=0,
            baseline_supported_period_count=0,
            critical_period_count=0,
            min_valid_pixel_count=None,
            mean_cloud_pct=None,
            rejected_period_count=0,
            quality_flag_counts={},
            preflight_reasons=("invalid_geometry",),
        )
    )

    assert assessment["classification"] == "rejected"
    assert "invalid_geometry" in assessment["reasons"]


def test_drought_validation_classifier_keeps_weak_signal_ambiguous() -> None:
    assessment = classify_drought_validation(
        DroughtValidationInputs(
            response_status="completed",
            trigger_candidate=False,
            detection_reason=None,
            confidence=0.7,
            target_period_count=4,
            baseline_supported_period_count=4,
            critical_period_count=0,
            min_valid_pixel_count=80,
            mean_cloud_pct=5.0,
            rejected_period_count=0,
            quality_flag_counts={},
        )
    )

    assert assessment["classification"] == "ambiguous"
    assert "weak_or_no_drought_signal" in assessment["reasons"]
