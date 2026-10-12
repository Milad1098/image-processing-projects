# Architecture

## One algorithm, three front-ends

```
                 ┌──────────────── scanner/ (pure Python + OpenCV) ───────────────┐
                 │ detect.py → orient.py → enhance.py → watermark.py → export.py  │
                 │                 pipeline.py: scan() / render()                 │
                 └────────▲───────────────────▲──────────────────────▲────────────┘
                          │                   │                      │
              web/bridge.py (Pyodide)    app.py (Gradio)      __main__.py (CLI)
                          │
              web/app.js + index.html  ◄── the public app, runs in the browser
```

`scanner/` has no UI code and no I/O beyond the PDF writer, so the same files run
unchanged in CPython (CLI, Gradio, tests) and in Pyodide (browser).

## `scan()` vs `render()`

- `scan(image, mode)` makes the **automatic decisions**: find the corners (or fall
  back), decide whether the page is sideways, then render.
- `render(image, corners, turns, mode)` is **deterministic**: crop, upscale, rotate,
  filter. The UI calls it again whenever the user drags a corner, rotates, or
  switches filters, without repeating detection.

## Detection

```
photo ─► downscale to 500 px tall
          ├─► edges: Canny → dilate → contours (RETR_LIST) → largest 4-gon ≥ 20% of frame
          └─► (if none) color: HSV mask (S < 45, V > p40) → close → open → largest blob
                         → convex hull → approxPolyDP (ε loosened until 4 points)
                         → accept only if blob fills ≥ 85% of the quad
          └─► (if none) fallback corners 8% inside the frame
corners ×(1/scale) ─► original resolution
```

Detection runs on a small copy for speed and stability; the crop uses the
full-resolution photo.

## Enhancement

| Filter | Steps |
|---|---|
| Magic color | per channel: flatten → sharpen → levels |
| Grayscale | gray → flatten → sharpen → levels |
| Black & white | gray → flatten → adaptive threshold → remove connected components smaller than the speck size |
| Original | the cropped page as is |

`flatten` divides by a background estimate (morphological closing on a 4× smaller
copy, then blur and upscale). Kernel and block sizes scale with the page, so results
do not depend on photo resolution. Pages are upscaled to ~2000 px on the long side
first, so thin strokes survive sharpening and thresholding.

## Browser app

```
file / drop ─► createImageBitmap ─► downscale to ≤ 2000 px (OffscreenCanvas)
           ─► RGBA bytes ─► bridge.load()    ─► scan() ─► corners, turns
           ─► bridge.process(corners, turns, mode) ─► PNG bytes ─► <img>
"Add page" ─► bridge.add_page()  ·  "Download PDF" ─► bridge.pdf() ─► Blob
```

- **Boot:** `loadPyodide()` → load `numpy`, `opencv-python`, `pillow` → fetch the
  `scanner/*.py` files and `bridge.py` into Pyodide's virtual filesystem → import.
- **State:** the photo and the PDF pages live in Python (`bridge.py`); the corners,
  rotation and filter live in JS and are passed on every render.
- **Interaction:** corners are dragged on a `<canvas>` with pointer events, so
  mouse and touch work alike. The render runs on `pointerup`, not on every move.
- **i18n:** `?lang=fa` switches the UI to Persian and RTL.
- **Analytics:** `track()` posts JSON events with `navigator.sendBeacon` to
  `SCANNER_CONFIG.endpoint` (if set). Events describe actions only, never images.

## Deployment

`web/publish.py` copies `web/` and `scanner/` into the website's static folder,
injecting a `<base href>` and the analytics endpoint. This repository stays the
single source of truth; the website holds a generated copy.
