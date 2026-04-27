import numpy as np

from orbitrisk.processing.indices import ndmi, ndvi, normalized_difference


def test_normalized_difference_handles_zero_denominator() -> None:
    left = np.array([1.0, 0.0], dtype=np.float32)
    right = np.array([0.0, 0.0], dtype=np.float32)

    result = normalized_difference(left, right)

    assert np.isclose(result[0], 1.0)
    assert np.isnan(result[1])


def test_ndvi_uses_nir_minus_red() -> None:
    red = np.array([0.2], dtype=np.float32)
    nir = np.array([0.6], dtype=np.float32)

    result = ndvi(red, nir)

    assert np.isclose(result[0], 0.5)


def test_ndmi_uses_nir_minus_swir() -> None:
    nir = np.array([0.5], dtype=np.float32)
    swir = np.array([0.2], dtype=np.float32)

    result = ndmi(nir, swir)

    assert np.isclose(result[0], 0.42857143)
