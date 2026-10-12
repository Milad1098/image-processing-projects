"""Copy the browser version into the website's static folder.

    python web/publish.py <website>/frontend/public/tools/scanner

This project stays the single source of truth; the site gets a generated copy.
The copy is served at /tools/scanner, so a <base> tag pins relative URLs there
and SCANNER_CONFIG points analytics at the site's own API.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_HEAD = """  <base href="/tools/scanner/">
  <script>window.SCANNER_CONFIG = { endpoint: "/api/tool-events/", pyBase: "" };</script>
"""


def main(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "scanner").mkdir(parents=True)
    for name in ("app.js", "style.css", "bridge.py"):
        shutil.copy2(ROOT / "web" / name, dest / name)
    for py in (ROOT / "scanner").glob("*.py"):
        if py.name != "__main__.py":           # CLI only, not needed in the browser
            shutil.copy2(py, dest / "scanner" / py.name)

    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    html = html.replace('  <meta charset="utf-8">\n', '  <meta charset="utf-8">\n' + SITE_HEAD, 1)
    (dest / "index.html").write_text(html, encoding="utf-8")
    print(f"published to {dest}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
