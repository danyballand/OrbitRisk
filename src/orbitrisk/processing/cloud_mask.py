from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# Sentinel-2 L2A Scene Classification Layer classes.
SCL_NO_DATA = 0
SCL_SATURATED_DEFECTIVE = 1
SCL_DARK_AREA_PIXELS = 2
SCL_CLOUD_SHADOWS = 3
SCL_VEGETATION = 4
SCL_NOT_VEGETATED = 5
SCL_WATER = 6
SCL_UNCLASSIFIED = 7
SCL_CLOUD_MEDIUM_PROBABILITY = 8
SCL_CLOUD_HIGH_PROBABILITY = 9
SCL_THIN_CIRRUS = 10
SCL_SNOW_OR_ICE = 11


@dataclass(frozen=True)
class MaskSummary:
    valid: int
    cloud: int
    shadow: int
    snow: int
    rejected: int

    @property
    def total(self) -> int:
        return self.valid + self.rejected

    @property
    def clear_fraction(self) -> float:
        return self.valid / self.total if self.total else 0.0


def build_scl_valid_mask(
    scl: NDArray[np.integer],
    *,
    exclude_classes: set[int] | None = None,
) -> NDArray[np.bool_]:
    excluded = exclude_classes or {
        SCL_NO_DATA,
        SCL_SATURATED_DEFECTIVE,
        SCL_CLOUD_SHADOWS,
        SCL_UNCLASSIFIED,
        SCL_CLOUD_MEDIUM_PROBABILITY,
        SCL_CLOUD_HIGH_PROBABILITY,
        SCL_THIN_CIRRUS,
        SCL_SNOW_OR_ICE,
    }
    return ~np.isin(scl, list(excluded))


def summarize_scl_mask(scl: NDArray[np.integer], valid_mask: NDArray[np.bool_]) -> MaskSummary:
    cloud = int(
        np.isin(
            scl,
            [SCL_CLOUD_MEDIUM_PROBABILITY, SCL_CLOUD_HIGH_PROBABILITY, SCL_THIN_CIRRUS],
        ).sum()
    )
    shadow = int((scl == SCL_CLOUD_SHADOWS).sum())
    snow = int((scl == SCL_SNOW_OR_ICE).sum())
    valid = int(valid_mask.sum())
    rejected = int(scl.size - valid)
    return MaskSummary(valid=valid, cloud=cloud, shadow=shadow, snow=snow, rejected=rejected)
