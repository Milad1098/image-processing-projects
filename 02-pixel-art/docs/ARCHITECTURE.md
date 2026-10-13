# Architecture

## Layers

```
            ┌──────────── pixelart/ (NumPy + OpenCV, no UI) ────────────┐
            │ color.py ─► quantize.py ─► dither.py      palettes.py     │
            │                  pipeline.py: pixelate()                   │
            └──────▲────────────────▲───────────────────▲───────────────┘
                   │                │                   │
      web/bridge.py (Pyodide)   __main__.py (CLI)   experiments/run.py, tests/
                   │
      web/app.js + index.html ◄── public app, runs in the browser
```

The package has no I/O and no UI, so the same files run in CPython (CLI, tests,
experiments) and in Pyodide (browser). `opencv` is used only for resizing and PNG encoding;
the color science, clustering and dithering are NumPy.

## `pixelate(rgb, width, colors, dither, space)`

```
photo ─► downscale(width, INTER_AREA)
      ├─ colors = int  ─► build_palette: sample ≤ 4096 px ─► K-Means in Lab ─► k RGB colors
      └─ colors = name ─► fixed palette ─► fit_tones (lightness range → palette's range)
                                          └─ single-hue palette ⇒ match on lightness only
      ─► DITHERS[dither](small, palette, space) ─► uint8 RGB, one value per big pixel
PixelArt.upscaled(s) ─► np.repeat: hard-edged s×s blocks
```

## K-Means (`quantize.py`)

- **Seeding:** greedy k-means++. Each new center is drawn ∝ squared distance to the nearest
  chosen center; 2 + ln k candidates are drawn and the one lowering total distance most is
  kept.
- **Lloyd iterations:** vectorized assignment with
  ‖p − c‖² = ‖p‖² − 2p·c + ‖c‖² (one matrix product), mean update, stop when centers move
  less than 1e-3 or after 20 iterations.
- Asking for more clusters than distinct colors returns fewer clusters instead of failing.

## Floyd–Steinberg (`dither.py`)

Pixels are processed in **wavefronts** x + 2y = t. Every dependency of a pixel (left
neighbour, three above) lies on an earlier wavefront, so each wavefront is one vectorized
step. Error pushes from one wavefront can collide on the same neighbour; `np.add.at`
accumulates them. The result equals the textbook raster loop exactly (asserted in tests and
in experiment E).

## Browser app

```
file ─► createImageBitmap ─► shrink to ≤ 1024 px ─► RGBA bytes ─► bridge.load()
controls (on release) ─► bridge.process(width, colors, dither, space)
                     ─► { true-size PNG, used colors } ─► <img style="image-rendering: pixelated">
"Download" ─► bridge.download(): upscaled to ~1024 px + credit bar ─► PNG
```

- The preview is the **true-size** image scaled by CSS with `image-rendering: pixelated`,
  so changing settings never encodes a large image.
- Renders are coalesced: changes made while a render runs trigger exactly one more render.
- Packages loaded: `numpy`, `opencv-python` (no Pillow needed, unlike project 01).
- Analytics: `track()` posts action events (never image data) to
  `PIXELART_CONFIG.endpoint` if set.

## Deployment

`web/publish.py <website>/frontend/public/tools/pixel-art` copies `web/` and `pixelart/`,
injecting a `<base href>` and the analytics endpoint. This repository stays the source of
truth.
