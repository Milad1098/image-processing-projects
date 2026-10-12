# Case study: building a document scanner that survives real photos

**Goal:** turn a phone photo of a page into a clean, flat, printable scan, with the
experience of an app like CamScanner, but using classic computer vision only and
running in the browser so nobody has to upload their documents.

**Result:** a working scanner at
[miladmobaseri.ir/en/tools/scanner](https://miladmobaseri.ir/en/tools/scanner),
~350 lines of Python for the algorithm, with no server-side processing at all.

The interesting part was not the textbook pipeline. It was the gap between that
pipeline and real photos. This document walks through each failure, why it
happened, and what fixed it.

---

## 1. The textbook pipeline

Most document-scanner tutorials describe the same four steps:

1. Grayscale → blur → **Canny** edge detection
2. Find **contours**, keep the largest one that simplifies (`approxPolyDP`) to 4 points
3. **Perspective transform** those 4 corners to a rectangle
4. **Adaptive threshold** for a black-and-white "scan" look

I built exactly that first, with a synthetic test: a white page with text lines,
warped in perspective onto a dark background, with known corners. It passed.
Then I tried it on real photos.

## 2. Failure: the background touched the page

**Symptom.** On two of three photos of a sheet lying on a floral tablecloth,
no page was found at all.

**Diagnosis.** The edge map showed the page outline was complete and clean. But
wherever a flower in the cloth pattern touched the edge of the paper, its edges
merged into the page outline. With `cv2.RETR_EXTERNAL`, OpenCV returns only the
outermost boundary of each connected edge blob, so the "page" contour became the
page *plus* half a flower, and it no longer simplified to 4 points.

**Fix.** One flag: `RETR_EXTERNAL` → `RETR_LIST`. The edge line around the page has
an *inside* boundary too, and that inner contour is a clean quadrilateral no
matter what touches the outside. All three photos were detected afterwards.

**Test added.** A synthetic circle drawn touching the page from outside. I checked
that the test **fails with the old flag and passes with the new one**, so it
actually guards the bug.

## 3. Failure: a halo around every word

**Symptom.** The "magic color" filter (white paper, colored ink kept) produced an
olive-colored halo around every line of text.

**Diagnosis.** Shadow removal works by estimating the paper's background
brightness and dividing it out. The first estimate was `dilate` followed by a
large `medianBlur`. Around text, that estimate was biased, so the area around the
ink came out darker than the paper elsewhere, and the contrast stretch that
followed made the error very visible.

**Fix.** Estimate the background with a **morphological closing** (which erases dark
strokes thinner than the kernel) on a 4× downscaled copy, then blur and upscale it.
That is cheaper and unbiased around the ink. The halo disappeared.

## 4. Failure: JPEG blocks and paper grain

**Symptom.** With the halo gone, the paper showed faint blocky texture: JPEG
compression artifacts and paper grain, amplified by the contrast stretch.

**Fix.** Replace the percentile stretch with **levels**: everything brighter than a
white point (215 after flattening) becomes pure white, and the rest is stretched
down to the darkest ink. Paper texture lives just below white, so it is erased,
while faint pencil and blue ink get *darker*. This is the look users expect from a
scan app.

## 5. Failure: the spiral notebook

**Symptom.** A photo of a spiral-bound notebook: "No page found", and the fallback
(enhance the whole photo) turned the patterned background into noise. It looked
broken, because it was.

**Diagnosis.** There was **no closed 4-sided outline to find**. The top edge was
curved, one side was the spiral binding, and the bottom of the page ran off the
frame. Edge-based detection cannot find an outline that is not in the photo.

**Fix.** A second detector based on what paper *is* rather than its outline: a
**bright, low-saturation region**. In HSV, keep pixels with saturation < 45 and
brightness above the photo's 40th percentile; close the mask to fill in ink and
ruled lines, open it to cut thin bridges to the background; take the largest blob,
its convex hull, and loosen `approxPolyDP` until it gives 4 corners.

**The catch.** On the first floral-tablecloth photo, the cream-colored cloth was
*also* bright and colorless, and the color detector returned a wrong quadrilateral.
So the color detector only runs when the edge detector fails, and its result must
pass a **sanity check**: the blob must fill at least 85% of its own quadrilateral.
A real page does; an irregular patch of tablecloth does not.

**Also fixed.** When nothing is found, the fallback corners now sit 8% inside the
photo instead of exactly on its edge, where the drag handles were half hidden.

**Test added.** A white page running off the bottom of the frame on a light blue
background: no closed outline, so only the color path can find it.

## 6. Failure: where should it run?

The first UI was Gradio, which processes on a server. Two problems:

- **Cost and abuse.** Every scan uses server CPU and RAM, and a public upload form is
  an attack surface.
- **Hosting.** The free tier I planned to use stopped offering server-backed apps.

**Fix.** Run the *same Python code* in the visitor's browser with **Pyodide**
(CPython compiled to WebAssembly, with NumPy, OpenCV and Pillow available). A small
`bridge.py` passes RGBA pixels from a canvas into NumPy and returns PNG bytes. The
UI is plain HTML/JS with draggable corners (pointer events, so touch works).
The server now serves only static files, and photos never leave the device.

Two deployment details mattered:

- The website has a strict Content Security Policy. Pyodide needs
  `'wasm-unsafe-eval'` and its CDN, so the relaxed policy is scoped to `/tools/*`
  only. Two CSP headers on one response are *intersected* by browsers, so the
  site-wide rule had to explicitly exclude that path.
- After an update, a returning browser kept running the **old** Python files from
  its cache, which made a fixed bug look unfixed. The Python sources are now fetched
  with `cache: "no-cache"` (revalidated on each visit).

## 7. What I would do next

- **Curved-page dewarping**: fit the ruled lines or text baselines and remap them to
  straight lines, so notebook pages flatten completely.
- **Full orientation detection** (90° vs 270°, upside down), e.g. with a small
  text-orientation classifier.
- **Batch mode**: several photos in, one PDF out.

## Takeaways

- **A test that passes on synthetic data proves very little.** Every real failure
  here came from something the synthetic image did not have: clutter, compression,
  curvature, a cut-off frame.
- **Diagnose from intermediate images, not the final output.** The edge map showed
  the merged-contour bug immediately; the output alone only said "not found".
- **Give every heuristic a sanity check.** The color detector is only safe because
  it can reject its own answer.
- **Where code runs is a design decision.** Moving to the browser removed the server
  cost, the privacy question and the abuse surface in one step.
