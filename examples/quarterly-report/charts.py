"""Figures for the example report. All data is invented."""
from pathlib import Path

import numpy as np

from folio import theme

plt = theme.use()
OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)

# Services in the programme. The burn-up plots progress against it and the
# migration stack sums to it, so it is named once rather than typed twice.
SCOPE = 43


def fig_deploys():
    """Deploy frequency — the dashboard-flavour bar chart."""
    labels = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    values = [312, 428, 501, 664, 712, 389]

    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    bars = ax.bar(labels, values, color=theme.BRAND, width=0.62, zorder=3)
    bars[4].set_color(theme.BRAND_DEEP)
    bars[-1].set_color(theme.MUTED)
    theme.grid(ax)
    ax.set_ylabel("deploys")
    ax.set_ylim(0, 820)
    for b, v in zip(bars, values, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + 18, f"{v:,}", ha="center",
                va="bottom", fontsize=7.5, color=theme.INK, fontweight="600")
    ax.text(0.995, 0.93, "Sep partial", transform=ax.transAxes, ha="right",
            fontsize=7, color=theme.MUTED, style="italic")
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-deploys.svg")
    plt.close(fig)


def fig_migration():
    """Migration status — stacked horizontal bar with two snapshots."""
    cats = ["MIGRATED", "IN FLIGHT", "NOT STARTED", "DEPRECATED"]
    colors = [theme.SUCCESS, theme.WARNING, theme.ERROR, theme.MUTED]
    q2 = [11, 6, 24, 2]
    q3 = [27, 9, 5, 2]

    fig, ax = plt.subplots(figsize=(6.6, 1.85))
    for row, (label, data) in enumerate([("end of Q3", q3), ("end of Q2", q2)]):
        left = 0
        for v, c in zip(data, colors, strict=True):
            ax.barh(row, v, left=left, color=c, height=0.52, zorder=3)
            if v >= 3:
                ax.text(left + v / 2, row, str(v), ha="center", va="center",
                        color="white", fontsize=8, fontweight="700")
            left += v
        ax.text(-0.7, row, label, ha="right", va="center", fontsize=8, color=theme.INK)

    ax.set_xlim(0, 43)
    ax.set_ylim(-0.55, 1.55)
    ax.set_yticks([])
    ax.set_xlabel("services (n=43)")
    ax.spines["left"].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    ax.legend(handles, cats, loc="upper center", bbox_to_anchor=(0.5, -0.42),
              ncol=4, frameon=False, fontsize=7.5, handlelength=1.1, handleheight=1.1)
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-migration.svg")
    plt.close(fig)


def fig_latency():
    """p99 latency distribution before and after — the analytical figure.

    The means are chosen so the drawn p99s land on the two numbers the document
    reports, 412ms and 231ms. They used to be chosen by eye, and the label was
    typed in beside them: the dashed lines fell at 646 and 290 while the text
    said 412 and 231, so the figure disagreed with itself in the one place a
    reader can check it — the axis it is drawn against.

    The label is computed from the same array the lines are drawn from now, so
    the two cannot drift apart again.
    """
    rng = np.random.default_rng(11)
    before = rng.lognormal(mean=4.9697, sigma=0.44, size=1400)
    after = rng.lognormal(mean=4.6326, sigma=0.31, size=1400)
    p99_before, p99_after = np.percentile(before, 99), np.percentile(after, 99)

    fig, ax = plt.subplots(figsize=(3.25, 2.45))
    bins = np.linspace(0, 750, 46)
    ax.hist(before, bins=bins, color=theme.RAMP[0], alpha=0.85, zorder=3, label="before")
    ax.hist(after, bins=bins, color=theme.BRAND_DEEP, alpha=0.85, zorder=4, label="after")
    for v, c, ls in ((p99_before, theme.RAMP[0], "--"), (p99_after, theme.BRAND_DEEP, "--")):
        ax.axvline(v, color=c, lw=1.1, ls=ls, zorder=5)
    ax.set_xlabel("request latency [ms]")
    ax.set_ylabel("requests")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    # Above the axes, not inside them. Sat at the top left until the p99s were
    # corrected — which moved both dashed lines left, straight through the
    # text. An annotation placed in the data area is one data change away from
    # being struck through, and no rule can see it: chart text is outlined, so
    # `text-overlap` stops at the figure's edge.
    ax.text(0, 1.04, f"p99  {p99_before:.0f} → {p99_after:.0f} ms", transform=ax.transAxes,
            fontsize=7.5, va="bottom", color=theme.INK, fontweight="600")
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-latency.svg")
    plt.close(fig)


def fig_burnup():
    """Cumulative services migrated — line with an annotation."""
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    done = [4, 9, 11, 19, 25, 27]

    fig, ax = plt.subplots(figsize=(3.25, 2.45))
    ax.plot(months, done, color=theme.BRAND, lw=2, marker="o", ms=4,
            mfc="white", mew=1.6, zorder=4)
    ax.fill_between(range(len(months)), done, color=theme.BRAND, alpha=0.09, zorder=2)
    theme.grid(ax)
    ax.set_ylabel("services migrated (cumulative)")
    # The scope line is the point of a burn-up: it is what 27 is short of. It
    # was drawn at 43 under a `set_ylim(0, 34)` that clipped it, so the caption
    # promised a dotted line no reader could see — the chart and its own axis
    # limit disagreeing, which nothing in `folio check` can reach.
    ax.set_ylim(0, 46)
    ax.axhline(SCOPE, color=theme.MUTED, lw=0.9, ls=":", zorder=1)
    ax.text(5.35, SCOPE + 0.8, f"{SCOPE} in scope", fontsize=6.5, color=theme.MUTED, ha="right")
    ax.annotate("dual-write\ncutover", xy=(3, 19), xytext=(1.1, 26), fontsize=6.8,
                color=theme.INK,
                arrowprops=dict(arrowstyle="-", color=theme.MUTED, lw=0.8))
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-burnup.svg")
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig_deploys, fig_migration, fig_latency, fig_burnup):
        f()
        print("  wrote", f.__name__)
