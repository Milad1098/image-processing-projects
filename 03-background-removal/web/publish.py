"""Copy the browser version into the website's static folder.

    python web/publish.py <website>/frontend/public/tools/background-remover

This project stays the single source of truth; the site gets a generated copy.
The copy is served at /tools/background-remover, so a <base> tag pins relative URLs there
and BGREMOVE_CONFIG points analytics at the site's own API and loads the models from the
site itself (models/*.onnx, byte-identical to the pinned Hugging Face files), so the
tool keeps working where Hugging Face is unreachable.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_HEAD = """  <base href="/tools/background-remover/">
  <script>window.BGREMOVE_CONFIG = { endpoint: "/api/tool-events/", modelBase: "models/" };</script>
"""


def main(dest: Path) -> None:
    """No Python ships to the browser here: the page, its script and stylesheet are all."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ("app.js", "style.css"):
        shutil.copy2(ROOT / "web" / name, dest / name)
    (dest / "models").mkdir()
    for name in ("modnet.onnx", "u2netp.onnx"):
        shutil.copy2(ROOT / "models" / name, dest / "models" / name)
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    html = html.replace('  <meta charset="utf-8">\n', '  <meta charset="utf-8">\n' + SITE_HEAD, 1)
    (dest / "index.html").write_text(html, encoding="utf-8")
    print(f"published to {dest}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
