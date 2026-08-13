"""Themes must be genuinely distinct, and structure must not leak into them."""

from __future__ import annotations

import re
from pathlib import Path

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
        ".cover::before",
        ".doc-head",
        ".eyebrow",
        ".facts",
        ".signature",
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


def test_the_shared_page_is_styled_for_a_screen():
    """`folio build` also writes an HTML page, and it was unusable.

    Every gutter in the kit comes from `@page`, which a browser ignores — so
    the shared page had no margins, no measure, and a cover locked to 297mm.
    It rendered, so nothing ever failed.
    """
    css = css_text()
    assert "@media screen" in css, "the shared page has no screen styles at all"
    screen = css[css.index("@media screen") :]
    for prop in ("max-width", "margin", "padding"):
        assert prop in screen, f"screen block sets no {prop}"


@pytest.mark.parametrize("name", THEMES)
def test_screen_styles_never_reach_the_paper(name):
    """Print is the product; the screen block must not move a single box.

    WeasyPrint lays out for print media, so a `@media screen` rule is inert —
    but only while it stays inside the media block. The two asserts below are
    the screen block's most destructive escapes: a cover that stops filling
    its page, and a grey ground printed behind every sheet.
    """
    weasyprint = pytest.importorskip("weasyprint")
    from folio.check import MM, _srgb, _walk

    html = (
        f"<!DOCTYPE html><html><head><style>{css_text(name)}</style></head>"
        '<body><section class="cover"><h1>Title</h1></section><p>body</p></body></html>'
    )
    page = weasyprint.HTML(string=html).render().pages[0]

    covers = [
        b.border_height()
        for b in _walk(page._page_box)
        if getattr(b, "element", None) is not None
        and "cover" in (b.element.attrib.get("class") or "").split()
        and isinstance(getattr(b, "height", None), int | float)
    ]
    assert covers, f"{name}: no cover box laid out"
    # Measured on the BORDER box, not the content box. A cover carries a
    # plate band as top padding (`--cover-plate-h`, 158mm in report), so its
    # content box is legitimately short while the page is still full — the
    # content-box reading called that a collapse. The border box is 297mm in
    # every theme, and 198mm or less the moment `height:auto` escapes.
    assert max(covers) / MM > 240, (
        f"{name}: cover collapsed to {max(covers) / MM:.0f}mm — `height:auto` escaped @media screen"
    )

    root = next(b for b in _walk(page._page_box) if getattr(b, "element_tag", None) == "html")
    ground = _srgb(root.style["background_color"])
    assert ground is None or ground[3] == 0, (
        f"{name}: the page ground is painted {ground} — the screen background escaped @media screen"
    )


@pytest.mark.parametrize("name", THEMES)
def test_a_bleeding_plate_reaches_both_page_edges(name):
    """`.bleed` cancels the page gutter with negative margins, and a theme rule
    using the `margin` shorthand silently resets them.

    base.css sets `.bleed` before any theme is appended, so a theme selector of
    equal specificity wins. When that happened the plate kept its full width but
    lost the left pull: it hung 24mm off the right edge and left a gutter-wide
    gap on the left. It still rendered.
    """
    weasyprint = pytest.importorskip("weasyprint")
    from folio.check import MM, _walk

    html = (
        f"<!DOCTYPE html><html><head><style>{css_text(name)}</style></head>"
        '<body><p>text</p><div class="plate bleed">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"></svg>'
        "</div></body></html>"
    )
    page = weasyprint.HTML(string=html).render().pages[0]
    plate = next(
        b
        for b in _walk(page._page_box)
        if getattr(b, "element", None) is not None
        and "plate" in (b.element.attrib.get("class") or "").split()
    )
    # position_x is the margin-box origin, so with a negative margin it sits
    # inside the ink. The visible edge is the border box.
    left = plate.position_x + plate.margin_left
    right = left + plate.border_width()
    assert abs(left) / MM < 1, f"{name}: plate starts {left / MM:.1f}mm in, not at the edge"
    assert abs(right - page.width) / MM < 1, (
        f"{name}: plate ends {right / MM:.1f}mm on a {page.width / MM:.0f}mm page"
    )


@pytest.mark.parametrize("name", THEMES)
def test_the_cover_band_survives_the_rtl_mirror(name):
    """Nothing rendered RTL, so an RTL-only regression could not be seen.

    The mirror layer used to offset two decorative circles the split-band
    redesign deleted. The offsets outlived them and re-anchored the band to
    `left: -60mm; right: auto`, collapsing it — every Arabic, Hebrew, Persian
    and Urdu cover lost its band entirely and every test still passed.
    """
    weasyprint = pytest.importorskip("weasyprint")
    from folio.check import MM, _walk

    def band(rtl: bool) -> tuple[float, float]:
        """The band's own box — `.cover` is 210mm either way and proves nothing."""
        html = (
            f'<!DOCTYPE html><html lang="ar" dir="rtl"><head>'
            f"<style>{css_text(name, rtl=rtl)}</style></head>"
            '<body><section class="cover"><h1>عنوان</h1></section><p>x</p></body></html>'
        )
        page = weasyprint.HTML(string=html).render().pages[0]
        box = next(
            b
            for b in _walk(page._page_box)
            if str(getattr(b, "element_tag", "")).endswith("::before")
        )
        return box.position_x / MM, box.border_width() / MM

    (ltr_x, ltr_w), (rtl_x, rtl_w) = band(False), band(True)
    assert abs(ltr_x) < 1 and abs(ltr_w - 210) < 1, (
        f"{name}: LTR band at {ltr_x:.0f}mm × {ltr_w:.0f}mm"
    )
    assert abs(rtl_x - ltr_x) < 1 and abs(rtl_w - ltr_w) < 1, (
        f"{name}: RTL band is {rtl_w:.0f}mm at x={rtl_x:.0f}mm, "
        f"against LTR {ltr_w:.0f}mm at x={ltr_x:.0f}mm"
    )


@pytest.mark.parametrize("name", THEMES)
def test_theme_styles_every_documented_callout_tone(name):
    """A tone is a component, and base.css paints none of them.

    `test_theme_restyles_every_component` checks `.callout` and stops there, so
    a theme could style the box and skip a tone — which is exactly what
    happened: `.callout.info` was unstyled in `editorial` and `minimal` while
    the shipped example used it, so in half the themes that block rendered as a
    plain callout and nothing said so.
    """
    css = theme_path(name).read_text(encoding="utf-8")
    documented = ("info", "ok", "warn", "risk")
    for tone in documented:
        assert f".callout.{tone}" in css, f"{name} never styles .callout.{tone}"


def test_the_documented_callout_tones_match_the_docs():
    """Guards the list above against COMPONENTS.md drifting away from it."""
    root = Path(__file__).resolve().parents[1]
    components = root / "docs" / "COMPONENTS.md"
    if not components.exists():  # pragma: no cover - installed without sources
        pytest.skip("docs not present")
    line = next(
        ln for ln in components.read_text(encoding="utf-8").splitlines() if ln.startswith("Tones:")
    )
    assert set(re.findall(r"`(\w+)`", line)) == {"info", "ok", "warn", "risk"}, line


def test_missing_matplotlib_names_the_extra(monkeypatch):
    """The first thing a fresh install does is `folio init && folio build`.

    matplotlib is deliberately an extra, so on a bare install that first build
    dies inside the charts.py folio itself just scaffolded. A bare
    `No module named 'matplotlib'` leaves the reader to guess which extra
    carries it — and `pip install matplotlib` is the wrong lesson, because the
    next missing piece is WeasyPrint. The message has to name the extra.
    """
    import builtins

    from folio import theme

    real_import = builtins.__import__

    def without_matplotlib(name, *args, **kwargs):
        if name == "matplotlib" or name.startswith("matplotlib."):
            # CPython's import machinery always populates `.name`; so must this.
            raise ModuleNotFoundError(f"No module named '{name}'", name=name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_matplotlib)

    with pytest.raises(ModuleNotFoundError) as excinfo:
        theme.use()

    message = str(excinfo.value)
    assert "folio-press[charts]" in message, f"no extra named in: {message}"
    assert "folio doctor" in message, f"no diagnosis offered in: {message}"


def test_a_broken_matplotlib_is_not_reported_as_a_missing_one(monkeypatch):
    """Only matplotlib's own absence earns the install hint.

    matplotlib importing but failing on a dependency of its own is a different
    fault, and telling that reader to install the charts extra sends them to
    reinstall the one thing they already have.
    """
    import builtins

    from folio import theme

    real_import = builtins.__import__

    def with_a_broken_numpy(name, *args, **kwargs):
        if name == "matplotlib" or name.startswith("matplotlib."):
            raise ModuleNotFoundError("No module named 'numpy'", name="numpy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", with_a_broken_numpy)

    with pytest.raises(ModuleNotFoundError) as excinfo:
        theme.use()

    assert "folio-press[charts]" not in str(excinfo.value)
    assert excinfo.value.name == "numpy"


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


@pytest.mark.parametrize("name", THEMES)
def test_furniture_none_strips_every_running_element(name):
    """An invoice, a letter and a one-pager carry no running furniture.

    Without this a single-sheet document still printed a running title, a
    section rail, `1 / 1`, and a footer line — page chrome for a page that has
    nowhere to run to.
    """
    weasyprint = pytest.importorskip("weasyprint")

    def margin_text(attr: str) -> list[str]:
        html = (
            f"<!DOCTYPE html><html><head><style>{css_text(name)}</style></head>"
            f'<body {attr} data-title="Invoice 2026-014" data-footer="Acme Ltd">'
            '<h2 class="section">Invoice</h2><p>Line items.</p></body></html>'
        )
        page = weasyprint.HTML(string=html).render().pages[0]
        found: list[str] = []

        def rec(box):
            text = getattr(box, "text", None)
            if text and text.strip():
                found.append(text.strip())
            for child in getattr(box, "children", []):
                rec(child)

        for child in page._page_box.children:
            if "Margin" in type(child).__name__:
                rec(child)
        return found

    assert margin_text(""), f"{name}: the default page lost its furniture"
    bare = margin_text('data-furniture="none"')
    assert bare == [], f"{name}: furniture survived data-furniture=none — {bare}"


@pytest.mark.parametrize("name", THEMES)
def test_a_document_title_outranks_a_section_heading(name):
    """`<h1>` outside `.cover` was never styled, so it fell to the UA default.

    Measured before the fix: 19.2pt in `minimal`, where `h2.section` is 22pt —
    the document title rendered *smaller* than the sections beneath it. Any
    document without a cover page shipped an inverted hierarchy.
    """
    weasyprint = pytest.importorskip("weasyprint")
    from folio.check import _walk

    html = (
        f"<!DOCTYPE html><html><head><style>{css_text(name)}</style></head>"
        '<body><div class="doc-head"><h1>Document title</h1></div>'
        '<h2 class="section">A section</h2><p>body</p></body></html>'
    )
    page = weasyprint.HTML(string=html).render().pages[0]
    size = {}
    for box in _walk(page._page_box):
        tag = getattr(box, "element_tag", None)
        if tag in ("h1", "h2") and tag not in size:
            size[tag] = box.style["font_size"]
    assert size.get("h1") and size.get("h2"), f"{name}: headings did not lay out"
    assert size["h1"] > size["h2"], (
        f"{name}: h1 is {size['h1']:.1f}px against h2.section {size['h2']:.1f}px — inverted"
    )


@pytest.mark.parametrize("name", THEMES)
def test_only_the_last_totals_row_carries_a_rule(name):
    """A Subtotal / Tax / Total block drew three stacked hairlines.

    Every theme put `border-top` on every `tfoot` row unconditionally, so the
    amount due carried no more weight than the subtotal — the difference
    between a finished invoice and an unfinished one.
    """
    weasyprint = pytest.importorskip("weasyprint")
    from folio.check import _walk

    html = (
        f"<!DOCTYPE html><html><head><style>{css_text(name)}</style></head>"
        "<body><table><thead><tr><th>Item</th><th>Amount</th></tr></thead>"
        "<tbody><tr><td>Work</td><td>1000</td></tr></tbody>"
        "<tfoot>"
        "<tr><td>Subtotal</td><td>1000</td></tr>"
        "<tr><td>VAT</td><td>200</td></tr>"
        "<tr class='total'><td>Total</td><td>1200</td></tr>"
        "</tfoot></table></body></html>"
    )
    page = weasyprint.HTML(string=html).render().pages[0]
    ruled = []
    for box in _walk(page._page_box):
        el = getattr(box, "element", None)
        if el is not None and str(getattr(el, "tag", "")) == "td":
            width = box.style["border_top_width"]
            if width:
                ruled.append((el.text or "").strip())
    assert "Subtotal" not in ruled, f"{name}: the subtotal row is still ruled — {ruled}"
    assert "Total" in ruled, f"{name}: the grand total carries no rule — {ruled}"


@pytest.mark.parametrize("name", THEMES)
def test_every_stylesheet_parses_without_errors(name):
    """Stray text inside a rule is silently fatal for everything after it.

    A comment closed one paragraph early left prose sitting bare inside
    `:root {}`. CSS recovers by discarding to the next semicolon, which took
    the font tokens with it, and the only thing that noticed was a heading
    that came out at the default size — two layers away from the cause, in a
    test about hierarchy. A stylesheet that does not parse should say so
    itself.
    """
    tinycss2 = pytest.importorskip(
        "tinycss2", reason="the CSS parser arrives with WeasyPrint; skipped in degraded runs"
    )

    css = css_text(name)
    errors = []
    for rule in tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True):
        if rule.type == "error":
            errors.append(f"{rule.source_line}: {rule.message}")
        for node in tinycss2.parse_blocks_contents(getattr(rule, "content", None) or []):
            if node.type == "error":
                errors.append(f"{node.source_line}: {node.message}")
    assert not errors, f"{name}: " + "; ".join(errors[:5])
