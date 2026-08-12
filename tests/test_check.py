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


def test_thin_page_is_flagged():
    """A block that could not fit jumps and leaves a near-empty page."""
    body = (
        '<p style="margin-bottom:200mm">first page</p>'
        '<div style="break-before:page">stranded</div>'
        '<div style="break-before:page">last page so the middle one counts</div>'
    )
    assert "thin-page" in rules(doc(body))


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
