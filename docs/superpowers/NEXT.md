# Where folio stands, and what to do next

Written 2026-08-15, at the end of the session that shipped quality Phases 1
and 2. Read this first; it is the shortest path back into the work.

## State

`main`, tree clean, 348 tests passing, all nine examples and all seven
scaffolds reporting **No layout problems found**. 22 check rules, 7 document
types, 4 themes.

Phases 1 and 2 of the quality program are shipped and in `CHANGELOG.md` under
`[Unreleased]`. Phase 3 is specced and unwritten.

## Do these in order

### 1. Finish the look pass — 8 of 33 pages read

The largest outstanding item and the highest value per hour. All pages are
rendered under `examples/*/document.pages/`; regenerate with
`folio build <doc> -q && folio preview <doc>.pdf`.

Read so far: `exhibition` p2–p3, `quarterly-report` p3, `runbook` p1,
`programme` p1, `case-study` p2 (×2, before and after ragged-right).

**Why it matters more than it sounds.** Four defects this session were found
only by opening a PNG, and no rule saw any of them: the `ch` measure putting
three right edges on one page, a lead hyphenating `an‐other`, `editorial`'s
justification stretching word spaces, and `editorial`'s synthetic small caps.
One further candidate dissolved under a proper before/after comparison — so
flag candidates, then verify with two renders before acting.

**Settle this first:** `exhibition` p2. One reading of the layout tree says it
is 100% full; a PNG appeared to show it half empty after the ragged-right
change. Both cannot be true. If the page is full, the "regression" reported at
the end of that session was wrong and can be disregarded. If it is half empty,
chase the interaction with `.bleed { break-before: avoid }` — and note
`thin-page` will not catch it, because it fires below 45% and that page sits
near 52%.

### 2. Phase 3 — the ceiling

`docs/superpowers/specs/2026-08-14-document-quality-program-design.md`. Each
capability was verified working on this renderer before it was proposed.

Ordered by how much they unlock rather than by effort:

- **Footnotes** — SHIPPED and verified on a rendered page (`489ceda`, wrap
  fixed in the commit after). Notes are authored inline, carry the renderer's
  counter, find their own page, and degrade to a marked aside on screen.
  One thing to know: WeasyPrint turns a newline *inside* a footnote into a
  hard line break, which no stylesheet can reach — `build.flatten_footnotes`
  collapses whitespace inside `.fn` before rendering. Do not remove it, and do
  not look for the cause in CSS.
- **PDF conformance and metadata.** `write_pdf()` is currently called with *no
  options at all*: no PDF/A, no PDF/UA, no metadata. This is what stands
  between folio and archival, regulatory and accessibility-mandated work, and
  folio is closer to PDF/UA than it looks — `heading-skip`, `image-alt` and
  `image-role` already enforce most of the structure. Claim only what a
  validator confirms; WeasyPrint states its output is not guaranteed valid.
- **Recto and verso** (`@page :left` / `:right`). Anything bound.
- **Bleed and crop marks.** Anything going to a commercial printer.

### 3. One CJK document through the whole loop

folio's font machinery is now well tested and **no CJK document has ever been
looked at**. Every example is Latin. This is where the kit has the most to
prove and the least evidence — and where its worst historical defect lived.

## Three traps, each of which cost real time

1. **Do not edit a function by replacing a slice between two landmarks.**
   `check.py` is 1200 lines and its neighbours move; this silently deleted two
   functions once and four SKILL.md entries once. Replace the thing itself.
2. **`hyphenate-limit-chars` and `text-align` are real properties, not
   tokens.** `base.css` sets both on `body`, so a declaration in a theme's
   `:root` block loses on specificity and does nothing. Put them on `body`.
   A measurement showing "no effect" may be your edit not applying.
3. **Two SKILL.md tests will refuse your prose.** Every rule name must appear
   as `` `rule-name` ``; and any bare `--word` is read as a CLI flag that must
   exist, so write CSS custom properties as `var(--name)`.

## Dead ends — do not re-derive

- **OS/2 codepage bits do not identify a face's language.** WenQuanYi Zen Hei
  declares Korean; Noto Sans CJK KR declares Chinese. The bits record what a
  face can *encode*, not what it was drawn for.
- **Hanging punctuation, drop caps and `text-wrap: balance` silently no-op**
  on this renderer. All three were tested against a control.
- **No Latin face folio resolves has `smcp` or `onum`** — Inter, P052 and
  DejaVu Serif all lack both. Small caps and old-style figures cannot be
  asked for without synthesis.

## Two stale claims in the spec

The Phase 1 spec carries amendment boxes where execution overturned it (the
prose floor is 6 lines not 8; the measure is 130mm not 68ch; hyphenation was a
repair, not insurance). The boxes are deliberate — the spec's value is partly
that it records a prediction a rendered page later contradicted. Do not tidy
them away.
