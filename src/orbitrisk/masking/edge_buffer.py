from shapely.geometry.base import BaseGeometry


def apply_negative_buffer(geometry: BaseGeometry, buffer_m: float) -> BaseGeometry:
    """Shrink an AOI to reduce mixed edge pixels.

    The caller must pass a projected geometry whose units are meters.
    """
    if buffer_m <= 0:
        return geometry
    buffered = geometry.buffer(-buffer_m)
    if buffered.is_empty:
        return geometry
    return buffered
