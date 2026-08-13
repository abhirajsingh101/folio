---
name: folio
description: Use when the user asks for a PDF, report, proposal, quote, statement of work, invoice, case study, runbook, SOP, handbook, letter, one-pager, whitepaper, or any print-ready document — "make a report", "PDF of this", "send this to the client", "write this up". Works for one-page documents as well as long ones. Produces branded, typeset PDFs plus a shareable HTML page from one design system, with charts themed to match, and measures the rendered layout for real defects before calling it done. Do NOT use for slide decks, video, or a résumé/CV (applicant tracking systems discard the formatting and the design system actively hurts).
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
folio templates                     # the document types, and the theme each pairs with
folio themes                        # the four design directions
folio init --template invoice       # scaffold that type here (default: report)
folio build document.html --check   # render, then measure the layout
folio check document.html           # measure without rebuilding
folio components                    # the component vocabulary — READ FIRST
folio gotchas                       # silent renderer failure modes
folio imagery                       # before adding any non-chart image
```

`folio build` runs a sibling `charts.py` first, injects the stylesheet, then
renders. The source document never links the stylesheet.

## Route first: what kind of document is this?

Do this before opening an editor. The shape of a document is decided by what
it is *for*, and getting it wrong is not recoverable by styling — an invoice
with a cover page is wrong no matter how good the cover is.

| They asked for | Start from | Shape | Theme | Furniture |
|---|---|---|---|---|
| Report, progress update, findings, review | `init --template report` | cover · contents · sections | `report` | full |
| Proposal, quote, statement of work, bid | `init --template proposal` | cover · contents · scope · pricing · signature | `report` or `editorial` | full |
| Invoice, estimate, credit note | `init --template invoice` | single sheet, no cover | `minimal` or `technical` | `data-furniture="none"` |
| Runbook, SOP, procedure, playbook | `init --template runbook` | doc-control head · numbered steps · warnings | `technical` | full |
| Letter, one-pager, brief, memo | `init --template letter` | single sheet, no cover | `minimal` | `data-furniture="none"` |
| Case study, customer story | `init --template case-study` | headline · metrics · narrative · quote | `editorial` | full |
| Essay, annual review, long read | `init --template essay` | cover · continuous prose · pull quote · notes | `editorial` | full |

The scaffold is a starting shape, not a form to fill in: delete every block the
document does not need, and never leave a placeholder value in place. Read
`folio components` before adding anything that is not already in it, and
`folio gotchas` before debugging a layout.

**Ambiguities worth resolving before you build, not after:**

- *"A report on X"* from a consultant usually means a **client deliverable**,
  not an internal update. Ask who receives it — it changes theme and register.
- *"Something to send the client"* is a proposal if money is being asked for,
  a case study if it is proof, a one-pager if it is a leave-behind.
- *"Documentation"* is a handbook if it is read, a runbook if it is executed
  under time pressure. Those are different documents.
- If they say **"just a quick"** anything, they want one page with no cover.

## Plan before you author

Four lines, written out before any HTML. This is the step that stops the
document drifting run to run, and it takes thirty seconds:

```
Type:      invoice
Reader:    the client's accounts-payable clerk, who will not read prose
Register:  plain and checkable; no persuasion, no adjectives
Evidence:  line items and rates from the user — invent nothing
```

**Register is the one people skip, and it is the one that shows.** For
anything persuasive — a proposal, a case study, a pitch — visible polish is
penalised by the reader, not rewarded. Buyers report docking points when a
document looks machine-made. Restraint is the correct treatment there; save
the plate and the display type for a document nobody is being sold by.

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

**Pass 1 — draft.** `folio init --template <type>` (add `--theme <t>` to
override the pairing), then write the content using the component vocabulary.
Real data only, and delete the blocks this document does not need.

**Pass 2 — measure.** `folio build document.html --check`

This renders and then measures the actual layout tree: text overrunning its
box (`overflow-x`, `overflow-y`), elements overlapping (`text-overlap`),
headings stranded at a page foot (`orphan-heading`), text below legible size
(`tiny-text`), rasters upscaled past their pixels (`image-upscaled`), a vector
drawn well off the size it was authored at (`figure-rescaled`), an image with
no `alt` (`image-alt`) or wearing the wrong role — a plate numbered like
evidence, a figure with no number (`image-role`) — and type too close in tone
to what it sits on (`low-contrast`). Every rule encodes a defect that really
shipped. The report prints the rule name; each one is explained here, so a
finding you do not recognise is a search away rather than a guess.

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

Two rules measure how a page filled, and they mean different things:

- `thin-page` — a page mid-section came out under half full, because a block
  could not fit and jumped. Reorder the section, or mark a short table
  `class="keep"`.
- `page-widow` — a page that was *meant* to end early ended almost empty: the
  last page of the document, or the page before a section break, holding a
  quarter or less. A section ending at 85% is a chapter break and is silent;
  the same section ending at 11% is a tail that spilled. **This is the one to
  take seriously on a short document** — it is what catches an invoice or a
  one-pager that quietly became two pages. Tighten the copy above it, or move
  a block up so the page carries more. A one-page document is never a widow.

One rule is not about geometry at all:

- `font-fallback` — text in a script that nothing in its font stack can set.
  A stack falls through per glyph; when it runs out, the renderer asks
  fontconfig, which never fails and never asks — for Korean on Linux it
  commonly answers with a *Chinese* face. The document renders and is simply
  in the wrong typeface. `folio build` injects covering faces for the scripts
  it detects, so this fires on type styled outside that: a hand-written stack,
  or a `brand.css` that names only Latin faces. Name a family that covers the
  script. The rule stays silent on a family folio does not recognise, because
  that may be exactly the face you chose.

One rule measures *where* a block sits rather than what it measures:

- `half-bleed` — a full-bleed block opened a page. `.bleed` cancels the page
  margin sideways; nothing cancels it upwards, so the block reaches both side
  edges of the paper and stops short of the top one, under a strip of white.
  Either move it into the prose, where a band belongs, or drop `bleed` and let
  it sit inset. Do not try to pull it up — content cannot enter the page
  margin, which is why the cover plate is positioned rather than flowed.

- **Any `✗` error → fix and re-run.** Never hand over a document with errors.
- **Each `!` warning → judge it.** Most are real.

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

## Iron Law

```
NO DOCUMENT IS FINISHED WITHOUT A GREEN --check AND A LOOK AT THE PAGES,
BOTH IN THE MESSAGE WHERE YOU CLAIM IT IS FINISHED.
```

Three things must be true, and you must have established them *now* — not
earlier in the session, not "it worked before":

1. `folio build <file> --check` ran in this message and **exited 0**.
2. The PDF **exists on disk**. Check it. Do not describe a file you have not
   confirmed is there.
3. You **read the page images** in `<name>.pages/`. Every one.

The failure this prevents is specific and common: a model that narrates having
produced a document it never wrote, or that silently drops half the content and
reports success. Users describe it exactly that way — *"it cos-plays like it's
generating an exported version"*, *"somehow half of the document was completely
omitted without me noticing"*. A confident summary is not a document.

`--check` measures the rendered layout tree and exits non-zero on real defects.
It cannot see taste, which is why the page images are not optional.

| Thought | Reality |
|---|---|
| "It rendered, so it's done." | A valid PDF that looks wrong is the *normal* failure here. Print defects are silent. |
| "I'll describe what the document contains." | Then you have not made a document. Build it, or say you did not. |
| "The check passed, no need to look." | The checker cannot see a chart of the wrong type or a caption that says nothing. |
| "I'll use placeholder figures; they'll swap them." | Invented numbers in a document that looks finished is the worst output folio can produce. Ask, or leave the slot visibly empty. |
| "It passed last time." | Evidence has a timestamp. Run it again. |
| "The user is in a hurry." | Then a broken PDF costs them more, not less. |

## What AI-generated documents look like

Readers identify them before reading a word, and say so. Know the tells so you
can avoid them — this is the document equivalent of a design system's
anti-pattern list, and every item below is drawn from a real complaint.

- **Every table set identically** regardless of what is in it — same widths,
  same header treatment, nothing considered. *"The tables followed the same
  format and they didn't even bother changing the font."*
- **Numbers without a baseline.** "44%" with no denominator, no comparison and
  no measurement window is not evidence; it is decoration that looks like
  evidence.
- **Captions that name the axes** instead of stating the finding.
- **Uniform section lengths** — the signature of a template being filled rather
  than an argument being made. Sections should be as long as they need to be.
- **Front-matter scaffolding on a short document.** An executive summary, an
  introduction and a conclusion on two pages of content is padding.
- **Bullet fragments where reasoning belongs.** A list of noun phrases is not
  an argument, and readers notice the thinking is missing.
- **Hedged register** — "it is important to note", "in today's fast-paced
  landscape", "robust and scalable". Cut every one.
- **A quote polished until it reads like vendor copy.** Real people do not talk
  in marketing sentences; an over-clean quote destroys a case study's
  credibility faster than no quote.
- **Opening with "About us"** instead of the reader's situation.
- **Chrome outweighing content** — a logo and letterhead larger than the one
  number the reader opened the document to find.
- **Emoji as section markers.** Never in a printed document.

The general form: polish applied evenly, everywhere, with no evidence that
anyone decided what mattered. *"Pretty formatting does not create
substantiation."*

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
   at the width they will print — roughly 6.4–7.0in full column and 3.1–3.4in
   half, depending on the theme's page margins (`folio components` has the
   table). Never scale a figure in CSS; the labels scale with it, and
   `folio check` reports it as `figure-rescaled`. Output SVG, never PNG.
5. **Caption the conclusion, not the axes.** "Deploy frequency doubled after the
   July cutover" beats "Deploys per month".
6. **Use real data, and know where it comes from for this document type.** For
   an internal report, that is the repo — git history, test counts, planning
   docs. For an invoice, a quote or a proposal, it is the **user**, and there
   is nothing to go looking for: ask. Do not mine a repository for a number
   that belongs to a commercial document, and never invent one to fill a slot.
   A document with fabricated figures that *looks* finished is worse than no
   document, because it will be sent.
7. **Never claim a document is finished without a clean `--check` and a look
   at the rendered pages.** "It built" is not "it is good".
8. **If `folio build` warns about the Chromium renderer**, tell the user: their
   PDF has no running headers or page numbers, and `folio doctor` prints the
   fix.

## Imagery

Enough to decide; `folio imagery` carries the rest, and is the copy that stays
current with the installed version.

Real data is *always* a real table or a real chart, never an image of one. For
everything else the default answer is **no** — the bar is whether you can say
in one sentence what the image does that the words do not. "Breaking up the
text" is not an answer.

**Never generate** anything a reader could take as data, anything with text in
it, anything evidentiary (a real place, person, product or screen), or anyone
else's logo.

Decoration is `<div class="plate">`, never `<figure>` — a figure is numbered
and referenced, and lending that grammar to decoration is how an illustration
gets read as evidence. `folio check` enforces it both ways.

**Run `folio imagery` before generating anything.** Prompt shape, the Codex
invocation, print resolution, per-theme placement.

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
  the command that says so. When it reports a gap, `folio fonts --install
  <script>` closes it — Noto, from Google Fonts, into the user's own font
  directory, no package manager and no admin rights. Ask before running it:
  it is a download, and Korean is 34MB.

The faces themselves are chosen for you: `folio build` puts the families that
cover the detected scripts into the stylesheet, a serif companion for the
serif themes and a sans one for the sans themes, so a Korean report is set in
Noto Serif CJK KR and a Korean invoice in Noto Sans CJK KR. **Do not name a
CJK face by hand** — a stack that ends at a bare `serif` leaves the choice to
fontconfig, which for Korean commonly answers with a *Chinese* face: legible,
wrong, and invisible to `folio check`, because fonts are not geometry. If a
document genuinely needs a specific face, name it in `brand.css`, which is
appended last and wins.

Italic is withdrawn in the scripts that do not have one — Hangul, kana, Han,
Arabic, Hebrew, Devanagari, Bengali, Tamil, Thai. A slant there is a
synthesised distortion, not emphasis. Latin inside those documents goes upright
with it, because CSS selects elements and not scripts; **do not** re-add
`font-style: italic` to fix what looks like a missing accent — reach for weight
or a `.eyebrow` instead.

## Not for

**Slide decks and video.** Different medium, different tool.

**Academic submissions to a venue that mandates its own class.** IEEE and ACM
specify exact column geometry and forbid font substitution; the value there is
conformance, and Overleaf and Quarto already win it.

**A résumé or CV.** This one is counter-intuitive, so the reason matters:
applicant tracking systems flatten a document into one stream of text, and
they ignore header and footer content outright — so a designed résumé loses
the candidate's name and phone number. Two columns scramble. Tables scramble.
Every strength folio has is a liability here. Tell the user plainly and point
them at a plain single-column document.

Short is **not** a reason to decline. An invoice, a quote, a letter and a
one-pager are one page each and are squarely folio's work — set
`<body data-furniture="none">` and the running title, section rail, page
counter and footer all go away. (Earlier versions of this skill said "nothing
under two pages", which contradicts the trigger above.)
