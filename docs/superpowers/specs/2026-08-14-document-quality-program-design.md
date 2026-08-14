# Higher-quality documents: the floor, the resolved face, and the ceiling

**Status:** approved, not yet implemented
**Date:** 2026-08-14
**Ships as:** three releases — 0.8.0 (the floor), 0.9.0 (the resolved face),
0.10.0 (the ceiling). Version numbers provisional; the sequence is not.

## Problem

folio produces documents that pass `folio check` cleanly and are still,
measurably, not typeset to the standard the kit claims. Two of the oldest
rules in the trade are being broken in the shipped examples, and neither is
visible to any rule folio owns — because every rule it owns measures geometry,
and both of these defects have perfectly correct geometry.

### The measure is too wide in five of nine examples

Body copy, measured off the laid-out document: line boxes whose nearest block
ancestor is a `<p>`, at the modal font size, excluding each paragraph's last
line. The canon — Butterick, and every book-design guide that agrees with him —
puts a comfortable line at 45–90 characters and the leading at 120–145% of the
point size.

| example | body | leading | chars/line | |
|---|---|---|---|---|
| architecture | 8.9pt | 1.46 | 51 | ✓ |
| programme | 9.6pt | 1.62 | 47 | ✓ |
| lookbook | 10.2pt | 1.66 | 58 | ✓ |
| menu | 7.4pt | 1.21 | 6 | not prose — see the 8-line floor below |
| case-study | 10.2pt | 1.66 | **92** | over |
| runbook | 8.6pt | 1.46 | **98** | over |
| exhibition | 10.2pt | 1.66 | **98** | over |
| quarterly-report | 9.8pt | 1.58 | **109** | over |
| survey | 9.8pt | 1.58 | **110** | over |

At 109 characters the eye loses the line return, which is the whole reason the
range exists. The leading in those same rows — 1.58 to 1.66, against a canon
ceiling of 1.45 — is not an independent defect. It is compensation for the
measure, and it is what a designer reaches for when the column is too wide to
fix.

### Straight apostrophes in seven of nine examples, and three of seven scaffolds

Almost every occurrence is a possessive: `Meridian's`, `Halloran's`,
`yesterday's`, `monolith's`, `survey's`. Typed as U+0027, which in a serif face
renders as a vertical tick — a foot mark, not an apostrophe. The exception is
worse than the rule: a heading, set large, reading `What "done" means for Q4`
with straight double quotes.

This is the single most reliable amateur tell in typesetting, it is present in
the artefacts people look at first, and it has survived seven releases under a
green `folio check`. The scaffolds matter more than the examples: `case-study`,
`proposal` and `runbook` each ship two, so every document started from one
inherits the defect.

### Capabilities the renderer supports and folio does not use

Each verified by rendering it on WeasyPrint 68 on the development host, not
read from a support table:

- **Footnotes.** `float: footnote` with `::footnote-call` and
  `::footnote-marker` renders correctly. folio has no footnote at all.
- **Recto and verso.** `@page :left` / `:right` produce genuinely mirrored
  margins (measured: 113px against 57px on facing pages). folio has no binding
  awareness.
- **Print production.** `bleed` and `marks: crop cross` are honoured. folio's
  `.bleed` is a full-width content class and unrelated.
- **PDF conformance.** `write_pdf()` is called with **no options at all** — no
  PDF/A variant, no PDF/UA tagging, no explicit metadata.

### What is already right, and is therefore not in scope

Checked before proposing, because proposing a fix for something already fixed
is its own defect:

- Contents page numbers are real `target-counter`, not typed by hand.
- Bookmarks come from WeasyPrint's user-agent stylesheet already.
- Hyphen ladders max out at **one** line across all nine examples.
- Runt last lines: at most two in any document.
- `orphans` and `widows` are set to 3 in `base.css`.

## Goals

- Body copy in every shipped example sits inside 45–90 characters, with leading
  back near 1.45 rather than compensating at 1.66.
- No straight quote, no `--` dash, no dotted ellipsis survives in prose, in any
  example or scaffold — enforced by a rule, not by a one-time sweep.
- A wrong-typeface document becomes catchable, including the case where the
  stack names the right family and the machine does not have it.
- folio can set a footnote, mirror a bound document, and emit a file a printer
  or an archive will accept.

## Non-goals

- **No hanging punctuation, drop caps, or balanced headings.** All three are
  things a well-set book has. All three were tested against a control on this
  renderer and silently no-op: `hanging-punctuation` moved the first text box
  by 0.00px, `initial-letter` left `::first-letter` at the body size, and
  `text-wrap: balance` produced line widths identical to the unbalanced
  control. They stay out until they would do something.
- **No rule for the spaced hyphen** (` - ` used as a dash). The corpus gives
  one occurrence, and it is `SELECT now() - last_replay` inside a `<code>`
  element — a real minus. The evidence for the rule is evidence against it.
- **No old-style figures.** They belong in a well-set book, and none of the
  four Latin faces folio resolves carries an `onum` table — Inter, P052 and
  DejaVu Serif all lack it. Asking for them would get synthesised lining
  figures, which is the same defect as fake small caps wearing different
  clothes.
- **No new theme, no fifth direction.** The measure lands as a token the four
  existing themes each set.
- **No change to the two-layer `base.css` / theme contract.**

## Decisions already made

| Decision | Choice | Why |
|---|---|---|
| Order | Rules before fixes | A fix that is not measured comes back. The apostrophes are the proof: seven releases, clean check. |
| Measure fix | One `--measure` token, not nine patches | The defect is systemic. Five separate corrections would drift apart by the next release. |
| Column treatment | Prose measured, figures and tables full width | The editorial pattern. Capping everything leaves a ragged right edge that reads as a fault; capping prose alone reads as deliberate. |
| Severity of all four character rules | `warn`, not `error` | Each has a legitimate exception (a data page, a quoted string). An error that people learn to expect is worse than a warning they read. |
| Code exemption | `code`, `pre`, `kbd`, `samp` on every character rule | Measured, not assumed: runbook's four `--` hits are `recon report --since 7d` and `deploy gate --closed`, correct as typed. |
| `font-fallback` | Rewritten to measure, not extended | The stack-reading version has a demonstrated false negative. Keeping both would mean keeping the one that is wrong. |
| PDF/A claim | Only what a validator confirms | WeasyPrint states its output is not guaranteed valid. "Declares PDF/A-3b" until veraPDF says otherwise. |

---

## Phase 1 — The floor: characters and measure

### The rules

Four rules in `check.py`, all measuring the laid-out document, all exempting
`code` / `pre` / `kbd` / `samp`.

| rule | severity | trips on | evidence in the corpus |
|---|---|---|---|
| `straight-quote` | warn | `'` or `"` in prose; digit-adjacent exempt, because feet and inches *should* be straight | 33 in the rendered text of 7 examples; 6 possessives across 3 scaffolds |
| `measure` | warn | median characters per line of body copy outside 45–90 | 5 of 9 examples, worst at 110 |
| `dash` | warn | `--` standing in for an em dash | none in prose; 4 in code, all correct |
| `dot-ellipsis` | warn | three periods where `…` belongs | none |

`dash` and `dot-ellipsis` are insurance rather than repairs, and the changelog
must say so plainly rather than implying they fixed something.

**`measure` is document-level**, reported once alongside `heading-skip` and
`type-drift`, not once per page. Body copy is the modal font size among `<p>`
line boxes. A document with **fewer than 8 such lines is skipped** — `menu` has
four and `architecture` six, and neither is prose; a median over that few lines
is noise, not a measurement.

**`straight-quote` is deduplicated per page** — one finding carrying the count
and the first instance, not eighteen findings on one page of the
quarterly-report.

### The fixes

In this order, so each rule is watched to fail before anything makes it pass:

1. The four rules, each with its golden pair.
2. Apostrophes and quotes: nine examples, three scaffolds.
3. `--measure`: each theme declares its column; `base.css` applies it to the
   prose blocks in the document flow — `p`, `ul`, `ol`, `blockquote`. Figures,
   tables, `figcaption`, and components that own their width (`.metric`,
   `.toc`, `.bleed`, the cover) are untouched. Target 65–75 characters, then
   bring leading down toward 1.45.
4. `hyphenate-limit-chars`, unset today. Insurance — the measured ladders are
   one line — and labelled as such.

### The risk this phase carries

Narrowing the measure changes how every shipped example looks. That is not a
change to claim on a green test suite. It gets the pass `folio gotchas`
prescribes: render the pages to PNG and look at them, one at a time, before the
release. The 0.7.0 look pass found four false numbers that every rule had
passed; this one is more likely to find something, not less.

---

## Phase 2 — The resolved face

WeasyPrint deactivates a text box's pango layout after layout to free it, and
`reactivate(style)` rebuilds it — which is exactly what the draw stage does
before painting. From there `item.analysis.font` and `pango_font_describe` give
the family that **actually set that run**, fontconfig substitutions included.
Verified working on this host.

The measurement it makes possible, run on three Korean documents:

| stack the document names | face that actually set the Hangul |
|---|---|
| `"Inter", sans-serif` | WenQuanYi Zen Hei — Chinese |
| `"Inter", "Noto Sans KR", sans-serif` | WenQuanYi Zen Hei — Chinese |
| `"Inter", "Noto Sans CJK KR", sans-serif` | Noto Sans CJK KR ✓ |

The middle row is the point. The document names a Korean family, so today's
`font-fallback` — which reads CSS stacks — judges it covered and says nothing,
while the text renders in a Chinese face. That is a live false negative on the
development host, not a hypothesis.

Two rules from the one mechanism:

- **`font-fallback`, rewritten** to compare each script against the face that
  set it. Strictly stronger than the version it replaces: it also catches the
  machine with no Korean face installed at all, where folio's injected CSS is
  blameless and the output is still wrong. The `judgeable` / `LATIN_ONLY`
  machinery in `scripts.py` exists to avoid judging families folio has never
  heard of; measuring the resolved face removes the need to guess, so that
  caution can relax to a narrower question: does the face that set this script
  cover this script.
- **`fake-small-caps`.** *If you don't have real small caps, don't use them at
  all.* This is a repair, not insurance. `editorial.css:111` sets
  `p.lead + p::first-line { font-variant: small-caps }` on `--font-body`, and
  the OpenType feature tables of the faces folio actually resolves say:

  | face | `smcp` | `onum` |
  |---|---|---|
  | Inter — 39 GSUB features | **no** | **no** |
  | P052 — folio's Latin serif | **no** | **no** |
  | DejaVu Serif | **no** | **no** |
  | Noto Serif | yes | yes |

  So the opening line of the first paragraph of every editorial document is
  set in capitals that pango scaled down, which is the thing the rule exists to
  forbid. The rule reports it; the theme then either drops the small caps or
  names a face that has them.

**The mechanism, verified end to end rather than assumed.** The route to a
resolved face's feature tags is not the obvious one — `hb_font_get_face` is not
in WeasyPrint's cffi surface, and `pango_fc_font_map_get_hb_face` lives in
`libpangoft2`, not `libpango`, and needs its arguments cast to `PangoFcFontMap *`
and `PangoFcFont *`. From the face, `hb_face_reference_table(b"GSUB")` returns
the raw table and its FeatureList is a count followed by fixed 6-byte records —
about twenty lines to read, and **no new dependency**, which keeps the promise
`pyproject.toml` makes about a broken install still being a working one.

This phase is where the kit stops trusting what a document *says* about its
typography and starts measuring what it *got* — the same move `check.py` made
for geometry, applied to type.

---

## Phase 3 — The ceiling: book craft

- **Footnotes.** `float: footnote`, `::footnote-call`, `::footnote-marker`,
  themed per direction; a `.fn` component in `COMPONENTS.md` with a screen
  fallback, since no browser implements the property and the `.page.html`
  output must not silently swallow the note.
- **Recto and verso.** `@page :left` / `:right` mirrored margins with mirrored
  running heads — title verso, section recto. Opt-in; it means nothing for a
  document that will not be printed double-sided and bound.
- **Print production.** `bleed` and `marks: crop cross`, opt-in, for work going
  to a commercial printer.
- **PDF conformance and metadata.** Pass `pdf_variant`, an identifier, and real
  document metadata to `write_pdf`. PDF/A for archival, PDF/UA for
  accessibility. folio is closer to PDF/UA than it looks: `heading-skip`,
  `image-alt` and `image-role` already enforce most of the structure the
  specification asks for. Claims limited to what a validator confirms.

---

## Testing

Every rule gets the golden pair `test_check.py` already uses: a document that
trips it, and a neighbouring one that must not. The exemptions get their own
cases — a `--` inside `<code>`, an inch mark after a digit — because those are
where a character rule earns or loses its keep.

`SKILL.md` gains an entry per rule; the existing conformance test fails a rule
that ships without one, so this is enforced rather than remembered.

The examples are re-rendered and **looked at** after the measure change. A
green suite is not evidence about how a page looks.

## How the numbers in this spec were obtained

Every figure above came from running something on the development host —
WeasyPrint 68, Python 3.12 — not from a support table or a style guide's
assertion. Recorded here so the next person can re-run them rather than take
them on trust, and so a figure that later turns out wrong can be traced to its
method.

- **Measure, leading, point size:** each example put through `build.prepare()`
  and rendered; line boxes whose nearest block ancestor is a `<p>` collected;
  modal font size taken as body copy; median character count over full lines,
  each paragraph's last line dropped as short by definition.
- **Characters:** regex over the rendered text for the four defect classes,
  with the offending context printed and read one at a time. This is what
  showed the `--` hits were CLI flags and the ` - ` hit was SQL, which is why
  the exemptions are in the design and the spaced-hyphen rule is not.
- **Renderer capabilities:** each feature rendered twice, with and without the
  property, and the two layouts compared. A feature that changed nothing was
  recorded as unsupported. This is how hanging punctuation, `initial-letter`
  and `text-wrap: balance` were ruled out — all three parse without error and
  do nothing.
- **Resolved faces:** `pango_layout.reactivate(style)`, then
  `item.analysis.font` per run, then `pango_font_describe`. OpenType features
  via `pango_fc_font_map_get_hb_face` and a GSUB FeatureList read.
- **Hyphen ladders and runts:** counted per paragraph across all nine examples,
  which is why neither appears in the goals.

## Release impact

- **0.8.0** changes the appearance of every shipped example. The changelog
  entry leads with that, names the five documents whose measure changed, and
  states plainly which of the four new rules repaired a real defect
  (`straight-quote`, `measure`) and which are insurance (`dash`,
  `dot-ellipsis`, hyphenation limits).
- **0.9.0** replaces a rule rather than adding one. A document that passed
  `font-fallback` on a machine missing its fonts will now report. That is the
  intent, and the entry says so.
- **0.10.0** adds capability and takes nothing away. Its honest limit is PDF/A
  and PDF/UA validity, which folio does not control.
