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
foot, text below legible size, rasters upscaled past their pixels. Every rule
encodes a defect that really shipped.

- **Any `✗` error → fix and re-run.** Never hand over a document with errors.
- **Each `!` warning → judge it.** Most are real. A thin page almost always
  means a block jumped rather than fitting; reorder the section, or mark a
  short table `class="keep"`.

**Pass 3 — look.** The checker measures geometry, not taste. It cannot see
that a chart is the wrong type, a caption states the obvious, or a page is
ugly. Render and actually look:

```bash
pdftoppm -png -r 100 document.pdf /tmp/p && ls /tmp/p*
```

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
