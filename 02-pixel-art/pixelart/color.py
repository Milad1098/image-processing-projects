"""sRGB <-> CIELAB (D65) and color difference.

Distances in RGB do not match how different two colors *look*; in CIELAB they
roughly do. Clustering and palette matching therefore work in Lab.
All functions take and return float arrays shaped (..., 3).
"""

import numpy as np

# sRGB (linear) -> XYZ, D65 white point
_RGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_XYZ_TO_RGB = np.linalg.inv(_RGB_TO_XYZ)
_WHITE = np.array([0.95047, 1.0, 1.08883])
_EPS, _KAPPA = 216 / 24389, 24389 / 27


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """rgb in [0, 255] -> Lab (L in [0, 100])."""
    c = np.asarray(rgb, np.float64) / 255
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = linear @ _RGB_TO_XYZ.T / _WHITE
    f = np.where(xyz > _EPS, np.cbrt(xyz), (_KAPPA * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Lab -> rgb in [0, 255] (float, clipped to the sRGB gamut)."""
    lab = np.asarray(lab, np.float64)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], axis=-1)
    xyz = np.where(f ** 3 > _EPS, f ** 3, (116 * f - 16) / _KAPPA) * _WHITE
    linear = np.clip(xyz @ _XYZ_TO_RGB.T, 0, 1)
    c = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    return c * 255


def delta_e(lab_a: np.ndarray, lab_b: np.ndarray) -> np.ndarray:
    """CIE76 color difference. ~2.3 is a just-noticeable difference."""
    return np.linalg.norm(np.asarray(lab_a) - np.asarray(lab_b), axis=-1)
