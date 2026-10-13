"""Edge refinement for low-resolution mattes.

Networks predict the matte at 320-512 px; upscaled to a large photo its edges become wide
and soft, and the background shows through the faint semi-transparent band as a halo.

- `tighten` (shipped): stretch the matte so faint values become 0 and near-opaque become 1.
- `guided_filter` (evaluated and rejected, kept for experiments/refine.py): rebuilds the matte
  as a local linear function of the photo's brightness (He et al., 2010). On busy backgrounds
  it copies background edges into the matte; see docs/CASE-STUDY.md, finding 6.
"""

import cv2
import numpy as np

TIGHTEN = (0.2, 0.8)   # matte values mapped to 0 and 1 (tuned in experiments/refine.py)
RADIUS = 0.01          # guided filter window radius, fraction of the longer side
EPS = 1e-3             # guided filter regularization


def _box(x: np.ndarray, r: int) -> np.ndarray:
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


def guided_filter(guide: np.ndarray, src: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Gray-guide guided filter. guide, src: float32 in 0..1, same shape."""
    mean_i, mean_p = _box(guide, r), _box(src, r)
    var_i = _box(guide * guide, r) - mean_i * mean_i
    cov_ip = _box(guide * src, r) - mean_i * mean_p
    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    return _box(a, r) * guide + _box(b, r)


def tighten(alpha: np.ndarray, low: float = TIGHTEN[0], high: float = TIGHTEN[1]) -> np.ndarray:
    """Values below `low` become transparent, above `high` opaque; the band between is stretched."""
    return np.clip((alpha - low) / (high - low), 0, 1)


def guided(rgb: np.ndarray, alpha: np.ndarray, radius: float = RADIUS, eps: float = EPS) -> np.ndarray:
    """Guided-filter refinement of the matte (rejected, see module docstring)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    r = max(1, round(radius * max(rgb.shape[:2])))
    return np.clip(guided_filter(gray, alpha.astype(np.float32), r, eps), 0, 1)
