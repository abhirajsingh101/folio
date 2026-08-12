# Cover redesign and a showcase that fills its pages

**Status:** approved, not yet implemented
**Date:** 2026-08-13
**Ships as:** 0.2.0 — folded into the first public release, see *Release impact*

## Problem

The gallery on the GitHub page reads as dated, and three separate causes sit
underneath that one impression.

**The cover treatment is ten years old.** `report.css` paints `.cover::before`
and `::after` as soft circles over a navy radial gradient. That is the single
most dated element in the kit, and because it lives in theme CSS rather than
the example, it is on the cover of every document folio produces.

**Every page stops at ~60% height.** Not a rendering fault:
`.section-wrap { break-before: page }` forces each section onto a fresh page,
and the showcase's six sections hold roughly half a page of content each. The
example is under-filled by construction. folio shipped `thin-page` in 0.2.0 to
catch exactly this, and the flagship document passes only because it is short
enough to stay under the rule's threshold rather than because it is well
composed.

**The showcase demonstrates none of 0.2.0's visual features.** Zero `.plate`,
zero `.bleed`, zero non-chart imagery — four chart SVGs and nothing else. The
release added plates, bleed support and an imagery doctrine, and the artefact
people actually look at uses none of them.

## Goals

- Replace the cover architecture in all four themes with something current.
- Put a generated plate on the covers doctrine allows, generated through the
  path `docs/IMAGERY.md` already prescribes.
- Rewrite the showcase so every page is genuinely full, and `folio check`
  reports zero across all four themes with no exemptions.
- Reshoot the gallery so the README leads with something that survives being
  800px wide.

## Non-goals

- No new theme. Four directions stay four.
- No chart rebuild. The existing figures (`fig-deploys`, `fig-burnup`,
  `fig-latency`, `fig-migration`) are reviewed for palette fit, not redesigned.
- No imagery in `technical` or `minimal`. See *Doctrine*, below.
- No change to `base.css`'s two-layer contract, the check rules, or any
  packaging beyond one sdist exclude.

## Decisions already made

| Decision | Choice | Why |
|---|---|---|
| Scope | Themes **and** example | The dated cover is in theme CSS; content alone cannot fix it. |
| Cover architecture | Split band | Type stays on a solid field, so `low-contrast` can still measure it. |
| Plate language | Two-ink riso strata | Re-palettes per theme by swapping ink names; already prescribed by IMAGERY.md. |
| Coverage | `report` + `editorial` only | Doctrine: `technical` and `minimal` take no imagery. |
| Release | Fold into 0.2.0 | Nothing is published; no user need ever see the old cover. |

### Doctrine

`docs/IMAGERY.md` states the per-theme position and this design does not
relitigate it:

| theme | imagery | cover plate here |
|---|---|---|
| `editorial` | yes — built on scale contrast and white space | generated plate |
| `report` | cover only | generated plate |
| `technical` | no — the theme exists to fit more on the page | thin hairline-ruled band |
| `minimal` | no — built on having nothing to hide behind | thin flat band, no fill |

folio having a stated opinion about when *not* to reach for an image is more
distinctive than four themes all reaching for one. The two imageless covers use
the same split-band architecture, so the family reads as one system.

## Design

### 1. Cover architecture

Remove `.cover::before` and `.cover::after` from `report.css`. `.cover` becomes
a two-zone vertical grid:

```
┌───────────────────────────┐
│  .cover-plate             │  bleeds top / left / right
│                           │  height is THEME-SET, not fixed
├───────────────────────────┤
│  .cover-field             │  solid ground
│    brand                  │
│    kicker                 │
│    h1                     │
│    sub                    │
│    rule                   │
│    meta row               │
└───────────────────────────┘
```

**The zone split is per theme, and this matters more than it looks.** A fixed
55% plate would give `minimal` a cover that is 55% empty band — reproducing the
exact "unfinished" failure this redesign exists to remove. So `base.css` owns
the grid and the bleed geometry; each theme sets its own plate height:

| theme | plate height | treatment |
|---|---|---|
| `report` | ~55% | generated plate |
| `editorial` | ~55% | generated plate |
| `technical` | thin band | hairline-ruled, echoing the theme's existing rule vocabulary |
| `minimal` | thin band | flat ground, no fill — the theme is built on having nothing to hide behind |

An imageless cover is a *narrow* band, never a large empty one.

**Layer split.** The two-layer contract is enforced by tests in both
directions, so:

- `base.css` gets the *structure* only — the grid, the zone proportions, the
  bleed geometry. It may not contain a `linear-gradient` or any hex colour
  after the `:root` contract (`test_base_carries_no_palette`).
- Each `themes/*.css` paints its own zones. `test_theme_carries_no_structure`
  guards the reverse direction.

**Component coverage.** `test_theme_restyles_every_component` checks a
hardcoded selector list. Add `.cover-plate` and `.cover-field` to it. The test
then fails until all four themes style both, which is what stops this landing
in two themes and being forgotten in the other two.

### 2. Plate generation

Generated with the documented path, not by hand:

```bash
codex exec "Use the imagegen skill. Generate a <W>x<H> image: \
matte risograph print in two inks, <ink-1> and <ink-2>, overlapping \
geometric strata like a cross-section, visible paper grain, no gradients, \
no text, no people, no logos. \
Save it to /data/abhi/projects/folio/examples/quarterly-report/art/<name>.png"
```

Inks are named from each theme's own brand tokens, so the plate belongs to the
page rather than sitting on it.

**Dimensions.** The plate is a bleeding band across a 210mm page at roughly 55%
of 297mm — about 210×163mm. At 300dpi that is ~2480×1925px, so the aspect to
ask for is landscape near 4:3 and the pixel count must not fall below what
`image-upscaled` tolerates at final size. Whatever `imagegen` actually returns
is measured against the rendered box, not assumed: if the rule fires, the plate
is regenerated larger rather than the rule relaxed.

**Rules the asset must satisfy** — these are folio's own check rules, and the
showcase failing them would be worse than having no plate:

- Marked up as `.plate`, never `<figure>` — a decorative image carrying a
  figure number wears the grammar of evidence (`image-role`).
- Real `alt` text, or explicit `alt=""` if genuinely decorative
  (`image-alt`).
- Generated at print resolution so `image-upscaled` stays quiet.
- No text, no data-like shapes, nothing evidentiary (IMAGERY.md, *Never
  generate*).

**Selection is not blind.** Generate 3–4 candidates per theme, render them into
real covers, and review the rendered pages before committing one. A plate that
looks good as a PNG and wrong under a title is the expected failure.

### 3. Interior density

Rewrite `examples/quarterly-report/document.html` into a report that fills 9–11
pages: more substance per section, a real appendix table, and one section-opener
plate in the `editorial` build where doctrine allows it.

This is content work, not CSS. The acceptance condition is behavioural:

```
folio build document.html --check      # for each of the four themes
→ exit 0, no findings, thin-page included
```

Passing by being short does not count. Each page should be full enough that
`thin-page` would have something to say if the content were removed.

### 4. Gallery

The README currently opens with a 4-up strip in which each cover renders about
500px wide — too small for any of them to land. Replace with:

1. **One hero cover, full width** — the strongest of the four.
2. **The 4-up strip below it**, captioned as the four directions.
3. `themes-pages.png` reshot from the rewritten interior.

## Testing

| Concern | How it is caught |
|---|---|
| A theme skips the new cover parts | `.cover-plate` / `.cover-field` added to the selector list in `test_theme_restyles_every_component` |
| Paint leaks into `base.css` | `test_base_carries_no_palette` (existing) |
| Structure leaks into a theme | `test_theme_carries_no_structure` (existing) |
| Cover title becomes illegible | `low-contrast` — works **only** because type stays off the plate; this is the architectural reason for the split band |
| Plate wears the grammar of evidence | `image-role` (existing) |
| Plate ships without alt text | `image-alt` (existing) |
| Pages under-filled | `thin-page`, run against all four themes |
| Plate rendered above its resolution | `image-upscaled` (existing) |

New tests to write: none beyond the two selectors added to the existing
coverage list. The rules that matter here already exist — the current example
simply never exercised them.

## Risks

**Riso is itself a trend.** Accepted with eyes open at selection time. The
mitigation is that the geometry underneath is plain, so the plate ages as a
two-colour abstract rather than as a period effect.

**Generated output is non-deterministic.** Candidates are reviewed as rendered
covers, and the chosen PNG is committed — the build never calls an image model.

**The sdist already carries the gallery.** `docs/` ships whole, so the two
gallery PNGs are why the sdist is 747KB against a 74KB wheel. Reshooting keeps
that roughly constant. Not fixed here; noted so it is a decision rather than a
surprise. This spec directory is excluded from the sdist so internal planning
docs do not accumulate in the published tarball.

## Release impact

0.2.0 is built, verified and tagged but **not published** — no PyPI upload, no
GitHub release. That is the whole reason this folds into 0.2.0 rather than
becoming 0.3.0: no user ever sees the old cover, and folio's first public
impression is the redesigned one.

Consequences, all already accepted:

- The `v0.2.0` tag moves once more, onto the commit that carries the redesign.
- The CHANGELOG's 0.2.0 section gains a cover-redesign entry.
- Artifacts are rebuilt and re-verified; the wheel-vs-tag diff is re-run.
- PyPI setup (pending publishers, TestPyPI rehearsal) waits until this lands.
- The drafted GitHub release notes need a paragraph on the cover, and their
  gallery references reshot.
