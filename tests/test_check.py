"""The quality gate. Each case is a defect that actually shipped once."""

from __future__ import annotations

from pathlib import Path

import pytest

from folio.assets import css_text
from folio.check import ERROR, WARN, inspect, summarise

pytest.importorskip("weasyprint", reason="check measures WeasyPrint's layout tree")

PAGE = "@page{size:A4;margin:20mm}"

# Pagination fixtures must not depend on the platform's default font. Pinning
# size and line-height, and leaving tens of millimetres of slack in whether a
# block fits, is what keeps them from passing on Linux and failing on macOS —
# which is exactly how the first version of these two got through review.
FLAT = "font-size:10pt;line-height:1;margin-top:0"

# A page carried to ~94% with text at its foot, and 20mm of slack in whether
# the block after it fits. Pushing the overflow with a trailing margin rather
# than a leading one keeps the fixture out of the question of whether a margin
# survives a page break, which is where two earlier versions of this went wrong.
FILLED_PAGE = (
    f'<p style="{FLAT};margin-bottom:230mm">page one opens</p>'
    f'<p style="{FLAT};margin-bottom:40mm">and fills to its foot</p>'
)

# What `.bleed` does, written out: cancel the page margin on both sides and
# grow by as much again. Spelled out rather than imported so the fixture
# measures the geometry the rule is about, not the class that usually causes it.
BLEED = "margin-left:-20mm;margin-right:-20mm;width:calc(100% + 40mm)"
# The kit zeroes this in base.css. Without it the UA's 8px keeps a bleed 8px
# clear of the paper on both sides, and the fixture stops being a bleed.
NO_BODY_MARGIN = "body{margin:0}"


def rules(html: str) -> set[str]:
    return {f.rule for f in inspect(html, Path("/tmp"))}


def rules_on(html: str, page: int) -> set[str]:
    """Pagination fixtures produce incidental short pages of their own.

    Naming the page under test keeps a fixture's own tail from deciding
    whether the case it was written for passes.
    """
    return {f.rule for f in inspect(html, Path("/tmp")) if f.page == page}


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
        f'<p style="{FLAT};margin-bottom:60mm">a short opening paragraph</p>'
        '<div style="height:230mm;break-inside:avoid">a block too tall to fit here</div>'
        f'<p style="{FLAT}">trailing text</p>'
    )
    assert "thin-page" in rules(doc(body))


def test_a_block_that_jumps_mid_section_is_still_flagged():
    """A section wrapper stays an ancestor of every page the section runs onto.

    So finding `break-before: page` somewhere overhead proves nothing about
    *this* page — the break may have happened two pages ago. Only an element
    that actually begins here authorises the short page before it.
    """
    body = (
        f'<p style="{FLAT}">one</p>'
        '<div style="break-before:page">'
        f'<p style="{FLAT};margin-bottom:60mm">section opens</p>'
        '<div style="height:230mm;break-inside:avoid"></div>'
        f'<p style="{FLAT}">tail</p></div>'
    )
    assert "thin-page" in rules(doc(body))


def test_a_page_the_author_asked_for_is_not_thin():
    """`break-before: page` ends a page on purpose; that is a chapter break.

    folio's own `.section-wrap` does exactly this, so every short section in
    every document reported a defect whose hint said a block had jumped —
    which was never what happened.

    The fixture now ends its first section around half the page rather than on
    one line. An authored break excuses a page that *ends*; it does not excuse
    a page that is empty, which is what `page-widow` measures below.
    """
    body = (
        f'<p style="{FLAT};margin-bottom:130mm">a section that runs down the page</p>'
        f'<p style="{FLAT}">and ends here, a little over halfway</p>'
        '<div style="break-before:page"><h2>Second section</h2><p>text</p></div>'
        '<div style="break-before:page"><h2>Third section</h2><p>text</p></div>'
    )
    found = rules_on(doc(body), 1)
    assert "thin-page" not in found
    assert "page-widow" not in found


def test_illegibly_small_text_is_flagged():
    assert "tiny-text" in rules(doc('<p style="font-size:3pt">unreadable小</p>'))


def test_orphan_heading_is_flagged():
    body = '<p style="margin-bottom:230mm">filler</p><h3>Stranded heading</h3>'
    assert "orphan-heading" in rules(doc(body))


def test_one_stranded_heading_is_reported_once():
    """A heading matched three boxes, so one defect arrived as three warnings.

    `<h3>` is a block box holding a line box holding a text box, and all three
    carry the element's tag. The rule walked every box that looked like a
    heading, so a page with two stranded headings reported six findings and the
    summary line counted them as six defects.
    """
    body = '<p style="margin-bottom:230mm">filler</p><h3>Stranded heading</h3>'
    found = [f for f in inspect(doc(body), Path("/tmp")) if f.rule == "orphan-heading"]
    assert len(found) == 1, [str(f) for f in found]


def test_a_heading_is_measured_from_its_ink_not_its_margin():
    """What deduplicating exposed: the block box is not where the type prints.

    Reporting once means reporting the outermost box, and *that* box's `_rect`
    top is the margin edge — so a heading carrying `margin-top` claims its foot
    that much higher than it prints, counting space the reader never sees as
    room. The line box used to mask this by matching too, which is the only
    reason the old rule landed on the right number.

    Here the ink ends 13mm from the foot and the margin edge 25mm from it:
    stranded to a reader either way.
    """
    body = (
        '<p style="margin-bottom:227mm">filler</p>'
        '<h3 style="margin-top:12mm;margin-bottom:0">Stranded heading</h3>'
    )
    assert "orphan-heading" in rules_on(doc(body, NO_BODY_MARGIN), 1)


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
    """A document is allowed to stop where it stops.

    The fixture carries the last page to about half, because "short" and
    "empty" are different claims: the second is `page-widow`, below.
    """
    body = (
        FILLED_PAGE
        + f'<p style="{FLAT};margin-bottom:120mm">the last page opens</p>'
        + f'<p style="{FLAT}">and ends a little past halfway down</p>'
    )
    found = rules_on(doc(body), 2)
    assert "thin-page" not in found
    assert "page-widow" not in found


# ── tail widows: the under-fill the fill rule could not see ───────────────


def test_a_document_that_spills_a_few_lines_onto_a_last_page_is_flagged():
    """The blind spot that shipped an invoice as two pages.

    `thin-page` excused the last page outright, so a single-sheet document
    that was not a single sheet passed with a clean report — the one defect an
    invoice cannot ship with. Being last excuses a page that ends; it cannot
    excuse a page that holds three lines.
    """
    body = FILLED_PAGE + f'<p style="{FLAT}">three words spill</p>'
    assert "page-widow" in rules_on(doc(body), 2)


def test_a_section_tail_that_widows_before_a_chapter_break_is_flagged():
    """The mirror case, and the more common one.

    A page is excused when the page after it begins with an authored break,
    on the reasoning that it is short because the next section demanded a
    fresh one. That is right for a section ending at 85% and wrong for one
    whose last line widowed at 11% — both precede an authored break, and the
    old rule could not tell them apart.
    """
    body = (
        f'<p style="{FLAT}">one line, then a chapter break</p>'
        '<div style="break-before:page"><h2>Second section</h2><p>text</p></div>'
    )
    assert "page-widow" in rules_on(doc(body), 1)


def test_a_one_page_document_is_never_a_widow():
    """Nothing widowed: there is no earlier page for the content to sit on.

    A one-page letter or a short invoice is allowed to use half a sheet, and
    reporting it would make the rule unusable for exactly the document types
    `data-furniture="none"` exists for.
    """
    body = f'<p style="{FLAT}">a letter of three lines, which is a whole document</p>'
    assert "page-widow" not in rules(doc(body))


# ── a bleed that stops short of the paper ─────────────────────────────────


def test_a_full_bleed_block_at_the_head_of_a_page_is_flagged():
    """The exhibition guide's plate, and the first composition defect measured.

    A block that bleeds runs to the left and right edges of the paper by
    cancelling the page margin. It cannot do the same upwards — content is laid
    out inside the page box, and the top margin is not content's to enter — so
    a bleed placed first on a page lands under a strip of white as tall as that
    margin. Three edges reach the paper and one stops short, which reads as a
    misprint rather than a decision.
    """
    body = f'<div style="{BLEED};background:#123456;height:60mm"></div><p>Body text.</p>'
    assert "half-bleed" in rules_on(doc(body, NO_BODY_MARGIN), 1)


def test_a_full_bleed_block_below_the_first_line_is_left_alone():
    """A band between paragraphs is the job `.bleed` exists for.

    The defect is the strip above it, and there is no strip when something is
    printed above it — so the rule has to be about position on the page, not
    about bleeding.
    """
    body = f'<p>Opening prose.</p><div style="{BLEED};background:#123456;height:60mm"></div>'
    assert "half-bleed" not in rules(doc(body, NO_BODY_MARGIN))


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
