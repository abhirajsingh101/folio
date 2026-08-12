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

### `var()` does not resolve inside `@page` margin boxes

Custom properties are scoped to the element tree, and margin boxes sit
outside it. A running header written as `color: var(--ink-mute)` silently
falls back to black — verified against WeasyPrint 68, not assumed.

This is why `base.css` uses literal colours in its `@page` block and nowhere
else. A theme that genuinely needs different page furniture must restate the
whole `@page` rule with its own literals.

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
