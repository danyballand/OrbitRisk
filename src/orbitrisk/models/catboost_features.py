from dataclasses import dataclass


@dataclass(frozen=True)
class DroughtFeatureRow:
    ndvi_ema: float
    ndmi_ema: float
    ndmi_anomaly_z: float
    valid_pixel_count: int
    cloud_pct: float
    day_of_year: int


def to_feature_vector(row: DroughtFeatureRow) -> list[float]:
    return [
        row.ndvi_ema,
        row.ndmi_ema,
        row.ndmi_anomaly_z,
        float(row.valid_pixel_count),
        row.cloud_pct,
        float(row.day_of_year),
    ]
