"""Components must occupy the space their content needs, and no more.

`folio check` measures a page for defects a document introduced. These check
the other direction: that the kit's own components do not introduce one. A box
that reserves space it never fills is invisible to every rule — nothing
overflows, nothing overlaps, nothing is illegible — and it is only visible on
the page, which is where it was eventually found.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

pytest.importorskip("weasyprint", reason="layout is measured off WeasyPrint's tree")

from folio.assets import css_text, theme_names  # noqa: E402
from folio.check import _content_frame, _content_root, _is_text, _rect, _walk  # noqa: E402


def _flat_png(width: int, height: int) -> bytes:
    """A large flat raster, built here so the fixture needs no image library.

    Size is load-bearing: the bug resolves a flex item's minimum height from
    the image's *intrinsic* pixels rather than its used width, so a thumbnail
    does not reproduce it and an SVG has no intrinsic pixels at all.
    """
    import struct
    import zlib

    row = b"\x00" + bytes((200, 196, 188)) * width

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height, 6))
        + chunk(b"IEND", b"")
    )


IMG = "data:image/png;base64," + base64.b64encode(_flat_png(1024, 560)).decode()

PROSE = (
    "Plain weave, wet-spun flax from Normandy. The slub is inherent to the "
    "cloth and is not a fault; it softens for about thirty washes and then "
    "stops changing, which is the point at which it is finished."
)

TWO_UP = f"""
<div class="cols">
  <div>
    <div class="plate"><img src="{IMG}" alt="cloth"><span class="credit">study</span></div>
    <p class="eyebrow">L1</p>
    <p>{PROSE}</p>
  </div>
  <div>
    <div class="plate"><img src="{IMG}" alt="cloth"><span class="credit">study</span></div>
    <p class="eyebrow">W2</p>
    <p>{PROSE}</p>
  </div>
</div>
"""


def measure(html: str, cls: str) -> tuple[float, float]:
    """(height of the box, height of the content inside it), in mm."""
    from weasyprint import HTML

    page = HTML(string=html, base_url=str(Path.cwd())).render().pages[0]
    frame = _content_frame(page)
    px_mm = (frame[3] - frame[1]) / 257  # A4 content height at folio's margins
    box = next(
        r
        for b in _walk(_content_root(page))
        if (el := getattr(b, "element", None)) is not None
        and (r := _rect(b)) is not None
        and (el.get("class") or "") == cls
    )
    bottoms = [
        r[3]
        for b in _walk(_content_root(page))
        if _is_text(b) and (r := _rect(b)) is not None and r[1] >= box[1] and r[3] <= box[3]
    ]
    return (box[3] - box[1]) / px_mm, (max(bottoms) - box[1]) / px_mm


@pytest.mark.parametrize("theme", theme_names())
def test_two_up_columns_do_not_reserve_space_they_never_fill(theme):
    """A `.cols` of a plate over wrapped prose stretched to a square.

    Flex items get `min-height: auto`, and WeasyPrint resolved that from the
    container's *width*: two columns whose content ran to 100mm occupied
    170mm — the measure — leaving a third of a page of white that no rule
    could see. Found in the lookbook example, where the closing paragraph
    appeared to float unattached below the columns.

    `min-width: 0` was already set here for the mirror-image reason. This is
    the same hygiene on the other axis.
    """
    html = (
        f"<!DOCTYPE html><html><head><style>{css_text(theme)}</style></head>"
        f"<body>{TWO_UP}</body></html>"
    )
    height, content = measure(html, "cols")
    assert height - content < 20, (
        f"{theme}: .cols is {height:.0f}mm tall for {content:.0f}mm of content"
    )
