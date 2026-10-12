"""Creator credit stamped on every exported page."""

import cv2
import numpy as np

CREDIT = "Scanned with miladmobaseri.ir"
FONT = cv2.FONT_HERSHEY_SIMPLEX


def stamp(page: np.ndarray, text: str = CREDIT) -> np.ndarray:
    """Small grey credit in the bottom-right corner, sized relative to the page."""
    out = page.copy()
    h, w = out.shape[:2]
    scale = w / 2200
    thickness = max(1, round(scale * 2))
    (tw, _), _ = cv2.getTextSize(text, FONT, scale, thickness)
    origin = (w - tw - w // 50, h - h // 60)
    color = 130 if out.ndim == 2 else (130, 130, 130)
    cv2.putText(out, text, origin, FONT, scale, color, thickness, cv2.LINE_AA)
    return out
