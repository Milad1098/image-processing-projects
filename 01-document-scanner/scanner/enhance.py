"""Scan filters, like CamScanner's modes: magic color, grayscale, black & white."""

import cv2
import numpy as np

TARGET_LONG_SIDE = 2000    # ~A4 at 170 DPI: enough detail for crisp text, still small files


def upscale(page: np.ndarray) -> np.ndarray:
    """Enlarge small crops so text strokes survive sharpening and thresholding."""
    factor = TARGET_LONG_SIDE / max(page.shape[:2])
    if factor <= 1:
        return page
    return cv2.resize(page, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def flatten(channel: np.ndarray) -> np.ndarray:
    """Divide out uneven lighting and shadows; paper becomes white.

    Background = the page with ink erased: a morphological closing (computed on a small
    copy, for speed) wipes out strokes thinner than the kernel, then a blur smooths it.
    """
    h, w = channel.shape
    small = cv2.resize(channel, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    background = cv2.GaussianBlur(cv2.morphologyEx(small, cv2.MORPH_CLOSE, kernel), (0, 0), 5)
    background = cv2.resize(background, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.divide(channel, background, scale=255)


def sharpen(img: np.ndarray, amount: float = 0.8) -> np.ndarray:
    """Unsharp mask: boost edges so handwriting and print look crisper."""
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def levels(img: np.ndarray, white: int = 215) -> np.ndarray:
    """Map the darkest ink to black and everything above `white` to pure paper white.

    After `flatten` paper sits near 255 with faint grain and JPEG blocks below it;
    clipping at `white` erases them, and stretching the rest darkens faint ink.
    """
    black = min(np.percentile(img, 1), white - 1)
    out = (img.astype(np.float32) - black) * 255 / (white - black)
    return np.clip(out, 0, 255).astype(np.uint8)


def magic_color(page: np.ndarray) -> np.ndarray:
    """White paper, vivid ink, colors kept: the default 'scan' look."""
    flat = cv2.merge([flatten(c) for c in cv2.split(page)])
    return levels(sharpen(flat))


def grayscale(page: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    return levels(sharpen(flatten(gray)))


def black_white(page: np.ndarray) -> np.ndarray:
    """Pure black text on pure white, with isolated specks removed."""
    gray = flatten(cv2.cvtColor(page, cv2.COLOR_BGR2GRAY))
    block = max(gray.shape) // 80 | 1
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 15)

    # drop tiny ink blobs (sensor noise, paper grain) but keep dots of letters
    n, labels, stats, _ = cv2.connectedComponentsWithStats(255 - bw, connectivity=8)
    min_area = max(gray.shape) // 250
    specks = np.where(stats[:, cv2.CC_STAT_AREA] < min_area)[0]
    bw[np.isin(labels, specks[specks > 0])] = 255
    return bw


MODES = {
    "magic": magic_color,
    "gray": grayscale,
    "bw": black_white,
    "original": lambda page: page,
}
