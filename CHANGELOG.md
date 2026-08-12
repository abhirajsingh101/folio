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

### Planned
- `folio build --check` to flag under-filled pages, the most common authoring
  problem and one the tool can detect better than a human can eyeball.
- A second document family (invoice / proposal) sharing the same tokens.
- Bundled subset fonts so output is byte-identical across machines. Currently
  the look degrades gracefully but is not identical everywhere.

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
