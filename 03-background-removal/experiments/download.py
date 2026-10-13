"""Download the model weights and the two test sets used by experiments/run.py.

    python -m experiments.download

Files are skipped if already present. Nothing here is committed to the repository:
weights belong to their authors (licenses in models/README.md) and the test sets are
used for evaluation only.
"""

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMBG = "https://github.com/danielgatis/rembg/releases/download/v0.0.0"
HF = "https://huggingface.co"

FILES = {
    "models/u2netp.onnx": f"{REMBG}/u2netp.onnx",
    "models/silueta.onnx": f"{REMBG}/silueta.onnx",
    "models/isnet-general-use.onnx": f"{REMBG}/isnet-general-use.onnx",
    "models/modnet.onnx": f"{HF}/Xenova/modnet/resolve/main/onnx/model.onnx",
    "models/birefnet-lite.onnx": f"{HF}/onnx-community/BiRefNet_lite-ONNX/resolve/main/onnx/model.onnx",
    "data/duts-te.parquet": f"{HF}/datasets/nobg/DUTS/resolve/main/data/test-00000-of-00001.parquet",
    "data/p3m-500-np.parquet": f"{HF}/datasets/nobg/P3M-10K/resolve/main/data/P3M_500_NP-00000-of-00001.parquet",
}
MIN_BYTES = 1_000_000   # an error page is a few bytes; a real file is megabytes


def main() -> None:
    for rel, url in FILES.items():
        path = ROOT / rel
        if path.exists() and path.stat().st_size > MIN_BYTES:
            print(f"have  {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetch {rel} ...", flush=True)
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        if tmp.stat().st_size < MIN_BYTES:
            tmp.unlink()
            raise SystemExit(f"{rel}: server returned an error page, try again later")
        tmp.replace(path)


if __name__ == "__main__":
    main()
