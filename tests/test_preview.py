"""Pass 3 is the one that gets skipped, so the pages have to be there already.

The checker measures geometry, contrast and conformance. It cannot see that a
chart is the wrong type, that a caption states the obvious, or that a page is
simply ugly. Only looking catches those — and looking is the pass an agent
quietly drops, because rendering the pages is a separate step nobody was
forced to take. Rendering them as a side effect of `--check` removes the
excuse.
"""

from __future__ import annotations

import shutil

import pytest

from folio import preview as P
from folio.renderers import ChromiumRenderer, WeasyRenderer

ANY_RENDERER = WeasyRenderer().available() or ChromiumRenderer().available()
HAS_POPPLER = shutil.which("pdftoppm") is not None

needs_render = pytest.mark.skipif(not ANY_RENDERER, reason="no PDF renderer available")
needs_poppler = pytest.mark.skipif(not HAS_POPPLER, reason="pdftoppm not installed")

TWO_PAGES = (
    "<!DOCTYPE html><html><head><title>t</title></head><body>"
    '<p>page one</p><p style="break-before:page">page two</p>'
    "</body></html>"
)


def _pdf(tmp_path):
    from folio.build import build

    src = tmp_path / "document.html"
    src.write_text(TWO_PAGES, encoding="utf-8")
    build(src, quiet=True, also_html=False)
    return tmp_path / "document.pdf"


@needs_render
@needs_poppler
def test_one_png_per_page(tmp_path):
    pages = P.render_pages(_pdf(tmp_path))
    assert len(pages) == 2
    assert all(p.exists() and p.stat().st_size > 0 for p in pages)


@needs_render
@needs_poppler
def test_pages_land_beside_the_pdf_in_their_own_directory(tmp_path):
    """Next to the output so they are easy to open, in a directory so the
    source folder does not fill up with loose images."""
    pdf = _pdf(tmp_path)
    pages = P.render_pages(pdf)
    assert pages[0].parent == pdf.with_suffix("").parent / "document.pages"


@needs_render
@needs_poppler
def test_pages_sort_in_reading_order(tmp_path):
    """p-10 must not sort before p-2, or 'read every page' silently misleads."""
    pages = P.render_pages(_pdf(tmp_path))
    assert pages == sorted(pages)
    assert "1" in pages[0].name and "2" in pages[1].name


@needs_render
@needs_poppler
def test_a_rerun_does_not_leave_pages_from_a_longer_draft(tmp_path):
    """A stale p-9 from yesterday's draft is worse than no preview at all."""
    pdf = _pdf(tmp_path)
    pages = P.render_pages(pdf)
    stale = pages[0].parent / "p-99.png"
    stale.write_bytes(b"not a real page")
    assert stale not in P.render_pages(pdf)
    assert not stale.exists()


def test_missing_poppler_is_not_an_error(monkeypatch, tmp_path):
    """Previews are a convenience; a machine without poppler still builds."""
    monkeypatch.setattr(P, "has_pdftoppm", lambda: False)
    assert P.render_pages(tmp_path / "nonexistent.pdf") == []
