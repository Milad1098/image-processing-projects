"""Turn a matte into something usable: a transparent cutout or a new background."""

import numpy as np


def cutout(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """RGBA image with the matte as the alpha channel."""
    return np.dstack([rgb, np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)])


def replace_background(rgb: np.ndarray, alpha: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    a = alpha[..., None].astype(np.float32)
    return (rgb * a + np.array(color, np.float32) * (1 - a) + 0.5).astype(np.uint8)
