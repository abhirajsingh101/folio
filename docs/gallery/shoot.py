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
    exhibition, survey = pages("exhibition"), pages("survey")
    lookbook, architecture = pages("lookbook"), pages("architecture")
    programme, menu = pages("programme"), pages("menu")
    case_study, runbook = pages("case-study"), pages("runbook")

    # Eight documents from eight fields, one page each — the quarterly report
    # is the hero above, so it sits this one out. Ordered for contrast rather
    # than by type: at this size what reads is the shape and the ink, not the
    # words, and two documents that look alike waste a cell.
    grid(
        [
            [
                exhibition / "p-1.png",
                survey / "p-1.png",
                lookbook / "p-2.png",
                architecture / "p-1.png",
            ],
            [
                programme / "p-1.png",
                menu / "p-1.png",
                case_study / "p-1.png",
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
        [survey / "p-3.png", runbook / "p-1.png"],
        OUT / "interiors.png",
        width=799,
        margin=54,
    )
