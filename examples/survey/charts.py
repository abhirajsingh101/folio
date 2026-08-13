"""Figures for the catchment survey. All data is invented.

Both are sized at 6.85in — `report`'s full column on A4, from the table in
`folio components`. A chart authored at one width and dropped into another
arrives with the wrong label size, and `folio check` reports it.
"""

from pathlib import Path

from folio import theme

plt = theme.use()
OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)

STANDARD = 11.3  # mg/l NO₃-N, drinking water standard


def fig_nitrate():
    """Peak spring nitrate by site, against the standard."""
    sites = [
        "C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07",
        "C-08", "C-09", "C-10", "C-11", "C-12", "C-13", "C-14",
    ]
    peak = [3.4, 4.1, 3.9, 6.0, 4.6, 4.4, 7.1, 12.4, 14.1, 11.9, 4.8, 11.5, 4.2, 9.8]

    fig, ax = plt.subplots(figsize=(6.85, 2.5))
    bars = ax.bar(sites, peak, color=theme.BRAND, width=0.62, zorder=3)
    for b, v in zip(bars, peak, strict=True):
        if v > STANDARD:
            b.set_color(theme.BRAND_DEEP)
    ax.axhline(STANDARD, color=theme.MUTED, lw=1, ls="--", zorder=4)
    ax.text(
        13.6,
        STANDARD + 0.4,
        "11.3 standard",
        ha="right",
        va="bottom",
        fontsize=7,
        color=theme.MUTED,
    )
    theme.grid(ax)
    ax.set_ylabel("mg/l NO₃-N")
    ax.set_ylim(0, 16)
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-nitrate.svg")
    plt.close(fig)


def fig_season():
    """Monthly mean nitrate, above and below the confluence."""
    months = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    above = [3.1, 3.4, 3.6, 3.9, 4.2, 4.6, 4.4, 4.0, 3.6, 3.3, 3.0, 3.1]
    below = [4.2, 4.6, 5.1, 6.8, 10.4, 13.2, 11.1, 7.4, 5.2, 4.6, 4.1, 4.3]

    fig, ax = plt.subplots(figsize=(6.85, 2.5))
    ax.plot(months, below, color=theme.BRAND_DEEP, lw=2, marker="o", ms=4,
            mfc="white", mew=1.6, zorder=4, label="Below Marchford")
    ax.plot(months, above, color=theme.BRAND, lw=2, marker="o", ms=4,
            mfc="white", mew=1.6, zorder=4, label="Above Marchford")
    ax.axhline(STANDARD, color=theme.MUTED, lw=1, ls="--", zorder=3)
    theme.grid(ax)
    ax.set_ylabel("mg/l NO₃-N")
    ax.set_ylim(0, 16)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-season.svg")
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig_nitrate, fig_season):
        f()
        print("  wrote", f.__name__)
