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
# Text below this size (px) is not reliably legible in print.
MIN_FONT_PX = 6.0
# A heading with less than this much room beneath it is stranded.
ORPHAN_HEADING_MM = 22
# Overflow smaller than this is rounding, not a bug.
OVERFLOW_TOLERANCE_PX = 1.0
# Raster upscaled beyond this looks soft on paper.
MAX_IMAGE_UPSCALE = 1.15

MM = 96 / 25.4  # WeasyPrint lays out in CSS px


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


def _is_text(box) -> bool:
    return type(box).__name__ == "TextBox" and bool((getattr(box, "text", "") or "").strip())


def _label(box, parents: dict) -> str:
    """A tag the author can actually find, walking up if the box is anonymous."""
    node = box
    while node is not None:
        tag = getattr(node, "element_tag", None)
        if tag:
            return tag
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


def _check_thin_page(root, n, frame, is_last: bool, kind: str) -> list[Finding]:
    """A page 15% full means a block jumped rather than fitting."""
    if is_last or kind != "body":
        return []
    top, bottom = frame[1], frame[3]
    usable = bottom - top
    lowest = top
    for box in _walk(root):
        r = _rect(box)
        if r and _is_text(box):
            lowest = max(lowest, r[3])
    fill = (lowest - top) / usable if usable else 1.0
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


def _check_text_overlap(root, n) -> list[Finding]:
    """Two pieces of text occupying the same space is never intentional."""
    rects = []
    for box in _walk(root):
        if _is_text(box):
            r = _rect(box)
            if r and r[2] > r[0] and r[3] > r[1]:
                rects.append((r, getattr(box, "element_tag", "?")))
    out, reported = [], set()
    for i, (a, ta) in enumerate(rects):
        for b, tb in rects[i + 1 :]:
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


def _check_image_scale(root, n) -> list[Finding]:
    """A raster blown up past its pixels looks soft on paper."""
    out = []
    for box in _walk(root):
        if type(box).__name__ != "InlineReplacedBox":
            continue
        img = getattr(box, "replacement", None)
        intrinsic = getattr(img, "intrinsic_width", None)
        r = _rect(box)
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
    findings: list[Finding] = []
    for i, page in enumerate(pages, start=1):
        frame = _content_frame(page)
        kind = _page_kind(page)
        root = _content_root(page)
        findings += _check_overflow(root, i, frame)
        findings += _check_text_overlap(root, i)
        findings += _check_thin_page(root, i, frame, i == len(pages), kind)
        findings += _check_tiny_text(root, i)
        findings += _check_orphan_heading(root, i, frame)
        findings += _check_image_scale(root, i)

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
