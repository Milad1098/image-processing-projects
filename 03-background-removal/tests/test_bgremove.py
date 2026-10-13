"""Run: python -m tests.test_bgremove   (no test framework, no model download needed)"""

import numpy as np

from bgremove import cutout, grabcut, replace_background
from bgremove.metrics import boundary_f, iou, mae
from bgremove.models import MODELS, ModelSpec, input_size, postprocess, preprocess


def square(h, w, y0, y1, x0, x1):
    m = np.zeros((h, w), np.float32)
    m[y0:y1, x0:x1] = 1
    return m


def main() -> None:
    # metrics against hand-computed values
    a, b = square(100, 100, 0, 50, 0, 100), square(100, 100, 25, 75, 0, 100)
    assert iou(a, a) == 1 and iou(a, 1 - a) == 0
    assert abs(iou(a, b) - 2500 / 7500) < 1e-9                  # overlap 25 rows / union 75 rows
    assert abs(mae(a, b) - 0.5) < 1e-9                           # 50 of 100 rows differ by 1
    assert iou(np.zeros((5, 5)), np.zeros((5, 5))) == 1          # both empty: perfect agreement
    big = square(200, 200, 50, 150, 50, 150)
    assert boundary_f(big, big) == 1
    assert boundary_f(big, square(200, 200, 51, 151, 51, 151)) == 1   # 1 px shift is within tolerance
    assert boundary_f(big, square(200, 200, 80, 120, 80, 120)) < 0.1  # different outline

    # preprocessing: shape, layout and normalization follow each spec
    rgb = np.full((300, 500, 3), 255, np.uint8)
    for name, spec in MODELS.items():
        x = preprocess(rgb, spec)
        h, w = input_size(spec, 300, 500)
        assert x.shape == (1, 3, h, w) and x.dtype == np.float32, name
        expected = (1 - np.array(spec.mean)) / np.array(spec.std)    # white pixel after normalization
        assert np.allclose(x[0, :, 0, 0], expected, atol=1e-5), name
    assert input_size(MODELS["modnet"], 300, 500) == (512, 864)        # short side 512, multiples of 32

    # postprocessing: each output kind becomes a 0..1 matte at the photo's size
    raw = np.linspace(-6, 6, 64 * 64, dtype=np.float32).reshape(1, 1, 64, 64)
    for kind in ("sigmoid", "minmax", "alpha"):
        spec = ModelSpec("x", 64, (0, 0, 0), (1, 1, 1), kind)
        m = postprocess(raw if kind != "alpha" else (raw + 6) / 12, spec, 30, 50)
        assert m.shape == (30, 50) and m.min() >= 0 and m.max() <= 1, kind
        assert m[0, 0] < 0.1 and m[-1, -1] > 0.9, kind

    # GrabCut baseline finds a clear subject on a plain, contrasting background
    photo = np.full((240, 320, 3), (40, 120, 200), np.uint8)
    photo[60:180, 100:220] = (230, 60, 30)
    assert iou(grabcut(photo), square(240, 320, 60, 180, 100, 220)) > 0.9

    # composition
    alpha = square(10, 10, 0, 5, 0, 10)
    rgba = cutout(np.full((10, 10, 3), 7, np.uint8), alpha)
    assert rgba.shape == (10, 10, 4) and rgba[0, 0, 3] == 255 and rgba[9, 9, 3] == 0
    out = replace_background(np.full((10, 10, 3), 7, np.uint8), alpha, (255, 255, 255))
    assert (out[0, 0] == 7).all() and (out[9, 9] == 255).all()
    print("all checks passed")


if __name__ == "__main__":
    main()
