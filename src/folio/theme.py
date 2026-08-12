"""Shared palette + matplotlib theme so charts look native to the report.

Every colour here mirrors a CSS custom property in assets/report.css.
Override the brand by setting FOLIO_BRAND=#RRGGBB, or by calling
`use(brand="#...")` before plotting.
"""

from __future__ import annotations

import os

INK = "#2d3748"
INK_SOFT = "#475569"
MUTED = "#94a3b8"
GRID = "#e2e8f0"
SUCCESS = "#2F855A"
WARNING = "#B7791F"
ERROR = "#C53030"

BRAND = os.environ.get("FOLIO_BRAND", "#003F87")
BRAND_DEEP = "#002B6B"

# light -> dark single-hue ramp, for categorical series
RAMP = ["#5FBEEB", "#2E86C7", "#0F5FA6", "#003F87", "#002B6B"]

_BODY_FONTS = ["Inter", "Noto Sans CJK KR", "Noto Sans KR", "DejaVu Sans"]


def use(brand: str | None = None, base_size: float = 8.5):
    """Apply the report chart theme to matplotlib. Call once before plotting.

    Text is emitted as outlines (`svg.fonttype='path'`) so the figure renders
    identically no matter which fonts the PDF engine can see.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    global BRAND
    if brand:
        BRAND = brand

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": _BODY_FONTS,
            "svg.fonttype": "path",
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.edgecolor": GRID,
            "axes.prop_cycle": plt.cycler(color=RAMP),
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": base_size,
            "figure.dpi": 100,
            "savefig.transparent": True,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )
    return plt


def grid(ax, axis: str = "y"):
    """Faint grid behind the marks — the default for bar and line charts."""
    ax.grid(axis=axis, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    return ax


def save(fig, path):
    """Write an SVG sized for the report column. Always vector, never raster."""
    fig.savefig(str(path), format="svg", transparent=True)
    return path
