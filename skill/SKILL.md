---
name: folio
description: Use when the user asks for a PDF, report, progress report, whitepaper, proposal, invoice, handbook, or any print-ready document — "make a report", "PDF of this", "write this up", "document for the team". Produces branded, typeset PDFs plus a shareable HTML page from one design system, with charts themed to match. Do NOT use for slide decks or video.
version: 0.1.0
license: MIT
---

# folio

Print-ready documents from HTML, using one shared design system.

Install once: `pipx install "folio-press[all]"` — then `folio` is on PATH.

## Why this exists

Documents drift. Ask an agent for a PDF twice and you get two different
stylesheets. folio fixes the design system in *files* — a stylesheet, a chart
theme, print page furniture — so every document comes out consistent instead of
being re-improvised.

Markdown is not the answer here: it has about eight visual elements, and a
document that looks designed needs a cover composition, running headers,
numbered figures, metric tiles, callouts with tone, status pills, and a
contents page whose numbers are real. Author in HTML with folio's classes.

## Workflow

```bash
folio doctor                        # FIRST RUN ON A NEW MACHINE — what's missing
folio themes                        # the four design directions
folio init --theme editorial        # scaffold document.html + charts.py
folio build document.html --check   # render, then measure the layout
folio check document.html           # measure without rebuilding
folio components                    # the component vocabulary — READ FIRST
folio gotchas                       # silent renderer failure modes
folio imagery                       # before adding any non-chart image
```

`folio build` runs a sibling `charts.py` first, injects the stylesheet, then
renders. The source document never links the stylesheet.

## Choosing a direction

Ask, or infer from the audience — do not always take the default.

- `report` — leadership, clients, anything that should read as corporate.
- `editorial` — a piece meant to be *read*: essays, annual reviews, research
  write-ups. Long prose, few tables.
- `technical` — engineers at a desk. Dense, table-heavy, many identifiers.
  Fits noticeably more per page.
- `minimal` — design-literate audiences, short high-signal documents. It is
  the least forgiving: with no fills or borders, weak content shows.

Set it on the document (`<body data-theme="…">`), never per element.

## The loop — do not skip a pass

A document is not done when it renders. Print defects are silent by nature:
the PDF is valid and merely looks wrong. Work in passes, and do not move on
while a pass is failing.

**Pass 1 — draft.** `folio init --theme <t>`, then write the content using the
component vocabulary. Real data only.

**Pass 2 — measure.** `folio build document.html --check`

This renders and then measures the actual layout tree: text overrunning its
box, elements overlapping, pages a fifth full, headings stranded at a page
foot, text below legible size, rasters upscaled past their pixels, and type
too close in tone to what it sits on. Every rule encodes a defect that really
shipped.

`low-contrast` is measured against WCAG AA — 4.5:1 for body text, 3:1 once
type is large — after resolving what the glyph actually sits on, so reversed
cover type passes and grey-on-grey does not. The shipped themes all clear it.
If your own colours trip it, **darken the colour in `brand.css`; never raise
the threshold and never silence the rule.** On paper there is no backlight and
no zoom, so a caption that looks merely quiet on screen is the one that comes
back from the printer unreadable.

Three further rules ask whether the document was built the way the kit
intends, because that failure is invisible — a hand-rolled style renders
perfectly:

- `inline-style` — you wrote `style="…"`. Use a class, or `brand.css`. If the
  component genuinely does not exist, that is a pull request to folio (rule 3),
  not an exception here.
- `heading-skip` — an `h2` jumping to `h4` claims a level of structure that
  was never built.
- `type-drift` — two type sizes less than 1% apart. No reader can tell them
  apart, so the scale has a step that carries no meaning. The usual cause is a
  relative size compounding: an `em` nested inside another `em`.

- **Any `✗` error → fix and re-run.** Never hand over a document with errors.
- **Each `!` warning → judge it.** Most are real. A thin page almost always
  means a block jumped rather than fitting; reorder the section, or mark a
  short table `class="keep"`.

**Pass 3 — look.** The checker measures geometry, contrast and conformance —
not taste. It cannot see that a chart is the wrong type for its data, that a
caption states the obvious, or that a page is simply ugly.

`--check` has already rendered the pages and printed the directory:

```
  pages     ./document.pages  (9 png)
```

**Open them.** This is the pass that gets skipped, and skipping it is how an
ugly document ships with a clean report. `folio preview document.pdf`
re-renders them on demand.

Read every page, not just the one you were working on. Print layout is global:
a change to table padding can strand rows four sections later.

**Pass 4 — read it as the recipient.** Does the first page answer "what
happened and what now?" Does every caption state a conclusion rather than
naming the axes? Is any number unsourced? Cut anything that survives only
because it was easy to generate.

Only after all four is it done.

## Rules

1. **Run `folio components` before authoring.** Use the existing classes:
   cover, toc, section, metrics, figure, fig-row, table, pill, callout,
   timeline, steps, tick, pullquote, code. If something seems missing, look
   again — it usually exists.
2. **Never hand-roll a style.** No inline `style=`, no `<style>` blocks in the
   document. To restyle a project, write `brand.css` beside the source; it is
   appended after the design system and always wins. Usually one line:
   `:root { --brand: #7A1F3D; }`
3. **Never edit the installed package for one document.** If a component is
   genuinely missing everywhere, that is a pull request to folio, not a local
   hack.
4. **Charts go through `from folio import theme`.** Size figures in real inches
   at final printed width — full column 6.6in, half column 3.25in. Never scale
   a figure in CSS; the labels shrink with it. Output SVG, never PNG.
5. **Caption the conclusion, not the axes.** "Deploy frequency doubled after the
   July cutover" beats "Deploys per month".
6. **Use real data.** Pull actual numbers from the repo — git history, test
   counts, planning docs. A report with invented figures is worse than none.
7. **Never claim a document is finished without a clean `--check` and a look
   at the rendered pages.** "It built" is not "it is good".
8. **If `folio build` warns about the Chromium renderer**, tell the user: their
   PDF has no running headers or page numbers, and `folio doctor` prints the
   fix.

## Imagery

Real data is *always* a real table or a real chart. Never an image of one.

For everything else — a cover, a section opener, a texture — the default
answer is **no**. A generic illustration does not read as neutral; it reads as
nobody having thought about the page. The bar: can you say in one sentence
what the image does that the words do not? "Breaking up the text" is not an
answer.

Never generate: anything a reader could take as data; anything with text in it
(models malform words, and a diagram with garbled labels is worse than no
diagram — diagrams are SVG); anything evidentiary, meaning a photo of a real
place, person, product or screen; anyone else's logo.

Where it earns its place: covers, section openers in a long `editorial`
document, a conceptual plate in an essay. `technical` and `minimal` should
have none — one is built on density, the other on having nothing to hide
behind.

Every such image is a `<div class="plate">`, never a `<figure>` — a figure is
numbered, captioned and referenced, and lending that grammar to decoration is
how an illustration gets read as evidence. `folio check` enforces the boundary
both ways.

**Run `folio imagery` before generating anything.** It carries the prompt
shape that avoids stock-AI output, the Codex invocation, resolution for print,
and the placement rules.

## Pagination

Tables split across pages; figures and callouts do not. If a page comes out
mostly empty, the cause is almost always a block that could not fit and jumped.
Fix by reordering blocks or adding `class="keep"` to a short table that must not
split. WeasyPrint ignores `widows`/`orphans` on table rows, so there is no CSS
knob for it.

## Writing systems

Scripts are detected and `lang`/`dir` set automatically, including full RTL
for Arabic and Hebrew. Two cases need you:

- Declare `<html lang="zh">` or `lang="ja"` for Han-heavy documents — they
  share characters and the heuristic cannot tell them apart.
- Run `folio fonts <file>` before shipping any non-Latin document. folio
  bundles no fonts; if a script has no font it renders as boxes, and this is
  the command that says so.

## Not for

Slide decks. Video. Academic submissions where a venue mandates its own LaTeX
class. Anything under ~2 pages, where the design system is overhead.
