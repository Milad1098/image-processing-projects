# Architecture

## Two implementations of one pipeline

```
                       photo
                         │
        ┌────────────────┴─────────────────┐
  Python (bgremove/)                 Browser (web/app.js)
  benchmark, figures, CLI-free       the public app
        │                                  │
  preprocess  ── resize, normalize, NCHW ── preprocess
        │                                  │
  onnxruntime (CPU)              onnxruntime-web (WASM)
        │                                  │
  postprocess ─ scale to 0..1, resize ─── postprocess
        │                                  │
      matte  ═══ compared: IoU ≥ 0.999 ═══ matte
```

The Python side is the reference: every number in [RESULTS.md](RESULTS.md) comes from it.
The browser side mirrors it in JavaScript (no Pyodide this time: the heavy lifting is the
network, which ONNX Runtime Web runs natively), and the outputs were checked to match.

## `bgremove/`

| module | role |
|---|---|
| `models.py` | `ModelSpec` per network (input size, mean/std, output kind), `predict(name, rgb)` |
| `classic.py` | GrabCut baseline seeded with a centered rectangle |
| `metrics.py` | IoU, MAE, Boundary F |
| `compose.py` | RGBA cutout, background replacement |

A `ModelSpec` captures everything that differs between networks:

| model | input | normalization | output |
|---|---|---|---|
| U²-Net-P, Silueta | 320×320 | ÷ image max, ImageNet mean/std | min-max scaled |
| MODNet | short side 512, multiples of 32 | (x − 0.5) / 0.5 | already 0..1 |
| IS-Net | 1024×1024 | (x − 0.5) / 1 | min-max scaled |
| BiRefNet-lite | 1024×1024 | ImageNet mean/std | sigmoid |

Only one ONNX session is kept in memory (`lru_cache(maxsize=1)`): the large models need
several GB while running, and holding all five crashed with an out-of-memory error.

## Experiments

- `experiments/download.py`: models and test sets, skipped if present.
- `experiments/run.py`: fixed-seed sample per dataset, streamed from parquet in batches
  (loading a whole 280 MB file next to a model ran out of memory), images capped at
  1024 px. Per-image results are appended to `data/results.csv` as they are computed, so an
  interrupted run resumes where it stopped.
- `experiments/speed.py`: clean timing (warm-up, best of two fresh sessions, minimum of
  repeated runs), all cores and one thread.

## Browser app (`web/`)

```
mode click / photo ─► getSession(mode)
                        ├─ Cache Storage hit ─► bytes
                        └─ fetch from Hugging Face (pinned commit), progress bar ─► cache ─► bytes
                     ─► ort.InferenceSession (wasm, 1 thread unless cross-origin isolated)
photo ─► shrink to ≤ 2048 px ─► preprocess ─► session.run ─► postprocess ─► alpha (Uint8)
alpha + background choice ─► compose on <canvas> (transparent / white / color / blurred original)
download ─► compose again with a small credit line ─► PNG
```

- Models are fetched from Hugging Face (GitHub release assets send no CORS headers), pinned
  to a commit, and byte-identical (SHA-256) to the benchmarked files.
- Analytics: action events (never image data) to `BGREMOVE_CONFIG.endpoint` if set.

## Deployment

`web/publish.py <website>/frontend/public/tools/background-remover` copies the three static
files and injects a `<base href>` and the analytics endpoint. Nothing else is needed on the
server: the models come from Hugging Face, the runtime from jsDelivr.
