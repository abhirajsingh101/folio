"""The quality gate. Each case is a defect that actually shipped once."""

from __future__ import annotations

from pathlib import Path

import pytest

from folio.assets import css_text
from folio.check import ERROR, WARN, inspect, summarise

pytest.importorskip("weasyprint", reason="check measures WeasyPrint's layout tree")

PAGE = "@page{size:A4;margin:20mm}"


def rules(html: str) -> set[str]:
    return {f.rule for f in inspect(html, Path("/tmp"))}


def doc(body: str, extra: str = "") -> str:
    return (
        f"<!DOCTYPE html><html><head><style>{PAGE}{extra}</style></head><body>{body}</body></html>"
    )


# ── clean input must stay silent, or nobody will trust the tool ───────────


def test_ordinary_document_is_clean():
    assert inspect(doc("<p>A short and entirely unremarkable paragraph.</p>"), Path("/tmp")) == []


def test_the_shipped_example_has_no_errors():
    """The bundled example is the reference; it must not regress."""
    src = Path(__file__).resolve().parents[1] / "examples/quarterly-report/document.html"
    if not src.exists():  # pragma: no cover - sdist without examples
        pytest.skip("example not present")
    html = src.read_text(encoding="utf-8")
    html = html.replace("</head>", f"<style>{css_text()}</style></head>")
    errors = [f for f in inspect(html, src.parent) if f.severity == ERROR]
    assert not errors, f"example regressed: {[str(e) for e in errors]}"


# ── real defects ──────────────────────────────────────────────────────────


def test_horizontal_overflow_is_an_error():
    """The callout bug: a flex child without min-width:0 overruns its box."""
    body = '<div style="display:flex"><div><p>' + "unbreakabletoken" * 12 + "</p></div></div>"
    assert "overflow-x" in rules(doc(body))


def test_overlapping_text_is_an_error():
    body = (
        '<div style="position:absolute;top:40mm;left:20mm">FIRST LABEL</div>'
        '<div style="position:absolute;top:40mm;left:20mm">SECOND ON TOP</div>'
    )
    assert "text-overlap" in rules(doc(body))


def test_tight_leading_inside_one_heading_is_not_an_overlap():
    """Two line boxes of the same heading are one thing, not a collision.

    Display type is routinely set below 1.1 line-height — folio's own
    `technical` cover uses 1.06 — where the glyph boxes overlap and the glyphs
    do not. Reported as an error, it blocks a document that is set correctly.
    """
    body = "<h1>Teaching a document kit to check its own work</h1>"
    extra = "h1{font:600 30pt/1.06 sans-serif;width:60mm}"
    assert "text-overlap" not in rules(doc(body, extra))


def test_thin_page_is_flagged():
    """A block that could not fit jumps and leaves a near-empty page.

    The fixture models an actual jump — a tall unbreakable block with too
    little room left — rather than a page the author asked for. An earlier
    version used `break-before: page`, which is the opposite case and is now
    deliberately silent.
    """
    body = (
        '<p style="margin-bottom:40mm">a short opening paragraph</p>'
        '<div style="height:230mm;break-inside:avoid">a block too tall to fit here</div>'
        "<p>trailing text</p>"
    )
    assert "thin-page" in rules(doc(body))


def test_a_block_that_jumps_mid_section_is_still_flagged():
    """A section wrapper stays an ancestor of every page the section runs onto.

    So finding `break-before: page` somewhere overhead proves nothing about
    *this* page — the break may have happened two pages ago. Only an element
    that actually begins here authorises the short page before it.
    """
    body = (
        "<p>one</p>"
        '<div style="break-before:page"><h2>Section</h2>'
        '<div style="height:230mm;break-inside:avoid"></div>'
        "<p>tail</p></div>"
    )
    assert "thin-page" in rules(doc(body))


def test_a_page_the_author_asked_for_is_not_thin():
    """`break-before: page` ends a page on purpose; that is a chapter break.

    folio's own `.section-wrap` does exactly this, so every short section in
    every document reported a defect whose hint said a block had jumped —
    which was never what happened.
    """
    body = (
        "<p>a deliberately short opening section</p>"
        '<div style="break-before:page"><h2>Second section</h2><p>text</p></div>'
        '<div style="break-before:page"><h2>Third section</h2><p>text</p></div>'
    )
    assert "thin-page" not in rules(doc(body))


def test_illegibly_small_text_is_flagged():
    assert "tiny-text" in rules(doc('<p style="font-size:3pt">unreadable小</p>'))


def test_orphan_heading_is_flagged():
    body = '<p style="margin-bottom:230mm">filler</p><h3>Stranded heading</h3>'
    assert "orphan-heading" in rules(doc(body))


# ── things that must NOT be flagged ───────────────────────────────────────


def test_cover_pages_are_not_thin_pages():
    """Covers are deliberately sparse. An earlier version flagged every one."""
    body = '<div class="cover">Title</div><p>body</p><p>more</p>'
    extra = "@page cover{margin:0} .cover{page:cover;height:250mm}"
    assert "thin-page" not in rules(doc(body, extra))


def test_running_headers_are_not_overflow():
    """Margin boxes live outside the content frame by design."""
    extra = (
        '@page{@top-left{content:"HEAD"}@bottom-right{content:counter(page)}'
        '@bottom-left{content:"foot"}}'
    )
    assert "overflow-y" not in rules(doc("<p>ordinary body text</p>", extra))
    assert "overflow-x" not in rules(doc("<p>ordinary body text</p>", extra))


def test_last_page_may_be_short():
    body = '<p style="margin-bottom:240mm">page one</p><p>a short final page</p>'
    assert "thin-page" not in rules(doc(body))


# ── reporting ─────────────────────────────────────────────────────────────


def test_findings_carry_a_page_and_a_hint():
    found = inspect(doc('<p style="font-size:3pt">x tiny</p>'), Path("/tmp"))
    assert found and found[0].page >= 1
    assert found[0].hint, "a finding with no remedy is not actionable"


def test_errors_sort_before_warnings():
    body = (
        '<p style="font-size:3pt">tiny</p>'
        '<div style="display:flex"><div><p>' + "unbreakabletoken" * 12 + "</p></div></div>"
    )
    found = inspect(doc(body), Path("/tmp"))
    severities = [f.severity for f in found]
    assert severities == sorted(severities, key=lambda s: 0 if s == ERROR else 1)


def test_summary_reads_correctly():
    assert summarise([]) == "No layout problems found."
    from folio.check import Finding

    assert "1 error" in summarise([Finding("r", ERROR, 1, "d")])
    assert "1 warning" in summarise([Finding("r", WARN, 1, "d")])
