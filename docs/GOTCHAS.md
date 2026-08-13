# folio — WeasyPrint gotchas

Every item here is a bug that shipped a *valid PDF that looked wrong*. None
of them raise an error, which is what makes them expensive. They are all
already fixed in folio's stylesheet (`folio css`) — this file exists so they don't get
reintroduced by a well-meaning edit.

---

### Flex children overflow without `min-width: 0`

A `<p>` inside a flex row will run past its container's right edge instead of
wrapping. This is why callouts wrap their prose in `<div class="body">` with
`flex: 1 1 auto; min-width: 0`.

**Symptom:** callout text bleeding over the box edge.

### Flex children reserve empty space without `min-height: 0`

The mirror image of the rule above, and much harder to spot. A flex item's
automatic minimum size is content-based, and with a raster inside one it is
resolved from the image's **intrinsic pixels** rather than the width it is
actually drawn at. A `.cols` column holding a `.plate` over a wrapped
paragraph reserved 170mm — the full measure — for 100mm of content, and the
next block was pushed down past a third of a page of white.

It needs both ingredients: a large raster *and* text that wraps. A thumbnail
does not trigger it, an SVG has no intrinsic pixels so it cannot, and with a
one-line caption the column measures correctly. That combination is why it
survived every other example in this repo and only appeared once a document
put cloth swatches beside real prose.

**Symptom:** a two-up block that ends, then a large gap, then the next
paragraph. Nothing overflows, nothing overlaps, no rule in `folio check` can
see it — only the rendered page can. Fixed in `base.css` with
`.cols > * { min-width: 0; min-height: 0 }`, and held by
`tests/test_layout.py`.

### `break-inside: avoid` on a long table pushes it whole to the next page

A 12-row table with `break-inside: avoid` will not split; it jumps to the
next page and leaves half a page blank. Tables must instead use:

```css
thead { display: table-header-group; }  /* header repeats on each page */
tbody tr { break-inside: avoid; }       /* only rows are atomic */
```

**Symptom:** a half-empty page followed by a table.

### Hyphenation fires inside table cells

`hyphens: auto` on `body` reaches into `<td>`, producing `hard-ware` and
`val-ues` in narrow columns. Fixed with `table { hyphens: none }`.

### `string-set: … content()` swallows child elements

`content()` captures the heading's *entire* text, including the
`<span class="idx">SECTION 01</span>` kicker, so the running header reads
"SECTION 01Executive summary". Use an explicit attribute instead:

```css
h2.section { string-set: section attr(data-section); }
```

### A table caption orphans from its table

`<caption>` needs `break-after: avoid` or it strands at the bottom of a page.

### Unsupported properties fail silently-ish

WeasyPrint prints a warning and continues for `word-break: keep-all`,
`hanging-punctuation`, and `overflow-x`. Korean line breaking therefore needs
`:lang(ko)` handling rather than a global `word-break`. Read build warnings.

### Table rows strand on an otherwise empty page

WeasyPrint does not apply `widows` or `orphans` to table rows — verified, not
assumed. A table that begins near the bottom of a page can leave two rows
alone on the next one.

There is no CSS fix. The remedies are structural:

- **Reorder the section** so the table starts higher on the page. Moving a
  figure or callout to *after* the table usually solves it outright.
- **`<table class="keep">`** on a short table forces it to move whole rather
  than split.
- **Shorten the preceding prose.** Print layout is global: content length two
  paragraphs earlier decides where a table lands.

If a page comes out mostly empty, the cause is almost always a non-splittable
block that could not fit and jumped. Figures, callouts and pull quotes all
behave this way by design — a split callout looks broken.

### `.bleed` cannot bleed off the top of a page

`.bleed` works by cancelling the page margin: negative left and right margins,
and as much again in width. There is no equivalent upwards. Content is laid out
inside the page box and the top margin is not content's to enter, so a bleed
placed first on a page opens *below* that margin — a band that reaches both
side edges of the paper and stops 20–34mm short of the top one.

Nothing is wrong with the file. Nothing overflows, nothing overlaps, and the
page is a perfectly legal object; it simply reads as a misprint, because three
edges reach the paper and one does not. This is what `half-bleed` reports.

Two remedies, and which one is right is a question about the document:

- **Move it into the prose.** A band between paragraphs is the job `.bleed`
  exists for, and there is no strip when something is printed above it.
- **Inset it** — drop `bleed` and let it sit in the measure. A plate that must
  open a page is an inset plate.

Only a `@page` with no top margin can carry a bleed at the head of a page, and
the shipped themes all have one. The cover is the exception, and it is built
differently on purpose: `.cover::before` and `img.cover-plate` are absolutely
positioned at `top: 0`, outside the flow, which is how they reach the edge.

### A gradient inside an SVG does not paint in a `.bleed` container

Put an SVG that fills a shape with `url(#someGradient)` inside `class="bleed"`
and the shape renders as nothing. No error, no warning — the box is laid out
at the right size and stays empty, so the page looks like it has a mysterious
gap. Strokes and flat fills in the same file paint normally, which makes it
read as "the image half-loaded" rather than "the gradient failed".

Measured on WeasyPrint 68, holding everything else constant:

| container | asset | result |
|---|---|---|
| `.plate` | gradient SVG | paints |
| `figure` | gradient SVG | paints |
| `.plate bleed` | gradient SVG | **blank** |
| `figure bleed` | gradient SVG | **blank** |
| `.plate bleed` | PNG | paints |
| `figure bleed` | flat-fill SVG | paints |

So the trigger is the combination — `.bleed` plus a gradient inside the SVG —
not either one alone. `.bleed` sets `width: calc(100% + 2 * var(--page-margin-x))`
with negative margins, and the gradient reference does not survive it.

**Full-bleed art must be a raster (PNG) or a flat-fill SVG.** This matters for
charts as much as for plates: `figure class="bleed"` is a documented pattern,
charts are SVG, and a full-bleed chart that used a gradient fill would vanish
silently. Charts from `folio.theme` use flat fills, so they are unaffected.

### `var()` in an `@page` margin box only sees properties declared on `:root`

A running header written as `color: var(--ink-mute)` works — but only if the
property is declared on `:root` or `html`. Declare it anywhere else and the
colour silently falls back to black.

The page context inherits from the **root element**, not from `body`, so a
token set in a `body { … }` block never reaches the running head. Measured on
WeasyPrint 68:

| declared on | running head resolves to |
|---|---|
| `:root` | the value |
| `html` | the value |
| `body` | **black** |
| any class | **black** |

This bites because `body { }` is the natural place to put document-wide
defaults, and the failure is silent: the PDF is valid and the header is simply
black. An earlier version of folio read this as "var() does not work in margin
boxes at all" and hardcoded three greys into `base.css`, which meant themes
could never restyle the page furniture — and left a 1.9:1 footnote grey in
every document until `folio check` grew a contrast rule and found it.

---

## Things that are *not* bugs

- **Charts must be SVG with text as outlines** (`svg.fonttype='path'`).
  WeasyPrint's SVG text support is adequate but not identical across font
  configurations; outlines remove the variable entirely.
- **WeasyPrint does not run JavaScript.** Plotly/ECharts cannot self-render.
  Export figures to SVG first — `charts.py` exists for this, and a
  pre-rendered figure is also reproducible and diffable.
- **`@page` margin boxes are the reason to use WeasyPrint over headless
  Chromium.** Running headers, page counters, and named pages work properly
  here and poorly there.
