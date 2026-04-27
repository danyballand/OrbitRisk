from dataclasses import asdict, dataclass
from typing import Literal

ValidationClassification = Literal["accepted", "rejected", "ambiguous"]


@dataclass(frozen=True)
class DroughtValidationThresholds:
    min_valid_pixels: int = 20
    min_baseline_supported_periods: int = 1
    min_confidence: float = 0.35
    max_mean_cloud_pct: float = 70.0
    max_rejected_period_fraction: float = 0.5


@dataclass(frozen=True)
class DroughtValidationInputs:
    response_status: str
    trigger_candidate: bool
    detection_reason: str | None
    confidence: float
    target_period_count: int
    baseline_supported_period_count: int
    critical_period_count: int
    min_valid_pixel_count: int | None
    mean_cloud_pct: float | None
    rejected_period_count: int
    quality_flag_counts: dict[str, int]
    preflight_reasons: tuple[str, ...] = ()


DEFAULT_DROUGHT_VALIDATION_THRESHOLDS = DroughtValidationThresholds()


def classify_drought_validation(
    inputs: DroughtValidationInputs,
    *,
    thresholds: DroughtValidationThresholds = DEFAULT_DROUGHT_VALIDATION_THRESHOLDS,
) -> dict[str, object]:
    """Classify one historical drought validation result for actuarial review."""
    rejected_reasons = _rejected_reasons(inputs, thresholds)
    if rejected_reasons:
        return _assessment("rejected", rejected_reasons, inputs, thresholds)

    ambiguous_reasons = _ambiguous_reasons(inputs, thresholds)
    if ambiguous_reasons:
        return _assessment("ambiguous", ambiguous_reasons, inputs, thresholds)

    return _assessment("accepted", ["clear_drought_trigger"], inputs, thresholds)


def _rejected_reasons(
    inputs: DroughtValidationInputs,
    thresholds: DroughtValidationThresholds,
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(inputs.preflight_reasons)
    if inputs.response_status == "failed":
        reasons.append("response_failed")
    if inputs.target_period_count == 0:
        reasons.append("no_target_periods")
    if inputs.baseline_supported_period_count < thresholds.min_baseline_supported_periods:
        reasons.append("no_baseline_support")
    if inputs.min_valid_pixel_count is None:
        reasons.append("no_ndmi_periods")
    elif inputs.min_valid_pixel_count < thresholds.min_valid_pixels:
        reasons.append("insufficient_valid_pixels")
    if _rejected_period_fraction(inputs) > thresholds.max_rejected_period_fraction:
        reasons.append("too_many_rejected_periods")
    if _cloud_gap(inputs, thresholds):
        reasons.append("cloud_gap")
    return reasons


def _ambiguous_reasons(
    inputs: DroughtValidationInputs,
    thresholds: DroughtValidationThresholds,
) -> list[str]:
    reasons: list[str] = []
    if not inputs.trigger_candidate or inputs.detection_reason is None:
        reasons.append("weak_or_no_drought_signal")
    if inputs.critical_period_count == 0:
        reasons.append("no_critical_periods")
    if inputs.confidence < thresholds.min_confidence:
        reasons.append("low_confidence")
    if _has_quality_warnings(inputs):
        reasons.append("quality_warnings_require_review")
    return reasons


def _cloud_gap(
    inputs: DroughtValidationInputs,
    thresholds: DroughtValidationThresholds,
) -> bool:
    if inputs.mean_cloud_pct is not None and inputs.mean_cloud_pct > thresholds.max_mean_cloud_pct:
        return True
    flags = inputs.quality_flag_counts
    if inputs.target_period_count == 0:
        return False
    cloud_like = (
        flags.get("high_cloud_fraction", 0)
        + flags.get("low_clear_fraction", 0)
        + flags.get("no_index_stats", 0)
    )
    return cloud_like == inputs.target_period_count


def _has_quality_warnings(inputs: DroughtValidationInputs) -> bool:
    warning_flags = {
        "high_cloud_fraction",
        "low_clear_fraction",
        "no_index_stats",
        "too_few_valid_pixels",
    }
    return any(inputs.quality_flag_counts.get(flag, 0) > 0 for flag in warning_flags)


def _rejected_period_fraction(inputs: DroughtValidationInputs) -> float:
    if inputs.target_period_count == 0:
        return 0.0
    return inputs.rejected_period_count / inputs.target_period_count


def _assessment(
    classification: ValidationClassification,
    reasons: list[str],
    inputs: DroughtValidationInputs,
    thresholds: DroughtValidationThresholds,
) -> dict[str, object]:
    return {
        "classification": classification,
        "reasons": reasons,
        "thresholds": asdict(thresholds),
        "inputs": asdict(inputs),
    }
