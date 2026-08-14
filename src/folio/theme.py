"""Shared palette + matplotlib theme so charts look native to the report.

Every colour here mirrors a CSS custom property in assets/report.css.
Override the brand by setting FOLIO_BRAND=#RRGGBB, or by calling
`use(brand="#...")` before plotting.
"""

from __future__ import annotations

import os

INK = "#2d3748"
INK_SOFT = "#475569"
MUTED = "#626d7e"
GRID = "#e2e8f0"
SUCCESS = "#2B7A53"
WARNING = "#97641A"
ERROR = "#C53030"

# Per-theme palettes, mirroring themes/*.css so a figure never looks pasted in.
PALETTES = {
    "report": {
        "brand": "#003F87",
        "deep": "#002B6B",
        "ramp": ["#5FBEEB", "#2E86C7", "#0F5FA6", "#003F87", "#002B6B"],
        "ink": "#2d3748",
        "mute": "#626d7e",
        "grid": "#e2e8f0",
    },
    "editorial": {
        "brand": "#6E1D2B",
        "deep": "#4A121C",
        "ramp": ["#D9A0A8", "#BF6C79", "#9E3F4F", "#6E1D2B", "#4A121C"],
        "ink": "#14161a",
        "mute": "#686c74",
        "grid": "#d8d5d0",
    },
    "technical": {
        "brand": "#0F5257",
        "deep": "#08383B",
        "ramp": ["#7FBFC2", "#4A9DA2", "#22797F", "#0F5257", "#08383B"],
        "ink": "#16191c",
        "mute": "#687077",
        "grid": "#d4d8db",
    },
    "minimal": {
        "brand": "#1a1a1a",
        "deep": "#000000",
        "ramp": ["#c9c9c9", "#9a9a9a", "#6b6b6b", "#3d3d3d", "#111111"],
        "ink": "#111111",
        "mute": "#6f6f6f",
        "grid": "#dcdcdc",
        "accent": "#C64014",
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
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # charts are an extra, not a dependency
        if not (exc.name or "").startswith("matplotlib"):
            raise
        raise ModuleNotFoundError(
            "folio needs matplotlib to draw charts, and it is not installed.\n"
            "  pip install 'folio-press[charts]'   — charts only\n"
            "  pip install 'folio-press[all]'      — charts and WeasyPrint\n"
            "Run `folio doctor` to see everything this machine is missing.",
            name=exc.name,
        ) from None  # the cause is "No module named 'matplotlib'" — it adds nothing

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


class FigureError(RuntimeError):
    """A figure that would ship saying something it does not show."""


def _clipped_reference_lines(fig) -> list[str]:
    """Reference lines drawn outside the axis that is meant to show them.

    `axhline` and `axvline` are how a chart states a threshold — a standard, a
    scope, a target — and the caption almost always points at one. Give it a
    value outside the limits and matplotlib draws it, clips it away, and says
    nothing: the quarterly report shipped `axhline(43)` under
    `set_ylim(0, 34)` for four releases, with a caption promising a dotted line
    no reader could see.

    Nothing downstream can catch it. By the time the figure reaches
    `folio check` it is an image, and its text is outlined by design. The
    figure is the only place it is knowable, so it is knowable here.

    A line *on* the boundary is drawn and therefore fine — a baseline at zero
    under `ylim=(0, n)` is the common case, and refusing it would make the
    guard unusable.
    """
    out = []
    for ax in fig.get_axes():
        for line in ax.lines:
            transform = line.get_transform()
            if transform is ax.get_yaxis_transform():
                value, (low, high), axis = line.get_ydata()[0], ax.get_ylim(), "y"
            elif transform is ax.get_xaxis_transform():
                value, (low, high), axis = line.get_xdata()[0], ax.get_xlim(), "x"
            else:
                continue
            if not low <= value <= high:
                out.append(
                    f"a reference line at {axis}={value:g} is outside the axis "
                    f"({low:g} to {high:g}), so it is drawn and then clipped away"
                )
    return out


def save(fig, path):
    """Write an SVG sized for the report column. Always vector, never raster."""
    clipped = _clipped_reference_lines(fig)
    if clipped:
        raise FigureError(
            f"{path.name if hasattr(path, 'name') else path}:\n  "
            + "\n  ".join(clipped)
            + "\n  Widen the limit to include it, or drop the line and the "
            "sentence that points at it."
        )
    fig.savefig(str(path), format="svg", transparent=True)
    return path
