# Where folio stands, and what to do next

Written 2026-08-15, at the end of the session that shipped the footnote
document. Read this first; it is the shortest path back into the work.

## State

`main`, tree clean, 365 tests passing, all ten examples and all seven scaffolds
reporting **No layout problems found**. 24 check rules, 7 document types,
4 themes. (The count earlier notes gave was low: three of the rules live in the
`CHARACTER_RULES` table and the regex those notes counted with only sees the
ones written out as `Finding("…")`.)

Phases 1 and 2 of the quality program are shipped. Phase 3's four capabilities
— footnotes, `data-pdf`, `data-binding`, `data-print` — are built; footnotes are
now documented, exercised by a real document and guarded by a rule, and press
is broken in two measurable ways (below).

## Do these in order

### 1. Fix `data-print="press"` — it produces a bleed nothing bleeds into

The newest finding, and the only shipped capability that is actively wrong.
Both halves were measured on a rendered page:

- **Crop marks are clipped.** WeasyPrint draws them inside the bleed area and
  the media box ends there. At `bleed: 3mm` only a stub of each mark survives;
  at 8mm they are whole. So the page box needs room for the marks *outside* the
  artwork bleed — which means a larger CSS `bleed` than the 3mm of ink.
- **Nothing reaches the bleed.** `.bleed` and the cover plate stop at the trim
  edge, so the 3mm beyond it is white — exactly the sliver a bleed exists to
  prevent. Content painted past the page box *does* reach the media box
  (verified with a control: a band with `margin-left: calc(-20mm - 3mm)` under
  `bleed: 3mm` paints to x=0), so the fix is reachable. It needs `.bleed` widened
  by the bleed distance and the cover's absolutely-positioned furniture moved
  with it, in the injected `production_css` only.

Do not shoot a press image for the README until this is fixed; the last
gallery commit exists because the README was advertising defects.

### 2. Finish the look pass

All pages render under `examples/*/document.pages/`; regenerate with
`folio build <doc> -q && folio preview <doc>.pdf`.

Read so far: `exhibition` p2–p3, `quarterly-report` p3, `runbook` p1,
`programme` p1, `case-study` p2, and all six pages of `essay` (twice, before and
after the notes moved).

**Why it matters more than it sounds.** Every defect fixed this session was
found by opening a PNG. `orphan-note` exists because a page image showed two
notes with no calls above them; no rule saw it, and the checker was green.

**Settle this first:** `exhibition` p2. One reading of the layout tree says it
is 100% full; a PNG appeared to show it half empty after the ragged-right
change. If the page is full, the "regression" reported two sessions ago was
wrong and can be disregarded. `thin-page` will not catch it either way — it
fires below 45% and that page sits near 52%.

### 3. One CJK document through the whole loop

folio's font machinery is well tested and **no CJK document has ever been looked
at**. All ten examples are Latin. This is where the kit has the most to prove
and the least evidence, and where its worst historical defect lived.

### 4. Validate the PDF variants

`data-pdf` declares PDF/A and PDF/UA; nothing has ever been run through a
validator. Claim only what one confirms — WeasyPrint states its output is not
guaranteed valid.

## Traps, each of which cost real time

1. **Do not edit a function by replacing a slice between two landmarks.**
   `check.py` is 1300 lines and its neighbours move; this silently deleted two
   functions once and four SKILL.md entries once. Replace the thing itself.
2. **`hyphenate-limit-chars` and `text-align` are real properties, not
   tokens.** `base.css` sets both on `body`, so a declaration in a theme's
   `:root` block loses on specificity and does nothing.
3. **Three SKILL.md tests will refuse your prose.** Every rule name must appear
   as `` `rule-name` ``; any bare `--word` is read as a CLI flag that must
   exist; every scaffold must be routed to.
4. **A page check only sees what hangs off the document root.** Margin boxes and
   the footnote area are PageBox children and have to be passed in as their own
   roots — which is why nothing measured a note for a whole release. If you add
   a rule, ask which of the three trees it should run against.
5. **A relative type size inside another relative type size will trip
   `type-drift` eventually.** It took the first four-theme build of a document
   with footnotes to surface `0.86em × 0.7em`. Name the step.

## Dead ends — do not re-derive

- **OS/2 codepage bits do not identify a face's language.** WenQuanYi Zen Hei
  declares Korean; Noto Sans CJK KR declares Chinese. The bits record what a
  face can *encode*, not what it was drawn for.
- **Hanging punctuation, drop caps and `text-wrap: balance` silently no-op**
  on this renderer. All three were tested against a control.
- **No Latin face folio resolves has `smcp` or `onum`** — Inter, P052 and
  DejaVu Serif all lack both.
- **A flex container does not fragment.** `.cols` moves whole to the next page,
  and until this session it left its footnotes behind. Keep notes out of it;
  that is what `orphan-note` now says when you forget.
- **A minimal repro of a note stranded *before* its call was not found.** Eight
  attempts, sweeping the fill in 2mm steps with and without the aside; the real
  document does it reliably and the fixture never did. The rule's test covers
  the *after* direction, which is deterministic between 175mm and 195mm of fill.

## Two stale claims in the spec

The Phase 1 spec carries amendment boxes where execution overturned it (the
prose floor is 6 lines not 8; the measure is 130mm not 68ch; hyphenation was a
repair, not insurance). The boxes are deliberate — the spec's value is partly
that it records a prediction a rendered page later contradicted. Do not tidy
them away.
