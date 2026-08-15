"""Two things a document needs only when it is physically printed."""

from __future__ import annotations

import pytest

pytest.importorskip("weasyprint", reason="both are print-layout features")

from weasyprint import HTML  # noqa: E402

from folio.build import binding_css, production_css  # noqa: E402

TWO_PAGES = "<p>one</p><h1 style='break-before:page'>two</h1>"


def _pages(extra: str, body_attr: str = ""):
    html = (
        f"<!DOCTYPE html><html><head><style>@page{{size:A4;margin:20mm}}{extra}</style>"
        f"</head><body{body_attr}>{TWO_PAGES}</body></html>"
    )
    return HTML(string=html, base_url="/tmp").render().pages


# ── recto and verso ───────────────────────────────────────────────────────


def test_a_bound_document_mirrors_its_margins():
    """The inner margin is the one the binding eats, so it must swap sides."""
    pages = _pages(binding_css('<body data-binding="book">'))
    left, right = pages[0]._page_box.margin_left, pages[1]._page_box.margin_left
    assert abs(left - right) > 10, f"margins did not mirror: {left} vs {right}"


def test_an_unbound_document_keeps_even_margins():
    pages = _pages(binding_css("<body>"))
    assert pages[0]._page_box.margin_left == pages[1]._page_box.margin_left


def test_binding_css_is_empty_unless_asked_for():
    assert binding_css("<body>") == ""
    assert binding_css('<body data-binding="book">') != ""


# ── bleed and crop marks ──────────────────────────────────────────────────


def test_a_press_ready_document_carries_bleed():
    page = _pages(production_css('<body data-print="press">'))[0]
    bleed = getattr(page, "bleed", None)
    assert bleed and all(v > 0 for v in bleed.values()), f"no bleed on the page box: {bleed}"


def test_an_ordinary_document_has_no_bleed():
    page = _pages(production_css("<body>"))[0]
    assert not any((getattr(page, "bleed", None) or {}).values())


# ── ink has to reach into the bleed, or the bleed is decoration ───────────

# A bleed is 3mm of ink *past* the trim, so the guillotine has something to cut
# through. A page box 3mm larger with nothing painted in it is the defect this
# section exists to catch: it looks correct in a PDF viewer and comes back from
# the printer with a white sliver down one edge.

PRESS = '<body data-print="press">'
INK_MM = 3
MM = 96 / 25.4  # WeasyPrint lays out in CSS px


def _walk(box):
    yield box
    for child in getattr(box, "children", ()) or ():
        yield from _walk(child)


def _press_page(body: str):
    from folio.assets import css_text

    html = (
        f"<!DOCTYPE html><html><head><style>{css_text()}"
        f"{production_css(PRESS)}</style></head><body>{body}</body></html>"
    )
    return HTML(string=html, base_url="/tmp").render().pages[0]


def _border_rect(box):
    try:
        return (
            box.border_box_x(),
            box.border_box_y(),
            box.border_box_x() + box.border_width(),
            box.border_box_y() + box.border_height(),
        )
    except (AttributeError, TypeError):
        return None


def test_a_bleeding_block_runs_past_the_trim():
    """`.bleed` cancels the page margin. Under press it must overshoot it."""
    page = _press_page('<div class="bleed" style="height:40mm">band</div>')
    lefts = [
        r[0] for b in _walk(page._page_box) if (r := _border_rect(b)) and r[2] - r[0] > 100 * MM
    ]
    assert lefts and min(lefts) <= -INK_MM * MM + 1, (
        f"nothing reached {INK_MM}mm past the trim: leftmost edge at {min(lefts, default=0) / MM:.1f}mm"
    )


def test_the_cover_ink_runs_past_every_trim_edge():
    """A cover fills the sheet, so it bleeds on four edges rather than two.

    The cover cannot simply be made 6mm taller — 303mm of block inside a 297mm
    page area paginates — so the ink is carried by a layer behind it.
    """
    page = _press_page('<section class="cover"><h1>Title</h1></section>')
    w, h = page._page_box.width, page._page_box.height
    covering = [
        r
        for b in _walk(page._page_box)
        if (r := _border_rect(b))
        and r[0] <= -INK_MM * MM + 1
        and r[1] <= -INK_MM * MM + 1
        and r[2] >= w + INK_MM * MM - 1
        and r[3] >= h + INK_MM * MM - 1
    ]
    assert covering, "no layer reaches past all four trim edges of the cover"


def test_the_crop_marks_clear_the_ink():
    """The marks must not be drawn on top of the bled artwork.

    WeasyPrint draws each crop mark from the media edge inward for *half* the
    bleed, so the gap between the mark and the trim line is also half the
    bleed. At `bleed: 3mm` that is a 1.5mm stub sitting inside the 3mm of ink;
    the page box has to be larger than the ink bleed for the marks to have
    anywhere to live.
    """
    page = _pages(production_css(PRESS))[0]
    bleed = page.bleed
    assert all(v / 2 >= INK_MM * MM for v in bleed.values()), (
        f"marks would be drawn over the ink: half-bleed {bleed} against {INK_MM}mm of ink"
    )
