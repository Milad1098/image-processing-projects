"""Classic baseline without deep learning: GrabCut.

GrabCut models foreground and background colors with Gaussian mixtures and
separates them with a graph cut. It needs a hint; with no user input, the only
generic hint is "the subject is somewhere inside, the border is background".
"""

import cv2
import numpy as np

BORDER = 0.05      # outer 5% of the frame is assumed background
ITERATIONS = 5
WORK_SIDE = 512    # GrabCut is slow at full size; the mask is scaled back up


def grabcut(rgb: np.ndarray) -> np.ndarray:
    """Binary matte (float32, 0 or 1) from GrabCut seeded with a centered rectangle."""
    h, w = rgb.shape[:2]
    scale = min(1.0, WORK_SIDE / max(h, w))
    small = cv2.resize(rgb, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    rect = (round(sw * BORDER), round(sh * BORDER), round(sw * (1 - 2 * BORDER)), round(sh * (1 - 2 * BORDER)))
    mask = np.zeros((sh, sw), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, ITERATIONS, cv2.GC_INIT_WITH_RECT)
    fg = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.float32)
    return cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST)
