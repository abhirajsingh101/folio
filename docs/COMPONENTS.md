# folio — component vocabulary

Every component below is defined in folio's stylesheet (`folio css`) and injected at build
time. Author documents in plain HTML using these classes; never hand-roll a
one-off style, and never link the stylesheet yourself.

---

## Pick a direction first

folio ships four design directions. They are not colour variants — each is a
different typographic system with its own page architecture.

| theme | character |
|---|---|
| `report` | corporate; serif body, soft filled surfaces *(default)* |
| `editorial` | magazine; large serif display, rules not fills, wide gutters |
| `technical` | dense memo; small sans, monospace labels, boxed tables |
| `minimal` | Swiss; sans throughout, near-monochrome, space not borders |

The document declares its own:

```html
<body data-theme="editorial" data-title="…" data-footer="…">
```

Charts follow automatically — `theme.use()` reads the same declaration.

Then tune with a `brand.css` beside the source. It is appended after
everything, so it always wins; usually one line:

```css
:root { --brand: #7A1F3D; --brand-deep: #4E1226; }
```

---

## Page furniture (automatic)

Set once on `<body>`; the running header, footer, and page numbers follow.

```html
<body data-title="Project · Progress Report" data-footer="confidential">
```

`@page` supplies: running title (upper-left), current section (upper-right),
`n / total` (lower-right), and the footer note (lower-left). The cover and
contents pages suppress all of it automatically.

---

## Cover

```html
<section class="cover">
  <div class="cover-brand">yourbrand</div>
  <div class="cover-kicker">Engineering Progress Report</div>
  <h1>Project&nbsp;Name</h1>
  <p class="sub">One sentence on what changed and why it matters.</p>
  <div class="cover-rule"></div>
  <div class="cover-meta">
    <div><span class="k">Period</span>2026.01.01 – 2026.03.31</div>
    <div><span class="k">Author</span>Your Name</div>
  </div>
</section>
```

Full-bleed gradient built from `--brand-deep` → `--brand`, with two layered
circles. Up to four `cover-meta` cells fit on one row.

## Contents

Page numbers resolve at render time via `target-counter` — never type them.

```html
<section class="toc">
  <h2>Contents</h2>
  <ol>
    <li><span class="num">01</span><span class="ttl">Executive summary</span>
        <span class="fill"></span><a class="pg" href="#s1"></a></li>
  </ol>
</section>
```

The `href` must match the section's `id`.

## Sections

```html
<div class="section-wrap">
  <h2 class="section" id="s1" data-section="Executive summary">
    <span class="idx">SECTION 01</span>Executive summary</h2>
  …
</div>
```

`section-wrap` starts a new page. `data-section` feeds the running header —
it must be the bare title, without the kicker. Add `cont` to the wrapper
(`class="section-wrap cont"`) to continue on the same page instead.

Inside: `<h3>` for subsections, `<h4>` for uppercase eyebrow labels.

## Lead paragraph

```html
<p class="lead">The headline finding, in one or two sentences.</p>
```

## Metric tiles

```html
<div class="metrics">
  <div class="metric"><span class="v">4,157</span><span class="l">Commits</span>
       <span class="d">since 2026.02.13</span></div>
</div>
```

Two to five tiles per row. `v` = value (tabular figures), `l` = uppercase
label, `d` = context line.

## Figures

```html
<figure>
  <img src="charts/fig-velocity.svg" alt="…">
  <figcaption><span class="fnum">Fig. 1</span>Say what to conclude.</figcaption>
</figure>
```

Two side by side: wrap both `<figure>` elements in `<div class="fig-row">`.
Full-bleed: add `class="bleed"` to the `<figure>`.

Caption the *conclusion*, not the axes.

## Tables

```html
<table>
  <caption><span class="tnum">Table 1</span>Caption above the table</caption>
  <thead><tr><th>Item</th><th class="num">Count</th></tr></thead>
  <tbody>
    <tr><td>First</td><td class="num">12</td></tr>
  </tbody>
  <tfoot><tr><td>Total</td><td class="num">12</td></tr></tfoot>
</table>
```

Zebra striping, brand header rule, and repeating header rows across page
breaks are automatic. `class="num"` right-aligns with tabular figures.
Hyphenation is disabled inside tables.

## Status pills

```html
<span class="pill ok">Done</span>
<span class="pill warn">Partial</span>
<span class="pill err">Blocked</span>
<span class="pill mute">N/A</span>
<span class="pill p0">P0</span>
<span class="pill p1">P1</span>
```

Encode state in *form* as well as text, so a table scans at a glance.

## Callouts

```html
<div class="callout warn">
  <span class="ico">Reclassified</span>
  <div class="body"><p>Body text.</p></div>
</div>
```

Tones: `info` `ok` `warn` `risk`. The `<div class="body">` wrapper is
required — without it the text overflows the box.

## Timeline

```html
<ul class="timeline">
  <li class="done"><span class="tl-h">Milestone</span>
    <span class="tl-d">2026.02.01 · detail</span>
    <div class="tl-b">What it delivered.</div></li>
  <li class="now">…</li>
</ul>
```

States: `done` (green), `now` (amber, larger), default (brand).

## Lists

```html
<ol class="steps"><li><strong>First.</strong> Why it comes first.</li></ol>
<ul class="tick"><li>Checklist item.</li></ul>
```

`steps` numbers into brand circles — use it only for genuine sequences.

## Pull quote

```html
<blockquote class="pullquote">A sentence worth lifting.<cite>— source</cite></blockquote>
```

## Code

```html
<pre><span class="c">// comment</span>
<span class="k">const</span> x = <span class="s">'string'</span>;</pre>
```

Spans: `c` comment, `k` keyword, `s` string. Inline: `<code>`.

## Keeping blocks together

Tables split across pages by default, which is correct for long ones. Figures,
callouts and pull quotes never split. When a short table must not split, say so:

```html
<table class="keep"> … </table>
```

`keep` works on any block. WeasyPrint ignores `widows`/`orphans` on table rows,
so this is the only control available — see GOTCHAS.

## Utilities

`two-col` (two-column text) · `divider` (horizontal rule) ·
`appendix` (smaller type for back matter) · `keep` (never split)

---

## Charts

Write a `charts.py` beside the document; `folio build` runs it first.

```python
import sys; from pathlib import Path
sys.path.insert(0, str(Path.home() / ".local/share/folio/lib"))
import theme

plt = theme.use()                      # applies palette + fonts
fig, ax = plt.subplots(figsize=(6.6, 2.5))
ax.bar(labels, values, color=theme.BRAND, zorder=3)
theme.grid(ax)
theme.save(fig, "charts/fig-example.svg")
```

Colours: `theme.BRAND` `BRAND_DEEP` `RAMP` (5-step) `SUCCESS` `WARNING`
`ERROR` `INK` `MUTED` `GRID`.

**Size in real inches at final printed width** — full column `6.6`, half
column `3.25`. Never scale a figure in CSS; the labels shrink with it.
Output is SVG with text as outlines, so it renders identically everywhere.

---

## Korean / CJK

Set `lang="ko"` on `<html>`, or `class="ko"` on any element. That switches on
`word-break: keep-all` and disables hyphenation, which is required for Korean
to break correctly. Body and sans stacks already fall back to Noto Sans KR.
