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

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from folio.assets import theme_names
from folio.build import retheme

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


def themed_pages(example: str, theme: str) -> Path:
    """Build one example in one direction — charts included — and return its pages.

    The theme strips used to be shot by injecting a different stylesheet into
    an already-rendered document. That changes the type and leaves the figures
    alone, so all four panels carried the palette of whichever theme the
    example was last built in: four typographic systems under four identical
    blue charts, directly beneath a caption promising the charts re-palette.
    They do. The shot did not.

    Building a real copy per theme is what makes the claim true, because
    `folio build` runs `charts.py` with FOLIO_THEME set.
    """
    src = ROOT / "examples" / example
    work = Path(tempfile.mkdtemp(prefix=f"folio-shoot-{theme}-")) / example
    shutil.copytree(
        src,
        work,
        ignore=shutil.ignore_patterns("charts", "*.pdf", "*.page.html", "*.pages"),
    )
    doc = work / "document.html"
    html = retheme(doc.read_text(encoding="utf-8"), theme)
    # Whether a cover takes a plate is a property of the direction, not of the
    # document: `report` and `editorial` have a band deep enough to hold one,
    # and doctrine gives `technical` and `minimal` none — one exists to fit
    # more on the page, the other is built on having nothing to hide behind.
    # Restyling alone left the report's plate on all four, which put a sliver
    # of it in a 3mm rule.
    plate = {"report": "art/cover-report.jpg", "editorial": "art/cover-editorial.jpg"}.get(theme)
    if plate:
        html = re.sub(r'(<img class="cover-plate" src=")[^"]+(")', rf"\1{plate}\2", html)
    else:
        html = re.sub(r'<img class="cover-plate"[^>]*>\s*', "", html)
    doc.write_text(html, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "folio", "build", str(doc), "-q"], check=True)
    subprocess.run(
        [sys.executable, "-m", "folio", "preview", str(doc.with_suffix(".pdf")), "--dpi", str(DPI)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return work / "document.pages"


def page(pages_dir: Path, n: int) -> Path:
    """The nth page, whatever the padding.

    `folio preview` pads the number to the width of the page count, so page 3
    is `p-3.png` in a nine-page document and `p-03.png` in a twelve-page one —
    and the same example paginates differently in each direction.
    """
    for name in (f"p-{n}.png", f"p-{n:02d}.png", f"p-{n:03d}.png"):
        if (pages_dir / name).exists():
            return pages_dir / name
    raise FileNotFoundError(f"{pages_dir} has no page {n}")


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
                page(exhibition, 1),
                page(survey, 1),
                page(lookbook, 2),
                page(architecture, 1),
            ],
            [
                page(programme, 1),
                page(menu, 1),
                page(case_study, 1),
                page(runbook, 1),
            ],
        ],
        OUT / "documents.png",
        width=411,
        margin=23,
    )

    # One document, four directions, built four times rather than restyled
    # once — see themed_pages. The cover strip and the interior strip are the
    # same four builds, so the charts in the second are the real thing.
    themed = {t: themed_pages("quarterly-report", t) for t in theme_names()}
    strip(
        [page(themed[t], 1) for t in theme_names()],
        OUT / "themes-covers.png",
        width=411,
        margin=23,
    )
    strip(
        [page(themed[t], 3) for t in theme_names()],
        OUT / "themes-pages.png",
        width=411,
        margin=23,
    )

    # Two interiors, large enough to read. The pages carrying the most
    # components, from the two directions furthest apart.
    strip(
        [page(survey, 3), page(runbook, 1)],
        OUT / "interiors.png",
        width=799,
        margin=54,
    )
