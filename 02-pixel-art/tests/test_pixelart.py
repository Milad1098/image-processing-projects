"""Run: python -m tests.test_pixelart   (no test framework needed)"""

import numpy as np

from pixelart import PALETTES, pixelate
from pixelart.color import delta_e, lab_to_srgb, srgb_to_lab
from pixelart.dither import floyd_steinberg, ordered
from pixelart.quantize import assign, kmeans, map_to_palette, to_space


def floyd_steinberg_reference(rgb, palette, space="lab"):
    """The textbook row-by-row loop; the vectorized version must match it exactly."""
    h, w = rgb.shape[:2]
    work = to_space(rgb.reshape(-1, 3), space).reshape(h, w, 3)
    pal = to_space(palette, space)
    out = np.empty((h, w), np.intp)
    for y in range(h):
        for x in range(w):
            i = assign(work[y, x][None], pal)[0]
            out[y, x] = i
            err = work[y, x] - pal[i]
            for dy, dx, share in ((0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16)):
                if y + dy < h and 0 <= x + dx < w:
                    work[y + dy, x + dx] += err * share
    return palette[out]


def colors_in(img: np.ndarray) -> set[tuple]:
    return {tuple(c) for c in img.reshape(-1, 3)}


def main() -> None:
    # color conversion: reference values (D65) and round trip
    assert np.allclose(srgb_to_lab([255, 255, 255]), [100, 0, 0], atol=0.01)
    assert np.allclose(srgb_to_lab([255, 0, 0]), [53.24, 80.09, 67.20], atol=0.05)
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 256, (1000, 3))
    assert np.abs(lab_to_srgb(srgb_to_lab(rgb)) - rgb).max() < 1e-6
    assert abs(delta_e(srgb_to_lab([0, 0, 0]), srgb_to_lab([255, 255, 255])) - 100) < 0.01

    # k-means finds three well-separated blobs exactly
    true = np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0]], float)
    pts = np.vstack([c + rng.normal(0, 2, (200, 3)) for c in true])
    centers, labels = kmeans(pts, 3)
    assert np.abs(np.sort(centers, axis=0) - np.sort(true, axis=0)).max() < 1
    assert len(set(labels[:200])) == len(set(labels[200:400])) == len(set(labels[400:])) == 1
    # asking for more clusters than distinct colors must not crash
    assert len(kmeans(np.repeat([[1, 2, 3], [4, 5, 6]], 10, axis=0), 8)[0]) == 2

    # mapping uses palette colors only
    img = rng.integers(0, 256, (20, 30, 3)).astype(np.uint8)
    pal = PALETTES["pico8"]
    assert colors_in(map_to_palette(img, pal)) <= colors_in(pal)
    assert colors_in(ordered(img, pal)) <= colors_in(pal)

    # dithering: on a smooth gradient with 2 colors, Floyd-Steinberg keeps the local average
    # (blur-then-compare error far below plain mapping)
    ramp = np.repeat(np.linspace(0, 255, 64)[None, :, None], 16, axis=0).repeat(3, axis=2).astype(np.uint8)
    bw = PALETTES["grayscale4"][[0, 3]]
    plain, fs = map_to_palette(ramp, bw).astype(float), floyd_steinberg(ramp, bw).astype(float)
    def column_mean_error(x):
        return np.abs(x.mean(axis=0) - ramp.mean(axis=0)).mean()
    assert column_mean_error(fs) < column_mean_error(plain) / 3

    # wavefront Floyd-Steinberg == textbook loop, on a real-looking image and a learned palette
    photo_like = np.clip(rng.normal(128, 60, (37, 53, 3)), 0, 255).astype(np.uint8)
    for space in ("lab", "rgb"):
        assert np.array_equal(floyd_steinberg(photo_like, pal, space), floyd_steinberg_reference(photo_like, pal, space))

    # full pipeline: size, color count, determinism, fixed palette
    photo = rng.integers(0, 256, (120, 200, 3)).astype(np.uint8)
    art = pixelate(photo, width=40, colors=8)
    assert art.small.shape == (24, 40, 3) and len(colors_in(art.small)) <= 8
    assert np.array_equal(art.small, pixelate(photo, width=40, colors=8).small)
    assert art.upscaled(5).shape == (120, 200, 3)
    assert colors_in(pixelate(photo, 32, "gameboy", "bayer").small) <= colors_in(PALETTES["gameboy"])
    print("all checks passed")


if __name__ == "__main__":
    main()
