# Roadmap

Ordered by value to users.

- [ ] **Curved-page dewarping.** Fit ruled lines or text baselines with smooth curves
  and remap them to straight lines, so notebook pages flatten completely instead of
  keeping a sliver of background at the edges.
- [ ] **Full orientation.** Tell 90° from 270° and detect upside-down pages
  (projection profiles of character shapes, or a tiny orientation classifier).
- [ ] **Batch mode.** Select several photos at once and get one PDF.
- [ ] **Reorder pages** in the PDF by dragging thumbnails.
- [ ] **Offline support.** Cache the runtime with a service worker so the tool works
  without a connection after the first visit.
- [ ] **Learned page detection** as a third fallback, for photos where both the edge
  and the color detector fail.
