# Case study: which background-removal model, for whom, on what device?

**Goal:** remove the background from a photo in the browser, with no upload, and choose
the model with evidence instead of by reputation.

**What changed since the earlier projects:**
[01](../../01-document-scanner/docs/CASE-STUDY.md) tuned classic computer vision by eye;
[02](../../02-pixel-art/docs/CASE-STUDY.md) backed every decision with experiments on a
few images. This project is the first with **deep learning**, and the first measured on
**public benchmark datasets with ground truth**: five neural networks and one classic
baseline, three metrics, two kinds of photos, and speed measured the way the target
device would run it.

---

## Setup

**Methods.** GrabCut (OpenCV's graph-cut segmentation, no learning) and five open-licensed
networks from 5 MB to 224 MB: U²-Net-P, Silueta, MODNet, IS-Net, BiRefNet-lite
([sources and licenses](../models/README.md)). One non-commercial model (BRIA RMBG) was
excluded on license grounds.

**Data.** 100 random images (fixed seed) from each of two test sets, used for evaluation
only:
- **DUTS-TE**: everyday objects with hand-drawn masks ("can it cut out *anything*?")
- **P3M-500-NP**: portraits with precise alpha mattes ("does a profile photo come out clean?")

**Metrics.**
- **IoU**: overlap between predicted and true mask, i.e. "did it find the subject?"
- **MAE**: average error of the *soft* matte, which also rewards correct partial transparency (hair).
- **Boundary F**: how well the outline matches within ~0.75% of the image diagonal.
  IoU is dominated by the subject's interior, so a model can score a high IoU with ragged
  edges; this metric is the one that sees edges.

All numbers: [RESULTS.md](RESULTS.md), reproducible with `python -m experiments.run`.

## Finding 1: deep learning vs. the classic method

| | GrabCut | smallest network (U²-Net-P, 5 MB) |
|---|---|---|
| IoU, objects | 0.39 | 0.74 |
| IoU, portraits | 0.59 | 0.94 |
| time (all cores) | 1,700 ms | 101 ms |

Without a user drawing hints, GrabCut only knows "the border is background" and fails on
most real photos. The smallest network roughly doubles object accuracy while running 17×
faster. Even the network chosen for its tiny size beats the classic method by a wide margin
here.

## Finding 2: "the best model" depends on the photo

<p align="center"><img src="images/methods.png" alt="All six methods on a portrait (top) and a cat (bottom)"></p>

| model | size | IoU objects | IoU portraits | Boundary F portraits |
|---|---|---|---|---|
| U²-Net-P | 5 MB | 0.738 | 0.941 | 0.875 |
| Silueta | 44 MB | 0.744 | 0.948 | 0.901 |
| MODNet | 26 MB | **0.274** | 0.970 | 0.952 |
| IS-Net | 179 MB | **0.942** | 0.941 | 0.883 |
| BiRefNet-lite | 224 MB | 0.818 | **0.992** | **0.989** |

- **No model wins both columns.** IS-Net is clearly best on objects and only average on
  portraits; BiRefNet is nearly perfect on portraits and behind IS-Net on objects.
- **MODNet is a specialist.** It is trained only on people: on portraits it is second only
  to a model 9× its size, on objects it scores below the classic baseline. In the figure it
  tears the cat apart.
- **A caveat I can't rule out:** IS-Net's object score is much higher than its portrait
  score, which fits a model trained on data similar to DUTS. I could not verify its exact
  training mix, so the object column should be read as "IS-Net is strong on this kind of
  image", not as a clean generalization result.

The lesson for picking a model: **evaluate on the photos your users will actually bring.**
A single leaderboard number would have picked the wrong model for one of the two cases.

## Finding 3: accuracy has a price, and the price is paid on the user's device

<p align="center"><img src="images/tradeoff.png" alt="Portrait IoU against model size"></p>

| model | size | all cores | **1 thread** |
|---|---|---|---|
| U²-Net-P | 5 MB | 101 ms | 530 ms |
| MODNet | 26 MB | 151 ms | 605 ms |
| Silueta | 44 MB | 370 ms | 1,302 ms |
| IS-Net | 179 MB | 583 ms | 3,501 ms |
| BiRefNet-lite | 224 MB | 4,730 ms | **15,371 ms** |

A browser page runs WebAssembly on **one thread** unless the site is cross-origin isolated,
and a phone is slower than this laptop, so the 1-thread column is the realistic one. On top
of that, the model is a download: 224 MB is several minutes on a slow mobile connection.
BiRefNet's extra 0.02 IoU on portraits costs 25× the time and 9× the download of MODNet.

**Decision for the web app:**
- **Person** mode (default): **MODNet**, 26 MB. 0.970 IoU, 0.6 s on one thread.
- **Object** mode: **U²-Net-P**, 5 MB. Only 0.74 IoU on objects; the accurate general
  models are 179–224 MB, too heavy for a phone browser. The page says so.

Each model downloads only when its mode is first used and is then kept in the browser's
Cache Storage, so a returning visitor downloads nothing.

## Finding 4: my first speed numbers were wrong, twice

Speed was first recorded during the accuracy run. The results made no sense: U²-Net-P, a
smaller version of Silueta, came out slower than Silueta, and repeat measurements disagreed
by up to 4×.

1. **Cold start.** The first model measured after the program started ran ~5× slower; the
   CPU had not reached full clock yet. Re-measured on its own, U²-Net-P took 108–118 ms,
   not 610 ms.
2. **Background noise.** With other programs running, the 1-thread BiRefNet time varied
   between 18 s and 57 s, and MODNet looked faster on one thread than on all cores.

**Fix** (a separate script, [`experiments/speed.py`](../experiments/speed.py)): one fixed
photo, two warm-up runs, each model measured twice with a fresh session, and the **minimum**
time reported. Interference only ever adds time, so the minimum is the cleanest estimate of
what the model costs. After that the numbers were consistent and ordered as expected. The
noisy timings were removed from the accuracy tables rather than reported next to clean ones.

## Finding 5: the browser computes the same thing

The web app does not run Python. ONNX Runtime Web runs the network, and the preprocessing
(resize, normalization, NCHW layout) and postprocessing (output scaling, resize back) are
re-implemented in JavaScript. Any difference there would silently invalidate every number
above. So the same images were run through both versions and compared:

| | IoU (JS vs Python) | mean abs. difference |
|---|---|---|
| MODNet, portrait | 1.0000 | 0.0003 |
| U²-Net-P, object | 0.9993 | 0.0006 |

The remaining difference is the browser's image resampling vs OpenCV's. In Chrome on this
laptop, one image took ~1.3 s (MODNet) and ~1.5 s (U²-Net-P), slower than native
1-thread inference, which is what WebAssembly costs. WebGPU is the next step
([roadmap](ROADMAP.md)).

---

## Takeaways

- **Benchmark on your users' photos.** The two test sets crowned different winners.
- **Report what a metric can't see.** IoU near 0.94 hid edge quality differences that
  Boundary F exposed (0.875 vs 0.952 on portraits).
- **Choose for the device, not the leaderboard.** The best portrait model is unusable in a
  phone browser; the second best is 25× faster at 0.022 lower IoU.
- **Benchmark speed like an experiment:** warm up, repeat, and take the minimum, or the
  numbers describe the machine's state instead of the model.
- **Verify the port.** A re-implementation of pre/post-processing is a place for silent
  bugs; comparing outputs (IoU 0.9993–1.0) is what makes the benchmark apply to the app.
