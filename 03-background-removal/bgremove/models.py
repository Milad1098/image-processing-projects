"""Background-removal networks behind one interface: photo in, alpha matte out.

Every model differs only in input size, color normalization and how its raw output
becomes a 0..1 matte, so each is described by a `ModelSpec` instead of its own code.
Weights are ONNX files in models/ (see models/README.md for sources and licenses).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
IMAGENET_MEAN, IMAGENET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class ModelSpec:
    file: str
    size: int | None             # square input side; None = keep aspect, multiple of 32 (MODNet)
    mean: tuple[float, float, float]
    std: tuple[float, float, float]
    output: str                  # "minmax" | "sigmoid" | "alpha": how raw output maps to 0..1
    divide_by_max: bool = False  # U²-Net family scales by the image's own max, not by 255
    license: str = ""


MODELS = {
    "u2netp": ModelSpec("u2netp.onnx", 320, IMAGENET_MEAN, IMAGENET_STD, "minmax", True, "Apache-2.0"),
    "silueta": ModelSpec("silueta.onnx", 320, IMAGENET_MEAN, IMAGENET_STD, "minmax", True, "Apache-2.0"),
    "modnet": ModelSpec("modnet.onnx", None, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), "alpha", False, "Apache-2.0"),
    "isnet": ModelSpec("isnet-general-use.onnx", 1024, (0.5, 0.5, 0.5), (1.0, 1.0, 1.0), "minmax", False, "Apache-2.0"),
    "birefnet-lite": ModelSpec("birefnet-lite.onnx", 1024, IMAGENET_MEAN, IMAGENET_STD, "sigmoid", False, "MIT"),
}
MODNET_REF = 512                 # MODNet's short side at inference, as in its reference code


# one model in memory at a time: the large ones need several GB while running
@lru_cache(maxsize=1)
def session(name: str) -> ort.InferenceSession:
    return ort.InferenceSession(str(MODELS_DIR / MODELS[name].file), providers=["CPUExecutionProvider"])


def input_size(spec: ModelSpec, h: int, w: int) -> tuple[int, int]:
    if spec.size:
        return spec.size, spec.size
    scale = MODNET_REF / min(h, w)
    return max(32, round(h * scale / 32) * 32), max(32, round(w * scale / 32) * 32)


def preprocess(rgb: np.ndarray, spec: ModelSpec) -> np.ndarray:
    ih, iw = input_size(spec, *rgb.shape[:2])
    x = cv2.resize(rgb, (iw, ih), interpolation=cv2.INTER_AREA).astype(np.float32)
    x /= max(x.max(), 1e-6) if spec.divide_by_max else 255.0
    x = (x - np.array(spec.mean, np.float32)) / np.array(spec.std, np.float32)
    return x.transpose(2, 0, 1)[None]          # HWC -> NCHW


def postprocess(raw: np.ndarray, spec: ModelSpec, h: int, w: int) -> np.ndarray:
    m = raw[0, 0].astype(np.float32)
    if spec.output == "sigmoid":
        m = 1 / (1 + np.exp(-m))
    elif spec.output == "minmax":
        m = (m - m.min()) / max(m.max() - m.min(), 1e-6)
    return np.clip(cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR), 0, 1)


def predict(name: str, rgb: np.ndarray) -> np.ndarray:
    """Alpha matte (float32, 0..1, same size as the photo) from network `name`."""
    spec = MODELS[name]
    sess = session(name)
    raw = sess.run(None, {sess.get_inputs()[0].name: preprocess(rgb, spec)})[0]
    return postprocess(raw, spec, *rgb.shape[:2])
