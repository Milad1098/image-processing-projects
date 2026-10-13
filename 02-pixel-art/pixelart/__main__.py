"""CLI: python -m pixelart photo.jpg [--width 64] [--colors 16 | --palette pico8] [--dither bayer] [--scale 8]"""

import argparse
from pathlib import Path

import cv2

from . import DITHERS, PALETTES, pixelate


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn a photo into pixel art.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="default: output/<name>_pixel.png")
    parser.add_argument("--width", type=int, default=64, help="pixels across (default 64)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--colors", type=int, default=16, help="palette size learned from the image")
    group.add_argument("--palette", choices=PALETTES, help="use a fixed retro palette instead")
    parser.add_argument("--dither", choices=DITHERS, default="none")
    parser.add_argument("--space", choices=["lab", "rgb"], default="lab")
    parser.add_argument("--scale", type=int, default=8, help="upscale factor for the saved image")
    args = parser.parse_args()

    bgr = cv2.imread(str(args.input))
    if bgr is None:
        parser.error(f"cannot read image: {args.input}")
    art = pixelate(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), args.width, args.palette or args.colors, args.dither, args.space)

    out = args.output or Path("output") / f"{args.input.stem}_pixel.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), cv2.cvtColor(art.upscaled(args.scale), cv2.COLOR_RGB2BGR))
    h, w = art.small.shape[:2]
    print(f"{w}x{h} pixels, {len(art.palette)} colors -> {out}")


if __name__ == "__main__":
    main()
