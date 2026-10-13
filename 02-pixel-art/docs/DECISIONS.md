# Design decisions

Where a choice was measured, the entry points to the experiment in [RESULTS.md](RESULTS.md).

### Implement K-Means instead of calling `cv2.kmeans`
The goal was to understand and control the algorithm, not just use it. Writing it exposed
the seeding detail that made the first version 1–3% worse, which a black box would have
hidden. It is now within 2% of OpenCV (experiment B). The 15× speed gap is irrelevant after
palette sampling.

### CIELAB for clustering and matching
−9 to −11% perceptual error (experiment A) and, visibly, small saturated details survive.
RGB stays selectable in the app for comparison.

### Learn the palette from 4,096 sampled pixels
Same ΔE within ±2%, 5–8× faster at 160 px. A palette describes a color distribution; a
fixed-seed sample describes it as well and keeps results deterministic.

### Two dithering methods, both kept
Floyd–Steinberg is the most accurate from a distance (−19% at 16 colors); Bayer is weaker
but gives the regular cross-hatch look people associate with 8-bit art, and is fully
vectorized. They are different aesthetics, not a better and a worse option.

### Bayer strength = median gap between palette colors
A fixed strength was measured to make 16-color output worse than no dithering
(experiment C, case study §3). Deriving it from the palette works at every size.

### Tone fitting for fixed palettes; lightness-only matching for single-hue ones
A fixed palette has its own lightness range; without fitting, dark photos collapse onto the
darkest entry. Structure correlation 0.69 → 0.87 on Game Boy (experiment D).

### Wavefront Floyd–Steinberg instead of a compiled extension
11× faster at 160 px with identical output, in pure NumPy, so it also runs in Pyodide.
A C/Numba version would be faster still but would not run in the browser.

### Area downscaling
Each output pixel is the average of the block it covers, which is what a pixel *means*
when shrinking. Nearest-neighbour downscaling samples one source pixel per block and
aliases fine textures into noise.

### ΔE76 as the metric
The simplest perceptual distance and the one K-Means minimizes in Lab, so metric and
objective agree. CIEDE2000 is more accurate for saturated colors; noted in the roadmap.

### Public-domain test images only
scikit-image's set (NASA, CC0). Every figure is publishable and every number can be
reproduced by anyone with `pip install -r requirements-dev.txt`.
