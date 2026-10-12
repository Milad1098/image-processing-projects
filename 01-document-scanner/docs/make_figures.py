"""Regenerate the README / case-study figures from one photo.

    python docs/make_figures.py samples/notebook.jpg

Writes docs/images/{before-after,pipeline,filters}.jpg.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scanner import render, scan                    # noqa: E402
from scanner.watermark import stamp                  # noqa: E402

OUT = Path(__file__).resolve().parent / "images"
HEIGHT = 720
FONT = cv2.FONT_HERSHEY_SIMPLEX


def fit(img: np.ndarray) -> np.ndarray:
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    return cv2.resize(img, (round(img.shape[1] * HEIGHT / img.shape[0]), HEIGHT), interpolation=cv2.INTER_AREA)


def labeled(img: np.ndarray, text: str) -> np.ndarray:
    img = fit(img)
    bar = np.full((56, img.shape[1], 3), 20, np.uint8)
    cv2.putText(bar, text, (16, 38), FONT, 0.9, (235, 235, 235), 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def row(images: list[np.ndarray], gap: int = 16) -> np.ndarray:
    spacer = np.full((images[0].shape[0], gap, 3), 20, np.uint8)
    parts = [p for img in images for p in (img, spacer)][:-1]
    return np.hstack(parts)


def main(photo_path: Path) -> None:
    OUT.mkdir(exist_ok=True)
    photo = cv2.imread(str(photo_path))
    result = scan(photo)
    if not result.detected:
        sys.exit("page not detected; pick another photo")

    def final(mode: str) -> np.ndarray:
        return stamp(render(photo, result.corners, result.turns, mode))

    full_outline = photo.copy()
    pts = result.corners.astype(np.int32)
    cv2.polylines(full_outline, [pts], True, (60, 220, 60), max(3, photo.shape[0] // 300))

    figures = {
        "before-after": row([labeled(photo, "Phone photo"), labeled(final("magic"), "Scan")]),
        "pipeline": row([
            labeled(result.steps["edges"], "1. Edges"),
            labeled(full_outline, "2. Page found"),
            labeled(result.steps["cropped"], "3. Perspective fixed"),
            labeled(final("magic"), "4. Enhanced"),
        ]),
        "filters": row([labeled(final(m), name) for m, name in
                        [("original", "Original"), ("magic", "Magic color"), ("gray", "Grayscale"), ("bw", "Black & white")]]),
    }
    for name, img in figures.items():
        cv2.imwrite(str(OUT / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(OUT / f"{name}.jpg", img.shape[1], "x", img.shape[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
