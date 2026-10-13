"""Color quantization: pick k representative colors, then map every pixel to one.

K-Means is implemented here directly (k-means++ seeding + Lloyd iterations,
vectorized with NumPy) so each step is visible and testable; experiments/
compares it against cv2.kmeans.
"""

import numpy as np

from .color import lab_to_srgb, srgb_to_lab


def kmeans(points: np.ndarray, k: int, iters: int = 20, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Cluster (n, d) points into k groups. Returns (centers (k, d), labels (n,))."""
    rng = np.random.default_rng(seed)
    points = np.asarray(points, np.float64)
    k = min(k, len(np.unique(points, axis=0)))      # can't have more clusters than distinct colors

    # greedy k-means++: each new center is drawn with probability ∝ squared distance to the
    # nearest existing one (spreads centers out); drawing a few candidates and keeping the one
    # that lowers the total distance most avoids unlucky draws (same scheme as OpenCV/sklearn)
    trials = 2 + int(np.log(k))
    centers = [points[rng.integers(len(points))]]
    nearest = np.sum((points - centers[0]) ** 2, axis=1)
    for _ in range(1, k):
        candidates = points[rng.choice(len(points), size=trials, p=nearest / nearest.sum())]
        options = np.minimum(nearest[None, :], ((points[None, :, :] - candidates[:, None, :]) ** 2).sum(axis=2))
        best = options.sum(axis=1).argmin()
        centers.append(candidates[best])
        nearest = options[best]
    centers = np.array(centers)

    for _ in range(iters):
        labels = assign(points, centers)
        moved = np.array([points[labels == i].mean(axis=0) if np.any(labels == i) else centers[i] for i in range(k)])
        if np.allclose(moved, centers, atol=1e-3):
            break
        centers = moved
    return centers, assign(points, centers)


def assign(points: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Index of the nearest center for each point (squared Euclidean distance)."""
    d = (np.sum(points ** 2, axis=1)[:, None] - 2 * points @ centers.T + np.sum(centers ** 2, axis=1)[None, :])
    return d.argmin(axis=1)


def to_space(rgb: np.ndarray, space: str) -> np.ndarray:
    """Working space for distances: "lab", "rgb", or "lightness" (Lab with a = b = 0, for
    single-hue palettes where only how light a pixel is should decide its color)."""
    if space == "rgb":
        return np.asarray(rgb, np.float64)
    lab = srgb_to_lab(rgb)
    return lab * [1, 0, 0] if space == "lightness" else lab


def from_space(values: np.ndarray, space: str) -> np.ndarray:
    return lab_to_srgb(values) if space == "lab" else np.asarray(values, np.float64)


PALETTE_SAMPLE = 4096   # pixels used to learn a palette; measured: same ΔE (±2%), 5-8x faster at 160 px


def build_palette(rgb: np.ndarray, k: int, space: str = "lab", seed: int = 0) -> np.ndarray:
    """k colors (uint8 RGB) that best represent the image, clustered in `space`.

    Learned from a fixed-seed random sample of the pixels: a palette is a summary of the
    color distribution, and 4096 samples describe that distribution as well as all of them.
    """
    pixels = to_space(rgb.reshape(-1, 3), space)
    if len(pixels) > PALETTE_SAMPLE:
        pixels = pixels[np.random.default_rng(seed).choice(len(pixels), PALETTE_SAMPLE, replace=False)]
    centers, _ = kmeans(pixels, k, seed=seed)
    return np.clip(np.rint(from_space(centers, space)), 0, 255).astype(np.uint8)


def map_to_palette(rgb: np.ndarray, palette: np.ndarray, space: str = "lab") -> np.ndarray:
    """Replace every pixel with its perceptually nearest palette color."""
    labels = assign(to_space(rgb.reshape(-1, 3), space), to_space(palette, space))
    return palette[labels].reshape(rgb.shape)


def fit_tones(rgb: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Stretch the image's lightness range (1st-99th percentile) onto the palette's.

    A fixed palette spans its own range of lightness; a dark photo matched to it directly
    collapses onto the darkest entries.
    """
    lab = srgb_to_lab(rgb)
    lo, hi = np.percentile(lab[..., 0], (1, 99))
    p_light = srgb_to_lab(palette)[:, 0]
    lab[..., 0] = np.interp(lab[..., 0], (lo, max(hi, lo + 1e-6)), (p_light.min(), p_light.max()))
    return np.clip(lab_to_srgb(lab), 0, 255)
