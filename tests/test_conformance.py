"""Does the document use the design system, or has it improvised?

Geometry and contrast ask whether a document renders correctly. These ask
whether it was *built the way the kit intends* — the rules folio documents but
until now could only ask nicely for. An improvised heading level or a one-off
inline size renders perfectly and passes every other check, which is exactly
how a design system erodes: silently, one reasonable-looking exception at a
time.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from folio.check import WARN, inspect

# A real image, so WeasyPrint lays out a real replaced box. SVG rather than a
# 1×1 raster, which would trip the upscale rule and muddy these tests.
_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="70"></svg>'
IMG = "data:image/svg+xml;base64," + base64.b64encode(_SVG).decode()

pytest.importorskip("weasyprint", reason="conformance is read off the layout tree")

PAGE = "@page{size:A4;margin:20mm}"


def doc(body: str, extra: str = "") -> str:
    return (
        f"<!DOCTYPE html><html><head><style>{PAGE}{extra}</style></head><body>{body}</body></html>"
    )


def findings(html: str, rule: str) -> list:
    return [f for f in inspect(html, Path("/tmp")) if f.rule == rule]


# ── heading hierarchy ─────────────────────────────────────────────────────


def test_skipping_a_heading_level_is_flagged():
    """h2 straight to h4 asserts a level of nesting that does not exist."""
    found = findings(doc("<h2>Section</h2><h4>Detail</h4>"), "heading-skip")
    assert found
    assert found[0].severity == WARN
    assert "h4" in found[0].detail


def test_descending_one_level_at_a_time_is_silent():
    assert not findings(doc("<h2>A</h2><h3>B</h3><h4>C</h4>"), "heading-skip")


def test_climbing_back_up_is_silent():
    """h4 → h2 closes two levels; only descending can skip."""
    body = "<h2>A</h2><h3>B</h3><h4>C</h4><h2>D</h2><h3>E</h3>"
    assert not findings(doc(body), "heading-skip")


def test_the_first_heading_may_be_any_level():
    """A document that opens at h2 under a cover h1 is normal, not a defect."""
    assert not findings(doc("<h2>Opening section</h2><p>text</p>"), "heading-skip")


def test_a_heading_split_across_pages_is_counted_once():
    """Boxes fragment; elements do not. Dedupe must be by element."""
    body = '<h2>A</h2><h3>B</h3><p style="margin-bottom:240mm">filler</p><h3>C</h3>'
    assert not findings(doc(body), "heading-skip")


# ── the shipped design system ─────────────────────────────────────────────


def test_every_theme_conforms_on_the_reference_document():
    """The kit must obey its own rules, or they are decoration.

    All four themes failed this when it was written: inline `code` was sized
    in `em`, so it compounded off every container it sat in and produced three
    near-identical sizes for one element. The reference document also carried
    two hand-rolled styles and a skipped heading level.
    """
    from folio.assets import css_text, theme_names

    src = Path(__file__).resolve().parents[1] / "examples/quarterly-report/document.html"
    if not src.exists():  # pragma: no cover - sdist without examples
        pytest.skip("example not present")
    source = src.read_text(encoding="utf-8")
    for theme in theme_names():
        html = source.replace("</head>", f"<style>{css_text(theme)}</style></head>")
        found = [
            f
            for f in inspect(html, src.parent)
            if f.rule in ("type-drift", "inline-style", "heading-skip")
        ]
        assert not found, f"{theme}: {[str(f) for f in found]}"


# ── type scale ────────────────────────────────────────────────────────────


def test_two_indistinguishable_sizes_are_flagged():
    """8.096pt beside 8.1pt is not a scale step, it is an accident.

    The usual cause is a relative size compounding — an `em` inside an `em` —
    which lands a hair off an established size. Nobody can see the difference,
    so the scale gains a step that carries no meaning.
    """
    body = (
        '<p style="font-size:10pt">one</p>'
        '<p style="font-size:10pt">two</p>'
        '<p style="font-size:10pt">three</p>'
        '<p style="font-size:10.05pt">stray</p>'
    )
    found = findings(doc(body), "type-drift")
    assert found
    assert found[0].severity == WARN


def test_a_genuine_scale_step_is_silent():
    """A designed scale steps by ratios a reader can actually see."""
    body = '<p style="font-size:10pt">body</p><h3 style="font-size:12pt">heading</h3>'
    assert not findings(doc(body), "type-drift")


def test_the_stray_is_named_not_the_established_size():
    """The fix belongs on the odd one out, so that is what the report points at."""
    body = (
        '<p style="font-size:9pt">a</p><p style="font-size:9pt">b</p>'
        '<p style="font-size:9pt">c</p><p style="font-size:9.04pt">odd</p>'
    )
    found = findings(doc(body), "type-drift")
    assert found
    assert "9.04pt" in found[0].detail
    assert found[0].hint


def test_the_finding_names_the_element_carrying_the_stray():
    """A size with no element attached leaves the author hunting the whole document."""
    body = (
        '<p style="font-size:9pt">a</p><p style="font-size:9pt">b</p>'
        '<p style="font-size:9pt">c</p><ul><li style="font-size:9.04pt">odd</li></ul>'
    )
    found = findings(doc(body), "type-drift")
    assert found
    assert "<li>" in found[0].detail


def test_a_size_used_once_at_its_own_step_is_silent():
    """A cover number is legitimately unique — rarity alone is not drift."""
    body = '<p style="font-size:9pt">body</p><p style="font-size:34pt">34</p>'
    assert not findings(doc(body), "type-drift")


# ── evidence vs decoration ────────────────────────────────────────────────


def test_a_plate_carrying_a_figure_number_is_flagged():
    """A decorative image numbered `Fig. 3` borrows the authority of evidence.

    This is the failure worth catching: not a fabricated chart, which is
    obvious, but an illustration wearing the same grammar as a measurement, so
    the reader files it as sourced.
    """
    body = (
        f'<div class="plate"><img src="{IMG}" alt="cover art">'
        '<span class="fnum">Fig. 3</span></div>'
    )
    found = findings(doc(body), "image-role")
    assert found
    assert found[0].severity == WARN


def test_a_figure_without_a_number_is_flagged():
    """The mirror image: if it is evidence, number it; if not, it is a plate."""
    body = f'<figure><img src="{IMG}" alt="chart"><figcaption>Throughput</figcaption></figure>'
    assert findings(doc(body), "image-role")


def test_a_numbered_figure_is_silent():
    body = (
        f'<figure><img src="{IMG}" alt="chart">'
        '<figcaption><span class="fnum">Fig. 1</span>Deploys doubled after July.'
        "</figcaption></figure>"
    )
    assert not findings(doc(body), "image-role")


def test_a_plain_plate_is_silent():
    body = f'<div class="plate"><img src="{IMG}" alt="a dark textural opener"></div>'
    assert not findings(doc(body), "image-role")


def test_an_image_with_no_alt_is_flagged():
    body = f'<div class="plate"><img src="{IMG}"></div>'
    found = findings(doc(body), "image-alt")
    assert found
    assert found[0].hint


def test_an_explicitly_decorative_image_is_silent():
    """alt="" is HTML's way of saying 'skip this', which is a real decision."""
    body = f'<div class="plate"><img src="{IMG}" alt=""></div>'
    assert not findings(doc(body), "image-alt")


# ── hand-rolled style ─────────────────────────────────────────────────────


def test_an_inline_style_is_flagged():
    """Rule 2 of the kit: never hand-roll a style. Now it is enforced."""
    found = findings(doc('<p style="color:#333">improvised</p>'), "inline-style")
    assert found
    assert found[0].severity == WARN
    assert "<p>" in found[0].detail


def test_a_document_using_only_classes_is_silent():
    body = '<p class="lede">as intended</p><div class="callout"><p>body</p></div>'
    assert not findings(doc(body), "inline-style")


def test_the_injected_stylesheet_is_not_an_inline_style():
    """folio injects its own <style> into head; that must not trip the rule."""
    assert not findings(doc("<p>ordinary</p>", "p{color:#222}"), "inline-style")


def test_each_offending_element_is_reported_once():
    """A styled element spans many boxes; the author wants one line per element."""
    body = '<div style="color:#333"><p>one</p><p>two</p><p>three</p></div>'
    assert len(findings(doc(body), "inline-style")) == 1
