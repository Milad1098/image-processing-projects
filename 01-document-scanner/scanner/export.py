"""Save scans as a (multi-page) PDF."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

PDF_DPI = 170              # matches enhance.TARGET_LONG_SIDE, so a page prints at ~A4 size


def save_pdf(pages: list[np.ndarray], path: Path) -> Path:
    images = [Image.fromarray(p if p.ndim == 2 else cv2.cvtColor(p, cv2.COLOR_BGR2RGB)).convert("RGB")
              for p in pages]
    images[0].save(path, save_all=True, append_images=images[1:], resolution=PDF_DPI,
                   title="Scanned document", author="Milad Mobaseri", creator="miladmobaseri.ir")
    return path
