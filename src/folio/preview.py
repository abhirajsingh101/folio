"""Render the finished PDF to page images, so the look pass actually happens.

`folio check` measures geometry, contrast and conformance. What it cannot see
is taste: a chart that is the wrong type for its data, a caption that names the
axes instead of stating a conclusion, a page that is merely ugly. Only looking
catches those.

Looking is also the pass that gets skipped, because it needed a separate
command nobody was obliged to run. Producing the pages as a side effect of
`--check` removes the excuse — the images are already sitting there with their
paths printed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .renderers import has_pdftoppm

PREVIEW_DPI = 110  # legible on screen without producing 4MB a page
_TIMEOUT = 120


def pages_dir(pdf: Path) -> Path:
    """Beside the PDF, in its own directory.

    Loose page images in the source folder get committed by accident and are a
    nuisance to clean up; one directory is easy to ignore and easy to delete.
    """
    return pdf.resolve().parent / f"{pdf.stem}.pages"


def render_pages(pdf: Path, dpi: int = PREVIEW_DPI) -> list[Path]:
    """One PNG per page, in reading order. Empty list if it cannot be done.

    Previews are a convenience, never a build requirement: a machine without
    poppler must still be able to produce documents.
    """
    if not has_pdftoppm() or not Path(pdf).exists():
        return []
    out = pages_dir(Path(pdf))
    # A stale page from a longer draft is worse than no preview, because it
    # looks like part of this document.
    if out.exists():
        for old in out.glob("p-*.png"):
            old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    try:
        # poppler pads the page number to the width of the last page, so every
        # name in a run is the same length and plain sorting is reading order.
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(Path(pdf).resolve()), str(out / "p")],
            capture_output=True,
            timeout=_TIMEOUT,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    return sorted(out.glob("p-*.png"))
