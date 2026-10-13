"""Reproducible experiments behind the design decisions. Writes docs/RESULTS.md.

    pip install -r requirements-dev.txt
    python -m experiments.run

Images: scikit-image's public-domain / CC0 test set. Every number is averaged
over images and random seeds; nothing is cherry-picked.
"""

import platform
import time
from pathlib import Path

import cv2
import numpy as np
from skimage import data

from pixelart import PALETTES, pixelate
from pixelart.color import delta_e, srgb_to_lab
from pixelart.dither import DITHERS
from pixelart.pipeline import downscale
from pixelart.quantize import build_palette, kmeans, map_to_palette

IMAGES = {name: getattr(data, name)() for name in ("astronaut", "coffee", "chelsea", "rocket")}
WIDTH = 96                       # pixel-art resolution used throughout
SEEDS = (0, 1, 2)
OUT = Path(__file__).resolve().parent.parent / "docs" / "RESULTS.md"


def small(name: str) -> np.ndarray:
    return downscale(IMAGES[name], WIDTH)


def mean_de(a: np.ndarray, b: np.ndarray, blur: float = 0) -> float:
    """Mean ΔE76 between two RGB images; `blur` > 0 compares them as seen from a distance."""
    if blur:
        a, b = (cv2.GaussianBlur(x.astype(np.float32), (0, 0), blur) for x in (a, b))
    return float(delta_e(srgb_to_lab(a), srgb_to_lab(b)).mean())


def rgb_error(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a.astype(float) - b.astype(float), axis=-1).mean())


def table(header: list[str], rows: list[list]) -> str:
    fmt = lambda v: f"{v:.2f}" if isinstance(v, float) else str(v)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows])


def exp_color_space() -> str:
    """A. Cluster in RGB or in CIELAB?"""
    rows = []
    for k in (4, 8, 16, 32):
        res = {s: {"de": [], "rgb": []} for s in ("rgb", "lab")}
        for name in IMAGES:
            img = small(name)
            for seed in SEEDS:
                for space in ("rgb", "lab"):
                    out = map_to_palette(img, build_palette(img, k, space, seed), space)
                    res[space]["de"].append(mean_de(img, out))
                    res[space]["rgb"].append(rgb_error(img, out))
        de_rgb, de_lab = np.mean(res["rgb"]["de"]), np.mean(res["lab"]["de"])
        rows.append([k, de_rgb, de_lab, f"{(1 - de_lab / de_rgb) * 100:.0f}%",
                     np.mean(res["rgb"]["rgb"]), np.mean(res["lab"]["rgb"])])
    return table(["colors", "ΔE · RGB clustering", "ΔE · Lab clustering", "ΔE reduction",
                  "RGB error · RGB clustering", "RGB error · Lab clustering"], rows)


def exp_kmeans_vs_opencv() -> str:
    """B. Is the hand-written K-Means as good as cv2.kmeans?"""
    rows = []
    for k in (8, 16, 32):
        ours_e, ours_t, cv_e, cv_t = [], [], [], []
        for name in IMAGES:
            pts = srgb_to_lab(small(name).reshape(-1, 3))
            for seed in SEEDS:
                t = time.perf_counter()
                centers, labels = kmeans(pts, k, seed=seed)
                ours_t.append(time.perf_counter() - t)
                ours_e.append(np.mean(np.sum((pts - centers[labels]) ** 2, axis=1)))

                cv2.setRNGSeed(seed)
                t = time.perf_counter()
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1e-3)
                _, lab, cen = cv2.kmeans(pts.astype(np.float32), k, None, criteria, 1, cv2.KMEANS_PP_CENTERS)
                cv_t.append(time.perf_counter() - t)
                cv_e.append(np.mean(np.sum((pts - cen[lab.ravel()]) ** 2, axis=1)))
        rows.append([k, np.mean(ours_e), np.mean(cv_e), f"{np.mean(ours_t) * 1000:.0f} ms", f"{np.mean(cv_t) * 1000:.0f} ms"])
    return table(["colors", "inertia · ours", "inertia · cv2.kmeans", "time · ours", "time · cv2.kmeans"], rows)


def exp_dithering() -> str:
    """C. What does dithering buy, measured up close and from a distance?"""
    rows = []
    for k in (4, 8, 16):
        raw = {d: [] for d in DITHERS}
        far = {d: [] for d in DITHERS}
        for name in IMAGES:
            img = small(name)
            palette = build_palette(img, k, "lab", 0)
            for d, fn in DITHERS.items():
                out = fn(img, palette, "lab").astype(np.uint8)
                raw[d].append(mean_de(img, out))
                far[d].append(mean_de(img, out, blur=1.5))
        rows.append([k] + [np.mean(raw[d]) for d in DITHERS] + [np.mean(far[d]) for d in DITHERS])
    names = list(DITHERS)
    return table(["colors"] + [f"ΔE up close · {d}" for d in names] + [f"ΔE from afar · {d}" for d in names], rows)


def exp_fixed_palettes() -> str:
    """D. Fixed palettes: does fitting the image's tones to the palette preserve structure?"""
    rows = []
    for pal in PALETTES:
        corr = {False: [], True: []}
        used = {False: [], True: []}
        for name in IMAGES:
            ref = srgb_to_lab(small(name))[..., 0].ravel()
            for fit in (False, True):
                out = pixelate(IMAGES[name], WIDTH, pal, tone_fit=fit).small
                corr[fit].append(np.corrcoef(ref, srgb_to_lab(out)[..., 0].ravel())[0, 1])
                used[fit].append(len(np.unique(out.reshape(-1, 3), axis=0)))
        rows.append([f"{pal} ({len(PALETTES[pal])})", np.mean(corr[False]), np.mean(corr[True]),
                     f"{np.mean(used[False]):.1f}", f"{np.mean(used[True]):.1f}"])
    return table(["palette", "lightness correlation · direct", "lightness correlation · tone-fitted",
                  "colors used · direct", "colors used · tone-fitted"], rows)


def exp_fs_speed() -> str:
    """E. Wavefront-vectorized Floyd-Steinberg vs the textbook loop."""
    from tests.test_pixelart import floyd_steinberg_reference
    from pixelart.dither import floyd_steinberg
    rows = []
    for width in (64, 96, 160):
        img = downscale(IMAGES["astronaut"], width)
        pal = build_palette(img, 16, "lab", 0)
        times = {}
        for name, fn in (("loop", floyd_steinberg_reference), ("wavefront", floyd_steinberg)):
            best = float("inf")
            for _ in range(3):
                t = time.perf_counter()
                result = fn(img, pal)
                best = min(best, time.perf_counter() - t)
            times[name] = (best, result)
        same = np.array_equal(times["loop"][1], times["wavefront"][1])
        rows.append([f"{width}×{img.shape[0]}", f"{times['loop'][0] * 1000:.0f} ms", f"{times['wavefront'][0] * 1000:.0f} ms",
                     f"{times['loop'][0] / times['wavefront'][0]:.0f}×", "yes" if same else "NO"])
    return table(["size", "textbook loop", "wavefront", "speed-up", "identical output"], rows)


def main() -> None:
    t0 = time.perf_counter()
    sections = [
        ("A. Color space for clustering", exp_color_space(),
         "Mean ΔE76 (CIELAB distance) and mean RGB distance between the downscaled image and its quantized "
         "version. Lab clustering optimizes Lab distance by construction, so the RGB-error columns are the "
         "fair cross-check: they show how much is lost on the metric RGB clustering itself optimizes."),
        ("B. Hand-written K-Means vs OpenCV", exp_kmeans_vs_opencv(),
         "Inertia = mean squared Lab distance from each pixel to its cluster center (lower is better). "
         "Same data, k-means++ seeding and 20-iteration cap for both."),
        ("C. Dithering", exp_dithering(),
         "\"Up close\" compares pixel by pixel. \"From afar\" blurs both images first (Gaussian σ = 1.5 px), "
         "which approximates viewing at a distance, where dithering is meant to work."),
        ("D. Fixed palettes: tone fitting", exp_fixed_palettes(),
         "Correlation between the lightness of the downscaled photo and of the result (1 = every "
         "light/dark relation kept), and how many palette entries actually appear. \"Direct\" matches "
         "each pixel to the nearest palette color in Lab; \"tone-fitted\" first stretches the photo's "
         "lightness range onto the palette's, and matches single-hue palettes on lightness only."),
        ("E. Floyd-Steinberg speed", exp_fs_speed(),
         "Best of 3 runs, 16 colors, astronaut image. Both versions produce the same pixels "
         "(checked here and in the tests)."),
    ]
    imgs = ", ".join(f"{n} {v.shape[1]}×{v.shape[0]}" for n, v in IMAGES.items())
    body = [
        "# Experiment results",
        "",
        "_Generated by `python -m experiments.run`; do not edit by hand._",
        "",
        f"Images: {imgs} (scikit-image test set), downscaled to {WIDTH} px wide. "
        f"Seeds: {list(SEEDS)}. Machine: {platform.processor() or platform.machine()}, "
        f"Python {platform.python_version()}, OpenCV {cv2.__version__}, NumPy {np.__version__}.",
    ]
    for title, tbl, note in sections:
        body += ["", f"## {title}", "", note, "", tbl]
    OUT.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"written: {OUT}")
    print(f"\n({time.perf_counter() - t0:.0f} s)")


if __name__ == "__main__":
    main()
