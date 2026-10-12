"""Find the page in a photo and crop it to a flat rectangle."""

import cv2
import numpy as np

WORK_HEIGHT = 500          # detection runs on a downscaled copy for speed and stability
MIN_AREA_RATIO = 0.2       # a valid page covers at least 20% of the photo
TRIM_RATIO = 0.01          # shave the warped border so no background slivers survive
PAPER_MAX_SAT = 45         # paper is nearly colorless (HSV saturation, 0-255)
MIN_FILL_RATIO = 0.85      # color blob must fill this much of its quadrilateral to count as a page


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Return corners as top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()        # y - x
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]])


def full_frame(image: np.ndarray, inset: float = 0.08) -> np.ndarray:
    """Fallback corners when no page is found: slightly inside the photo so the handles are easy to grab."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = w * inset, h * inset, w * (1 - inset), h * (1 - inset)
    return np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def _by_edges(small: np.ndarray, steps: dict | None) -> np.ndarray | None:
    """Largest 4-sided contour in the edge map: works when the whole page outline is visible."""
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))  # close small gaps in the page outline
    if steps is not None:
        steps["edges"] = edges

    # RETR_LIST also returns the inner side of the page outline, which stays a clean
    # quadrilateral even when background clutter touches the page and merges into its outer side
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    min_area = MIN_AREA_RATIO * small.shape[0] * small.shape[1]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < min_area:
            break
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            return order_corners(approx)
    return None


def _by_color(small: np.ndarray) -> np.ndarray | None:
    """Largest bright, colorless region: works for curved pages, notebooks and pages cut by the frame."""
    hsv = cv2.cvtColor(cv2.GaussianBlur(small, (7, 7), 0), cv2.COLOR_BGR2HSV)
    sat, val = hsv[..., 1], hsv[..., 2]
    mask = ((sat < PAPER_MAX_SAT) & (val > np.percentile(val, 40))).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))   # fill ink and ruled lines
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))    # cut thin bridges to the background

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        return None
    biggest = 1 + stats[1:, cv2.CC_STAT_AREA].argmax()
    area = stats[biggest, cv2.CC_STAT_AREA]
    if not MIN_AREA_RATIO < area / mask.size < 0.95:
        return None

    blob = (labels == biggest).astype(np.uint8)
    hull = cv2.convexHull(cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0])
    for eps in np.linspace(0.02, 0.12, 11):    # loosen until the hull reduces to 4 corners
        approx = cv2.approxPolyDP(hull, eps * cv2.arcLength(hull, True), True)
        if len(approx) <= 4:
            break
    # a real page fills its quadrilateral; a light tablecloth blob does not
    if len(approx) != 4 or area / cv2.contourArea(approx) < MIN_FILL_RATIO:
        return None
    return order_corners(approx)


def detect_corners(image: np.ndarray, steps: dict | None = None) -> np.ndarray | None:
    """Page corners in photo coordinates, or None. Tries the edge method, then the color method."""
    scale = WORK_HEIGHT / image.shape[0]
    small = cv2.resize(image, None, fx=scale, fy=scale)
    corners = _by_edges(small, steps)
    if corners is None:
        corners = _by_color(small)
    if steps is not None:
        steps["detected"] = draw_corners(small, corners)
    return None if corners is None else corners / scale


def draw_corners(image: np.ndarray, corners: np.ndarray | None) -> np.ndarray:
    """Overlay the page outline and corner handles."""
    out = image.copy()
    if corners is None:
        return out
    thickness = max(2, image.shape[0] // 250)
    pts = corners.astype(np.int32)
    cv2.polylines(out, [pts], True, (0, 220, 0), thickness)
    for x, y in pts:
        cv2.circle(out, (int(x), int(y)), thickness * 4, (0, 140, 255), -1)
    return out


def warp(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Map the four corners onto an upright rectangle and trim its border."""
    tl, tr, br, bl = corners
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    target = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    matrix = cv2.getPerspectiveTransform(corners.astype(np.float32), target)
    page = cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_CUBIC)
    m = int(TRIM_RATIO * min(width, height))
    return page[m:height - m, m:width - m]
