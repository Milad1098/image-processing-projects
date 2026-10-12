# Design decisions

Short records of choices that are not obvious from the code.

### Classic computer vision, no neural network
A segmentation model would detect pages more robustly, but it adds tens of
megabytes to the download, hides *why* something fails, and teaches less. Every
step here can be inspected as an image ([Case study](CASE-STUDY.md) shows why that
mattered). A model stays an option for the cases heuristics cannot handle
([Roadmap](ROADMAP.md)).

### Run in the browser (Pyodide), not on a server
Server-side processing costs CPU per scan, needs a public upload endpoint, and
means users send their documents to someone else. Pyodide runs the same Python in
the browser, so there is no server cost, no upload, and nothing to abuse.
Trade-off: a one-time download of the runtime (~10–15 s on first visit).

### Plain HTML/JS UI instead of a framework
The UI is one page with a canvas and a few buttons. A framework would add a build
step and more to download, with nothing gained. Gradio stays for local experiments
(`app.py`) because it gives a UI for free during development.

### Two detectors: edges first, color second
Edges are precise when the outline is visible; color works when it is not (curved,
bound or cut-off pages) but can be fooled by pale backgrounds. Running color only
as a fallback, and only accepting a blob that fills ≥ 85% of its quadrilateral,
keeps the precise method in charge and the risky one checked.

### `RETR_LIST` instead of `RETR_EXTERNAL`
The inner side of a page's edge line stays a clean quadrilateral even when
background clutter merges into the outer side.

### Levels, not a percentile stretch
Clipping everything above a white point erases paper grain and JPEG blocks while
darkening faint ink: the expected "scan" look.

### Downscale input to 2000 px, upscale crops to 2000 px
Phone photos are 12+ MP; processing them at full size in WebAssembly is slow on
phones and adds no visible detail to a document. Small crops are upscaled so thin
strokes survive thresholding. 2000 px on the long side is about A4 at 170 DPI.

### Watermark on every exported page
The tool is free; the credit line ("Scanned with miladmobaseri.ir") and PDF author
metadata keep the source attached to every page that leaves it.

### Tests without a framework
One file, plain `assert`s, synthetic images with known answers:
`python -m tests.test_pipeline`. Each real-world bug got a synthetic test that
fails on the old code and passes on the fix.
