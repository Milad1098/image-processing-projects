"""CLI: python -m scanner photo1.jpg [photo2.jpg ...] [--mode magic|gray|bw|original] [--pdf out.pdf] [--steps]"""

import argparse
from pathlib import Path

import cv2

from . import MODES, save_pdf, scan

OUTPUT_DIR = Path("output")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan photos of documents.")
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--mode", choices=MODES, default="magic")
    parser.add_argument("--pdf", type=Path, help="also combine all pages into this PDF")
    parser.add_argument("--steps", action="store_true", help="also save intermediate images")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    pages = []
    for path in args.inputs:
        image = cv2.imread(str(path))
        if image is None:
            parser.error(f"cannot read image: {path}")

        result = scan(image, args.mode)
        out = OUTPUT_DIR / f"{path.stem}_{args.mode}.png"
        cv2.imwrite(str(out), result.scan)
        pages.append(result.scan)

        if args.steps:
            for name, img in result.steps.items():
                cv2.imwrite(str(OUTPUT_DIR / f"{path.stem}_{name}.png"), img)

        status = "page detected" if result.detected else "no page found, used whole photo"
        print(f"{path.name}: {status}, rotated {result.turns * 90}° -> {out}")

    if args.pdf:
        print(f"PDF -> {save_pdf(pages, args.pdf)}")


if __name__ == "__main__":
    main()
