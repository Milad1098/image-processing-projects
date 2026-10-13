# Design decisions

### Two public test sets, not one
Objects (DUTS-TE) and portraits (P3M-500) crowned different winners
([case study](CASE-STUDY.md#finding-2-the-best-model-depends-on-the-photo)). One set would
have produced a confident, wrong recommendation for half the use cases.

### Three metrics
IoU alone hides edge quality, the part users notice first (hair, fingers). Boundary F
measures the outline; MAE measures soft transparency.

### GrabCut as the baseline
It is the strongest automatic method without learning available in OpenCV, so it shows
what deep learning adds, in numbers.

### Open licenses only
Five Apache-2.0/MIT models. BRIA RMBG, a popular choice, is non-commercial and was left out.

### MODNet for people, U²-Net-P for objects in the browser
Chosen from the 1-thread speed and the download size, not from the top of the accuracy
table. BiRefNet is the most accurate on portraits but 15 s per image on one thread and 224 MB.
IS-Net is the most accurate on objects but 179 MB and 3.5 s. The object mode's lower accuracy
is stated on the page.

### ONNX Runtime Web instead of Pyodide
Projects 01–02 ran Python in the browser. Here the work is a neural network, which ONNX
Runtime Web runs directly; shipping a Python runtime would add ~10 MB and seconds of start-up
for a few lines of pre/post-processing. Those lines were ported to JavaScript and the outputs
checked against Python (IoU ≥ 0.999).

### Models from Hugging Face, pinned to a commit
Hugging Face sends CORS headers (GitHub release assets do not), so the browser can fetch the
files directly and the website serves nothing heavy. Pinning to a commit and checking the
SHA-256 against the benchmarked file means the app can never silently switch models.

### Cache Storage for models
A visitor on a slow connection downloads each model once; later visits load it from disk.

### Minimum time, not median, for speed
Other processes can only slow a run down. After two rounds of inconsistent medians, the
minimum over repeated runs (after warm-up) gave stable, correctly ordered numbers.

### Edge tightening instead of a guided filter
The guided filter is the textbook refinement but raised MAE by 16–33% and copied background
edges into the matte on busy backgrounds. Clamping the matte (below 0.2 → 0, above 0.8 → 1)
removed the halo and cut MAE by 11–12% on portraits, for free. Its cost: very fine hair loses
partial transparency.

### MODNet at its training resolution
Feeding it 768 or 1024 px instead of 512 lowered every metric. Networks are run at the scale
they were trained on.

### Evaluation data and weights are never committed
Neither belongs to this project. `experiments/download.py` fetches them; results are
reproducible without redistributing anything.
