"""The one figure in the proposal. All data is invented.

Sized at 6.85in — `report`'s full column on A4, from the table in
`folio components`. A chart authored at one width and dropped into another
arrives with the wrong label size, and `folio check` reports it.
"""

from pathlib import Path

from folio import theme

plt = theme.use()
OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)


def fig_windows():
    """Releases held for a schema migration window, by month."""
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    held = [2, 3, 5, 6, 9, 11]

    fig, ax = plt.subplots(figsize=(6.85, 2.4))
    bars = ax.bar(months, held, color=theme.BRAND, width=0.6, zorder=3)
    for b in bars[-2:]:
        b.set_color(theme.BRAND_DEEP)
    theme.grid(ax)
    ax.set_ylabel("releases held")
    ax.set_ylim(0, 13)
    for b, v in zip(bars, held):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.35,
            str(v),
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=theme.INK,
            fontweight="600",
        )
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-windows.svg")
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig_windows,):
        f()
        print("  wrote", f.__name__)
