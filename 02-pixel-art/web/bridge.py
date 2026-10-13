"""Browser glue: called from app.js through Pyodide. Holds the current photo."""

import cv2
import numpy as np
from js import Object
from pyodide.ffi import to_js

from pixelart import pixelate

CREDIT = "miladmobaseri.ir"
_photo: np.ndarray | None = None
_art = None


def load(rgba, width: int, height: int) -> None:
    global _photo
    _photo = np.frombuffer(rgba.to_py(), np.uint8).reshape(height, width, 4)[..., :3].copy()


def process(width: int, colors, dither: str, space: str):
    """Pixel art at its true size (one pixel per block) as PNG bytes, plus the palette as hex."""
    global _art
    _art = pixelate(_photo, int(width), colors if isinstance(colors, str) else int(colors), dither, space)
    _, png = cv2.imencode(".png", cv2.cvtColor(_art.small, cv2.COLOR_RGB2BGR))
    used = np.unique(_art.small.reshape(-1, 3), axis=0)
    return to_js({"png": png.tobytes(), "colors": ["#%02x%02x%02x" % tuple(c) for c in used]},
                 dict_converter=Object.fromEntries)


def download(target: int = 1024):
    """Upscaled PNG (hard-edged blocks, ~`target` px wide) with a small creator credit underneath."""
    scale = max(1, target // _art.small.shape[1])
    big = _art.upscaled(scale)
    bar = np.full((max(18, scale * 2), big.shape[1], 3), 20, np.uint8)
    cv2.putText(bar, CREDIT, (6, bar.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, bar.shape[0] / 40, (150, 150, 150), 1, cv2.LINE_AA)
    _, png = cv2.imencode(".png", cv2.cvtColor(np.vstack([big, bar]), cv2.COLOR_RGB2BGR))
    return to_js(png.tobytes())
