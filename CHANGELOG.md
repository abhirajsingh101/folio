# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
