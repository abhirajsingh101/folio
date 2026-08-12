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

# Per-theme palettes, mirroring themes/*.css so a figure never looks pasted in.
PALETTES = {
    "report": {
        "brand": "#003F87",
        "deep": "#002B6B",
        "ramp": ["#5FBEEB", "#2E86C7", "#0F5FA6", "#003F87", "#002B6B"],
        "ink": "#2d3748",
        "mute": "#94a3b8",
        "grid": "#e2e8f0",
    },
    "editorial": {
        "brand": "#6E1D2B",
        "deep": "#4A121C",
        "ramp": ["#D9A0A8", "#BF6C79", "#9E3F4F", "#6E1D2B", "#4A121C"],
        "ink": "#14161a",
        "mute": "#82878f",
        "grid": "#d8d5d0",
    },
    "technical": {
        "brand": "#0F5257",
        "deep": "#08383B",
        "ramp": ["#7FBFC2", "#4A9DA2", "#22797F", "#0F5257", "#08383B"],
        "ink": "#16191c",
        "mute": "#7d868d",
        "grid": "#d4d8db",
    },
    "minimal": {
        "brand": "#1a1a1a",
        "deep": "#000000",
        "ramp": ["#c9c9c9", "#9a9a9a", "#6b6b6b", "#3d3d3d", "#111111"],
        "ink": "#111111",
        "mute": "#949494",
        "grid": "#dcdcdc",
        "accent": "#E8501E",
    },
}

BRAND = PALETTES["report"]["brand"]
BRAND_DEEP = PALETTES["report"]["deep"]
RAMP = PALETTES["report"]["ramp"]
ACCENT = BRAND

_BODY_FONTS = ["Inter", "Noto Sans CJK KR", "Noto Sans KR", "DejaVu Sans"]


def use(theme: str | None = None, brand: str | None = None, base_size: float = 8.5):
    """Apply the chart theme matching the document. Call once before plotting.

    `folio build` sets FOLIO_THEME, so a chart script needs no arguments and
    still tracks whatever design direction the document declares.

    Text is emitted as outlines (`svg.fonttype='path'`) so the figure renders
    identically no matter which fonts the PDF engine can see.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    global BRAND, BRAND_DEEP, RAMP, INK, MUTED, GRID, ACCENT

    name = theme or os.environ.get("FOLIO_THEME", "report")
    pal = PALETTES.get(name, PALETTES["report"])
    BRAND, BRAND_DEEP, RAMP = pal["brand"], pal["deep"], list(pal["ramp"])
    INK, MUTED, GRID = pal["ink"], pal["mute"], pal["grid"]
    ACCENT = pal.get("accent", BRAND)
    if brand:
        BRAND = ACCENT = brand

    fonts = (
        ["Inter", "Noto Sans CJK KR", "DejaVu Sans"]
        if name in ("technical", "minimal")
        else _BODY_FONTS
    )

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": fonts,
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
