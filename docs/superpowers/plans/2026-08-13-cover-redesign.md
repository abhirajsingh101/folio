# Cover Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dated cover architecture in all four themes with a split band, put a generated two-ink riso plate on the two covers doctrine allows, and rewrite the showcase so every page is genuinely full.

**Architecture:** `.cover-plate` is an *optional* absolutely-positioned bleeding band at the top of `.cover`, sized by a per-theme `--cover-plate-h` token. The existing bottom-anchored cover children become the field automatically, so no existing document breaks. Themes paint; base.css only positions.

**Tech Stack:** WeasyPrint 69, hatchling, pytest, matplotlib, `codex exec` + `imagegen`.

## Global Constraints

- `base.css` may not contain `linear-gradient` or any `#rrggbb` after the `:root` contract — enforced by `test_base_carries_no_palette`.
- Themes may not restate structure — enforced by `test_theme_carries_no_structure`.
- Every selector in the hardcoded list in `test_theme_restyles_every_component` must appear in all four theme files.
- Imagery goes on `report` and `editorial` covers only. `technical` and `minimal` get a thin band, never a large empty one. (`docs/IMAGERY.md`)
- Generated images: no text, no data-like shapes, nothing evidentiary, no logos.
- A decorative image is `.plate`, never `<figure>` (`image-role`), and carries `alt` (`image-alt`).
- `MAX_IMAGE_UPSCALE = 1.15`; a 210mm bleed draws at 794 CSS px, so any plate ≥ 794px passes.
- Ships as 0.2.0. The `v0.2.0` tag moves onto the final commit; artifacts are rebuilt and re-diffed against it.

## Deviation from the spec, recorded

The spec described two zones, `.cover-plate` **and** `.cover-field`, both added to the
component-coverage list. Implementing it that way requires every existing folio
document to wrap its cover children in a new element or lose its layout.

Instead `.cover-plate` is optional and absolutely positioned, and the "field" is
`.cover`'s own background with its existing bottom-anchored children. Same visual
result, no markup migration, one new component to style instead of two. `.cover-field`
is therefore **not** created and **not** added to the coverage list.

---

### Task 1: Cover architecture — base.css scaffolding

**Files:**
- Modify: `src/folio/assets/base.css:123-135`
- Test: `tests/test_themes.py`

**Interfaces:**
- Produces: `.cover-plate` selector; `--cover-plate-h` token consumed by all four themes in Task 2.

- [ ] **Step 1: Add the plate structure to base.css**

Replace the `.cover` rule and append the plate block:

```css
.cover {
  page: cover;
  break-after: page;
  height: 297mm;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: var(--cover-plate-h, 0) var(--page-margin-x) 22mm;
  text-align: start;
}

/* Optional bleeding band. Themes set --cover-plate-h and paint it; a theme
   that leaves the token at 0 has no band and the cover is unchanged. */
.cover-plate {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: var(--cover-plate-h, 0);
  overflow: hidden;
}
.cover-plate img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

- [ ] **Step 2: Verify base.css still carries no paint**

Run: `python -m pytest tests/test_themes.py::test_base_carries_no_palette -q`
Expected: PASS (no hex, no gradient added).

- [ ] **Step 3: Verify `object-fit` actually works in WeasyPrint**

This is an assumption, not a known. Build the showcase with a temporary plate and
inspect the rendered page PNG. If `object-fit: cover` is ignored, fall back to
`.cover-plate img { width: 100%; height: auto; }` with `overflow: hidden` doing the
cropping.

Run: `cd examples/quarterly-report && folio build document.html --check`
Expected: cover page renders, plate band not distorted.

- [ ] **Step 4: Commit**

```bash
git add src/folio/assets/base.css
git commit -m "feat(cover): optional bleeding plate band, positioned in base"
```

---

### Task 2: Repaint the four covers

**Files:**
- Modify: `src/folio/assets/themes/report.css`, `editorial.css`, `technical.css`, `minimal.css`
- Modify: `tests/test_themes.py` (coverage list)

**Interfaces:**
- Consumes: `.cover-plate`, `--cover-plate-h` from Task 1.

- [ ] **Step 1: Add `.cover-plate` to the coverage list**

In `test_theme_restyles_every_component`, add `".cover-plate"` to the selector tuple.

- [ ] **Step 2: Run it and watch all four themes fail**

Run: `python -m pytest tests/test_themes.py::test_theme_restyles_every_component -q`
Expected: 4 FAILED — "report never styles .cover-plate", and the same for the other three.

- [ ] **Step 3: report — delete the ghost circles, add the plate**

Remove `.cover::before` and `.cover::after` entirely. Replace the `.cover` background:

```css
.cover { --cover-plate-h: 160mm; background: var(--brand-deep); color: #fff; }
.cover-plate { background: var(--brand-deep); }
```

- [ ] **Step 4: editorial — plate above the rule, brand below it**

```css
.cover {
  --cover-plate-h: 158mm;
  background: var(--paper); color: var(--ink);
  justify-content: flex-end; padding-top: calc(var(--cover-plate-h) + 14mm);
}
.cover-plate { background: var(--paper); }
```

`.cover-brand` loses `margin-bottom: auto` and its top position, sitting under the
plate instead.

- [ ] **Step 5: technical — the existing 6mm brand bar becomes the band**

The theme already has a top bar as `::before`. Convert it to the shared component so
the family is one system:

```css
.cover { --cover-plate-h: 6mm; }
.cover-plate { background: var(--brand); }
```

Delete `.cover::before`. Keep `padding-top` behaviour via the token.

- [ ] **Step 6: minimal — a thin flat band, no fill**

```css
.cover { --cover-plate-h: 3mm; }
.cover-plate { background: var(--accent); }
```

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: 186 passed.

- [ ] **Step 8: Render all four and look at them**

For each theme, build the showcase with `data-theme` set and read every cover PNG.
The checker cannot see taste; the covers must actually look better.

- [ ] **Step 9: Commit**

```bash
git add src/folio/assets/themes tests/test_themes.py
git commit -m "feat(cover): split band in four themes, ghost circles gone"
```

---

### Task 3: Generate and select the plates

**Files:**
- Create: `examples/quarterly-report/art/cover-report.png`, `art/cover-editorial.png`

- [ ] **Step 1: Generate 3 candidates per theme**

```bash
codex exec "Use the imagegen skill. Generate a 1536x1024 image: \
matte risograph print in two inks, <ink-1> and <ink-2>, overlapping geometric \
strata like a geological cross-section, visible paper grain, hard edges, \
no gradients, no text, no people, no logos. \
Save it to /data/abhi/projects/folio/examples/quarterly-report/art/cand-<theme>-<n>.png"
```

Inks come from each theme's own tokens. `report`: `--brand-deep` navy with a pale
blue. `editorial`: its `--brand` with a warm off-white.

- [ ] **Step 2: Look at every candidate**

Read each PNG. Reject anything with text artefacts, anything that reads as a chart,
anything that reads as a photograph of a real place.

- [ ] **Step 3: Render the survivors into real covers and look again**

A plate that works as a PNG and fails under a title is the expected failure mode.
Selection happens on the rendered cover, never on the raw asset.

- [ ] **Step 4: Commit the two winners, delete the rest**

```bash
git add examples/quarterly-report/art/cover-report.png examples/quarterly-report/art/cover-editorial.png
git commit -m "feat(example): two-ink riso cover plates"
```

---

### Task 4: Wire the plate into the showcase and template

**Files:**
- Modify: `examples/quarterly-report/document.html:10`
- Modify: `src/folio/assets/templates/starter.html:10`

- [ ] **Step 1: Add the plate to the showcase cover**

```html
<section class="cover">
  <div class="cover-plate">
    <img src="art/cover-report.png" alt="">
  </div>
  <div class="cover-brand">meridian</div>
  ...
```

`alt=""` is correct and deliberate: the plate is decorative, and `image-alt` accepts
an empty alt as a decision rather than an omission.

- [ ] **Step 2: Leave the scaffold template imageless**

`folio init` must keep working on a machine with no art. The template gets a comment
pointing at `folio imagery`, not an `<img>` with a broken path.

- [ ] **Step 3: Check every rule the plate can trip**

Run: `cd examples/quarterly-report && folio build document.html --check`
Expected: exit 0. Specifically no `image-role` (it is a `.plate`, not a `<figure>`),
no `image-alt`, no `image-upscaled`, no `low-contrast`.

- [ ] **Step 4: Commit**

```bash
git add examples/quarterly-report/document.html src/folio/assets/templates/starter.html
git commit -m "feat(example): cover plate on the showcase"
```

---

### Task 5: Rewrite the showcase to fill its pages

**Files:**
- Modify: `examples/quarterly-report/document.html`
- Modify: `examples/quarterly-report/charts.py` if new figures are needed

- [ ] **Step 1: Measure what is actually short**

Run `folio build document.html --check` and read every page PNG. Record which pages
are under-filled and by how much.

- [ ] **Step 2: Write content until each section fills its page**

Six sections, each currently about half a page. Target 9–11 pages total. Real prose,
a real appendix table, no filler — the document is read as a sample of what folio
produces, so weak writing is a product defect.

- [ ] **Step 3: Verify against all four themes**

Each theme has different page margins and type sizes, so a page that fills in
`report` may not in `technical`.

Run, for each of the four: `folio build document.html --check`
Expected: exit 0, zero findings, `thin-page` included.

- [ ] **Step 4: Commit**

```bash
git add examples/quarterly-report
git commit -m "feat(example): a showcase that fills its pages"
```

---

### Task 6: Reshoot the gallery and lead the README with a hero

**Files:**
- Modify: `docs/gallery/themes-covers.png`, `docs/gallery/themes-pages.png`
- Create: `docs/gallery/hero.png`
- Modify: `README.md:14-16`

- [ ] **Step 1: Render the four covers and four interiors afresh**

- [ ] **Step 2: Compose the hero**

One cover at full width — whichever of the four is strongest once rendered.

- [ ] **Step 3: Restructure the README opening**

Hero first, then the 4-up strip captioned as the four directions, then the pages
strip. Alt text on all three.

- [ ] **Step 4: Commit**

```bash
git add docs/gallery README.md
git commit -m "docs: lead with a hero cover, reshoot the gallery"
```

---

### Task 7: Changelog, rebuild, re-verify, move the tag

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the redesign to the 0.2.0 section**

Explain the cover architecture, why `technical` and `minimal` take no image, and the
under-filled-by-construction finding. Repo voice: state the defect, then the fix.

- [ ] **Step 2: Full verification**

```bash
python -m pytest                      # expect 186 passed, exit 0
python -m ruff check src tests
python -m ruff format --check src tests
rm -rf dist build && python -m build
python -m twine check dist/*
```

- [ ] **Step 3: Bare-install rehearsal against the rebuilt wheel**

Fresh venv, install the wheel, `folio init`, `folio build`. The scaffold must still
work with no art directory.

- [ ] **Step 4: Move the tag and re-diff**

```bash
git tag -d v0.2.0 && git tag -a v0.2.0 <sha> -m "folio-press 0.2.0"
git push origin main && git push origin v0.2.0 --force
```

Then diff every `.py` in the wheel against the tagged tree; expect zero drift.

- [ ] **Step 5: Wait for CI**

Expect 8/8 green.
