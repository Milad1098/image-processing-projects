"""Regenerate the README / case-study figures (scikit-image public-domain images).

    python docs/make_figures.py

Writes docs/images/{hero,lab-vs-rgb,dithering,palettes,tone-fit}.png.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from skimage import data

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pixelart import pixelate                     # noqa: E402

OUT = Path(__file__).resolve().parent / "images"
BG = (20, 20, 20)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def labeled(img: np.ndarray, text: str, height: int) -> np.ndarray:
    """Resize to `height` (nearest, so pixel art stays crisp) and add a caption bar."""
    w = round(img.shape[1] * height / img.shape[0])
    img = cv2.resize(img, (w, height), interpolation=cv2.INTER_NEAREST if img.shape[0] < height / 2 else cv2.INTER_AREA)
    bar = np.full((44, w, 3), BG, np.uint8)
    cv2.putText(bar, text, (12, 30), FONT, 0.7, (235, 235, 235), 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def grid(rows: list[list[np.ndarray]], gap: int = 12) -> np.ndarray:
    def hrow(items):
        sp = np.full((items[0].shape[0], gap, 3), BG, np.uint8)
        return np.hstack([p for it in items for p in (it, sp)][:-1])
    built = [hrow(r) for r in rows]
    width = max(r.shape[1] for r in built)
    built = [np.pad(r, ((0, 0), (0, width - r.shape[1]), (0, 0)), constant_values=BG[0]) for r in built]
    sp = np.full((gap, width, 3), BG, np.uint8)
    return np.vstack([p for r in built for p in (r, sp)][:-1])


def save(name: str, rgb: np.ndarray) -> None:
    path = OUT / f"{name}.png"
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(path, rgb.shape[1], "x", rgb.shape[0])


def main() -> None:
    OUT.mkdir(exist_ok=True)
    astronaut, coffee, chelsea, rocket = data.astronaut(), data.coffee(), data.chelsea(), data.rocket()

    save("hero", grid([[labeled(img, "Photo", 300), labeled(pixelate(img, 64, 16).small, "64 px, 16 colors", 300)]
                       for img in (astronaut, chelsea)]))

    save("lab-vs-rgb", grid([[labeled(pixelate(img, 64, 8, space=s).small, f"8 colors, clustered in {s.upper()}", 360)
                              for s in ("rgb", "lab")] for img in (astronaut, coffee)]))

    crop = coffee[60:300, 150:450]       # the cup: smooth gradients show banding best
    save("dithering", grid([[labeled(pixelate(crop, 80, 6, dither=d).small, f"6 colors, {d}", 300)
                             for d in ("none", "floyd-steinberg", "bayer")]]))

    save("palettes", grid([[labeled(pixelate(rocket, 96, p, dither="bayer").small, name, 260)
                            for p, name in (("gameboy", "Game Boy (4)"), ("pico8", "PICO-8 (16)"), (16, "Learned (16)"))]]))

    save("tone-fit", grid([[labeled(pixelate(rocket, 96, "gameboy", tone_fit=fit).small, title, 300)
                            for fit, title in ((False, "Game Boy, direct match"), (True, "Game Boy, tone-fitted"))]]))


if __name__ == "__main__":
    main()
