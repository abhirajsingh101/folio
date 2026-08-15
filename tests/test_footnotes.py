"""Footnotes: a note leaves the sentence and lands at the foot of its page."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("weasyprint", reason="footnotes are a print-layout feature")

from weasyprint import HTML  # noqa: E402

from folio.assets import css_text  # noqa: E402

PAGE = "@page{size:A4;margin:20mm}"


def _render(body: str):
    html = (
        f"<!DOCTYPE html><html><head><style>{css_text()}{PAGE}</style></head>"
        f"<body>{body}</body></html>"
    )
    return HTML(string=html, base_url=str(Path("/tmp"))).render().pages[0]


def _walk(box):
    yield box
    for child in getattr(box, "children", ()) or ():
        yield from _walk(child)


def _texts(page):
    return [(b.position_y, b.text) for b in _walk(page._page_box) if type(b).__name__ == "TextBox"]


def test_a_note_moves_to_the_foot_of_its_page():
    """The note is authored inline and must not render inline.

    Asserted by position rather than by presence: a `.fn` that simply stayed
    in the sentence would still put its words on the page, and that is the
    failure this is written to catch.
    """
    page = _render(
        '<p>The claim in the body<span class="fn">And the qualification.</span> '
        "continues after it.</p>"
    )
    found = _texts(page)
    body = [y for y, t in found if "claim in the body" in t]
    note = [y for y, t in found if "qualification" in t]
    assert body and note, f"missing text: {found}"
    assert note[0] > body[0] + 200, "the note did not leave the sentence"


def test_the_call_is_numbered_and_the_marker_matches():
    page = _render(
        '<p>First<span class="fn">One.</span> and second<span class="fn">Two.</span>.</p>'
    )
    joined = "".join(t for _, t in _texts(page))
    assert "1" in joined and "2" in joined, joined
