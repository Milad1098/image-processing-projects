"""Full scan: photo -> detect page -> crop -> upright -> enhance.

`render` is the deterministic part (used by the UI when the user edits corners,
rotation or mode); `scan` adds the automatic decisions on top of it.
"""

from dataclasses import dataclass, field

import numpy as np

from .detect import detect_corners, full_frame, warp
from .enhance import MODES, upscale
from .orient import auto_rotation, rotate


@dataclass
class ScanResult:
    scan: np.ndarray                         # final enhanced page
    corners: np.ndarray                      # 4x2 corners in photo coords
    detected: bool                           # False -> corners are the full frame fallback
    turns: int                               # 90° clockwise turns applied
    steps: dict[str, np.ndarray] = field(default_factory=dict)  # intermediate images, for demos


def render(image: np.ndarray, corners: np.ndarray, turns: int = 0, mode: str = "magic") -> np.ndarray:
    page = rotate(upscale(warp(image, corners)), turns)
    return MODES[mode](page)


def scan(image: np.ndarray, mode: str = "magic") -> ScanResult:
    steps: dict[str, np.ndarray] = {}
    corners = detect_corners(image, steps)
    detected = corners is not None
    if not detected:
        corners = full_frame(image)

    page = warp(image, corners)
    turns = auto_rotation(page)
    steps["cropped"] = page
    return ScanResult(render(image, corners, turns, mode), corners, detected, turns, steps)
