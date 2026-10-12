"""Browser glue: called from app.js through Pyodide. Holds the current photo and PDF pages."""

import cv2
import numpy as np
from pyodide.ffi import to_js
from js import Object

from scanner import render, save_pdf, scan
from scanner.watermark import stamp

_photo: np.ndarray | None = None
_pages: list[np.ndarray] = []
_current: np.ndarray | None = None


def _js(value):
    return to_js(value, dict_converter=Object.fromEntries)


def load(rgba, width: int, height: int):
    """Receive the photo as RGBA pixels, auto-detect the page."""
    global _photo
    pixels = np.frombuffer(rgba.to_py(), np.uint8).reshape(height, width, 4)
    _photo = cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)
    result = scan(_photo)
    return _js({"corners": result.corners.tolist(), "detected": result.detected, "turns": result.turns})


def process(corners, turns: int, mode: str):
    """Render the scan with the user's corners/rotation/filter; return it as PNG bytes."""
    global _current
    _current = stamp(render(_photo, np.float32(corners.to_py()), turns, mode))
    _, png = cv2.imencode(".png", _current)
    return to_js(png.tobytes())


def add_page() -> int:
    _pages.append(_current)
    return len(_pages)


def remove_page(index: int) -> int:
    _pages.pop(index)
    return len(_pages)


def pdf():
    save_pdf(_pages, "/tmp/scan.pdf")
    with open("/tmp/scan.pdf", "rb") as f:
        return to_js(f.read())
