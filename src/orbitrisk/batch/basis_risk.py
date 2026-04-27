from dataclasses import asdict, dataclass
from typing import Literal

BasisRiskClassification = Literal["improved", "degraded", "ambiguous", "not_run"]


@dataclass(frozen=True)
class BasisRiskThresholds:
    min_crop_coverage_pct: float = 5.0
    min_non_crop_pixel_delta: int = 1
    max_valid_pixel_loss_pct: float = 75.0
    max_abs_ndmi_ema_delta: float = 0.15


@dataclass(frozen=True)
class BasisRiskInputs:
    vector_status: str | None
    crop_mask_coverage_pct: float | None
    crop_mask_median_valid_pixel_count: int | None
    min_valid_pixels: int | None
    non_crop_pixel_delta: int | None
    valid_pixel_delta_pct: float | None
    min_ndmi_ema_delta: float | None


DEFAULT_BASIS_RISK_THRESHOLDS = BasisRiskThresholds()


def classify_basis_risk(
    inputs: BasisRiskInputs,
    *,
    thresholds: BasisRiskThresholds = DEFAULT_BASIS_RISK_THRESHOLDS,
) -> dict[str, object]:
    """Classify whether crop masking improves basis-risk evidence for one AOI.

    This is intentionally conservative. A crop mask is only an improvement when it removes
    measurable non-crop pixels without destroying valid-pixel support or materially
    rewriting the NDMI signal.
    """
    if inputs.vector_status in {None, "skipped"}:
        return _assessment("not_run", ["missing_crop_mask"], inputs, thresholds)

    degraded_reasons = _degraded_reasons(inputs, thresholds)
    if degraded_reasons:
        return _assessment("degraded", degraded_reasons, inputs, thresholds)

    ambiguous_reasons = _ambiguous_reasons(inputs, thresholds)
    if ambiguous_reasons:
        return _assessment("ambiguous", ambiguous_reasons, inputs, thresholds)

    non_crop_delta = inputs.non_crop_pixel_delta
    if non_crop_delta is not None and non_crop_delta >= thresholds.min_non_crop_pixel_delta:
        return _assessment("improved", ["non_crop_pixels_removed"], inputs, thresholds)

    return _assessment("ambiguous", ["no_measurable_non_crop_delta"], inputs, thresholds)


def _degraded_reasons(
    inputs: BasisRiskInputs,
    thresholds: BasisRiskThresholds,
) -> list[str]:
    reasons: list[str] = []
    crop_coverage = inputs.crop_mask_coverage_pct
    if crop_coverage is None or crop_coverage <= 0:
        reasons.append("empty_crop_mask_coverage")
    elif crop_coverage < thresholds.min_crop_coverage_pct:
        reasons.append("low_crop_mask_coverage")

    valid_count = inputs.crop_mask_median_valid_pixel_count
    min_valid = inputs.min_valid_pixels
    if valid_count is not None and min_valid is not None and valid_count < min_valid:
        reasons.append("insufficient_crop_mask_valid_pixels")

    valid_delta_pct = inputs.valid_pixel_delta_pct
    if (
        valid_delta_pct is not None
        and valid_delta_pct < -thresholds.max_valid_pixel_loss_pct
    ):
        reasons.append("excessive_valid_pixel_loss")

    return reasons


def _ambiguous_reasons(
    inputs: BasisRiskInputs,
    thresholds: BasisRiskThresholds,
) -> list[str]:
    reasons: list[str] = []
    ndmi_delta = inputs.min_ndmi_ema_delta
    if ndmi_delta is not None and abs(ndmi_delta) > thresholds.max_abs_ndmi_ema_delta:
        reasons.append("large_ndmi_shift_requires_review")
    return reasons


def _assessment(
    classification: BasisRiskClassification,
    reasons: list[str],
    inputs: BasisRiskInputs,
    thresholds: BasisRiskThresholds,
) -> dict[str, object]:
    return {
        "classification": classification,
        "reasons": reasons,
        "thresholds": asdict(thresholds),
        "inputs": asdict(inputs),
    }
