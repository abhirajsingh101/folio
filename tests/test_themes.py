"""Themes must be genuinely distinct, and structure must not leak into them."""

from __future__ import annotations

import re

import pytest

from folio.assets import DEFAULT_THEME, base_path, css_text, theme_names, theme_path
from folio.build import BuildError, detect_theme

THEMES = theme_names()


def test_there_are_several_directions():
    assert len(THEMES) >= 4
    assert THEMES[0] == DEFAULT_THEME, "default theme must sort first"


@pytest.mark.parametrize("name", THEMES)
def test_theme_defines_the_token_contract(name):
    css = theme_path(name).read_text(encoding="utf-8")
    for token in ("--brand", "--ink", "--rule"):
        assert token in css, f"{name} does not set {token}"


@pytest.mark.parametrize("name", THEMES)
def test_theme_restyles_every_component(name):
    """A theme that skips a component inherits nothing — base.css has no look."""
    css = theme_path(name).read_text(encoding="utf-8")
    for sel in (
        ".cover",
        ".toc",
        "h2.section",
        ".metric",
        ".plate",
        "figcaption",
        "thead th",
        ".pill",
        ".callout",
        ".pullquote",
        "pre",
        ".timeline",
    ):
        assert sel in css, f"{name} never styles {sel}"


@pytest.mark.parametrize("name", THEMES)
def test_theme_carries_no_structure(name):
    """Layout mechanics belong in base.css; a theme repeating them is a smell."""
    css = theme_path(name).read_text(encoding="utf-8")
    for prop in ("break-inside:", "display: table-header-group", "string-set:"):
        assert prop not in css.replace(" ", "").replace("break-inside:", "break-inside:"), (
            f"{name} restates structure ({prop})"
        )


def test_chart_text_colours_clear_aa():
    """Chart labels are text, and unmeasurable from the document.

    `theme.use` emits them as outlines (`svg.fonttype='path'`) so a figure
    renders identically wherever the PDF is built — a deliberate trade that
    also means no document-time rule can ever see inside. `figure-rescaled`
    covers their effective *size*; their colour can only be enforced here,
    where it is chosen.
    """
    from folio import theme
    from folio.check import contrast_ratio

    def rgb(h: str) -> tuple[float, float, float]:
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    paper = (1.0, 1.0, 1.0)
    for name, palette in theme.PALETTES.items():
        for slot in ("ink", "mute"):
            ratio = contrast_ratio(rgb(palette[slot]), paper)
            assert ratio >= 4.5, f"{name} chart {slot} is {ratio:.2f}:1 on paper"


def test_status_fills_take_white_labels():
    """The bars carry their value in white; the fill has to support it."""
    from folio import theme
    from folio.check import contrast_ratio

    def rgb(h: str) -> tuple[float, float, float]:
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    for name in ("SUCCESS", "WARNING", "ERROR"):
        ratio = contrast_ratio((1.0, 1.0, 1.0), rgb(getattr(theme, name)))
        assert ratio >= 4.5, f"white on {name} is {ratio:.2f}:1"


def test_base_carries_no_palette():
    """base.css may define token defaults but must not paint components.

    Only the `:root` contract is exempt. The `@page` block is *included*: it
    used to hardcode three greys on the belief that var() cannot resolve in a
    margin box, which is wrong — it resolves whenever the property is declared
    on `:root`. See docs/GOTCHAS.md.
    """
    body = base_path().read_text(encoding="utf-8")
    body = body[body.index("/* ── Page furniture ──") :]  # past the :root contract
    assert "linear-gradient" not in body
    hexes = re.findall(r"#[0-9a-fA-F]{6}", body)
    assert not hexes, f"base.css hard-codes colours outside @page: {set(hexes)}"


@pytest.mark.parametrize("name", THEMES)
def test_composed_stylesheet_has_both_layers(name):
    css = css_text(name)
    assert "folio base (structure)" in css
    assert f"folio theme: {name}" in css
    assert css.index("folio base") < css.index(f"folio theme: {name}"), "theme must win"


def test_themes_are_visually_distinct():
    """Guards against a 'theme' that is only a colour swap."""
    sigs = {}
    for name in THEMES:
        css = theme_path(name).read_text(encoding="utf-8")
        sigs[name] = (
            re.search(r"--brand:\s*(\S+);", css).group(1),
            "linear-gradient" in css,
            len(re.findall(r"text-transform:\s*uppercase", css)),
        )
    assert len(set(s[0] for s in sigs.values())) == len(THEMES), "brand colours collide"


# ── declaration on the document ───────────────────────────────────────────


def test_default_theme_when_undeclared():
    assert detect_theme("<html><body>x</body></html>") == DEFAULT_THEME


@pytest.mark.parametrize("name", THEMES)
def test_theme_read_off_the_body(name):
    assert detect_theme(f'<html><body data-theme="{name}" data-title="t">x</body></html>') == name


def test_unknown_theme_is_a_clear_error():
    with pytest.raises(BuildError, match="unknown theme"):
        detect_theme('<body data-theme="chartreuse">')
