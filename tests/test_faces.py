"""What face actually set this text? Not what the stylesheet asked for."""

from __future__ import annotations

import pytest

pytest.importorskip("weasyprint", reason="faces reads WeasyPrint's pango layout")

from conftest import needs_faces  # noqa: E402
from weasyprint import HTML  # noqa: E402

from folio.faces import feature_tags, resolved_runs  # noqa: E402

pytestmark = needs_faces


def _first_textbox(html: str):
    doc = HTML(string=html).render()

    def walk(b):
        yield b
        for c in getattr(b, "children", ()) or ():
            yield from walk(c)

    for box in walk(doc.pages[0]._page_box):
        if type(box).__name__ == "TextBox":
            return box
    raise AssertionError("no TextBox in fixture")


def test_a_latin_run_resolves_to_the_family_it_asked_for():
    box = _first_textbox('<style>p{font-family:"DejaVu Serif"}</style><p>Hello</p>')
    assert [family for _, family in resolved_runs(box)] == ["DejaVu Serif"]


def test_a_run_the_stack_cannot_set_resolves_to_something_else():
    """The defect, measured: a Latin-only stack still renders Hangul.

    Which face fontconfig picks is machine-dependent, so the assertion is that
    it is *not* the family that was asked for — that is the whole finding.
    """
    box = _first_textbox('<style>p{font-family:"DejaVu Serif"}</style><p lang="ko">한국어</p>')
    families = {family for _, family in resolved_runs(box)}
    assert families and "DejaVu Serif" not in families


def test_feature_tags_tell_real_small_caps_from_none():
    has = _first_textbox('<style>p{font-family:"Noto Serif"}</style><p>Nato</p>')
    hasnt = _first_textbox('<style>p{font-family:"DejaVu Serif"}</style><p>Nato</p>')
    assert "smcp" in feature_tags(has)
    assert "smcp" not in feature_tags(hasnt)
