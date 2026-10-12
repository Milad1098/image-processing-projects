"""Detect whether a page is lying on its side, from the direction of its text lines."""

import cv2
import numpy as np


def is_sideways(page: np.ndarray) -> bool:
    """True if text lines run vertically.

    Horizontal text makes the row-ink profile alternate sharply (line, gap, line...),
    while the column profile stays flat. Whichever axis alternates more is across the lines.
    """
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY) if page.ndim == 3 else page
    gray = cv2.resize(gray, (600, 600))
    ink = cv2.adaptiveThreshold(gray, 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    ink = ink[30:-30, 30:-30]               # ignore borders
    rows, cols = ink.sum(axis=1), ink.sum(axis=0)
    return cols.std() > 1.2 * rows.std()    # ponytail: tells 0° from 90°, not 90° from 270°; UI has rotate buttons


def auto_rotation(page: np.ndarray) -> int:
    """Number of 90° clockwise turns to make text horizontal (0 or 1).

    Sideways phone shots usually come out rotated counter-clockwise, so one clockwise turn fixes them.
    """
    return 1 if is_sideways(page) else 0


def rotate(img: np.ndarray, turns: int) -> np.ndarray:
    """Rotate by turns × 90° clockwise."""
    return np.rot90(img, -(turns % 4)).copy()
