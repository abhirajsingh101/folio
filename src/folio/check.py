"""Verify a rendered document, rather than producing one and hoping.

Print bugs are silent by nature: the PDF is valid and merely looks wrong. Every
entry in docs/GOTCHAS.md is something that shipped a perfectly well-formed file
— text overrunning a box, a table stranding two rows on an empty page, a
caption divorced from its figure.

WeasyPrint exposes its layout tree, so those are not matters of opinion. Each
check below measures actual box geometry on the actual rendered pages.

The checks encode failures that really happened while building folio, which is
why they are worth running: they are not hypothetical.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ERROR, WARN = "error", "warn"

# A page is "thin" below this fraction of its content height.
THIN_PAGE_FILL = 0.45
# A page that is *meant* to end early — the last one, or the one before an
# authored break — is a widow below this. Measured rather than guessed: across
# folio's five examples in all four directions, 52 pages end early, and their
# fills fall either side of a gap between 21% and 34%. Below the gap the page
# reads as a spill; above it, as an ending.
WIDOW_PAGE_FILL = 0.25
# Text below this size (px) is not reliably legible in print.
MIN_FONT_PX = 6.0
# A heading with less than this much room beneath it is stranded.
ORPHAN_HEADING_MM = 22
# Overflow smaller than this is rounding, not a bug.
OVERFLOW_TOLERANCE_PX = 1.0
# Raster upscaled beyond this looks soft on paper.
MAX_IMAGE_UPSCALE = 1.15
# A vector this far off its authored size carries type that no longer matches
# the page. Column width shifts with each theme's page margins, so exact is
# not achievable and a few percent is invisible; this catches the mistakes
# that change what the labels look like.
FIGURE_SCALE_TOL = 0.10
# WCAG AA: body text needs 4.5:1, large text 3:1. Print is if anything less
# forgiving than a screen — no backlight, and ink dries lighter than it renders.
AA_NORMAL = 4.5
AA_LARGE = 3.0
# WCAG's "large" is 18pt, or 14pt when bold, expressed here in CSS px.
LARGE_PX = 24.0
LARGE_BOLD_PX = 18.6
BOLD = 700

# Two type sizes closer than this are the same size to a reader. Set below the
# finest deliberate step in the shipped themes (1.4%), measured not guessed —
# widen it and real scale steps start reporting as drift.
SAME_SIZE_PCT = 1.0

MM = 96 / 25.4  # WeasyPrint lays out in CSS px
PT = 96 / 72
PX_IN = 96
PAPER = (1.0, 1.0, 1.0)


@dataclass
class Finding:
    rule: str
    severity: str
    page: int
    detail: str
    hint: str = ""

    def __str__(self) -> str:
        mark = "✗" if self.severity == ERROR else "!"
        return f"  {mark} p{self.page:<3} {self.rule:<18} {self.detail}"


class CheckUnavailable(RuntimeError):
    """Raised when the layout tree cannot be obtained."""


# ── layout tree helpers ───────────────────────────────────────────────────


def _walk(box):
    yield box
    for child in getattr(box, "children", ()) or ():
        yield from _walk(child)


def _content_root(page):
    """The <html> box.

    Running headers and footers are MarginBox children of the PageBox and live
    outside the content frame by design, so measuring from the PageBox reports
    every page as overflowing. Walk the document, not the page furniture.
    """
    for box in _walk(page._page_box):
        if getattr(box, "element_tag", None) == "html":
            return box
    return page._page_box


def _parent_map(root) -> dict:
    parents = {}
    for box in _walk(root):
        for child in getattr(box, "children", ()) or ():
            parents[id(child)] = box
    return parents


def _rect(box) -> tuple[float, float, float, float] | None:
    try:
        x, y = box.position_x, box.position_y
        w, h = box.width, box.height
    except AttributeError:
        return None
    if None in (x, y, w, h) or not isinstance(w, int | float) or not isinstance(h, int | float):
        return None
    return (x, y, x + w, y + h)


def _border_rect(box) -> tuple[float, float, float, float] | None:
    """The box as it is painted, margins excluded.

    `_rect` reads `position_x`, which is the *margin* edge, alongside `width`,
    which is the content width — near enough for a box with no margins, and
    wrong by the margin for one that has them. A bleed is a negative margin, so
    it is precisely the case that mix cannot measure.
    """
    try:
        x, y = box.border_box_x(), box.border_box_y()
        w, h = box.border_width(), box.border_height()
    except (AttributeError, TypeError):
        return None
    if None in (x, y, w, h):
        return None
    return (x, y, x + w, y + h)


def _is_text(box) -> bool:
    return type(box).__name__ == "TextBox" and bool((getattr(box, "text", "") or "").strip())


def _label(box, parents: dict) -> str:
    """A tag the author can actually find, walking up if the box is anonymous."""
    node = box
    while node is not None:
        tag = getattr(node, "element_tag", None)
        if tag:
            return tag
        at = getattr(node, "at_keyword", None)
        if at:
            return at  # page furniture: "@bottom-right" and friends
        node = parents.get(id(node))
    return "block"


def _content_frame(page) -> tuple[float, float, float, float]:
    """The page's usable area.

    Left/right come from the root block, but the bottom must come from the
    PageBox: the html box is only as tall as its content, so measuring against
    it reports every short page as overflowing.
    """
    pb = page._page_box
    usable_h = getattr(pb, "height", None) or page.height
    for box in _walk(pb):
        if getattr(box, "element_tag", None) == "html":
            r = _rect(box)
            if r:
                return (r[0], r[1], r[2], r[1] + usable_h)
    return (0.0, 0.0, page.width, page.height)


def _margin_boxes(page):
    """Running headers and footers.

    They are PageBox children rather than document content, which is why the
    geometry checks skip them — and exactly why their colour never gets a
    second look. Each is walked as its own root so the page background is not
    composited twice.
    """
    for child in getattr(page._page_box, "children", ()) or ():
        if type(child).__name__ == "MarginBox":
            yield child


def _page_kind(page) -> str:
    """Cover and contents pages are deliberately sparse; do not flag them.

    Identified by the named page (`@page cover`), which WeasyPrint reports on
    the PageBox. Boxes carry no class attribute, so this is the only reliable
    signal — an earlier version keyed off `element_class` and silently never
    matched, flagging every cover as a thin page.
    """
    page_type = getattr(page._page_box, "page_type", None)
    name = getattr(page_type, "name", None)
    if name in ("cover", "frontmatter"):
        return name
    return "body"


# ── colour ────────────────────────────────────────────────────────────────


def _srgb(color) -> tuple[float, float, float, float] | None:
    """(r, g, b, alpha) in sRGB, or None if the value is not a usable colour.

    Values reach us as tinycss2 `Color`, which may be in any CSS colour space;
    `lab()` and `oklch()` are legal in a stylesheet and must be converted, not
    read coordinate-wise.
    """
    if color is None:
        return None
    try:
        srgb = color if getattr(color, "space", None) == "srgb" else color.to("srgb")
        r, g, b = srgb.coordinates
        return (float(r), float(g), float(b), float(srgb.alpha))
    except Exception:
        return None


def _over(rgba, backdrop) -> tuple[float, float, float]:
    """Composite a translucent colour onto an opaque one (source-over)."""
    alpha = rgba[3]
    return tuple(c * alpha + b * (1 - alpha) for c, b in zip(rgba[:3], backdrop, strict=True))


def _luminance(rgb) -> float:
    def channel(c: float) -> float:
        c = min(max(c, 0.0), 1.0)
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg) -> float:
    """WCAG relative-luminance ratio: 1.0 is invisible, 21.0 is black on white."""
    lo, hi = sorted((_luminance(fg), _luminance(bg)))
    return (hi + 0.05) / (lo + 0.05)


def _hex(rgb) -> str:
    return "#" + "".join(f"{round(min(max(c, 0.0), 1.0) * 255):02x}" for c in rgb)


def _paints_an_image(style) -> bool:
    for layer in style["background_image"] or ():
        kind = layer[0] if isinstance(layer, tuple | list) else layer
        if kind != "none":
            return True
    return False


def _backdrop(box, parents: dict, paper) -> tuple[float, float, float] | None:
    """The colour actually behind this text.

    Backgrounds are painted by ancestors, so the only way to know what a glyph
    sits on is to walk up collecting layers and composite them onto the page.
    Returns None when anything in the stack paints an image or a gradient: the
    backdrop is then genuinely unknowable, and silence beats a confident wrong
    answer.
    """
    layers = []
    node = box
    while node is not None:
        style = getattr(node, "style", None)
        if style is not None:
            if _paints_an_image(style):
                return None
            rgba = _srgb(style["background_color"])
            if rgba and rgba[3] > 0:
                layers.append(rgba)
        node = parents.get(id(node))
    backdrop = paper
    for rgba in reversed(layers):  # outermost first
        backdrop = _over(rgba, backdrop)
    return backdrop


def _paper(page) -> tuple[float, float, float] | None:
    """What the sheet is painted before the document draws anything.

    A cover that sets `@page cover { background: … }` paints the page box, not
    a block inside it. Read only the page background here; margin boxes are
    checked separately.
    """
    style = getattr(page._page_box, "style", None)
    if style is None:
        return PAPER
    if _paints_an_image(style):
        return None
    rgba = _srgb(style["background_color"])
    if rgba and rgba[3] > 0:
        return _over(rgba, PAPER)
    return PAPER


def _is_large(style) -> bool:
    size = style["font_size"]
    weight = style["font_weight"]
    try:
        bold = int(weight) >= BOLD
    except (TypeError, ValueError):
        bold = str(weight) in ("bold", "bolder")
    return size >= (LARGE_BOLD_PX if bold else LARGE_PX)


# ── checks ────────────────────────────────────────────────────────────────


def _check_overflow(root, n, frame) -> list[Finding]:
    """Content running past the page edge. The classic silent print bug."""
    _, _, right, bottom = frame
    parents = _parent_map(root)
    out = []
    seen = set()
    for box in _walk(root):
        r = _rect(box)
        if not r or not _is_text(box):
            continue
        tag = _label(box, parents)
        if r[2] > right + OVERFLOW_TOLERANCE_PX:
            key = ("h", tag, round(r[2]))
            if key not in seen:
                seen.add(key)
                over = (r[2] - right) / MM
                out.append(
                    Finding(
                        "overflow-x",
                        ERROR,
                        n,
                        f"<{tag}> runs {over:.1f}mm past the right edge",
                        "a flex child usually needs min-width:0; see `folio gotchas`",
                    )
                )
        if r[3] > bottom + OVERFLOW_TOLERANCE_PX:
            key = ("v", tag, round(r[3]))
            if key not in seen:
                seen.add(key)
                out.append(
                    Finding(
                        "overflow-y",
                        ERROR,
                        n,
                        f"<{tag}> runs past the bottom margin",
                        "the block is taller than a page and cannot break",
                    )
                )
    return out


FORCED_BREAK = frozenset({"page", "always", "left", "right", "recto", "verso"})


def _authored_page_starts(pages) -> list[bool]:
    """Per page: did an element carrying `break-before` actually begin on it?

    A page can be short for two reasons, and by fill alone they look the same:
    the author demanded the next page, or a block on this one would not fit.
    Only the second is a defect — folio's own `.section-wrap` breaks this way,
    so without the distinction every short section reported a problem whose
    suggested remedy did not apply to it.

    Finding `break-before: page` overhead is not enough. A section wrapper
    stays an ancestor of every page its section runs onto, so the break it
    caused may be two pages back. WeasyPrint exposes no marker for a
    continuation fragment, so "begins here" is established the only way left:
    the element was on no earlier page.
    """
    seen: set[int] = set()
    authored: list[bool] = []
    for page in pages:
        root = _content_root(page)
        parents = _parent_map(root)

        chain, node = [], next((b for b in _walk(root) if _is_text(b)), None)
        while node is not None:
            element, style = getattr(node, "element", None), getattr(node, "style", None)
            if element is not None and style is not None:
                chain.append((id(element), style["break_before"]))
            node = parents.get(id(node))
        authored.append(any(brk in FORCED_BREAK and ref not in seen for ref, brk in chain))

        for box in _walk(root):
            element = getattr(box, "element", None)
            if element is not None:
                seen.add(id(element))
    return authored


def _check_thin_page(root, n, frame, total: int, kind: str, authored: bool) -> list[Finding]:
    """Under-filled pages, which arrive two ways and need different words.

    Mid-section, a short page means a block would not fit and jumped: that is
    `thin-page`, and the remedy is to reorder or to keep a table together.

    A page the author ended — the last one, or the one before a forced break —
    is short because that is where the content stopped, and for a long time
    that excused it entirely. It excused too much. A section ending at 85% is
    a chapter break; the same section ending at 11% is a tail that widowed,
    and the two are indistinguishable by cause. Both were silent, so the rule
    that exists to catch under-fill was blind to its most common form, and a
    one-sheet invoice that ran onto a second page passed clean.
    """
    if kind != "body":
        return []
    is_last = n == total
    if is_last and total == 1:
        # Nothing widowed: there is no earlier page for the content to sit on.
        # A one-page letter is allowed to use half a sheet.
        return []
    top, bottom = frame[1], frame[3]
    usable = bottom - top
    lowest = top
    for box in _walk(root):
        r = _rect(box)
        if r and _is_text(box):
            lowest = max(lowest, r[3])
    fill = (lowest - top) / usable if usable else 1.0

    if is_last or authored:
        if fill >= WIDOW_PAGE_FILL:
            return []
        return [
            Finding(
                "page-widow",
                WARN,
                n,
                (
                    f"the document ends {fill * 100:.0f}% into its last page"
                    if is_last
                    else f"a section ends {fill * 100:.0f}% into its page"
                ),
                "a tail this short reads as a spill, not an ending; tighten the "
                "copy above it, or move a block up so the page carries more",
            )
        ]

    if fill < THIN_PAGE_FILL:
        return [
            Finding(
                "thin-page",
                WARN,
                n,
                f"only {fill * 100:.0f}% full",
                "a figure, callout or table could not fit and jumped; "
                'reorder the section or use class="keep"',
            )
        ]
    return []


def _check_tiny_text(root, n) -> list[Finding]:
    out, seen = [], set()
    for box in _walk(root):
        if not _is_text(box):
            continue
        style = getattr(box, "style", None)
        if style is None:
            continue
        size = style["font_size"]
        if size < MIN_FONT_PX:
            tag = getattr(box, "element_tag", "?")
            if tag not in seen:
                seen.add(tag)
                out.append(
                    Finding(
                        "tiny-text",
                        WARN,
                        n,
                        f"<{tag}> set at {size / (96 / 72):.1f}pt",
                        f"below {MIN_FONT_PX / (96 / 72):.1f}pt is not reliably legible in print",
                    )
                )
    return out


def _check_orphan_heading(root, n, frame) -> list[Finding]:
    """A heading at the foot of a page with its content overleaf."""
    bottom = frame[3]
    out = []
    for box in _walk(root):
        tag = getattr(box, "element_tag", None)
        if tag not in ("h1", "h2", "h3", "h4"):
            continue
        r = _rect(box)
        if not r:
            continue
        room = (bottom - r[3]) / MM
        if 0 <= room < ORPHAN_HEADING_MM:
            out.append(
                Finding(
                    "orphan-heading",
                    WARN,
                    n,
                    f"<{tag}> sits {room:.0f}mm from the page foot",
                    "add break-after: avoid, or move the block",
                )
            )
    return out


def _check_half_bleed(root, n, page_width) -> list[Finding]:
    """A block that reaches the paper on both sides and stops short at the top.

    Bleeding sideways is a margin cancelled: the block is given a negative
    left and right margin and grows by as much again. Upwards there is nothing
    to cancel — content is laid out inside the page box, and the top margin is
    not content's to enter — so a bleed placed first on a page opens under a
    strip of white as tall as that margin. Three edges reach the paper, one
    does not, and the reader files it as a misprint.

    Every other rule here asks whether a measurement is out of range. This one
    asks where a component sits, which is the class of defect that has been
    escaping: nothing overflows, nothing overlaps, and the page is a perfectly
    legal object that looks like a mistake.
    """
    for box in _walk(root):  # pre-order: the outermost bleeding box wins
        r = _border_rect(box)
        if not r:
            continue
        bleeds = r[0] <= OVERFLOW_TOLERANCE_PX and r[2] >= page_width - OVERFLOW_TOLERANCE_PX
        strip = r[1]
        if not bleeds or strip <= OVERFLOW_TOLERANCE_PX:
            continue
        if _prints_above(root, r[1]):
            continue  # a band between blocks: no strip, and the job .bleed is for
        tag = getattr(box, "element_tag", None) or "block"
        return [
            Finding(
                "half-bleed",
                WARN,
                n,
                f"a full-bleed <{tag}> opens {strip / MM:.0f}mm below the page's top edge",
                "content cannot enter the page margin — inset it, or move it "
                "into the prose, where a band is meant to sit",
            )
        ]
    return []


def _prints_above(root, top: float) -> bool:
    """Is anything on this page printed clear of `top`?

    Ancestors enclose the candidate rather than sitting above it, so their
    bottoms fall below this line and they do not count — which is what makes a
    bottom-edge test enough, with no parent map to consult.
    """
    for box in _walk(root):
        r = _border_rect(box)
        if r and r[3] - r[1] > OVERFLOW_TOLERANCE_PX and r[3] <= top + OVERFLOW_TOLERANCE_PX:
            return True
    return False


def _check_text_overlap(root, n) -> list[Finding]:
    """Two pieces of text occupying the same space is never intentional.

    Two *lines* of the same piece of text are a different matter. Display type
    is routinely set below 1.1 line-height — folio's own `technical` cover uses
    1.06 — where consecutive line boxes overlap while the glyphs do not. Pairs
    from one element are therefore skipped: they are one thing, correctly set.
    """
    rects = []
    for box in _walk(root):
        if _is_text(box):
            r = _rect(box)
            if r and r[2] > r[0] and r[3] > r[1]:
                rects.append((r, getattr(box, "element_tag", "?"), getattr(box, "element", None)))
    out, reported = [], set()
    for i, (a, ta, ea) in enumerate(rects):
        for b, tb, eb in rects[i + 1 :]:
            if ea is not None and ea is eb:
                continue  # same element, wrapped across lines
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            # require a real 2-D intersection, not touching edges
            if ox > 2.0 and oy > 2.0:
                key = tuple(sorted((ta, tb)))
                if key not in reported:
                    reported.add(key)
                    out.append(
                        Finding(
                            "text-overlap",
                            ERROR,
                            n,
                            f"<{ta}> and <{tb}> overlap by {ox / MM:.1f}×{oy / MM:.1f}mm",
                            "usually an absolutely-positioned element colliding with flow content",
                        )
                    )
    return out


def _check_contrast(root, n, parents: dict, paper) -> list[Finding]:
    """Type too close in tone to what it sits on.

    Screens flatter low contrast: they are lit from behind and the reader can
    zoom. Paper does neither, so a caption that looked merely quiet in the
    browser is the one that comes back from the printer unreadable.
    """
    if paper is None:
        return []
    out, seen = [], set()
    for box in _walk(root):
        if not _is_text(box):
            continue
        style = getattr(box, "style", None)
        if style is None:
            continue
        fg = _srgb(style["color"])
        backdrop = _backdrop(box, parents, paper)
        if fg is None or backdrop is None:
            continue
        ink = _over(fg, backdrop)
        ratio = contrast_ratio(ink, backdrop)
        large = _is_large(style)
        wanted = AA_LARGE if large else AA_NORMAL
        if ratio >= wanted:
            continue
        tag = _label(box, parents)
        key = (tag, _hex(ink), _hex(backdrop))
        if key in seen:
            continue
        seen.add(key)
        size = "large text" if large else "body text"
        out.append(
            Finding(
                "low-contrast",
                ERROR if ratio < AA_LARGE else WARN,
                n,
                f"<{tag}> {_hex(ink)} on {_hex(backdrop)} is {ratio:.1f}:1",
                f"{size} wants {wanted}:1 — darken the ink or lighten the fill",
            )
        )
    return out


def _replaced(root):
    """Every box that draws an image, block or inline.

    Restricting this to InlineReplacedBox was a silent bug: folio's own
    stylesheet sets `figure img { display: block }`, so the only images the
    kit produces were the ones the check could not see.
    """
    for box in _walk(root):
        if getattr(box, "replacement", None) is not None:
            yield box


def _intrinsic_width(box) -> float | None:
    """The image's own width in CSS px, or None if it declares none.

    WeasyPrint 68 has no `intrinsic_width` attribute — the size comes from
    `get_intrinsic_size`. Reading the attribute returned None for every image,
    so the upscale rule quietly stopped firing at some point and nothing
    noticed, because it was the one rule with no test.
    """
    try:
        width, height, _ratio = box.replacement.get_intrinsic_size(1, box.style["font_size"])
    except Exception:  # pragma: no cover - defensive
        return None
    if not width or not height:
        return None
    return float(width)


def _check_image_scale(root, n) -> list[Finding]:
    """A raster blown up past its pixels looks soft on paper."""
    out = []
    for box in _replaced(root):
        if type(box.replacement).__name__ != "RasterImage":
            continue
        intrinsic, r = _intrinsic_width(box), _rect(box)
        if not r or not intrinsic:
            continue
        drawn = r[2] - r[0]
        if drawn > intrinsic * MAX_IMAGE_UPSCALE:
            out.append(
                Finding(
                    "image-upscaled",
                    WARN,
                    n,
                    f"raster drawn at {drawn / intrinsic:.1f}× its pixel width",
                    "export the figure as SVG, or at the printed size",
                )
            )
    return out


def _check_figure_scale(root, n) -> list[Finding]:
    """A vector carries type, and scaling the image scales the type with it.

    This is the blind spot every other rule had: a chart is an image, so
    measurement stopped at its edge — while inside it were tick labels and a
    legend, authored to sit with the document's own type. Draw a half-column
    figure across a full column and its 8pt labels arrive at 16pt; do the
    reverse and they arrive at 4pt, below the legibility floor, with nothing
    downstream able to tell.

    Vectors do not go soft, so this is not the raster problem wearing a
    different name — nothing is lost in resolution. What changes is the type.
    """
    out = []
    for box in _replaced(root):
        if type(box.replacement).__name__ != "SVGImage":
            continue
        intrinsic, r = _intrinsic_width(box), _rect(box)
        if not r or not intrinsic:
            continue
        drawn = r[2] - r[0]
        scale = drawn / intrinsic
        if abs(scale - 1.0) <= FIGURE_SCALE_TOL:
            continue
        out.append(
            Finding(
                "figure-rescaled",
                WARN,
                n,
                f"vector drawn at {scale:.1f}× its authored size "
                f"({intrinsic / PX_IN:.2f}in authored, {drawn / PX_IN:.2f}in drawn)",
                "author the figure at its printed width — scaling it scales "
                "every tick label with it",
            )
        )
    return out


# ── conformance: was the document built the way the kit intends? ──────────

HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _elements_in_order(pages):
    """Every source element once, in document order, with the page it starts on.

    Boxes fragment across pages and nest inside anonymous parents, so the same
    element surfaces many times over. Identity here is the element, never the
    box — otherwise one styled `<div>` reports as a dozen findings.
    """
    seen = set()
    for number, page in enumerate(pages, start=1):
        for box in _walk(page._page_box):
            el = getattr(box, "element", None)
            if el is None or id(el) in seen:
                continue
            seen.add(id(el))
            yield number, el


def _check_heading_levels(ordered) -> list[Finding]:
    """A level skipped is a level of structure claimed but never built.

    Descending h2 → h4 says "this belongs to an h3" about an h3 that does not
    exist. Climbing back up is fine: that closes sections rather than inventing
    them.
    """
    out = []
    previous = None
    for page, el in ordered:
        tag = str(getattr(el, "tag", "")).lower()
        if tag not in HEADINGS:
            continue
        level = int(tag[1])
        if previous is not None and level > previous + 1:
            out.append(
                Finding(
                    "heading-skip",
                    WARN,
                    page,
                    f"<{tag}> follows <h{previous}>, skipping h{previous + 1}",
                    "use the next level down, or promote the heading",
                )
            )
        previous = level
    return out


def _has_class(el, name: str) -> bool:
    return name in (el.attrib.get("class") or "").split()


def _contains_class(el, name: str) -> bool:
    try:
        return any(node is not el and _has_class(node, name) for node in el.iter())
    except (AttributeError, TypeError):  # pragma: no cover - defensive
        return False


def _check_image_role(ordered) -> list[Finding]:
    """Evidence and decoration must not share a grammar.

    A `<figure>` is a claim: it is numbered, captioned and referenced from the
    text. A `.plate` is atmosphere — cover art, a section opener, a texture.
    The dangerous case is not a fabricated chart, which anyone spots, but a
    decorative image wearing `Fig. 3`, because the reader files it as sourced
    without ever deciding to. So the boundary is enforced in both directions:
    a plate may not carry a number, and a figure must.
    """
    out = []
    for page, el in ordered:
        tag = str(getattr(el, "tag", "")).lower()
        if _has_class(el, "plate"):
            if _contains_class(el, "fnum"):
                out.append(
                    Finding(
                        "image-role",
                        WARN,
                        page,
                        "a plate carries a figure number",
                        "a plate is decoration — drop the number, or make it a "
                        "<figure> and reference it from the text",
                    )
                )
        elif tag == "figure" and not _contains_class(el, "fnum"):
            out.append(
                Finding(
                    "image-role",
                    WARN,
                    page,
                    "<figure> has no figure number",
                    'number it with <span class="fnum">Fig. N</span>, or make it '
                    'a <div class="plate"> if it is decoration rather than evidence',
                )
            )
    return out


def _check_image_alt(ordered) -> list[Finding]:
    """An image nobody described is an image nobody decided the purpose of."""
    out = []
    for page, el in ordered:
        if str(getattr(el, "tag", "")).lower() != "img" or "alt" in el.attrib:
            continue
        out.append(
            Finding(
                "image-alt",
                WARN,
                page,
                "<img> has no alt text",
                'say what it shows; alt="" declares it purely decorative',
            )
        )
    return out


def _collect_type_sizes(pages) -> dict[float, tuple[int, int, str]]:
    """Type size in pt → (text boxes using it, page it first appears, element)."""
    sizes: dict[float, tuple[int, int, str]] = {}
    for number, page in enumerate(pages, start=1):
        parents = _parent_map(page._page_box)
        for box in _walk(page._page_box):
            if not _is_text(box):
                continue
            style = getattr(box, "style", None)
            if style is None:
                continue
            pt = round(style["font_size"] / PT, 3)
            count, first, tag = sizes.get(pt, (0, number, ""))
            label = _label(box, parents)
            # A ::marker or ::after merely inherits the size; name the element
            # the author actually wrote. Keep a pseudo only if nothing else
            # uses the size — then it really is the culprit.
            if not tag or ("::" in tag and "::" not in label):
                tag = label
            sizes[pt] = (count + 1, first, tag)
    return sizes


def _check_type_drift(pages) -> list[Finding]:
    """Two sizes a reader cannot tell apart are one size and one accident.

    A designed scale steps by ratios the eye can see. When 8.096pt turns up
    beside 8.1pt, nothing was designed: a relative size compounded — an `em`
    nested inside an `em` — and landed a hair off an established step. The
    scale gains a step that carries no meaning, which is how a type system
    stops being a system.

    The threshold sits below the finest deliberate step in the shipped themes,
    so this catches artifacts and leaves design decisions alone. Widening it
    starts flagging real scale steps, which was measured, not guessed.
    """
    sizes = _collect_type_sizes(pages)
    ordered = sorted(sizes)
    out, reported = [], set()
    for lower, upper in zip(ordered, ordered[1:], strict=False):
        gap = (upper - lower) / lower * 100
        if gap >= SAME_SIZE_PCT:
            continue
        # The rarer of the pair is the stray; that is where the fix belongs.
        stray, kept = (upper, lower) if sizes[upper][0] <= sizes[lower][0] else (lower, upper)
        if stray in reported:
            continue
        reported.add(stray)
        out.append(
            Finding(
                "type-drift",
                WARN,
                sizes[stray][1],
                f"<{sizes[stray][2]}> at {stray:g}pt sits {gap:.1f}% "
                f"from {kept:g}pt — indistinguishable in print",
                "collapse them onto one step; an em nested inside an em is the usual cause",
            )
        )
    return out


def _check_inline_style(ordered) -> list[Finding]:
    """Rule 2 of the kit — never hand-roll a style — now measured.

    An inline declaration renders perfectly and passes every other check, which
    is precisely how a design system erodes: one reasonable-looking exception
    at a time, none of which anyone can see going wrong.
    """
    out = []
    for page, el in ordered:
        attrib = getattr(el, "attrib", None)
        if not attrib or not attrib.get("style"):
            continue
        out.append(
            Finding(
                "inline-style",
                WARN,
                page,
                f"<{str(el.tag).lower()}> carries an inline style",
                "use an existing class, or put the rule in brand.css beside the source",
            )
        )
    return out


# ── entry point ───────────────────────────────────────────────────────────


def inspect(html: str, base_dir: Path) -> list[Finding]:
    """Render the document and measure it. Requires WeasyPrint."""
    try:
        from weasyprint import HTML
    except Exception as exc:  # pragma: no cover - environment dependent
        raise CheckUnavailable(
            "`folio check` measures the real layout tree, which only WeasyPrint\n"
            "  provides. The Chromium fallback cannot do it. Run `folio doctor`."
        ) from exc

    doc = HTML(string=html, base_url=str(base_dir)).render()
    pages = doc.pages
    # Indexed 0-based, so page i (1-based) reads its successor at [i].
    authored_starts = _authored_page_starts(pages) + [False]
    findings: list[Finding] = []
    for i, page in enumerate(pages, start=1):
        frame = _content_frame(page)
        kind = _page_kind(page)
        root = _content_root(page)
        parents = _parent_map(root)
        paper = _paper(page)
        findings += _check_overflow(root, i, frame)
        findings += _check_contrast(root, i, parents, paper)
        for margin_box in _margin_boxes(page):
            findings += _check_contrast(margin_box, i, _parent_map(margin_box), paper)
        findings += _check_text_overlap(root, i)
        # A page is short because the next one was demanded, because the
        # document ended, or because something here would not fit. The first
        # two are defects only once the page is nearly empty.
        findings += _check_thin_page(root, i, frame, len(pages), kind, authored=authored_starts[i])
        findings += _check_tiny_text(root, i)
        findings += _check_orphan_heading(root, i, frame)
        findings += _check_image_scale(root, i)
        findings += _check_figure_scale(root, i)
        findings += _check_half_bleed(root, i, page.width)

    # Structure and conformance are properties of the document, not of a page.
    ordered = list(_elements_in_order(pages))
    findings += _check_heading_levels(ordered)
    findings += _check_inline_style(ordered)
    findings += _check_image_role(ordered)
    findings += _check_image_alt(ordered)
    findings += _check_type_drift(pages)

    order = {ERROR: 0, WARN: 1}
    findings.sort(key=lambda f: (order[f.severity], f.page))
    return findings


def summarise(findings: list[Finding]) -> str:
    errors = sum(1 for f in findings if f.severity == ERROR)
    warns = len(findings) - errors
    if not findings:
        return "No layout problems found."
    parts = []
    if errors:
        parts.append(f"{errors} error{'s' if errors != 1 else ''}")
    if warns:
        parts.append(f"{warns} warning{'s' if warns != 1 else ''}")
    return ", ".join(parts)
