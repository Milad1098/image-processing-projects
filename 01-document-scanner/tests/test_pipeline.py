"""Run: python -m tests.test_pipeline   (no test framework needed)"""

import tempfile
from pathlib import Path

import cv2
import numpy as np

from scanner import MODES, save_pdf, scan
from scanner.detect import order_corners
from scanner.orient import is_sideways, rotate

PAGE_CORNERS = np.float32([[170, 100], [440, 120], [460, 480], [150, 470]])


def synthetic_photo() -> tuple[np.ndarray, np.ndarray]:
    """A white 'page' with text lines, tilted in perspective on a dark desk."""
    page = np.full((400, 300, 3), 255, np.uint8)
    for y in range(60, 360, 40):
        cv2.line(page, (30, y), (270, y), (0, 0, 0), 4)
    m = cv2.getPerspectiveTransform(np.float32([[0, 0], [299, 0], [299, 399], [0, 399]]), PAGE_CORNERS)
    return cv2.warpPerspective(page, m, (640, 640), borderValue=(40, 40, 40)), PAGE_CORNERS


def main() -> None:
    shuffled = PAGE_CORNERS[[2, 0, 3, 1]]
    assert np.allclose(order_corners(shuffled), PAGE_CORNERS)

    # detection + crop
    photo, expected = synthetic_photo()
    result = scan(photo)
    assert result.detected and np.abs(result.corners - expected).max() < 12, result.corners
    h, w = result.scan.shape[:2]
    assert 1.1 < h / w < 1.6, (h, w)                      # page shape recovered (~4:3)

    # background clutter touching the page from outside must not break detection
    cluttered = photo.copy()
    cv2.circle(cluttered, (165, 280), 30, (90, 60, 200), 3)
    page_mask = np.zeros(photo.shape[:2], np.uint8)
    cv2.fillPoly(page_mask, [expected.astype(np.int32)], 255)
    cluttered[page_mask > 0] = photo[page_mask > 0]
    assert np.abs(scan(cluttered).corners - expected).max() < 12, "clutter broke detection"

    # page cut off by the frame on a light, colored background: no closed outline, found by paper color
    cut = np.full((640, 640, 3), (200, 170, 120), np.uint8)          # light blue cloth (BGR)
    cut[80:, 120:520] = 250                                           # white page running off the bottom
    for y in range(140, 640, 40):
        cv2.line(cut, (150, y), (490, y), (90, 40, 20), 3)
    cut_result = scan(cut)
    assert cut_result.detected, "page cut by the frame not found"
    assert np.abs(cut_result.corners - [[120, 80], [519, 80], [519, 639], [120, 639]]).max() < 15, cut_result.corners

    # orientation: upright page stays, sideways page gets one turn
    assert result.turns == 0
    sideways = rotate(photo, 1)
    assert is_sideways(scan(sideways).steps["cropped"])
    assert scan(sideways).scan.shape[0] > scan(sideways).scan.shape[1]  # back to portrait

    # filters
    bw = scan(photo, "bw").scan
    assert set(np.unique(bw)) <= {0, 255}
    magic = scan(photo, "magic").scan
    assert magic.ndim == 3 and np.median(magic) == 255     # paper is pure white
    assert set(MODES) == {"magic", "gray", "bw", "original"}

    # graceful fallback: no page -> whole frame
    blank = np.full((300, 300, 3), 40, np.uint8)
    assert not scan(blank).detected

    # multi-page PDF
    pdf = save_pdf([magic, bw], Path(tempfile.gettempdir()) / "test_scan.pdf")
    assert pdf.read_bytes().count(b"/Type /Page") - pdf.read_bytes().count(b"/Type /Pages") == 2
    print("all checks passed")


if __name__ == "__main__":
    main()
