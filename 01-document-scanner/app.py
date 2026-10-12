"""Gradio web UI, CamScanner-style.

Upload -> page is auto-detected and cropped -> fix corners by clicking, rotate, pick a filter
-> add pages -> download a single PDF.
"""

import tempfile
from pathlib import Path

import cv2
import gradio as gr
import numpy as np

from scanner import render, save_pdf, scan
from scanner.detect import draw_corners

MODE_LABELS = {"Magic color": "magic", "Grayscale": "gray", "Black & white": "bw", "Original": "original"}


def to_rgb(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB if img.ndim == 2 else cv2.COLOR_BGR2RGB)


def refresh(state: dict, mode: str):
    """Redraw the crop overlay and the scan from the current state."""
    overlay = to_rgb(draw_corners(state["image"], state["corners"]))
    result = render(state["image"], state["corners"], state["turns"], MODE_LABELS[mode])
    state["result"] = result
    return overlay, to_rgb(result)


def on_upload(photo: np.ndarray | None, mode: str):
    if photo is None:
        return None, None, None, ""
    image = cv2.cvtColor(photo, cv2.COLOR_RGB2BGR)
    result = scan(image)
    state = {"image": image, "corners": result.corners, "turns": result.turns}
    msg = "✅ Page detected — click on the photo to move the nearest corner." if result.detected \
        else "⚠️ No page found — click near each corner of the page to set it by hand."
    return state, *refresh(state, mode), msg


def on_click(state: dict | None, mode: str, evt: gr.SelectData):
    if not state:
        return None, None
    point = np.float32(evt.index)
    nearest = np.linalg.norm(state["corners"] - point, axis=1).argmin()
    state["corners"][nearest] = point
    return refresh(state, mode)


def on_rotate(state: dict | None, mode: str, delta: int):
    if not state:
        return None, None
    state["turns"] = (state["turns"] + delta) % 4
    return refresh(state, mode)


def on_add_page(state: dict | None, pages: list):
    if not state or "result" not in state:
        return pages, None, "Upload a photo first."
    pages = pages + [state["result"]]
    path = save_pdf(pages, Path(tempfile.gettempdir()) / "scan.pdf")
    return pages, str(path), f"📄 {len(pages)} page(s) in the PDF."


with gr.Blocks(title="Document Scanner") as demo:
    state = gr.State()
    pages = gr.State([])

    gr.Markdown("# 📄 Document Scanner\nAuto-crop, flatten and clean up photos of documents. Export to PDF.")
    with gr.Row():
        with gr.Column():
            photo = gr.Image(label="1. Upload a photo", type="numpy", sources=["upload", "webcam", "clipboard"])
            crop = gr.Image(label="2. Crop — click to move the nearest corner", interactive=False)
            status = gr.Markdown()
        with gr.Column():
            result = gr.Image(label="3. Scan", format="png", interactive=False)
            mode = gr.Radio(list(MODE_LABELS), value="Magic color", label="Filter")
            with gr.Row():
                rotate_left = gr.Button("⟲ Rotate left")
                rotate_right = gr.Button("⟳ Rotate right")
            add_page = gr.Button("➕ Add to PDF", variant="primary")
            pdf = gr.File(label="Download PDF")
            pages_info = gr.Markdown()

    photo.change(on_upload, [photo, mode], [state, crop, result, status])
    crop.select(on_click, [state, mode], [crop, result])
    mode.change(lambda s, m: refresh(s, m) if s else (None, None), [state, mode], [crop, result])
    rotate_left.click(lambda s, m: on_rotate(s, m, -1), [state, mode], [crop, result])
    rotate_right.click(lambda s, m: on_rotate(s, m, 1), [state, mode], [crop, result])
    add_page.click(on_add_page, [state, pages], [pages, pdf, pages_info])

if __name__ == "__main__":
    demo.launch()
