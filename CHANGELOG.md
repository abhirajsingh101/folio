# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — `section-number`, written from a defect folio shipped last release
The `essay` scaffold went out with two sections numbered `04`: one was inserted
ahead of `Notes` and nothing after it moved. `folio check` reported "No layout
problems found", correctly — every rule it had measures geometry, and the page
was laid out perfectly. It was caught by rendering page 3 and looking at it.

Section indices are `<span class="idx">` in the DOM, so unlike most of what the
look pass finds, this one never needed taste to judge. It is `heading-skip`'s
neighbour: that rule asks whether the structure is real, this one asks whether
the numbering on it is, and both fail by asserting something a reader cannot
find.

- **`section-number`** — two sections with the same index, or a jump in the
  sequence. Reports the exact defect that shipped, on the exact document:
  "two sections are numbered 04".
- **A label with no digits is not a counter.** `APPENDIX A` is a real index in
  this repo, and both reading it as a number and reporting it for not being one
  would make the rule wrong on a document that is right. Found by looking at
  what `.idx` actually holds across the scaffolds and examples rather than
  assuming it holds integers.
- Silent across all nine examples and seven scaffolds in four directions — 64
  renders. The contents page does not trip it, because a TOC entry is `.num`
  rather than `.idx`, which the sweep confirmed rather than the design assumed.

## [0.6.1] — 2026-08-14

### Fixed — 0.6.0 claimed byte-identical output, and CI disproved it
The claim was measured, and measured too narrowly. Two builds of one document
hash the same here, across twenty runs and twelve fixed hash seeds, on
WeasyPrint 68 and 69 alike — so it went into 0.6.0 as fact, with a test to hold
it. The release commit's own CI then failed on **one job of eight**:
`ubuntu · py3.10` produced two PDFs differing by two bytes at `startxref`,
while `ubuntu · py3.13` beside it — same WeasyPrint 69.0, same pydyf, same
fonttools, same code — passed.

It has not been reproduced since, and the cause is not known. Rendering the
same document twice through bare WeasyPrint 69 is byte-identical; through
`folio build` it is byte-identical everywhere it has been run by hand. That is
not enough to assert on a supported configuration, so the assertion is gone.
What is left is a smaller, true statement: folio's output is byte-identical in
every environment it has been measured in bar one, and nobody yet knows what
that one did differently.

The lesson is the one this project keeps relearning in a new place: *"it holds
on this machine" is not a property, it is a sample.* The same mistake produced
`--font-mono` falling through to a proportional face, and font-install tests
that passed only because this machine had Noto Sans Thai. This time it reached
a tag.

## [0.6.0] — 2026-08-14

### Added — `font-fallback`, so the checker can finally see a font
0.5.0 shipped four font defects' worth of fixes and not one of them was found
by `folio check`. Every rule there measures geometry, and a document set in the
wrong typeface has perfectly correct geometry — so all four were found by
rendering a PDF and reading the embedded fonts back out by hand. That is a
tool-shaped hole, and 0.5.0's Planned section said so.

- **`font-fallback`** — text in a script that nothing in its stack can set.
  A stack falls through per glyph; when it runs out the renderer asks
  fontconfig, which never fails and never asks. For Korean on a Linux machine
  it commonly answers with a *Chinese* face.
- **It catches the defect the last release was cut for.** Run against the
  stylesheet as it shipped before 0.5.0, it reports "Korean text, and nothing
  in its stack covers Korean" on page 1; run against the same document as
  folio builds it today, it is silent.
- **Silent on a family folio does not recognise.** The table is Noto-centric
  and Korean typography is not: Pretendard, Nanum Gothic and Apple SD Gothic
  Neo are not in it, and a rule that fired on all three would be noise on
  exactly the documents whose author knew what they were doing. It reports only
  when *every* named family is one folio knows to be Latin-only, or a generic —
  which is the case where the choice provably falls to fontconfig.
- **Judged against the document's scripts, not each run's.** Han and Japanese
  share characters, so a run of kanji with no kana in it reads as Chinese, and
  judging per run would report a Japanese document for naming Japanese faces.
  The document-level profile has already settled that question.
- Silent across all nine examples and six scaffolds in four directions.

Both halves are mutation-tested rather than assumed: neutering `covers` fails
the covering-face test, and neutering `judgeable` fails the unknown-family
test. Written after 0.5.0's guard refused the commit — a new rule with no
`SKILL.md` entry, which is what that guard exists for.

### Added — `folio fonts --install <script>`
A report that names a gap it cannot close is half a feature. `folio fonts`
would tell you Tamil has no face and then leave you to it, which on a machine
with no package manager — most Windows, plenty of locked-down macOS — turns
"install Noto Sans Tamil" from a step into an afternoon. Carried in Planned
since 0.3.0.

`folio fonts --install ko` fetches the sans and the serif covering a script
into the user's own font directory and refreshes the font cache. Both faces,
because half the themes set body copy in a serif and a serif document with a
sans Korean face in it is still two documents.

The doctrine does not move: **no font is bundled, and nothing is fetched at
build time.** This runs only when asked, only for the script asked for, and
only into `~/.local/share/fonts` (or the macOS and Windows equivalents) —
never a system directory, never with admin rights. Everything it fetches is
Noto under the SIL Open Font License, from `google/fonts`, and the command
prints that.

- **A 200 carrying an error page is refused.** A moved URL answers with HTML
  on plenty of hosts, and a `.ttf` full of `<!DOCTYPE html>` installs happily
  and renders as nothing at all. The first four bytes decide.
- **Re-running is free rather than 34MB** — that being what Korean costs.
  Families already installed are skipped.
- **The filenames are a table, not a pattern.** Each family names its own
  variable axes: `NotoSansKR[wght].ttf` beside `NotoSansThai[wdth,wght].ttf`.
  A derived URL would 404 on half the world. A test asserts the table covers
  every script `check_document_fonts` can report as missing.
- `folio fonts <file>` now names this command first when it reports a gap,
  ahead of the platform's package manager.

Verified against the live upstream rather than only against mocks: all twenty
URLs resolve, and a real fetch of both Tamil faces produces files that
fontconfig identifies as `Noto Sans Tamil` and `Noto Serif Tamil` — the exact
names folio's stacks write — and that WeasyPrint then renders Tamil with. The
tests themselves inject the fetch and never touch the network.

### Added — `--install kit`, and output is already reproducible
The Planned item read "byte-identical output across machines. Currently the
look degrades gracefully but is not pinned." The first half of that turned out
to be done already, and measuring it changed what the second half means.

**On one machine, folio's output is byte-identical today.** Two builds of the
same document hash the same, including through the charts path where
matplotlib runs — WeasyPrint 68 writes no `CreationDate` and no document ID.
That is now a test rather than a happy accident: a timestamp in a running
footer, or a renderer that starts stamping one, would take it away silently and
the only symptom would be that nobody can diff two builds any more.

So the remaining variable across machines is not the renderer. It is **which
faces are installed** — and that is what `--install kit` closes:

- Inter, JetBrains Mono and P052, which are the three faces `folio doctor`
  checks for and the first names in every stack the kit writes. A machine
  without P052 sets every report and essay in whatever serif fontconfig
  prefers, and P052 is the first name in `--font-body`.
- Four P052 files, because a body face without its italic and bold is not a
  body face — but **one family**, which is what fontconfig calls them. Listing
  the styles as separate families would have re-fetched three files on every
  run of a machine that already had the set, quietly making "re-running is
  free" false for the one family that ships as a set. Caught by looking at what
  `fc-scan` says the fetched files actually are.
- P052 comes from Artifex rather than Google Fonts, under the AGPL with a font
  exemption that permits embedding in a PDF regardless of the document's own
  licence — precisely what a typesetting kit does with it. Each entry carries
  its licence and the command prints the ones that apply, so the OFL line is no
  longer claimed over a font it does not cover.
- `folio doctor`'s "missing Inter — falling back" now names the command that
  fixes it.

Verified against the live upstream: all six files fetch, and fontconfig
identifies them as `Inter`, `JetBrains Mono` and `P052` — the exact names the
stacks ask for.

### Added — the `essay` scaffold, and the routing table is complete
Seven rows in the skill's routing table, and until now six of them started from
a scaffold. The seventh was sent to `report --theme editorial`, which is a
document with a contents page and sections that each start on a fresh sheet —
the opposite of a long read, which is one argument broken into stages. Carried
in Planned since 0.4.0, where it was called the weakest of the four items; it
was, and it is also the last one that could be finished.

- **A cover, and deliberately no contents.** An essay is read from the front,
  not navigated, and a contents page in front of an argument invites a reader
  to skip to the part they already agree with. Sections carry `cont` so the
  prose runs continuously.
- The placeholders are the advice, as in `letter` and `case-study`: open on
  the claim rather than the background, one idea per section with the heading
  as the idea, state the opposing reading as strongly as its holder would, and
  name what would change your mind — the most persuasive section in any
  argument and the one most often left out.
- Notes and colophon sit **side by side**: end matter is reference rather than
  reading, and stacking two short blocks puts a third of a page of white under
  them.

Clean under `folio check` in `report`, `editorial` and `minimal`. In
`technical` it reports a 21% tail, and that is left standing: technical fits
about 1.19× more per page than report, so no content length clears its 25%
floor without spilling `editorial` onto a fourth page. It is a true statement
about pairing a long-form essay with the densest procedural direction — the
same call the `runbook` scaffold got in 0.4.0.

Two sections were numbered `04` — the new one was added ahead of `Notes`
without renumbering. Nothing measures that; it was caught by rendering page 3
and looking at it, which is the pass that keeps earning its place.

### Planned
- **Two sections numbered `04`, and a rule could have said so.** It shipped in
  a scaffold in this release and was caught by reading page 3. Section numbers
  are `<span class="idx">` in the DOM, so a duplicate or a gap in the sequence
  is as measurable as a heading level — and unlike most of what the look pass
  finds, this one does not need taste to judge. The nearest neighbour to
  `heading-skip`, and the next rule to write.
- **Byte-identical output across machines.** The claim that the renderer half
  was already done did not survive its own release — see the Unreleased entry
  above. Two questions now, in order: what `ubuntu · py3.10` did differently to
  produce a two-byte difference no other job produced, and then the original
  item — a document that records which faces it was actually set with, so
  rebuilding it elsewhere can say "this was set in P052 and you do not have it"
  instead of quietly substituting. Carried from 0.3.0.
- `tests/test_layout.py`, for the class where a component reserves more space
  than its content fills, still holds the single `.cols` case that created it.
  Carried from 0.5.0.
- **The composition frontier is thinner than it looked.** Of the three defects
  0.4.0 recorded, the plate at a page head became `half-bleed`, the band above
  a table turned out to be `page-widow` already, and the third — an image
  credit under a signature block reading as part of the signature — is
  semantic adjacency that no measurement distinguishes from a correct layout.
  It is not a rule. It belongs in `folio components`, as advice.

## [0.5.0] — 2026-08-13

### Fixed — every Korean document folio built was set in a Chinese face
`scripts.py` opens with "folio does not assume Latin", and folio really does
detect the writing system, set `lang` and `dir` from it, apply the right
line-breaking, and report which families cover it. Then it handed WeasyPrint a
stylesheet whose body stack was `"P052", "Palatino", "Bitstream Charter",
Georgia, serif` — not one of which has a Hangul glyph. The knowledge existed
and was never applied.

What that produced, measured on a machine with the Noto CJK families
installed, by building the same Korean document in all four directions and
reading the embedded fonts back out of the PDFs:

| direction | before | after |
|---|---|---|
| `report` | WenQuanYi Zen Hei + Noto Sans CJK KR | Noto **Serif** CJK KR + Noto Sans CJK KR |
| `editorial` | WenQuanYi Zen Hei (+ synthesised oblique) | Noto **Serif** CJK KR |
| `minimal` | WenQuanYi Zen Hei | Noto Sans CJK KR |
| `technical` | WenQuanYi Zen Hei | Noto Sans CJK KR |

WenQuanYi Zen Hei is a **Chinese** face. Hangul renders in it, so nothing
failed and nothing was reported — the document was simply set in the wrong
typeface, next to labels and tables that were correctly in Noto Sans CJK KR.
Two faces, one document, and no rule in `folio check` can see it: every rule
there measures geometry, and a document in the wrong face has correct
geometry.

Two causes, both now fixed:

- **A bare generic ends the stack, so fontconfig chose.** `serif` for Korean
  is whatever the machine feels like. `folio build` now emits the families for
  the scripts it detects, spliced into the stacks as `--script-sans` /
  `--script-serif` just before the generic. The Latin faces stay first and keep
  setting Latin — a stack falls through per glyph — so this only catches what
  Inter and P052 do not have.
- **Only one of the two names a face goes by was ever listed.**
  `Noto Sans KR` is the Google Fonts name; the identical face is packaged as
  `Noto Sans CJK KR` by Linux distributions, and a machine typically has
  exactly one of them. `SCRIPT_INFO` now carries both, for eleven scripts.

Two rules govern the splice, and both were learned the hard way while writing
it — each default is **the generic of its own classification**, and each splice
sits **after the platform generic** and before the final one:

- A first draft gave `--font-mono` the *sans* variable, so that a Korean
  comment in a code block would find a face. For a Latin document that
  variable holds `sans-serif`, which then sat ahead of `monospace`: on any
  machine without JetBrains Mono, code would have been set in a proportional
  face and every column in a `technical` table would have lost its alignment.
  Invisible on the machine it was written on, which has JetBrains Mono and
  never reaches the fallback. There is a `--script-mono` now, defaulting to
  `monospace`, carrying `Noto Sans Mono CJK KR` and its siblings.
- Placing the splice *first* put `sans-serif` ahead of `system-ui`, which on
  macOS is the difference between Helvetica and San Francisco — a change to
  every Latin document, made silently, while adding support for a script it
  does not use.

With both rules, a Latin document resolves to exactly the stack it had before.
A test asserts that per theme, on the resolved chain rather than the line as
written, because a `var()` can introduce a face from another classification
while the declaration still reads correctly.

`SCRIPT_INFO` also gained a **serif** list per script, because half the themes
set body copy in a serif and a serif document with a sans Korean face in it is
still two documents. The injected block sits between the kit and `brand.css`:
a document does not choose its writing system, but a `brand.css` that names a
face has chosen deliberately and must win.

Also fixed, from the same root: `folio doctor`'s **system** font check ran its
own `fc-list` and asked for `Noto Sans KR` by name, so on a Linux machine with
the CJK package installed it warned about a font that was present, for a
script the document might not even use. It checks the three faces the kit's
own typography is drawn in and nothing else; script coverage is
`check_document_fonts`, which answers per document and knows every name a face
goes by.

### Changed — italic is withdrawn in the scripts that do not have one
Italic is a Latin invention. Hangul, kana, Han, Arabic, Hebrew, Devanagari,
Bengali, Tamil and Thai never developed an equivalent, so a slant in them is a
distorted letterform rather than emphasis — and `editorial` was asking for one
on every Korean caption, eyebrow, subtitle and pull-quote attribution it set,
which WeasyPrint duly synthesised.

Two ways out were measured on WeasyPrint 68 and neither works:
`font-synthesis: none` is ignored, and `@font-face { src: local(…) }` — which
would map the italic slot to the upright face and cost nothing at all — is not
resolved, so the rule does nothing. The request is therefore withdrawn:
`folio build` emits `font-style: normal` for those scripts.

**Latin inside those documents goes upright with them.** CSS selects elements,
not scripts, and a Korean caption with an English title in it is one element.
That is the trade, made deliberately: upright Latin in a Korean caption is
unremarkable, and slanted Hangul is not. `brand.css` is appended afterwards and
takes it back for a document that wants it. Cyrillic and Greek are excluded —
both have true italics and use them.

The selector carries a doubled `:lang()`, which is specificity rather than a
typo: language inherits, so every element matches both halves, and the second
buys the level needed to outrank `.doc-head .sub`. A test asserts it on the
laid-out document, so a future theme rule that outranks it fails loudly.

That test is also the reason this entry is trustworthy. The first version of it
searched the PDF bytes for `Oblique` and passed before the fix existed —
WeasyPrint compresses its object streams, so the font names are not in the
bytes and the assertion could never fail. It reads the computed style off the
layout tree now.

### Added — `half-bleed`, the first rule that measures where a block sits
0.4.0's Planned section recorded that everything the look pass caught was
compositional: a component in the wrong place, with every measurement around it
legal. Three defects, and one of them is measurable.

`.bleed` works by cancelling the page margin sideways — negative left and right
margins, and as much again in width. There is no equivalent upwards, because
content is laid out inside the page box and the top margin is not content's to
enter. So a bleed placed first on a page opens *below* that margin: a band that
reaches both side edges of the paper and stops 20–34mm short of the top one,
with the running header floating in the gap. Three edges reach the paper and
one does not, which reads as a misprint.

- **`half-bleed`** — a full-bleed block with nothing printed above it on the
  page. The detail gives the strip: "a full-bleed `<div>` opens 34mm below the
  page's top edge". Two remedies, and the choice is about the document: move it
  into the prose, where a band between paragraphs is the job `.bleed` exists
  for, or drop `bleed` and let it sit inset. Never try to pull it up.
- Verified against the defect as it actually shipped — the exhibition guide's
  halftone plate, put back at the head of its page — and silent across all nine
  examples and six scaffolds in all four directions, which is 60 renders.
- The cover is the exception and is built differently on purpose:
  `.cover::before` and `img.cover-plate` are absolutely positioned at `top: 0`,
  outside the flow, which is how they reach the edge at all. Recorded in
  `folio gotchas` beside the other `.bleed` trap.

Measuring it needed a second rect. `_rect` reads `position_x` — the *margin*
edge — alongside `width`, the content width: near enough for a box with no
margins and wrong by the margin for one that has them. A bleed **is** a
negative margin, so it was the one case that mix could not measure, and the
first version of the rule silently found nothing. `_border_rect` measures the
box as it is painted.

### Fixed — one stranded heading arrived as three warnings
`_border_rect` was written for `half-bleed`; checking whether the older rules
needed it turned up a different defect in `orphan-heading`.

A heading is a block box holding a line box holding a text box, and all three
carry the element's tag. The rule walked boxes, so every stranded heading was
reported three times: a page with two of them produced six findings, and the
summary line counted six defects. Identity is the element now, as it already
was for the rules that walk the document rather than a page.

Deduplicating is what made the measurement matter. Reporting once means
reporting the outermost box, and *that* box's `_rect` top is the margin edge —
so the room beneath a heading would have included the theme's own
`margin-top`, space no reader sees. The line box had been masking it by
matching too, and reporting the right number alongside two wrong ones. Both
halves are held by tests: one that fails on three findings, one that fails on
the margin edge.

The first guess was wrong and is worth recording: the block-box skew looked
like a live under-reporting bug, and it was not one — the line box was already
landing on the correct number. There is no change to what the rule reports on
any shipped document; all nine examples and six scaffolds are silent on it in
all four directions, before and after.

### Added — a stylesheet that does not parse now says so itself
A comment closed one paragraph early, leaving prose sitting bare inside
`:root {}`. CSS recovers from that by discarding to the next semicolon, which
took the font tokens with it — so headings came out at the browser default
size, and the only thing that noticed was a test about *heading hierarchy*,
two layers from the cause and with nothing in its message about CSS.

Every theme's composed stylesheet is now parsed with tinycss2, descending into
each rule's declarations, and any error fails with the file's own line number
and reason: `59: Stop token reached before {} block`. Nothing else in the repo
was checking that the CSS it ships is valid CSS.

### Added — a test that a rule nobody documented cannot ship
`folio check` prints a rule name; what the name means and which of two remedies
applies lives in SKILL.md. There was nothing holding those together, and
shipping `half-bleed` meant finding three doc sites by hand.

The new test derives the rule list from `check.py` itself and fails if SKILL.md
never names one. It failed on the commit that introduced it, which is the point
of writing it: **eight rules were described in prose but never named** —
`overflow-x`, `overflow-y`, `text-overlap`, `orphan-heading`, `tiny-text`,
`image-upscaled`, `image-role`, `image-alt`. An agent reading `! p4 tiny-text`
could not search its way to the explanation. Pass 2 now names each rule beside
the defect it describes.

### Planned
- **`folio check` cannot see a font, and this release is the argument for
  fixing that.** Four defects were found this cycle — a Chinese face setting
  every Korean document, a proportional face setting code on machines without
  JetBrains Mono, a synthesised slant on Hangul, and a stylesheet that stopped
  parsing mid-block — and not one was visible to the checker. Every one was
  found by reading fonts back out of a rendered PDF. The layout tree carries
  the computed `font_family` of every box and folio already knows which
  families cover which script, so the rule is writeable: *text in script X
  whose stack names no family that covers X*. It would have caught the
  headline fix in this release on the day it was introduced.
- **Optional `folio fonts --install <script>`** to fetch a single Noto family
  into a user font directory, for machines with no package manager. Carried
  from 0.3.0, and cheaper now that `check_document_fonts` is the single place
  that knows what a script needs.
- **Byte-identical output across machines.** Currently the look degrades
  gracefully but is not pinned; solving it without bundling everything means
  optional per-script subsets. Carried from 0.3.0. The before/after pixel
  comparison written for this release — all eleven examples rendered and
  hashed against the previous commit — is the harness that work would use.
- **The `essay` row is the last of the skill's seven without a scaffold**, and
  it routes to `report --theme editorial`. The fit is close, which is why it
  keeps coming last. Carried from 0.4.0.
- `tests/test_layout.py`, for the class where a component reserves more space
  than its content fills, still holds the single `.cols` case that created it.

## [0.4.0] — 2026-08-13

### Fixed — the theme gallery showed one palette four times
The two theme strips were shot by injecting a different stylesheet into an
already-rendered document. That restyles the type and leaves the figures alone,
so all four panels carried the palette of whichever direction the example was
last built in: four typographic systems under four identical blue charts,
directly beneath a caption promising that charts re-palette to match. They do —
`report` navy, `editorial` oxblood, `minimal` near-black, `technical` teal. The
shot did not.

Worse on the covers: `editorial` wore `report`'s plate, and `technical` and
`minimal` — which doctrine gives no cover image at all — showed a sliver of it
inside a 6mm bar and a 3mm rule.

`docs/gallery/shoot.py` now builds the example four times rather than restyling
it once, because `folio build` is what runs `charts.py` with FOLIO_THEME set,
and it makes the plate a property of the direction. It also stopped assuming
page numbers are unpadded: the same document is 9 pages in `report` and 12 in
`editorial`, so page 3 is `p-3.png` in one and `p-03.png` in the other, and the
strip had been silently shooting whatever it found.

### Fixed — `.cols` reserved space it never filled
A flex item's automatic minimum size is content-based, and with a raster inside
one WeasyPrint resolves it from the image's **intrinsic pixels** rather than
the width it is drawn at. A `.cols` column holding a `.plate` over a wrapped
paragraph reserved 170mm — the full measure — for 100mm of content, and pushed
the next block down past a third of a page of white.

It needs both a large raster and text that wraps, which is why it survived
every example in this repo until one put cloth swatches beside real prose.
Nothing overflowed, nothing overlapped, nothing was illegible: no rule in
`folio check` could see it, and it was found by looking at the page.

`base.css` now sets `min-height: 0` beside the `min-width: 0` that was already
there for the mirror-image reason — the same hygiene on the other axis. Held by
`tests/test_layout.py`, a new file for the class of defect where a component
occupies more space than its content, and documented in `folio gotchas`.

### Changed — examples pruned for variety, three fields added
Eight examples had become five documents from one world plus three, and the
landing page showed three navy covers in a row. The set is chosen for contrast
now, not for coverage:

- **Removed `examples/proposal` and `examples/invoice`.** Both were a third
  software-consultancy document with a look already on the page — a navy cover
  beside two other navy covers, and a white table sheet beside another. The
  `proposal` and `invoice` *scaffolds* are unchanged; it is the showcase that
  needed pruning, not the vocabulary.
- **`examples/architecture`** — a practice's finishes and materials schedule.
  `technical`, dense and tabular, with two generated material studies (board
  -marked concrete, unlacquered brass) and a callout stating that approval is
  against the physical sample panel and never against a print.
- **`examples/programme`** — a concert programme. `minimal`, one sheet, a
  single-ink lithograph plate, a running order with durations, and a back page
  of players and practicalities.
- **`examples/lookbook`** — a fashion label's collection notes. `editorial`,
  two cloth studies, an argument for the constraint, then the line sheet.

Nine examples across nine fields, and the gallery now shows eight of them in
one image — the quarterly report is the hero above it.

### Added — three examples from outside software, and the imagery to carry them
Every example in the repo was a software engineering document: a platform
report, a migration proposal, the invoice for it, its runbook, its case study.
One world, five documents, and a landing page that quietly said folio is for
consultancies. It is a print design system; the narrowness was in the examples,
not the tool.

- **`examples/exhibition`** — an art gallery's exhibition guide. `editorial`,
  a risograph cover plate, a halftone band inside the curator's essay, works
  listed by room. This is the document type where a plate genuinely earns its
  place, and where it is most likely to be mistaken for a work in the show, so
  both plates are credited as generated in the colophon.
- **`examples/survey`** — a river catchment water quality survey. `report`, a
  cyanotype photogram cover, two charts, a site table with status pills. The
  register is the point: a survey states its method and its limits *before* its
  findings, and says plainly what a monthly grab sample cannot tell you.
- **`examples/menu`** — a bakery's seasonal card. `minimal`, one sheet, no
  furniture, a letterpress texture strip as a masthead. The shortest and least
  prose-shaped document in the set.

All four plates were generated through the path `folio imagery` prescribes —
`codex exec` with the `imagegen` skill, prompted for a **medium and a process**
rather than a concept, in each document's own palette, flat and matte, no text
and no people. Together they add 1.0 MB: generated as PNG at 11 MB, shipped as
JPEG, which is the same trade the first two plates made.

The gallery now shows all eight documents in one image — four that take a
cover, four built without one.

Three defects came out of the look pass, none of which `folio check` can see:
a full-bleed plate at the head of a sheet cannot reach into the page's top
margin, so it lands with a white strip above it and reads as a mistake (inset
instead); a band above a table pushed the last room's works onto a page of its
own (the plate moved into the essay, where breaking up prose is the job it was
made for); and an image credit under a signature block reads as part of the
signature (it goes above).

### Added — `letter` and `case-study` scaffolds
Six of the skill's seven routing rows now start from a scaffold of their own.
The two that did not were being routed to the nearest thing with instructions
to delete half of it — "start from the invoice and strip the table" is not a
starting point, it is a chore with a chance of leaving a table in.

- **`letter`** — `minimal`, one sheet, no furniture. Letterhead, subject as the
  title, to/from, references, and a sign-off. The placeholders are the advice:
  say why you are writing in the first sentence, and close on a specific next
  step, because a formal letter is skim-read for exactly those two things.
- **`case-study`** — `editorial`, no cover, because a case study opens on the
  result and a title page in front of two pages is front matter nobody asked
  for. Headline, metric tiles with a baseline each, the situation, what was
  done, **what went wrong**, and the client's own words at the end.

Both are clean under `folio check` in all four directions, not only the one
they ship with. The last combination to clear was the case study in
`technical`, whose density left a 21% tail; it gained the handover list it was
missing — which is the case-study section readers actually look for, so the
rule found a content gap rather than a layout one.

### Added — `page-widow`, and the end of a known blind spot
0.2.0 shipped `thin-page` with a caveat recorded against it: a page is excused
when the page after it begins with an authored break, which is right for a
section ending at 85% and wrong for one whose last line widowed at 11%. The
last page was excused outright on the same reasoning. Both exemptions were
blanket, so the rule that exists to catch under-fill was blind to its most
common form — and that is not theoretical: it let a one-sheet invoice ship as
two pages with a clean report, and it stayed quiet on a case study whose last
page held four lines.

A page that is *meant* to end early is now measured against a second, lower
threshold instead of being skipped:

- **`page-widow`** — the last page, or the page before an authored break,
  holding a quarter or less. The detail says which: "the document ends 12%
  into its last page", or "a section ends 11% into its page".
- `thin-page` is unchanged for pages mid-section, where the cause is a block
  that jumped rather than a tail that spilled. Two causes, two remedies, two
  rules.
- **A one-page document is never a widow.** Nothing spilled — there is no
  earlier page for the content to sit on — and reporting it would make the
  rule unusable for exactly the short documents `data-furniture="none"` exists
  for.
- The threshold is 25%, measured rather than guessed. Across the five examples
  in all four directions, 52 pages end early and their fills fall either side
  of a gap between 21% and 34%: below it a page reads as a spill, above it as
  an ending.

The rule immediately failed three documents in this repo, which is the point of
writing it. The case study's last page held 15% — its pull quote now closes the
document instead of sitting mid-section, which is both a better ending and two
pages instead of three. The `report` scaffold stranded its code block on a page
of its own in every direction: the checklist and pull quote have moved into
section 01, the demo figures were oversized and are now shorter, and it is four
pages instead of five. The `runbook` scaffold is clean in `technical`, which is
what it ships as; paired with `editorial` or `minimal` it reports a short tail,
and that is a true statement about that document rather than something to
suppress.

### Added — four more example documents, and a gallery that shows them
The README sold one document: a quarterly report, four times over. Nothing on
the landing page showed that folio makes anything else, which is the first
question a reader has and the one the scaffolds had just answered in the CLI
and nowhere visible.

- **`examples/proposal`, `examples/invoice`, `examples/runbook`,
  `examples/case-study`** — real documents, not filled-in scaffolds, and one
  story rather than four disconnected samples: a consultancy proposes the
  extraction the existing quarterly report names as its Q4 keystone, invoices
  for the first month of it, hands over the cutover runbook, and writes the
  engagement up afterwards. Each is a different direction — `report`,
  `minimal`, `technical`, `editorial` — so the set doubles as a tour of them.
- **`docs/gallery/documents.png`** — the four side by side. What reads at that
  size is the shape: a cover, a one-sheet, a dense procedure, a headline.
- **`docs/gallery/interiors.png`** — two interior pages at a size where the
  body type is legible, because "it looks designed" is a claim a thumbnail
  cannot make.
- **`docs/gallery/shoot.py`** composes both from the rendered pages. The
  geometry was previously reproduced by hand, and images that sit in one
  README at two different margins read as two different products.
- Conformance now sweeps **every example in every theme**, the same bar the
  scaffolds are held to.

Three defects the checker could not see, caught by reading the pages: a metric
label wrapped and pushed its context line out of alignment with the row; a rail
sat beside a single short paragraph and left a third of a page empty; and a
four-item fact grid wrapped one item onto a row of its own.

### Planned
- **The defects that keep escaping are compositional, not dimensional.** Every
  rule in `folio check` asks whether a measurement is out of range. Nothing it
  found this release came from the look pass: a full-bleed plate at the head of
  a sheet cannot reach the page's top edge and lands under a white strip; a
  band above a table pushed the last section's rows onto a page of their own;
  an image credit under a signature block reads as part of the signature. Each
  is a component in the wrong *place*, and every measurement around it is
  legal. The first of the three is the one a rule could plausibly catch —
  a full-bleed element whose top edge stops short of the page edge is a
  measurable contradiction — and it is where the next rule should start.
- **`.cols` was the second defect this release that no rule could see**, and
  unlike the three above it was structural rather than authorial. It got
  `tests/test_layout.py`, a file for the class where a component reserves more
  space than its content fills. That file currently holds one case.
- **The `essay` row is the last of the skill's seven without a scaffold**, and
  it routes to `report --theme editorial`. Unlike the two rows that got
  scaffolds this release, the fit is close — a long read does take a cover,
  contents and prose — so this is the weakest of the four items here.
- Optional `folio fonts --install <script>` to fetch a single Noto family into
  a user font directory, for machines with no package manager. Carried from
  0.3.0.
- Byte-identical output across machines. Currently the look degrades
  gracefully but is not pinned; solving it without bundling everything means
  optional per-script subsets. Carried from 0.3.0.

## [0.3.0] — 2026-08-13

### Added — a scaffold per document type
`folio init` had one document baked into it, a progress report, which is one of
the seven shapes the skill routes to. Everything else — an invoice, a proposal,
an SOP — was improvised from the component list on the spot, which is the drift
the kit exists to stop, happening at the moment nobody checks: the first minute
of a document, before there is anything to measure.

- **`folio init --template <type>`**, with **`folio templates`** to list what
  exists. Four ship: `report` (unchanged, still the default), `proposal`,
  `invoice` and `runbook`.
- Each scaffold declares the direction that suits it — an invoice in `minimal`,
  a runbook in `technical` — so the routing table's pairing arrives with the
  file instead of being remembered. `--theme` rewrites that declaration rather
  than adding a second one, which would leave the winner to the parser.
- Scaffolds are **discovered from the directory**, and their files are named
  for where they land, so `init` copies rather than maps: a scaffold with
  nothing to plot simply ships no `charts.py`. A manifest beside them carries
  the one-line description, and a test asserts the two never diverge. That is
  the gap `folio themes` still has — its blurbs live in a dict in the CLI with
  an empty-string fallback, so a fifth theme would list as a bare name.
- The conformance suite is parametrised over every scaffold in every theme.
  A scaffold is the first folio markup anyone reads and it gets copied, so a
  hand-rolled style or a skipped heading level in one does not stay in one.
- The skill's routing table now names the command for each row, held to the
  installed set in both directions: a row cannot send an agent to a scaffold
  that does not exist, and a scaffold nobody is routed to fails the suite.

**What looking caught that measuring did not.** The invoice scaffold ran onto a
second page carrying the remit-to block at 12% fill — a single-sheet document
that is not a single sheet, which is the one defect an invoice cannot ship
with. `folio check` was silent, because the rule that would report it excuses
the last page: the tail-widow blind spot recorded in 0.2.0, found again by
reading the pages. Bank details are now lines rather than a `.facts` grid, and
the currency is stated once in the column head instead of taking a fourth fact
that wrapped to a row of its own.

### Added — five components every non-report document needed
Each is structure in `base.css` and look in all four themes, so the layer
contract holds.

- **`.doc-head`** — a title block for a document with no cover. `<h1>` outside
  `.cover` was never styled and fell to the UA default: 19.2pt in `minimal`
  against a 22pt `h2.section`, so the document title rendered *smaller* than
  the sections under it. Every cover-less document shipped an inverted
  hierarchy. Now 1.26–1.38× its sections in all four.
- **`.facts`** — a labelled key/value grid. Bill-to on an invoice, the
  at-a-glance panel on a case study, document control on an SOP. Seven of
  eight researched document types need it and folio had nowhere to put it.
- **`.cols` / `.cols.rail`** — two-up, and a main measure with a rail. The
  asymmetric form is what real briefs and reports use; `.two-col` is a
  different thing (one block flowed into two equal columns) and was the only
  option.
- **`.signature`** — an acceptance block that cannot split across a page.
  Proposals, SOWs, quotes, SOPs and handbooks all need one.
- **Totals** — `tfoot` ruled *every* row, so Subtotal / VAT / Total drew three
  stacked hairlines with the amount due carrying no more weight than the
  subtotal. Only the last row is ruled now, and it steps up in size and colour.

Found while adding them, by the reference document rather than by review: the
new bare `h1` rule out-specified the white that `report`'s cover title
inherits, painting ink on navy at **1.1:1**. `low-contrast` caught it before it
left the working tree — the argument for keeping that document in the suite.

### Added — the skill routes, plans, and gates
`folio check` measures containers. The other half of what makes a document read
as machine-made is behaviour, which no stylesheet touches: a model that
narrates having produced a document it never wrote, or drops half the content
and reports success.

- **A routing table** — shape, theme and furniture per document type, plus the
  ambiguities worth resolving before building ("a report" from a consultant is
  a client deliverable; "just a quick" anything means one page, no cover).
- **A plan step** — type, reader, register, evidence, in four lines before any
  HTML. Register is the one that gets skipped and the one that shows.
- **An Iron Law** — a green `--check` and a look at the pages, both established
  in the message that claims the document is finished, with the file confirmed
  on disk. Plus the rationalisation table, because "it rendered, so it's done"
  is the thought that ships a broken PDF.
- **A named slop list** — what AI-generated documents look like, item by item,
  each drawn from a real reader complaint.
- **`tests/test_skill.py`** holds the prose to the argparse surface: every
  command and flag the skill names must resolve. It immediately caught the
  commit that added it promising a `--furniture none` flag that did not exist.
  A stale reference does not error — the agent improvises around it.

### Fixed — four defects that blocked every document type but a report
- **`heading-skip` fired on the labels the docs told you to write.**
  COMPONENTS.md said to use `<h4>` for uppercase labels; the checker counted it
  as a fourth level, so `<h2>Invoice</h2><h4>Bill to</h4>` warned in all four
  themes — and because conformance treats the rule as a hard failure, no short
  labelled document could enter the repo at all. Fixed on the side the audit
  did not expect: a heading level is structure that screen readers and the
  shareable HTML page both consume, so the checker was right and the
  documentation was wrong. `.eyebrow` is the label now, carrying each theme's
  existing h4 treatment, so nothing changes visually.
- **`.callout.info` was unstyled in `editorial` and `minimal`.** The shipped
  example uses it, so in half the themes that block rendered as a plain
  callout — including in the gallery. The theme test checked `.callout` and
  stopped, so a theme could style the box and skip a tone; every documented
  tone is now checked in every theme, tied back to COMPONENTS.md.
- **`assets/folio.css` was 575 orphan lines** that nothing read, while
  CONTRIBUTING told contributors to add new components to it. Deleted, and the
  guide now names the real two-layer split.
- **The RTL cover band was gone.** `rtl.css` still mirrored the ghost circles
  the split-band redesign deleted, and the surviving offsets re-anchored the
  band to `left: -60mm`, collapsing it: every Arabic, Hebrew, Persian and Urdu
  cover rendered flat, with every test passing because nothing in the suite
  rendered RTL. Fixed at the cause — `.cover-brand` is pinned to both margins,
  so it is symmetric and `text-align: start` turns it round by itself — and
  `rtl.css` now carries no cover rules at all.

### Fixed — `folio components` described a cover that was retired
The Cover entry still promised the gradient and two layered circles the split
band replaced. It is the reference an agent reads before authoring, so stale
copy there is read as current. Now the band, its per-theme heights,
`img.cover-plate`, and why type never sits on it.

### Planned
- **`thin-page` still cannot see a tail widow**, and it has now cost two real
  defects — the 0.2.0 example's section tails and this release's invoice
  running onto a second page at 12% fill. A page is excused when the page
  *after* it begins with an authored break, which is right for a section
  ending at 85% and wrong for one that widowed at 11%. The last page is
  excused outright, which is where a single-sheet document fails. This is the
  next rule to fix.
- Scaffolds for the three routing rows that have none of their own — letter
  and one-pager, case study, essay. They currently route to the nearest
  scaffold with blocks to delete.
- Optional `folio fonts --install <script>` to fetch a single Noto family into
  a user font directory, for machines with no package manager.
- Byte-identical output across machines. Currently the look degrades
  gracefully but is not pinned; solving it without bundling everything means
  optional per-script subsets.

## [0.2.0] — 2026-08-12

### Added
- **Four design directions** — `report`, `editorial`, `technical`, `minimal`.
  Not colour variants: each is a distinct typographic system with its own page
  architecture. Declared per document via `<body data-theme="…">` or
  `folio init --theme`. `folio themes` lists them.
- Chart palettes per theme. `theme.use()` reads the document's declaration
  from the environment, so a figure is never the wrong colour for its page.
- The stylesheet is now two layers: `base.css` (structure, never varies) and
  `themes/*.css` (look). Tests enforce the split in both directions — base may
  not paint, themes may not restate structure.

### Added — quality gate
- **`folio check` / `folio build --check`** measures the rendered layout tree
  and reports real defects: horizontal and vertical overflow, overlapping
  text, near-empty pages, stranded headings, illegibly small type, upscaled
  rasters. Errors exit non-zero.
- Every rule encodes a defect that actually shipped during development, so
  the suite is regression tests for the design system as much as a linter.
- **Contrast (`low-contrast`)** against WCAG AA — 4.5:1 for body text, 3:1
  once type is large (18pt, or 14pt bold). The backdrop is resolved rather
  than assumed: ancestor fills are composited, translucent colours are applied
  before measuring, and a page background counts, so reversed cover type is
  silent while grey-on-grey is not. Where the backdrop is genuinely unknowable
  — anything over a gradient or image — the rule stays quiet instead of
  guessing. Running headers and footers are measured as well, since margin
  boxes sit outside the content frame and never get a second look.

### Fixed — `thin-page` reported chapter breaks as defects
A page can be short for two reasons that look identical by fill: the author
demanded the next page, or a block on this one would not fit. Only the second
is a defect, and the rule reported both — with a hint about a block that
jumped, on pages where nothing had. folio's own `.section-wrap` breaks with
`break-before: page`, so every short section in every document produced a
warning whose suggested remedy did not apply to it.

The rule now reads the property that caused the break. Finding
`break-before: page` overhead is not sufficient: a section wrapper stays an
ancestor of every page its section runs onto, so the break it caused may be
two pages back. WeasyPrint exposes no marker for a continuation fragment, so a
page counts as authored only when the element carrying the break appears on no
earlier page.

The reference document now reports **nothing at all** in any of the four
themes, down from seven warnings — and a tall figure that genuinely jumps
mid-section still reports, which is the case the rule exists for.

### Added — figures
- **`figure-rescaled`** — a vector drawn at a materially different size than
  it was authored. This was the last blind spot: a chart is an image, so every
  other rule stopped at its edge, while inside sat tick labels and a legend
  authored to match the document's type. Stretch a half-column figure across a
  full column and its 8pt labels arrive at 16pt; do the reverse and they
  arrive at 4pt, under the legibility floor, with nothing downstream able to
  say so. Vectors do not go soft, so this is not the raster rule renamed —
  nothing is lost in resolution; what changes is the type.
- Tolerance is ±10%. Column width shifts with each theme's page margins, so
  exact is not achievable and a few percent is invisible. `folio components`
  now carries the per-theme column widths, which nobody could derive.

### Fixed — two checks that never ran
- **`image-upscaled` had been dead.** It read `image.intrinsic_width`, which
  WeasyPrint 68 does not have — the size comes from `get_intrinsic_size` — so
  the attribute returned None for every image and the rule silently skipped
  all of them. It was also the only rule with no test, which is why nothing
  noticed. Now measured through the supported API, with tests.
- **It also only looked at `InlineReplacedBox`**, while folio's own stylesheet
  sets `figure img { display: block }`. So even once the size was readable,
  the rule could not see a single image the kit actually produces. Both block
  and inline replaced boxes are now covered, and rasters and vectors are split
  between the two rules that suit them.

### Added — chart colours enforced at the source
`theme.use` emits chart text as outlines (`svg.fonttype='path'`) so a figure
renders identically wherever the PDF is built. That is the right trade for a
kit whose fragile dependency is fonts — and it means no document-time rule can
ever see inside a chart. Chart label colours are therefore enforced where they
are chosen: tests assert every palette's `ink` and `mute` clear AA on paper,
and that the status fills support the white numerals drawn on them. Every
pre-`0.1.0` mute value fails them.

### Added — imagery guidance
- **`folio imagery`** — when a document may carry a non-chart image and how to
  make one that does not look generated. The default answer is no: a generic
  illustration does not read as neutral, it reads as nobody having thought
  about the page.
- Hard rules, not judgement calls: nothing a reader could take as data;
  nothing with text in it, since models malform words and a diagram with
  garbled labels is worse than no diagram; nothing evidentiary; no borrowed
  logos. Real numbers stay in real tables and real charts.
- Prompt guidance aimed at the actual failure — a stock AI image illustrates a
  *concept*, so prompt for a medium and a process instead, name the palette
  from the document's own brand, and ask for flat rather than the default
  glossy render. Plus the Codex `imagegen` invocation, print resolution, and
  why clearing `image-upscaled` is a floor rather than a quality bar.
- Reference docs are now registered in one place (`assets.SERVED_DOCS`), and a
  test asserts each one is force-included in the wheel. `doc_text` falls back
  to the repo, so a doc missing from the build would have worked locally and
  in CI while raising `FileNotFoundError` for everyone installing from PyPI.

### Added — plates
- **`.plate`** — decorative imagery: cover art, a section opener, a texture.
  Deliberately *not* a `<figure>`: no number, never referenced from the text.
  Styled in all four themes, with an optional `.credit` line.
- **`image-role`** enforces the boundary in both directions — a plate carrying
  a figure number is flagged, and so is a `<figure>` without one. The failure
  this prevents is subtle: a fabricated chart is obvious, but a decorative
  illustration captioned `Fig. 3` wears the same grammar as a measurement, so
  the reader files it as sourced without ever deciding to.
- **`image-alt`** — an `<img>` with no `alt`. `alt=""` passes: it declares the
  image purely decorative, which is a decision rather than an omission.

### Fixed — a silent renderer failure found while testing plates
A gradient inside an SVG does not paint when the container is `.bleed`. The
box is laid out at full size and stays empty — no error, and strokes in the
same file still render, so it reads as a half-loaded image. It is the
combination that breaks: gradient SVG in `.plate` or `figure` is fine, PNG or
flat-fill SVG in `.bleed` is fine. This is pre-existing and applies to
`figure class="bleed"` too, which matters because charts are SVG. Documented
in `folio gotchas` with the measured table; charts from `folio.theme` use flat
fills and are unaffected.

### Added — the look pass
- **`folio build --check` now renders the pages** to `<name>.pages/`, one PNG
  per page, and prints the directory. Looking is the only pass that catches a
  chart of the wrong type or a caption that states the obvious, and it was the
  pass that got skipped — because it needed a separate command nobody was
  obliged to run. The images are simply there now.
- **`folio preview <pdf>`** re-renders them on demand, `--dpi` to taste. The
  command was referenced in the source months before it existed.
- Previews are a convenience, never a build requirement: without poppler the
  build still succeeds and the step is silently skipped. Stale pages from a
  longer draft are cleared first, since a leftover `p-9` reads as part of the
  current document.

### Added — conformance
Geometry and contrast ask whether a document renders correctly. These ask
whether it was built the way the kit intends — the failure nothing else
catches, because a hand-rolled style renders perfectly and passes every other
check. This is how a design system erodes: one reasonable-looking exception at
a time, none of which anyone can see going wrong.

- **`inline-style`** — a `style="…"` attribute. Rule 2 of the kit was
  honour-system until now.
- **`heading-skip`** — an `h2` jumping straight to `h4`, which asserts a level
  of structure that does not exist. Climbing back up is silent; only
  descending can skip.
- **`type-drift`** — two type sizes less than 1% apart. A designed scale steps
  by ratios a reader can see; 8.096pt beside 8.1pt is an `em` compounding
  inside another `em`. The threshold sits below the finest deliberate step in
  the shipped themes, measured rather than guessed — widen it and real scale
  steps start reporting as drift.

### Fixed — the kit's own conformance
Every one of the three rules failed the design system that shipped it.

- Inline `code` was sized in `em` in all four themes, so it compounded off
  each container and produced three near-identical sizes for one element
  (8.096pt in a paragraph, 8.624pt in a list item). It is now a fixed size per
  theme: one typographic register instead of three accidental ones.
- `report` set `.cover .sub` at 12.5pt and `.pullquote` at 12.4pt — two names
  for the same step, now collapsed.
- The reference document carried two hand-rolled `font-size` styles, because
  the metric tile had no component for a unit suffix. Added as `.metric .v .u`
  in all four themes and documented, rather than patched at the call site.
- The reference document's appendix skipped `h3`.

### Fixed — a gotcha that was wrong
`docs/GOTCHAS.md` claimed `var()` does not resolve inside `@page` margin
boxes, "verified against WeasyPrint 68". It does — but only when the custom
property is declared on `:root` or `html`; declare it on `body` and the value
silently falls back to black. The original diagnosis mistook the symptom for
the cause, and cost three hardcoded greys in `base.css`, page furniture that
no theme could restyle, and a 1.9:1 footnote. The entry now carries the
measured table, and `test_base_carries_no_palette` covers the `@page` block
instead of exempting it.

### Changed — palette
The contrast rule immediately failed the design system that shipped it, so the
palette moved rather than the threshold. Muted text is now a little darker in
every direction; the hierarchy is unchanged, and it is legible on paper.

- `--ink-mute` darkened in all four themes (base `#7c8899` → `#626d7e`,
  editorial `#82878f` → `#686c74`, technical `#7d868d` → `#687077`, minimal
  `#949494` → `#6f6f6f`). Each now clears 4.5:1 on the *darkest* surface it is
  used on, not merely on white.
- `--ok` `#2F855A` → `#2B7A53` and `--warn` `#B7791F` → `#97641A`, which fixes
  them both as text on their own tint and reversed out of a solid pill.
  minimal's `--accent` `#E8501E` → `#C64014`.
- Page furniture now uses `var(--ink-mute)` instead of three hardcoded greys.
  This fixes a real bug — themes could never restyle the running head — and
  retires a footnote grey of `#b3bcc8`, which measured **1.9:1** and had
  shipped in every folio document to date.
- Chart tick labels followed the same move (`theme.MUTED` was `#94a3b8`, or
  2.9:1). The checker cannot see inside an SVG, so those must be right at
  source.

### Added — internationalisation
- **Script detection.** A document is inspected for the writing systems in it,
  which sets `lang` and `dir`. Korean, Japanese, Chinese, Arabic, Hebrew, Thai,
  Devanagari, Bengali, Tamil, Cyrillic, Greek and Latin.
- **Per-script line breaking.** Korean `word-break: keep-all`; kinsoku and no
  hyphenation for Japanese and Chinese; shaper-driven breaking for Thai, Lao,
  Khmer, Burmese; whole clusters for Indic; no hyphenation for RTL scripts.
  Applying Latin hyphenation to these was previously silent breakage.
- **Right-to-left layout** for Arabic, Hebrew, Persian and Urdu, as a mirror
  layer injected only when needed. Every accent rule, list marker, timeline
  spine and tile border flips.
- **`folio fonts <file>`** reports whether this machine can set the scripts a
  document uses, with the install command for the platform. No fonts are
  bundled: shipping every writing system would cost every user tens of
  megabytes so that a few can set Japanese.

### Changed — the cover, in all four directions
`report` opened on a navy radial gradient with two soft circles floating in it.
It was the most dated thing in the kit and it was on the cover of every
document folio produced.

All four covers now share one architecture: a bleeding band across the head of
the page, sized per theme by `--cover-plate-h`, with the type below it on solid
ground. The band is `.cover::before` rather than an element, so it lands
without a markup migration — `technical`'s 6mm brand bar and `minimal`'s new
3mm accent rule are the same component sized down, one system with four
positions on it instead of a pseudo-element in one theme and nothing in two
others. `img.cover-plate` optionally covers the band, and the painted band
shows through if the image fails to load.

**Type never sits on the plate.** `low-contrast` declines to measure anything
over an image, so a cover that reversed its title out of a generated plate
would ship illegible with a green build. Keeping the type on a solid field is
what preserves the one check that would catch it.

### Fixed — the report cover's meta labels were 4.4:1
Under AA, and shipped that way in every document. The gradient made the
backdrop unmeasurable, so the contrast rule never got to speak; on solid ground
it fires immediately. The label alpha moves 0.5 → 0.58, now 5.4:1 — headroom
rather than sitting on the 4.5 line.

### Added — generated cover plates on `report` and `editorial`
Two-ink risograph strata, generated through the path `docs/IMAGERY.md` already
prescribed and folio's own showcase had never used. The two plates share a
composition and differ only in ink, so the themes read as siblings.

`technical` and `minimal` take no image, which is what the doctrine has always
said: one exists to fit more on the page, the other is built on having nothing
to hide behind. Having a stated position on when *not* to reach for an image is
more distinctive than four themes all reaching for one.

### Changed — the showcase fills its pages
`.section-wrap { break-before: page }` gives every section a fresh page, and
the example held about half a page per section. `report` had an 18%-full page
and `technical` a 7%-full one — a heading, a paragraph, then nothing. Worst
body page, before → after: `report` 18% → 52%, `technical` 7% → 38%, `minimal`
4% → 19%, `editorial` 19% → 11%.

`editorial` moved the wrong way. One document rendered at four type scales with
a forced break per section cannot fill every page in all four, and its
remaining thin pages are section tails running a paragraph over.

### Known — `thin-page` cannot see a tail widow
A page is excused when the page *after* it begins with an authored break, on
the reasoning that a short page is short because the next section demanded a
fresh one. That is right for a section ending at 85% and wrong for one whose
last paragraph widowed at 11% — both precede an authored break, and the rule
cannot tell them apart. So a section-tail widow, the most common under-fill in
a sectioned document, is invisible to the rule that exists to catch under-fill.
Found while measuring this release's own example; not fixed here, because
changing it changes what every existing document reports.

### Fixed — the first build on a bare install ended in a traceback
`pip install folio-press` is deliberately core-only, so the charts extra is
absent on a fresh machine. But `folio init` scaffolds a `charts.py` and prints
`Next: folio build document.html`, and that build died inside folio's own
scaffold with a bare `ModuleNotFoundError: No module named 'matplotlib'` —
the tool's first impression, on the path it had just recommended.

`theme.use()` now names the extra that carries it and points at `folio doctor`,
which already reports the whole picture. Only matplotlib's own absence earns
the hint: an ImportError raised *inside* matplotlib is a different fault, and
telling that reader to install the charts extra sends them to reinstall the one
thing they have.

`folio doctor` was pointing the other way for the same two gaps — `pip install
matplotlib`, `pip install weasyprint`. Both work, and both teach that folio's
pieces are installed one loose package at a time, so the next gap sends the
reader to a search engine instead of to `[all]`. Both now name the extra.
WeasyPrint keeps its platform commands underneath: the native libraries are
outside pip's reach, and that half of the remedy is the half users get stuck
on. A test ties every extra folio recommends to one pyproject declares, so a
hint cannot name an extra that does not exist.

### Changed
- Install posture: `pipx install folio-press` is core-only. Charts, WeasyPrint
  and fonts are pulled in per need, guided by `doctor` and `fonts`.

### Planned
- A second document family (invoice / proposal) sharing the same tokens.
- Optional `folio fonts --install <script>` to fetch a single Noto family into
  a user font directory, for machines with no package manager.
- Byte-identical output across machines. Currently the look degrades
  gracefully but is not pinned; solving it without bundling everything means
  optional per-script subsets.

## [0.1.0] — 2026-08-12

First release.

### Added
- `folio init` / `build` / `doctor` / `components` / `gotchas` / `css`.
- A print design system with 15 components: cover, contents with resolved page
  numbers, sections with running headers, metric tiles, figures and figure
  rows, tables with repeating headers, status pills, four callout tones,
  timeline, numbered steps, tick lists, pull quotes, code blocks, appendix.
- Chart theme (`from folio import theme`) matching the document palette and
  emitting SVG with text as outlines, so figures render identically anywhere.
- `folio doctor`: detects missing native libraries and prints the exact fix for
  apt, dnf, pacman, apk, Homebrew and MSYS2.
- Chromium fallback renderer so a machine without Pango still produces a
  document, with an explicit warning about the lost print features.
- Standalone HTML output alongside every PDF, images inlined.
- `keep` utility for short tables that must not split across pages.

### Notes
- WeasyPrint is the default renderer, chosen by measuring the same 11-page
  report built in WeasyPrint, Typst and LaTeX. See `docs/ENGINE-CHOICE.md`.
