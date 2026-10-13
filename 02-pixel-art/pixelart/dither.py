"""Dithering: trade spatial resolution for apparent color depth.

With few colors, smooth gradients turn into flat bands. Dithering mixes nearby
palette colors in a pattern so that, seen from a distance, the average matches
the original color.
"""

import numpy as np

from .quantize import assign, map_to_palette, to_space

# 4x4 Bayer matrix, normalized to thresholds in [-0.5, 0.5)
_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 - 0.5


# Floyd-Steinberg error weights: (dy, dx, share of the error)
_FS_KERNEL = ((0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16))


def floyd_steinberg(rgb: np.ndarray, palette: np.ndarray, space: str = "lab") -> np.ndarray:
    """Error diffusion: each pixel's quantization error is pushed onto its unvisited neighbours.

    Pixel (y, x) only depends on (y, x-1) and the three pixels above it, so every pixel on
    the skewed line x + 2y = t depends only on lines < t. Processing one such "wavefront"
    at a time vectorizes the scan: w + 2h NumPy steps instead of w * h Python steps, with
    the same result as the classic row-by-row loop (tests compare against it).
    """
    h, w = rgb.shape[:2]
    work = to_space(rgb.reshape(-1, 3), space).reshape(h, w, 3)
    pal = to_space(palette, space)
    out = np.empty((h, w), np.intp)

    ys, xs = np.indices((h, w)).reshape(2, -1)
    order = np.argsort(xs + 2 * ys, kind="stable")
    bounds = np.cumsum(np.bincount(xs + 2 * ys))
    for front in np.split(order, bounds[:-1]):
        y, x = ys[front], xs[front]
        i = assign(work[y, x], pal)
        out[y, x] = i
        err = work[y, x] - pal[i]
        for dy, dx, share in _FS_KERNEL:
            ny, nx = y + dy, x + dx
            ok = (ny < h) & (nx >= 0) & (nx < w)
            # two pixels of one front can hit the same neighbour; add.at accumulates both
            np.add.at(work, (ny[ok], nx[ok]), err[ok] * share)
    return palette[out]


def palette_spacing(palette: np.ndarray) -> float:
    """Median distance (RGB) from each palette color to its nearest neighbour."""
    p = palette.astype(np.float64)
    d = np.linalg.norm(p[:, None] - p[None, :], axis=2)
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(axis=1)))


def ordered(rgb: np.ndarray, palette: np.ndarray, space: str = "lab") -> np.ndarray:
    """Bayer dithering: a fixed threshold pattern nudges each pixel before matching.

    Fully vectorized and gives the regular cross-hatch texture of classic 8-bit art.
    The nudge range equals the typical gap between palette colors: enough to tip a pixel
    to the neighbouring color, never so much that it jumps past it (a fixed range was
    measured to make 16-color results worse than no dithering; docs/CASE-STUDY.md).
    """
    h, w = rgb.shape[:2]
    threshold = np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w, None]
    nudged = np.clip(rgb.astype(np.float64) + threshold * palette_spacing(palette), 0, 255)
    return map_to_palette(nudged, palette, space)


DITHERS = {
    "none": lambda rgb, palette, space: map_to_palette(rgb, palette, space),
    "floyd-steinberg": floyd_steinberg,
    "bayer": ordered,
}
