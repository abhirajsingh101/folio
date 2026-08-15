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


def press_pages(example: str) -> Path:
    """Build a copy of one example as it would go to a printer.

    `data-print="press"` belongs on the file sent to press and on nothing else,
    so the shipped example does not carry it and the shot is taken from a copy
    — the same argument as `themed_pages`, and for the same reason: what is on
    the page has to be a real build rather than a picture of one.
    """
    src = ROOT / "examples" / example
    work = Path(tempfile.mkdtemp(prefix="folio-shoot-press-")) / example
    shutil.copytree(
        src,
        work,
        ignore=shutil.ignore_patterns("charts", "*.pdf", "*.page.html", "*.pages"),
    )
    doc = work / "document.html"
    doc.write_text(
        doc.read_text(encoding="utf-8").replace("<body ", '<body data-print="press" ', 1),
        encoding="utf-8",
    )
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


def spread(left: Path, right: Path, out: Path, *, width: int, margin: int) -> None:
    """A verso and a recto, abutted at the spine.

    No gutter between the two cells: the gap is what makes `strip` read as two
    separate documents, and the whole point of this shot is that these are two
    halves of one opening. The mirrored margins only show as mirrored when the
    wide edges meet in the middle.
    """
    cells = [scaled(left, width), scaled(right, width)]
    w = margin * 2 + width * 2
    h = max(c.height for c in cells) + margin * 2
    canvas = Image.new("RGB", (w, h), BG)
    for i, c in enumerate(cells):
        canvas.paste(c, (margin + i * width, margin))
    canvas.quantize(colors=256, method=Image.MAXCOVERAGE).save(out, optimize=True)
    print(f"  {out.name:<24} {w}×{h}  {out.stat().st_size // 1024}KB")


def detail(page: Path, out: Path, *, top: float, bottom: float, width: int, margin: int) -> None:
    """A horizontal band of one page, at reading size.

    Some things are only legible in close-up: the rule over a footnote block,
    the numbers matching their calls, 8pt type that survives being printed. A
    whole page at README width cannot show any of it, and the strip shots are
    sized for shape rather than for reading.
    """
    im = Image.open(page).convert("RGB")
    band = im.crop((0, round(im.height * top), im.width, round(im.height * bottom)))
    cell = band.resize((width, round(width * band.height / band.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (width + margin * 2, cell.height + margin * 2), BG)
    canvas.paste(cell, (margin, margin))
    canvas.quantize(colors=256, method=Image.MAXCOVERAGE).save(out, optimize=True)
    print(f"  {out.name:<24} {canvas.width}×{canvas.height}  {out.stat().st_size // 1024}KB")


def corner(page: Path, out: Path, *, across: float, down: float, width: int, margin: int) -> None:
    """The corner of a sheet, for the things that only exist at its edge.

    A press file's crop marks and bleed are three millimetres of the page and
    invisible at any size that fits a whole one in a README.
    """
    im = Image.open(page).convert("RGB")
    box = im.crop((0, 0, round(im.width * across), round(im.height * down)))
    cell = box.resize((width, round(width * box.height / box.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (width + margin * 2, cell.height + margin * 2), BG)
    canvas.paste(cell, (margin, margin))
    canvas.quantize(colors=256, method=Image.MAXCOVERAGE).save(out, optimize=True)
    print(f"  {out.name:<24} {canvas.width}×{canvas.height}  {out.stat().st_size // 1024}KB")


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


# The showcase: every example, two pages each, in the order the README reads
# them. A visitor who lands on the repo should be able to see what each kind of
# document actually looks like without cloning anything, and one page per
# document does not show what a document *does* — a cover proves nothing about
# how the inside is set. The pairs are chosen for that: a cover beside the page
# carrying the most of what that document is for.
SHOWCASE = [
    ("quarterly-report", (1, 3)),
    ("essay", (1, 5)),
    ("exhibition", (1, 2)),
    ("survey", (1, 3)),
    ("lookbook", (1, 2)),
    ("architecture", (1, 2)),
    ("programme", (1, 2)),
    ("case-study", (1, 2)),
    ("runbook", (1, 2)),
    ("menu", (1,)),  # one sheet, and a second cell would be a hole
]


if __name__ == "__main__":
    exhibition, survey = pages("exhibition"), pages("survey")
    lookbook, architecture = pages("lookbook"), pages("architecture")
    programme, menu = pages("programme"), pages("menu")
    case_study, runbook = pages("case-study"), pages("runbook")

    # Every document folio ships, one page each. Ordered for contrast rather
    # than by type: at this size what reads is the shape and the ink, not the
    # words, and two documents that look alike waste a cell. The strips further
    # down are where a visitor sees what each one actually contains; this is the
    # shot that says how many there are.
    essay_pages = pages("essay")
    quarterly = pages("quarterly-report")
    grid(
        [
            [
                page(exhibition, 1),
                page(survey, 1),
                page(lookbook, 2),
                page(architecture, 1),
                page(quarterly, 1),
            ],
            [
                page(programme, 1),
                page(menu, 1),
                page(case_study, 1),
                page(runbook, 1),
                page(essay_pages, 1),
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

    # The bound essay, which is the only example that carries footnotes and the
    # only one set for a binding. Two shots, because the two things it proves
    # are legible at different sizes: the opening shows the mirrored gutter and
    # the running heads swapping sides, and only a close-up shows that the
    # notes under the rule are numbered to match their calls.
    essay = essay_pages
    spread(page(essay, 2), page(essay, 3), OUT / "spread.png", width=799, margin=54)
    detail(page(essay, 5), OUT / "footnotes.png", top=0.60, bottom=0.99, width=1652, margin=54)

    # One strip per document, at a size where the type is legible rather than
    # merely shaped. Built from the pages already rendered above where possible.
    built = {
        "quarterly-report": quarterly,
        "exhibition": exhibition,
        "survey": survey,
        "lookbook": lookbook,
        "architecture": architecture,
        "programme": programme,
        "menu": menu,
        "case-study": case_study,
        "runbook": runbook,
        "essay": essay,
    }
    for name, wanted in SHOWCASE:
        pages_dir = built.get(name) or pages(name)
        strip(
            [page(pages_dir, n) for n in wanted],
            OUT / f"doc-{name}.png",
            width=799,
            margin=54,
        )

    # The corner of a press file: crop marks in the margin, artwork running
    # past the trim into the bleed. Three millimetres of the sheet, and the
    # only part of `data-print="press"` anyone can see.
    press = press_pages("exhibition")
    corner(page(press, 1), OUT / "press.png", across=0.46, down=0.30, width=1100, margin=54)
