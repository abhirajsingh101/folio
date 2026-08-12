"""Contrast is measurable, so it is checked rather than eyeballed.

Print is less forgiving than a screen: there is no backlight, ink dries lighter
than it renders, and a caption that reads fine at 200% zoom disappears at 100%
on paper. The thresholds here are WCAG's, which is the only widely agreed
reference — a document that clears them clears a printer too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from folio.check import ERROR, WARN, contrast_ratio, inspect

pytest.importorskip("weasyprint", reason="contrast is measured on the layout tree")

PAGE = "@page{size:A4;margin:20mm}"


def doc(body: str, extra: str = "") -> str:
    return (
        f"<!DOCTYPE html><html><head><style>{PAGE}{extra}</style></head><body>{body}</body></html>"
    )


def contrast_findings(html: str) -> list:
    return [f for f in inspect(html, Path("/tmp")) if f.rule == "low-contrast"]


# ── the maths, against published reference values ─────────────────────────


def test_ratio_matches_the_wcag_reference_values():
    """Anchors from WCAG itself, so a refactor cannot quietly drift."""
    white, black = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)
    assert contrast_ratio(black, white) == pytest.approx(21.0, abs=0.01)
    assert contrast_ratio(white, white) == pytest.approx(1.0, abs=0.001)
    # #767676 on white is WCAG's canonical "just passes AA" grey.
    grey = (0x76 / 255, 0x76 / 255, 0x76 / 255)
    assert contrast_ratio(grey, white) == pytest.approx(4.54, abs=0.01)


def test_ratio_is_symmetric():
    """Which colour is foreground must not change the number."""
    a, b = (0.1, 0.2, 0.3), (0.9, 0.8, 0.7)
    assert contrast_ratio(a, b) == pytest.approx(contrast_ratio(b, a), abs=1e-9)


# ── real defects ──────────────────────────────────────────────────────────


def test_light_grey_caption_is_flagged():
    """The commonest print defect: muted text that vanished on paper."""
    assert contrast_findings(doc('<p style="color:#999">muted caption</p>'))


def test_barely_visible_text_is_an_error():
    found = contrast_findings(doc('<p style="color:#ddd">nearly invisible</p>'))
    assert found and found[0].severity == ERROR


def test_marginal_text_is_a_warning_not_an_error():
    """#808080 is 3.96:1 — fails AA for body text, but is not illegible."""
    found = contrast_findings(doc('<p style="color:#808080">marginal</p>'))
    assert found and found[0].severity == WARN


def test_translucent_text_is_measured_after_compositing():
    """Black at 15% opacity is light grey, however black the declaration looks."""
    assert contrast_findings(doc('<p style="color:rgba(0,0,0,.15)">faint</p>'))


def test_background_comes_from_the_ancestor_not_the_paper():
    """#555 on #222 is 2.1:1. Assume white paper and it scores 7.5:1 — a pass.

    So this case fails loudly if the backdrop is ever guessed rather than
    resolved by walking up the box tree.
    """
    body = '<div style="background:#222"><p style="color:#555">on a dark panel</p></div>'
    found = contrast_findings(doc(body))
    assert found and found[0].severity == ERROR


def test_white_on_a_mid_tone_fill_is_flagged():
    """White on a warm accent is the classic status-pill failure."""
    body = '<span style="background:#E8501E;color:#fff">ATTENTION</span>'
    assert contrast_findings(doc(body))


def test_running_headers_are_checked_too():
    """Page furniture is where faint grey hides — it is set once and never re-read.

    Margin boxes sit outside the content frame, so a checker that walks only
    the document tree gives a clean bill of health to an unreadable footer.
    """
    extra = '@page{@bottom-right{content:"12";color:#ccc;font-size:8pt}}'
    found = contrast_findings(doc("<p>body</p>", extra))
    assert found
    assert "@bottom-right" in found[0].detail


# ── things that must NOT be flagged ───────────────────────────────────────


def test_ordinary_body_text_is_silent():
    assert not contrast_findings(doc('<p style="color:#1f2733">ordinary prose</p>'))


def test_reversed_cover_text_is_silent():
    """A dark cover with white type is correct, and must not be reported."""
    body = '<div style="background:#002B6B"><h1 style="color:#fff">Annual Review</h1></div>'
    assert not contrast_findings(doc(body))


def test_a_page_background_counts_as_the_backdrop():
    """Some covers paint the page itself rather than a div inside it.

    Miss that and reversed cover type reads as white-on-white — an error on
    the one page of the document everybody looks at.
    """
    body = '<div class="cover"><h1 style="color:#fff">Title</h1></div>'
    extra = "@page cover{background:#002B6B;margin:0}.cover{page:cover;height:200mm}"
    assert not contrast_findings(doc(body, extra))


def test_large_headings_use_the_lower_threshold():
    """WCAG relaxes to 3:1 at 18pt. #808080 is 3.96:1, so it passes there."""
    big = '<h1 style="font-size:24pt;color:#808080">Large heading</h1>'
    small = '<p style="font-size:10pt;color:#808080">Body copy</p>'
    assert not contrast_findings(doc(big))
    assert contrast_findings(doc(small))


def test_bold_14pt_counts_as_large_text():
    body = '<p style="font-size:14pt;font-weight:700;color:#808080">Bold lead-in</p>'
    assert not contrast_findings(doc(body))


def test_a_legible_running_header_is_silent():
    extra = '@page{@top-left{content:"REPORT";color:#475569;font-size:8pt}}'
    assert not contrast_findings(doc("<p>body</p>", extra))


def test_text_over_a_background_image_is_not_guessed():
    """The backdrop is unknowable, so silence beats a confident wrong answer."""
    body = (
        '<div style="background-image:linear-gradient(#000,#fff)">'
        '<p style="color:#eee">over a gradient</p></div>'
    )
    assert not contrast_findings(doc(body))


# ── the shipped design system ─────────────────────────────────────────────


def test_every_theme_clears_aa_on_the_reference_document():
    """The kit must pass its own check, or the check is theatre.

    All four themes failed this when it was written — muted text at 3.0–3.7:1,
    a footnote at 1.9:1 — so it guards a fix rather than a hypothetical.
    """
    from folio.assets import css_text, theme_names

    src = Path(__file__).resolve().parents[1] / "examples/quarterly-report/document.html"
    if not src.exists():  # pragma: no cover - sdist without examples
        pytest.skip("example not present")
    source = src.read_text(encoding="utf-8")
    for theme in theme_names():
        html = source.replace("</head>", f"<style>{css_text(theme)}</style></head>")
        found = [f for f in inspect(html, src.parent) if f.rule == "low-contrast"]
        assert not found, f"{theme}: {[str(f) for f in found]}"


# ── the report itself ─────────────────────────────────────────────────────


def test_the_finding_names_both_colours_and_the_ratio():
    """'Low contrast somewhere' is not actionable; the numbers are."""
    found = contrast_findings(doc('<p style="color:#999">muted</p>'))
    assert found
    detail = found[0].detail
    assert "#999999" in detail
    assert "#ffffff" in detail
    assert ":1" in detail
    assert found[0].hint
