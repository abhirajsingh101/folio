"""Compose the README gallery from rendered example pages.

Run after `folio build --check` has produced `<example>/document.pages/`:

    python docs/gallery/shoot.py

The geometry is fixed here rather than recreated by hand each time, because
the images sit side by side in one README and a strip shot at a different
margin reads as a different product. Pages are rendered at 200dpi and
downscaled, which is what keeps 8pt type from turning to mush at README width.

Output is palette-quantised: retina-sharp at 1760px and about a third the cost
of straight RGB. The gallery ships whole in the sdist, so the sizes matter.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BG = (238, 240, 242)
DPI = 200


def pages(example: str) -> Path:
    """Render one example at gallery resolution and return its pages dir."""
    src = ROOT / "examples" / example / "document.html"
    subprocess.run([sys.executable, "-m", "folio", "build", str(src), "-q"], check=True)
    subprocess.run(
        [sys.executable, "-m", "folio", "preview", str(src.with_suffix(".pdf")), "--dpi", str(DPI)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return src.parent / "document.pages"


def scaled(path: Path, width: int) -> Image.Image:
    im = Image.open(path).convert("RGB")
    return im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)


def strip(paths: list[Path], out: Path, *, width: int, margin: int) -> None:
    cells = [scaled(p, width) for p in paths]
    gutter = margin
    w = margin * 2 + width * len(cells) + gutter * (len(cells) - 1)
    h = max(c.height for c in cells) + margin * 2
    canvas = Image.new("RGB", (w, h), BG)
    x = margin
    for c in cells:
        canvas.paste(c, (x, margin))
        x += width + gutter
    canvas.quantize(colors=256, method=Image.MAXCOVERAGE).save(out, optimize=True)
    print(f"  {out.name:<24} {w}×{h}  {out.stat().st_size // 1024}KB")


def grid(rows: list[list[Path]], out: Path, *, width: int, margin: int) -> None:
    """Two strips stacked, so eight documents fit one image."""
    cells = [[scaled(p, width) for p in row] for row in rows]
    gutter = margin
    w = margin * 2 + width * len(cells[0]) + gutter * (len(cells[0]) - 1)
    row_h = max(c.height for row in cells for c in row)
    h = margin * 2 + row_h * len(cells) + gutter * (len(cells) - 1)
    canvas = Image.new("RGB", (w, h), BG)
    for r, row in enumerate(cells):
        y = margin + r * (row_h + gutter)
        for c, cell in enumerate(row):
            canvas.paste(cell, (margin + c * (width + gutter), y))
    canvas.quantize(colors=256, method=Image.MAXCOVERAGE).save(out, optimize=True)
    print(f"  {out.name:<24} {w}×{h}  {out.stat().st_size // 1024}KB")


if __name__ == "__main__":
    quarterly, proposal = pages("quarterly-report"), pages("proposal")
    exhibition, survey = pages("exhibition"), pages("survey")
    case_study, invoice = pages("case-study"), pages("invoice")
    menu, runbook = pages("menu"), pages("runbook")

    # Eight documents, first page of each. Top row takes a cover, bottom row
    # is built without one — which is the distinction that decides a document's
    # shape long before the theme does. Small on purpose: at this size what
    # reads is the shape, not the words.
    grid(
        [
            [
                quarterly / "p-1.png",
                proposal / "p-1.png",
                exhibition / "p-1.png",
                survey / "p-1.png",
            ],
            [
                case_study / "p-1.png",
                invoice / "p-1.png",
                menu / "p-1.png",
                runbook / "p-1.png",
            ],
        ],
        OUT / "documents.png",
        width=411,
        margin=23,
    )

    # Two interiors, large enough to read. The pages carrying the most
    # components, from the two directions furthest apart.
    strip(
        [proposal / "p-3.png", runbook / "p-1.png"],
        OUT / "interiors.png",
        width=799,
        margin=54,
    )
