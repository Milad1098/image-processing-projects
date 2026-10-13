"""Regenerate the README / case-study figures (scikit-image public-domain images).

    python docs/make_figures.py          # needs the models (python -m experiments.download)

Writes docs/images/{hero,methods,backgrounds,tradeoff}.png.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from skimage import data

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bgremove import MODELS, grabcut, predict, replace_background   # noqa: E402
from bgremove.refine import tighten                                  # noqa: E402

OUT = Path(__file__).resolve().parent / "images"
RESULTS = Path(__file__).resolve().parent.parent / "data" / "results.csv"
BG = (20, 20, 20)
FONT = cv2.FONT_HERSHEY_SIMPLEX
LABELS = {"grabcut": "GrabCut (classic)", "u2netp": "U2-Net-P  5 MB", "silueta": "Silueta  44 MB",
          "modnet": "MODNet  26 MB", "isnet": "IS-Net  179 MB", "birefnet-lite": "BiRefNet  224 MB"}


def checker(h: int, w: int, cell: int = 16) -> np.ndarray:
    yy, xx = np.mgrid[:h, :w]
    return np.where(((yy // cell + xx // cell) % 2)[..., None] == 0, 200, 235).astype(np.uint8).repeat(3, axis=2)


def on_checker(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = alpha[..., None]
    return (rgb * a + checker(*rgb.shape[:2]) * (1 - a)).astype(np.uint8)


def tile(img: np.ndarray, text: str, height: int = 300) -> np.ndarray:
    w = round(img.shape[1] * height / img.shape[0])
    img = cv2.resize(img, (w, height), interpolation=cv2.INTER_AREA)
    bar = np.full((40, w, 3), BG, np.uint8)
    cv2.putText(bar, text, (10, 27), FONT, 0.6, (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def grid(rows: list[list[np.ndarray]], gap: int = 10) -> np.ndarray:
    def hrow(items):
        sp = np.full((items[0].shape[0], gap, 3), BG, np.uint8)
        return np.hstack([p for it in items for p in (it, sp)][:-1])
    built = [hrow(r) for r in rows]
    width = max(r.shape[1] for r in built)
    built = [np.pad(r, ((0, 0), (0, width - r.shape[1]), (0, 0)), constant_values=BG[0]) for r in built]
    sp = np.full((gap, width, 3), BG, np.uint8)
    return np.vstack([p for r in built for p in (r, sp)][:-1])


def save(name: str, rgb: np.ndarray) -> None:
    cv2.imwrite(str(OUT / f"{name}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(OUT / f"{name}.png", rgb.shape[1], "x", rgb.shape[0])


def tradeoff_chart() -> np.ndarray:
    """Portrait IoU against model size, drawn with OpenCV (no plotting dependency)."""
    import csv
    import statistics
    rows = list(csv.DictReader(RESULTS.open()))
    w, h, pad = 900, 460, 70
    img = np.full((h, w, 3), BG, np.uint8)
    xmax, ylo = 240, 0.5
    px = lambda mb: int(pad + mb / xmax * (w - 2 * pad))
    py = lambda v: int(h - pad - (v - ylo) / (1 - ylo) * (h - 2 * pad))
    cv2.line(img, (pad, h - pad), (w - pad, h - pad), (120, 120, 120), 1)
    cv2.line(img, (pad, pad), (pad, h - pad), (120, 120, 120), 1)
    for v in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        cv2.putText(img, f"{v:.1f}", (18, py(v) + 5), FONT, 0.45, (160, 160, 160), 1, cv2.LINE_AA)
    for mb in (0, 50, 100, 150, 200):
        cv2.putText(img, f"{mb} MB", (px(mb) - 18, h - pad + 24), FONT, 0.45, (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(img, "Portrait IoU vs model size (P3M-500, 100 images)", (pad, 36), FONT, 0.65, (235, 235, 235), 1, cv2.LINE_AA)
    for method, label in LABELS.items():
        vals = [float(r["iou"]) for r in rows if r["method"] == method and r["dataset"].startswith("P3M")]
        size = 0 if method == "grabcut" else (Path(__file__).resolve().parent.parent / "models" / MODELS[method].file).stat().st_size / 1e6
        x, y = px(size), py(statistics.fmean(vals))
        color = (255, 77, 79) if method == "modnet" else (220, 220, 220)
        cv2.circle(img, (x, y), 7, color, -1, cv2.LINE_AA)
        dy = 24 if method == "u2netp" else -10          # below the dot: above it collides with MODNet
        cv2.putText(img, label.split("  ")[0], (x + 10, y + dy), FONT, 0.5, color, 1, cv2.LINE_AA)
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    portrait, cat = data.astronaut(), data.chelsea()
    methods = list(LABELS)
    mattes = {name: {m: grabcut(img) if m == "grabcut" else predict(m, img) for m in methods}
              for name, img in (("portrait", portrait), ("cat", cat))}

    app = tighten(mattes["portrait"]["modnet"])          # what the browser app shows (MODNet + tightening)
    save("hero", grid([[tile(portrait, "Photo"), tile(on_checker(portrait, app), "MODNet, in the browser")]]))
    save("methods", grid([[tile(on_checker(img, mattes[name][m]), LABELS[m], 220) for m in methods]
                          for name, img in (("portrait", portrait), ("cat", cat))]))
    alpha = app
    blurred = cv2.GaussianBlur(portrait, (0, 0), 8)
    save("backgrounds", grid([[tile(on_checker(portrait, alpha), "Transparent", 240),
                               tile(replace_background(portrait, alpha, (255, 255, 255)), "White", 240),
                               tile(replace_background(portrait, alpha, (255, 77, 79)), "Color", 240),
                               tile((portrait * alpha[..., None] + blurred * (1 - alpha[..., None])).astype(np.uint8), "Blur", 240)]]))
    save("tradeoff", tradeoff_chart())


if __name__ == "__main__":
    main()
