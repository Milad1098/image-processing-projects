"""Photo -> pixel art: downscale, choose a palette, map colors (optionally dithered), upscale."""

from dataclasses import dataclass

import cv2
import numpy as np

from .dither import DITHERS
from .palettes import PALETTES, TONAL
from .quantize import build_palette, fit_tones

DOWNSCALE = {"area": cv2.INTER_AREA, "nearest": cv2.INTER_NEAREST}


@dataclass
class PixelArt:
    small: np.ndarray       # the actual pixel art, one value per "big pixel" (uint8 RGB)
    palette: np.ndarray     # colors used (uint8 RGB, (k, 3))

    def upscaled(self, scale: int) -> np.ndarray:
        """Blow each pixel up to a scale×scale block, keeping hard edges."""
        return np.repeat(np.repeat(self.small, scale, axis=0), scale, axis=1)


def downscale(rgb: np.ndarray, width: int, method: str = "area") -> np.ndarray:
    """Shrink to `width` pixels across, keeping the aspect ratio."""
    h, w = rgb.shape[:2]
    height = max(1, round(h * width / w))
    return cv2.resize(rgb, (width, height), interpolation=DOWNSCALE[method])


def pixelate(rgb: np.ndarray, width: int = 64, colors: int | str = 16, dither: str = "none",
             space: str = "lab", method: str = "area", seed: int = 0, tone_fit: bool = True) -> PixelArt:
    """`colors` is a number (palette learned from the image) or the name of a fixed palette.

    Fixed palettes get the image's tones fitted to them first; single-hue ones are matched
    on lightness only (`tone_fit=False` disables both, for experiments).
    """
    small = downscale(rgb, width, method)
    if isinstance(colors, str):
        palette = PALETTES[colors]
        if tone_fit:
            small = fit_tones(small, palette)
            space = "lightness" if colors in TONAL else space
    else:
        palette = build_palette(small, colors, space, seed)
    return PixelArt(DITHERS[dither](small, palette, space).astype(np.uint8), palette)
