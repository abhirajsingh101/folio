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

## Document head

A title block for a document that does not spend a page on a cover — an
invoice, a letter, a one-pager, a brief.

```html
<div class="doc-head">
  <p class="eyebrow">Invoice</p>
  <h1>2026-014</h1>
  <p class="sub">Monolith decomposition, September retainer.</p>
</div>
```

`<h1>` is styled in every theme now, so it outranks `h2.section` whether or not
you use the wrapper. It previously fell to the browser default, which rendered
it *smaller* than the sections beneath it in two of the four themes.

## Facts

A labelled key/value grid: bill-to and remit-to on an invoice, the at-a-glance
panel on a case study, document control on an SOP. Wrap each pair so the label
sits over its value.

```html
<dl class="facts">
  <div><dt>Invoice</dt><dd>2026-014</dd></div>
  <div><dt>Issued</dt><dd>2026.08.13</dd></div>
  <div><dt>Due</dt><dd>2026.09.12</dd></div>
</dl>
```

## Columns

`.cols` is two equal halves. `.cols.rail` is a main measure with a narrower
rail beside it — the pattern real reports and briefs use, and not the same
thing as `.two-col`, which flows one block into two equal columns.

```html
<div class="cols">
  <div><p class="eyebrow">From</p>…</div>
  <div><p class="eyebrow">Bill to</p>…</div>
</div>

<div class="cols rail">
  <div>…the argument…</div>
  <aside>…at a glance…</aside>
</div>
```

## Signature

An acceptance block. It will not split across a page.

```html
<div class="signature">
  <div><span class="line"></span><span class="who">For Meridian Ltd</span>
       <span class="role">Authorised signatory</span></div>
  <div><span class="line"></span><span class="who">Date</span></div>
</div>
```

## Totals

A `<tfoot>` rules only its **last** row, so a Subtotal / Tax / Total block
reads as one figure the reader is looking for rather than three of equal
weight. Put the grand total last.

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

A bleeding band across the head of the page with the type below it on solid
ground. Each theme sizes the band — `report` 158mm, `editorial` 118mm,
`technical` a 6mm brand bar, `minimal` a 3mm rule — so the same markup gives
four covers. Up to four `cover-meta` cells fit on one row.

Optionally an image covers the band:

```html
<img class="cover-plate" src="art/cover.jpg" alt="Abstract dark blue strata">
```

**Type never sits on the band.** `low-contrast` declines to measure anything
over an image, so a title reversed out of a plate would ship illegible with a
green build; keeping the type on solid ground is what preserves the check.
`report` and `editorial` are the two directions doctrine allows a plate on —
see `folio imagery`.

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

Inside: `<h3>` for subsections, `<h4>` for a fourth level where you genuinely
have one.

For a *label* — "Bill to", "Attendees", "Payment terms" — use `.eyebrow`, not a
heading:

```html
<p class="eyebrow">Bill to</p>
```

A heading level is structure that screen readers and the shareable HTML page
both consume, so `<h4>` directly under `<h2>` claims an `<h3>` that does not
exist and `folio check` reports it. `.eyebrow` carries the same uppercase
label treatment in every theme without inventing a level.

## Page furniture

Every page carries a running title, a section rail, a page counter and a footer
line, fed by `data-title`, `data-section` and `data-footer`.

A single-sheet document — an invoice, a quote, a letter, a one-pager — should
carry none of it. Page chrome on a page with nowhere to run to is noise, and on
a résumé it is worse than noise: applicant tracking systems discard header and
footer content outright.

```html
<body data-furniture="none">
```

It is an attribute rather than a build flag on purpose: an invoice is
furniture-free wherever it is rebuilt, and a flag has to be remembered every
time.

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

A unit or denominator rides on the value as `u`, so it stays proportional to
whatever size the theme sets — never size it by hand:

```html
<span class="v">231<span class="u">ms</span></span>
<span class="v">27<span class="u">/43</span></span>
```

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

Every figure needs a number. A figure is a claim: numbered, captioned, and
referenced from the text. If an image is not that, it is a plate.

### Size a chart at the width it will print

A chart carries type — tick labels, axis titles, a legend — authored to sit
with the document's own. Scaling the image scales all of it, so a half-column
figure stretched across a full column arrives with 16pt labels, and the
reverse arrives with 4pt. `folio check` reports it as `figure-rescaled`.

Column width depends on the theme's page margins, so there is no single right
number. On A4:

| theme | full column | half column |
|---|---|---|
| `report` | 6.85in | 3.31in |
| `editorial` | 6.38in | 3.07in |
| `technical` | 7.01in | 3.39in |
| `minimal` | 6.54in | 3.15in |

Half column assumes two figures in a `.fig-row`, which has a 6mm gutter.
Being a few percent out is invisible and not reported; the check exists to
catch a figure authored for one slot and dropped into another.

## Plates

Decorative imagery — cover art, a section opener, a texture. **Never
evidence.**

```html
<div class="plate bleed">
  <img src="art/opener.png" alt="Abstract dark blue strata">
  <span class="credit">Generated illustration</span>
</div>
```

A plate carries no figure number and is never referenced from the text. That
distinction is the whole point of the component, and `folio check` enforces it
both ways: a plate with a `fnum` is flagged, and so is a `<figure>` without
one.

The failure this prevents is subtle. A fabricated chart is obvious to
everyone. A decorative illustration captioned `Fig. 3` is not — it wears the
same grammar as a measurement, so the reader files it as sourced without ever
deciding to.

**Where the credit sits is part of what it says.** A `.credit` under a plate
that sits above a `.signature` reads as belonging to the signature — a line of
small type directly over a name is a job title, not an image credit, and no
measurement distinguishes the two. Put the plate's credit above the signature
block, or move the plate. This is advice rather than a rule for exactly that
reason: `folio check` measures geometry, and both arrangements are
geometrically correct.

Rules for what may go in a plate:

- **Never anything a reader could take as data or record.** Real numbers go in
  a real table or a real chart, always.
- **No text inside the image.** Generated text comes out malformed, and a
  diagram with garbled labels is worse than no diagram. Diagrams are SVG, same
  path as charts.
- **Nothing evidentiary** — no photo of a real place, person, or screen. That
  is a factual claim about the world.
- `alt` is required. `alt=""` is allowed and means "purely decorative"; it is
  a decision, not an omission.
- **Full-bleed art must be a raster or a flat-fill SVG.** A gradient inside an
  SVG silently fails to paint inside `.bleed` — see `folio gotchas`.

Plates suit `editorial` and covers. `minimal` is built on having nothing to
hide behind and `technical` is built on density — in both, an illustration is
usually the wrong answer.

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

## Footnotes

Authored inline, in the sentence that provoked the note, and set at the foot of
whatever page that sentence lands on. Never type a number: the call in the text
and the marker under the rule are both the renderer's counter, so notes
renumber themselves when one is added and a note moves with its call when the
text repaginates.

```html
<p>The claim in the body<span class="fn">Anthony Grafton, <em>The Footnote: A
Curious History</em> (Harvard University Press, 1997).</span> continues after
it.</p>
```

Write the note as ordinary prose and wrap it across source lines like anything
else — `folio build` collapses whitespace inside a `.fn` first, because this
renderer would otherwise turn a source newline into a hard line break.

**Keep a note out of a block that can only move whole.** `.cols`, `.fig-row`,
`.signature` and anything else that does not fragment is laid out, contributes
its notes to the page, and then jumps *entire* to the next page if it does not
fit — leaving the notes a page ahead of their calls. `folio check` reports it
as `orphan-note`. Move the sentence into ordinary prose.

This is the one component a browser cannot reproduce: none implements
`float: footnote`. In the shareable `.page.html` a note becomes a marked aside
in the flow rather than vanishing, so use footnotes when the PDF is the
deliverable and the web page is the courtesy copy.

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
from folio import theme

plt = theme.use()                      # applies palette + fonts for the theme
fig, ax = plt.subplots(figsize=(7.01, 2.5))
ax.bar(labels, values, color=theme.BRAND, zorder=3)
theme.grid(ax)
theme.save(fig, "charts/fig-example.svg")
```

Colours: `theme.BRAND` `BRAND_DEEP` `RAMP` (5-step) `SUCCESS` `WARNING`
`ERROR` `INK` `MUTED` `GRID`.

**Size in real inches at the width it will print** — see the per-theme table
under Figures above; there is no single number, because column width follows
each theme's page margins. Never scale a figure in CSS: the labels scale with
it, and `folio check` reports it as `figure-rescaled`. Output is SVG with text
as outlines, so it renders identically everywhere.

**`theme.save` refuses a reference line drawn outside its axis.** `axhline` and
`axvline` are how a chart states a threshold, and the caption almost always
points at one; give it a value beyond the limits and matplotlib draws it, clips
it away, and says nothing. The report in this repo shipped `axhline(43)` under
`set_ylim(0, 34)` for four releases with a caption promising a dotted line that
was never on the page. Widen the limit to include the line, or drop the line
and the sentence that points at it. A line *on* the boundary — a baseline at
zero under `ylim=(0, n)` — is drawn, and passes.

**Put annotations outside the data area.** A label placed at the top left of
the axes is one data change away from having a line drawn through it, and that
is invisible to every check folio has: chart text is outlined, so `text-overlap`
stops at the figure's edge. `ax.text(0, 1.04, …, transform=ax.transAxes)` sits
above the plot where nothing can reach it.

---

## Writing systems

folio detects the scripts in your document and sets `lang` and `dir` for you.
You only need to intervene in two cases:

- **Chinese vs Japanese** — they share Han characters, so declare
  `<html lang="zh">` or `<html lang="ja">` when a document is mostly Han.
- **A document whose language differs from its content** — a mostly-English
  document quoting long Korean passages, for instance.

An explicit `<html lang="…">` always wins.

What it buys you: Korean gets `word-break: keep-all` so words never split
mid-syllable; Japanese and Chinese get kinsoku line breaking and no
hyphenation; Thai, Lao, Khmer and Burmese defer to the shaper; Indic scripts
keep clusters whole; Arabic, Hebrew, Persian and Urdu get a mirrored
right-to-left layout.

Check fonts before you ship: `folio fonts document.html`.
