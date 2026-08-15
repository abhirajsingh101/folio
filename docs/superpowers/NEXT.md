# Where folio stands, and what to do next

Written 2026-08-15, at the end of the session that shipped the footnote
document. Read this first; it is the shortest path back into the work.

## State

`main`, tree clean, 371 tests passing, all eleven examples and all seven scaffolds
reporting **No layout problems found**. 24 check rules, 7 document types,
4 themes. (The count earlier notes gave was low: three of the rules live in the
`CHARACTER_RULES` table and the regex those notes counted with only sees the
ones written out as `Finding("…")`.)

Phases 1, 2 and 3 of the quality program are shipped: footnotes, `data-pdf`,
`data-binding` and `data-print` are built, documented, exercised by a real
document and — where they can be — guarded by rules. Press bleeds properly as
of this session; `--bleed` is the ink, and the page box is derived from it so
the crop marks have somewhere to live.

The README is now the showcase: every example appears there, two pages each,
plus the spread, the footnote close-up and a press corner. If you add an
example, add its strip — `SHOWCASE` in `docs/gallery/shoot.py` — or it is a
document nobody sees.

## Do these in order

### 1. Finish the look pass

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

### 2. The rest of the non-Latin loop

`examples/conservation` took Korean through it and found three things in one
build (see the changelog). What is still unexercised:

- **Japanese and Chinese.** Kinsoku breaking is implemented and has never set a
  page. A Japanese document would also test the kana/Han discriminator from the
  other side.
- **RTL — half done, and the half that is left needs a reader of Arabic.**
  `examples/proposal-ar` renders and checks clean, and building it fixed two
  real defects in `rtl.css` (below). What has *not* happened is the pass that
  matters: nobody who reads Arabic has looked at the page. Composition, the
  wording of a commercial proposal, and whether the digits and the currency sit
  where a Saudi reader expects are all unverified — the author of that document
  misread one of its own headings as reversed when it was correct. **It is
  deliberately not in the README showcase for that reason.** Get it read, then
  add its strip to `SHOWCASE` in `docs/gallery/shoot.py`.

  The two defects it did find, both measured against a control:
  `letter-spacing` prises apart a cursive script — every theme tracks its
  labels, and tracked Arabic reads as disconnected shapes; and the Arabic faces
  want a line box of 2.11em where Inter wants 1.21, so sixteen pairs of
  elements overlapped. Both are fixed in the RTL layer, which ships only with an
  RTL document, so no Latin page moved.

- **Hebrew has no face on this machine.** `folio fonts` will report it; the
  install path is `folio fonts --install hebrew`.
- **The measure canon is Latin.** 45–90 characters is Bringhurst's range for
  Latin; a full-width glyph is about twice a Latin letter, so the same column
  holds half as many. `conservation` measures 47 characters a line and passes,
  but only because its Hangul is diluted by Latin units and digits — a pure
  Hangul document in the same column measures about 37 and would be reported as
  too narrow. Make `_check_measure` script-aware before that lands on someone.

### 3. Validate the PDF variants

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
4. **`font:` shorthand resets `line-height` to `normal`, and `normal` is read
   off the *strut* — the first font on the element — not off the face that set
   the glyphs.** In a Latin document those are the same font. In a CJK one they
   are not, and stacked labels overlap. 104 declarations in the themes are
   written this way; the timeline is the only one measured to collide so far.
5. **A page check only sees what hangs off the document root.** Margin boxes and
   the footnote area are PageBox children and have to be passed in as their own
   roots — which is why nothing measured a note for a whole release. If you add
   a rule, ask which of the three trees it should run against.
6. **A relative type size inside another relative type size will trip
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
