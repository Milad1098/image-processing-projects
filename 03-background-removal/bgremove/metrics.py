"""How close a predicted matte is to the ground truth.

- IoU: overlap of the binarized masks (|A∩B| / |A∪B|). The standard "did it find the object".
- MAE: mean absolute difference of the soft mattes, in 0..1. Also rewards soft edges (hair).
- Boundary F: precision/recall of the mask *outline* within a few pixels. IoU is dominated
  by the object's interior; this is the number that moves when edges get better or worse.
"""

import cv2
import numpy as np


def iou(pred: np.ndarray, gt: np.ndarray, threshold: float = 0.5) -> float:
    p, g = pred >= threshold, gt >= threshold
    union = np.logical_or(p, g).sum()
    return float(np.logical_and(p, g).sum() / union) if union else 1.0


def mae(pred: np.ndarray, gt: np.ndarray) -> float:
    return float(np.abs(pred.astype(np.float32) - gt.astype(np.float32)).mean())


def _outline(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8)
    return m - cv2.erode(m, np.ones((3, 3), np.uint8))


def boundary_f(pred: np.ndarray, gt: np.ndarray, threshold: float = 0.5, tolerance: float = 0.0075) -> float:
    """F-measure of outlines matched within `tolerance` × image diagonal (≈ 5 px at 640×480)."""
    p, g = _outline(pred >= threshold), _outline(gt >= threshold)
    if not p.any() and not g.any():
        return 1.0
    if not p.any() or not g.any():
        return 0.0
    radius = max(1, round(tolerance * np.hypot(*gt.shape)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    precision = (p & cv2.dilate(g, disk)).sum() / p.sum()
    recall = (g & cv2.dilate(p, disk)).sum() / g.sum()
    return float(2 * precision * recall / (precision + recall)) if precision + recall else 0.0
