"""Figures for this document. `folio build` runs this automatically.

Everything lands in charts/ as SVG, themed to match the page. Size figures in
real inches at the width they will print, so the labels come out at the size
they were authored: roughly 6.4-7.0in full column and 3.1-3.4in half, per
theme (`folio components` has the table). Never scale a figure in CSS — the
labels scale with it, and `folio check` reports it as `figure-rescaled`.
"""

from pathlib import Path

from folio import theme

plt = theme.use()
OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)


def fig_example():
    labels = ["Jan", "Feb", "Mar", "Apr"]
    values = [120, 340, 285, 410]

    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    bars = ax.bar(labels, values, color=theme.BRAND, width=0.62, zorder=3)
    bars[-1].set_color(theme.BRAND_DEEP)
    theme.grid(ax)
    ax.set_ylabel("units")
    for b, v in zip(bars, values):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v * 1.03,
            f"{v:,}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=theme.INK,
            fontweight="600",
        )
    fig.tight_layout(pad=0.3)
    theme.save(fig, OUT / "fig-example.svg")
    plt.close(fig)


def fig_pair():
    for name in ("fig-a", "fig-b"):
        fig, ax = plt.subplots(figsize=(3.25, 2.45))
        ax.plot(
            range(10),
            [x**1.4 for x in range(10)],
            color=theme.BRAND,
            lw=2,
            marker="o",
            ms=4,
            mfc="white",
            mew=1.6,
            zorder=4,
        )
        theme.grid(ax)
        ax.set_ylabel("value")
        fig.tight_layout(pad=0.3)
        theme.save(fig, OUT / f"{name}.svg")
        plt.close(fig)


if __name__ == "__main__":
    for f in (fig_example, fig_pair):
        f()
        print("  wrote", f.__name__)
