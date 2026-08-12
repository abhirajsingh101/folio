# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Install posture: `pipx install folio-press` is core-only. Charts, WeasyPrint
  and fonts are pulled in per need, guided by `doctor` and `fonts`.

### Planned
- `folio build --check` to flag under-filled pages, the most common authoring
  problem and one the tool can detect better than a human can eyeball.
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
