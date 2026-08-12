"""Figures are the one thing on the page the checker could not see inside.

A chart is an image, so every measurement stopped at its edge. But a chart
carries type — tick labels, axis titles, a legend — authored at a size chosen
to sit with the document's own type. Scale the image and all of it scales:
draw a half-column figure across a full column and its 8pt labels arrive at
16pt; do the reverse and they arrive at 4pt, under the legibility floor and
past the point where a warning helps.

Nothing about that is visible to a rule that only looks at boxes, which is why
these read the image itself.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from folio.check import WARN, inspect

pytest.importorskip("weasyprint", reason="figures are measured on the layout tree")

PAGE = "@page{size:A4;margin:20mm}"


def svg(width: int, height: int) -> str:
    raw = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" '
        f'fill="#0F5FA6"/></svg>'
    ).encode()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()


# A real 1x1 PNG. Drawn at any size at all, it is grossly upscaled.
PNG_1PX = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def doc(body: str, extra: str = "") -> str:
    return (
        f"<!DOCTYPE html><html><head><style>{PAGE}{extra}</style></head><body>{body}</body></html>"
    )


def findings(html: str, rule: str) -> list:
    return [f for f in inspect(html, Path("/tmp")) if f.rule == rule]


# ── a vector drawn at the wrong size ──────────────────────────────────────


def test_a_vector_drawn_at_half_its_authored_width_is_flagged():
    """Its 8pt labels arrive at 4pt, and no rule downstream can tell."""
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    found = findings(doc(body, "img{width:150px}"), "figure-rescaled")
    assert found
    assert found[0].severity == WARN


def test_a_vector_drawn_at_double_is_flagged():
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    assert findings(doc(body, "img{width:600px}"), "figure-rescaled")


def test_a_vector_drawn_at_its_authored_size_is_silent():
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    assert not findings(doc(body, "img{width:300px}"), "figure-rescaled")


def test_a_few_percent_is_silent():
    """Column width varies with the theme's page margins, so exact is not
    achievable and a 3% difference is invisible. Only material rescaling —
    the kind that changes what the labels look like — is worth reporting."""
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    assert not findings(doc(body, "img{width:309px}"), "figure-rescaled")


def test_the_finding_gives_both_sizes_in_inches():
    """'Rescaled' is not actionable; 3.23in authored against 6.85in drawn is."""
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    found = findings(doc(body, "img{width:600px}"), "figure-rescaled")
    assert found
    assert "in" in found[0].detail and "2.0" in found[0].detail
    assert found[0].hint


# ── the raster check, which never ran ─────────────────────────────────────


def test_an_upscaled_block_image_is_flagged():
    """`display:block` on an image produces a BlockReplacedBox.

    The upscale rule only looked at InlineReplacedBox, and folio's own
    stylesheet sets `figure img { display: block }` — so the rule had never
    once fired on a folio document.
    """
    body = f'<img src="{PNG_1PX}" alt="photo">'
    assert findings(doc(body, "img{display:block;width:200px}"), "image-upscaled")


def test_an_upscaled_inline_image_is_still_flagged():
    body = f'<img src="{PNG_1PX}" alt="photo">'
    assert findings(doc(body, "img{width:200px}"), "image-upscaled")


def test_a_scaled_vector_is_not_called_an_upscaled_raster():
    """Vectors do not go soft; scaling one is a type-size problem, not a
    resolution problem, and saying otherwise sends the author to fix the
    wrong thing."""
    body = f'<img src="{svg(300, 150)}" alt="chart">'
    assert not findings(doc(body, "img{display:block;width:600px}"), "image-upscaled")
