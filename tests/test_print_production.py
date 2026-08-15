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
