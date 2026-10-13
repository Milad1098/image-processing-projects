"""Fixed retro palettes, as uint8 RGB arrays."""

import numpy as np


def _hex(*codes: str) -> np.ndarray:
    return np.array([[int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in codes], np.uint8)


PALETTES = {
    # original Game Boy (DMG) LCD greens
    "gameboy": _hex("0F380F", "306230", "8BAC0F", "9BBC0F"),
    # PICO-8 fantasy console, 16 colors
    "pico8": _hex("000000", "1D2B53", "7E2553", "008751", "AB5236", "5F574F", "C2C3C7", "FFF1E8",
                  "FF004D", "FFA300", "FFEC27", "00E436", "29ADFF", "83769C", "FF77A8", "FFCCAA"),
    "grayscale4": _hex("000000", "555555", "AAAAAA", "FFFFFF"),
}

# single-hue palettes: colors differ only in lightness, so pixels are matched on lightness alone
TONAL = {"gameboy", "grayscale4"}
