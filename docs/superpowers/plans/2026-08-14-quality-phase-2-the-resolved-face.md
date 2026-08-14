# Quality Phase 2 — The Resolved Face: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop trusting what a document *says* about its typography and measure
what it *got* — the face pango actually resolved for each run — then use that to
fix a demonstrated false negative in `font-fallback` and to add
`fake-small-caps`.

**Architecture:** One new module, `src/folio/faces.py`, owns the cffi work:
given a WeasyPrint `TextBox`, return the resolved family name and the OpenType
feature tags of the face that set it. `check.py` consumes it for two rules. The
cffi route is non-obvious and is written out in full below — it took real
digging and must not be rediscovered.

**Tech Stack:** Python 3.10+, WeasyPrint's bundled cffi bindings (`pango`,
`pangoft2`, `harfbuzz`), `struct` from the standard library.

## Global Constraints

- **No new dependency.** `pyproject.toml` declares `dependencies = []`. The
  GSUB table is parsed with `struct`; **do not add fontTools**.
- **Every rule needs a SKILL.md entry** — `test_every_rule_the_checker_can_emit_is_named_in_the_skill`
  enforces it. Fold the doc edit into the rule's task.
- **SKILL.md may only name folio's own CLI flags**, and a bare `--word` in it is
  read as a flag by `test_every_flag_the_skill_names_exists`. Write CSS custom
  properties as `var(--name)`. Both of these bit Phase 1.
- **Rules are `WARN`.** A face that folio does not recognise must stay silent.
- **Commit style:** `type(scope): lowercase summary`, no emoji, no trailer.

## The mechanism, verified end to end

This is the part worth writing down. Four things about it are counter-intuitive:

1. **The pango layout is dead by check time.** WeasyPrint calls
   `layout.deactivate()` after layout, which does `del self.layout`. Calling
   `reactivate(style)` rebuilds it — this is exactly what `draw/text.py` does
   before painting, so it re-runs the same shaping the PDF gets.
2. **`hb_font_get_face` is not in WeasyPrint's cffi surface.** Do not reach for it.
3. **`pango_fc_font_map_get_hb_face` lives in `libpangoft2`, not `libpango`** —
   import it from `weasyprint.text.ffi.pangoft2`. Calling it on `pango` raises
   `undefined symbol`.
4. **Its arguments need explicit casts** to `PangoFcFontMap *` and
   `PangoFcFont *`, or cffi raises `TypeError: initializer for ctype
   'PangoFcFont *' must be a pointer to same type`.

Measured output of the code below on the development host:

| face asked for | resolved | `smcp` | `onum` |
|---|---|---|---|
| Inter (39 GSUB features) | Inter | no | no |
| P052 — folio's Latin serif | P052 | no | no |
| DejaVu Serif | DejaVu Serif | no | no |
| Noto Serif | Noto Serif | yes | yes |

And the false negative the whole phase exists to remove, on Korean text:

| stack the document names | face that actually set the Hangul |
|---|---|
| `"Inter", sans-serif` | WenQuanYi Zen Hei — Chinese |
| `"Inter", "Noto Sans KR", sans-serif` | WenQuanYi Zen Hei — **Chinese** |
| `"Inter", "Noto Sans CJK KR", sans-serif` | Noto Sans CJK KR ✓ |

Row two is the point: the document names a Korean family, today's rule reads
the CSS stack, calls it covered, and says nothing while the text renders in a
Chinese face.

---

### Task 1: `src/folio/faces.py` — the resolved face

**Files:**
- Create: `src/folio/faces.py`
- Test: `tests/test_faces.py`

**Interfaces:**
- Produces: `resolved_runs(textbox) -> list[tuple[str, str]]` — `(text, family)`
  per pango run; `feature_tags(textbox) -> set[str]` — GSUB feature tags of the
  face that set the box's first run; `FacesUnavailable(RuntimeError)`.

- [ ] **Step 1: Write the failing test**

```python
"""What face actually set this text? Not what the stylesheet asked for."""

from __future__ import annotations

import pytest

pytest.importorskip("weasyprint", reason="faces reads WeasyPrint's pango layout")

from weasyprint import HTML  # noqa: E402

from folio.faces import feature_tags, resolved_runs  # noqa: E402


def _first_textbox(html: str):
    doc = HTML(string=html).render()

    def walk(b):
        yield b
        for c in getattr(b, "children", ()) or ():
            yield from walk(c)

    for box in walk(doc.pages[0]._page_box):
        if type(box).__name__ == "TextBox":
            return box
    raise AssertionError("no TextBox in fixture")


def test_a_latin_run_resolves_to_the_family_it_asked_for():
    box = _first_textbox('<style>p{font-family:"DejaVu Serif"}</style><p>Hello</p>')
    assert [family for _, family in resolved_runs(box)] == ["DejaVu Serif"]


def test_a_run_the_stack_cannot_set_resolves_to_something_else():
    """The defect, measured: a Latin-only stack still renders Hangul.

    Which face fontconfig picks is machine-dependent, so the assertion is that
    it is *not* the family that was asked for — that is the whole finding.
    """
    box = _first_textbox(
        '<style>p{font-family:"DejaVu Serif"}</style><p lang="ko">한국어</p>'
    )
    families = {family for _, family in resolved_runs(box)}
    assert families and "DejaVu Serif" not in families


def test_feature_tags_tell_real_small_caps_from_none():
    has = _first_textbox('<style>p{font-family:"Noto Serif"}</style><p>Nato</p>')
    hasnt = _first_textbox('<style>p{font-family:"DejaVu Serif"}</style><p>Nato</p>')
    assert "smcp" in feature_tags(has)
    assert "smcp" not in feature_tags(hasnt)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_faces.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'folio.faces'`.

- [ ] **Step 3: Write the module**

```python
"""Which face actually set a run of text.

Every other measurement folio takes reads the layout tree, which records what
the stylesheet asked for. This one reads what pango chose, which is a different
thing whenever the asked-for family is not installed: a font stack falls
through per glyph, and when it runs out fontconfig answers — never failing,
never asking, and for Korean on Linux commonly answering with a Chinese face.

The route is not the obvious one. See docs/superpowers/plans for why each step
is the way it is; briefly: WeasyPrint deactivates a text box's pango layout
after layout and `reactivate` rebuilds it (the draw stage does the same),
`hb_font_get_face` is absent from WeasyPrint's cffi surface,
`pango_fc_font_map_get_hb_face` lives in libpangoft2 rather than libpango, and
its arguments need explicit casts.
"""

from __future__ import annotations

import struct


class FacesUnavailable(RuntimeError):
    """Raised when the resolved face cannot be read on this platform."""


def _ffi():
    try:
        from weasyprint.text.ffi import ffi, harfbuzz, pango, pangoft2
    except Exception as exc:  # pragma: no cover - environment dependent
        raise FacesUnavailable("WeasyPrint's pango bindings are unavailable") from exc
    return ffi, pango, pangoft2, harfbuzz


def _first_line(textbox):
    """The pango line for this box, reactivating the layout if it was freed."""
    layout = textbox.pango_layout
    if not hasattr(layout, "layout"):
        # WeasyPrint frees the cdata after layout; the draw stage does exactly
        # this to get it back, so the shaping matches what the PDF receives.
        layout.reactivate(textbox.style)
    line, _ = layout.get_first_line()
    return layout, line


def resolved_runs(textbox) -> list[tuple[str, str]]:
    """[(text, family)] per pango run — the face that set each piece."""
    ffi, pango, _pangoft2, _harfbuzz = _ffi()
    layout, line = _first_line(textbox)
    utf8 = layout.text.encode()
    out: list[tuple[str, str]] = []
    run = line.runs[0]
    while run != ffi.NULL:
        item = run.data.item
        run = run.next
        piece = utf8[item.offset : item.offset + item.length].decode("utf-8", "replace")
        description = ffi.gc(
            pango.pango_font_describe(item.analysis.font),
            pango.pango_font_description_free,
        )
        family = ffi.string(
            pango.pango_font_description_get_family(description)
        ).decode()
        out.append((piece, family))
    return out


def _hb_face(font):
    """The harfbuzz face behind a pango font.

    `hb_font_get_face` is not declared by WeasyPrint, and
    `pango_fc_font_map_get_hb_face` is in libpangoft2 and needs both arguments
    cast. Getting either wrong raises rather than returning something wrong.
    """
    ffi, pango, pangoft2, _harfbuzz = _ffi()
    font_map = pango.pango_font_get_font_map(font)
    return pangoft2.pango_fc_font_map_get_hb_face(
        ffi.cast("PangoFcFontMap *", font_map), ffi.cast("PangoFcFont *", font)
    )


def feature_tags(textbox) -> set[str]:
    """OpenType GSUB feature tags of the face that set this box's first run.

    Parsed from the raw table rather than with fontTools, which folio does not
    depend on: the GSUB header holds the FeatureList offset at byte 6, and a
    FeatureList is a count followed by fixed six-byte records whose first four
    bytes are the tag.
    """
    ffi, _pango, _pangoft2, harfbuzz = _ffi()
    _layout, line = _first_line(textbox)
    face = _hb_face(line.runs[0].data.item.analysis.font)
    blob = harfbuzz.hb_face_reference_table(
        face, harfbuzz.hb_tag_from_string(b"GSUB", -1)
    )
    try:
        if not harfbuzz.hb_blob_get_length(blob):
            return set()
        with ffi.new("unsigned int *") as length:
            data = ffi.unpack(harfbuzz.hb_blob_get_data(blob, length), int(length[0]))
    finally:
        harfbuzz.hb_blob_destroy(blob)
    if len(data) < 10:
        return set()
    (feature_list,) = struct.unpack_from(">H", data, 6)
    (count,) = struct.unpack_from(">H", data, feature_list)
    return {
        struct.unpack_from(">4s", data, feature_list + 2 + i * 6)[0].decode(
            "ascii", "replace"
        )
        for i in range(count)
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_faces.py -v`
Expected: 3 PASSED. If `test_a_run_the_stack_cannot_set_resolves_to_something_else`
fails because the machine has no CJK face at all, that is a genuinely different
environment — note it and move on rather than weakening the test.

- [ ] **Step 5: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/faces.py tests/test_faces.py
git commit -m "feat(faces): read the face pango actually chose

Every measurement folio takes reads what the stylesheet asked for. This
reads what was resolved, which differs whenever the named family is not
installed — and for Korean on Linux fontconfig commonly answers with a
Chinese face.

No new dependency: the GSUB feature list is twenty lines of struct rather
than fontTools."
```

---

### Task 2: `font-fallback`, rewritten to measure

**Files:**
- Modify: `src/folio/check.py` — replace `_check_font_fallback`
- Modify: `tests/test_check.py`
- Modify: `skill/SKILL.md`

**Interfaces:**
- Consumes: `resolved_runs` from Task 1; `SCRIPT_INFO`, `covers`, `scripts_in`
  from `scripts.py`.

The rule stops reading `box.style["font_family"]` and instead asks, for each
script present in a run, whether the face that *set* that run covers it. The
`judgeable` / `LATIN_ONLY` caution in `scripts.py` exists only because the old
rule had to guess about families it had never heard of; measuring removes the
guess. Keep one piece of caution: if the resolved family is one folio does not
recognise at all, stay silent — it may be exactly the face the author chose.

- [ ] **Step 1: Write the failing test**

```python
def test_a_stack_naming_an_uninstalled_korean_family_is_now_reported():
    """The false negative this rewrite exists to remove.

    `Noto Sans KR` and `Noto Sans CJK KR` are the same design under two names,
    and a machine typically has one. Naming only the first satisfied the old
    rule, which read the stack, while the text rendered in whatever fontconfig
    picked — commonly Chinese.
    """
    body = '<p lang="ko">한국어 문서입니다</p>'
    extra = 'p{font-family:"DejaVu Serif","Noto Sans KR",serif}'
    assert "font-fallback" in rules(doc(body, extra))


def test_a_stack_whose_resolved_face_covers_the_script_is_silent():
    body = '<p lang="ko">한국어 문서입니다</p>'
    extra = 'p{font-family:"Noto Sans CJK KR",serif}'
    assert "font-fallback" not in rules(doc(body, extra))
```

The second test needs a Korean face installed; guard it with
`pytest.importorskip`-style detection if the suite must pass on a bare machine
— check `folio fonts` behaviour first rather than inventing a skip.

- [ ] **Step 2: Run and watch the first test fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k font_fallback -v`
Expected: `test_a_stack_naming_an_uninstalled_korean_family_is_now_reported`
FAILS — the old rule sees `Noto Sans KR` in the stack and stays silent. That
failure IS the false negative, reproduced as a test.

- [ ] **Step 3: Rewrite the rule**

Replace the body of `_check_font_fallback` in `src/folio/check.py`. Keep the
name, the severity and the page-level signature; change what it measures.

```python
def _check_font_fallback(root, n, scripts) -> list[Finding]:
    """Text set in a face that does not cover its own script.

    Rewritten to measure. The previous version read the CSS stack and asked
    whether any family named in it covers the script, which is a question about
    the stylesheet rather than about the page: `Noto Sans KR` and
    `Noto Sans CJK KR` are one design under two names, a machine typically has
    one of them, and naming only the absent one satisfied the rule while the
    text rendered in whatever fontconfig chose. For Korean on Linux that is
    commonly a Chinese face — legible, wrong, and invisible to every other rule
    here.

    Now the question is the one that matters: does the face that actually set
    this run cover the script it set? Still silent on a resolved family folio
    does not recognise, because that may be exactly the face the author chose.
    """
    from .faces import FacesUnavailable, resolved_runs
    from .scripts import SCRIPT_INFO, covers, judgeable, scripts_in

    candidates = [s for s in scripts if s != "latin"]
    if not candidates:
        return []
    out, seen = [], set()
    for box in _walk(root):
        if not _is_text(box) or box.text.isascii():
            continue
        try:
            runs = resolved_runs(box)
        except FacesUnavailable:  # pragma: no cover - environment dependent
            return []
        for text, family in runs:
            for script in scripts_in(text, candidates):
                if script in seen or covers(family, script):
                    continue
                if not judgeable(family):
                    continue  # an unknown face may well be the covering one
                seen.add(script)
                label = SCRIPT_INFO[script][1]
                out.append(
                    Finding(
                        "font-fallback",
                        WARN,
                        n,
                        f"{label} text is set in {family}, which does not cover {label}",
                        "name a family that covers the script — and name every "
                        "spelling of it, because `Noto Sans KR` and "
                        "`Noto Sans CJK KR` are one design and a machine "
                        "usually has one",
                    )
                )
    return out
```

- [ ] **Step 4: Run the tests**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k font_fallback -v`
Expected: both PASS.

- [ ] **Step 5: Confirm the corpus did not regress**

```bash
cd /data/abhi/projects/folio
for d in examples/*/ src/folio/assets/templates/*/; do
  printf "%-46s %s\n" "$d" "$(folio check "$d/document.html" 2>/dev/null | tail -1)"
done
```

Expected: all clean. The examples are Latin, so the rule should not fire; if it
does, `judgeable` is being asked about a family it should be silent on.

- [ ] **Step 6: Update the SKILL.md entry**

The existing `font-fallback` entry says the rule "stays silent on a family folio
does not recognise" and describes reading the stack. Rewrite the middle of it:
the rule now names the face that set the text, and the remedy gains "name every
spelling of the family". Keep the entry in the "not about geometry" group.

- [ ] **Step 7: Full suite, then commit**

```bash
cd /data/abhi/projects/folio && python -m pytest -p no:cacheprovider
git add src/folio/check.py tests/test_check.py skill/SKILL.md
git commit -m "fix(check): font-fallback measures the face, not the stack"
```

---

### Task 3: `fake-small-caps`

**Files:**
- Modify: `src/folio/check.py`
- Modify: `tests/test_check.py`
- Modify: `skill/SKILL.md`
- Modify: `src/folio/assets/themes/editorial.css`

**Interfaces:**
- Consumes: `feature_tags` from Task 1.

A repair, not insurance. `editorial.css:111` sets
`p.lead + p::first-line { font-variant: small-caps }` on `var(--font-body)`,
which resolves to P052 — and P052, Inter and DejaVu Serif all lack an `smcp`
table. Pango then synthesises small caps by scaling capitals, which is
Butterick's rule 14 exactly: *if you don't have real small caps, don't use them
at all.* Verified by rendering `editorial` and looking at the opening line.

- [ ] **Step 1: Write the failing test**

```python
def test_small_caps_on_a_face_without_them_is_reported():
    body = "<p>Nato and the treaty</p>"
    extra = 'p{font-family:"DejaVu Serif";font-variant-caps:small-caps}'
    assert "fake-small-caps" in rules(doc(body, extra))


def test_small_caps_on_a_face_that_has_them_is_silent():
    body = "<p>Nato and the treaty</p>"
    extra = 'p{font-family:"Noto Serif";font-variant-caps:small-caps}'
    assert "fake-small-caps" not in rules(doc(body, extra))
```

- [ ] **Step 2: Run and watch the first fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k small_caps -v`
Expected: the first FAILS, the second passes vacuously.

- [ ] **Step 3: Add the rule**

Add beside `_check_font_fallback` in `check.py`, and call it from the per-page
loop in `inspect()` next to the other character-adjacent rules.

```python
def _check_fake_small_caps(root, n) -> list[Finding]:
    """Small caps asked of a face that has none.

    Butterick's rule 14: if you do not have real small caps, do not use them.
    Asked anyway, pango synthesises them by scaling capitals, which reads as a
    weight error rather than as a style — the letters are too light and too
    wide for the size they are pretending to be.

    Measured off the resolved face's GSUB table, so it is silent when the face
    genuinely has the feature.
    """
    from .faces import FacesUnavailable, feature_tags

    out, seen = [], set()
    for box in _walk(root):
        if not _is_text(box):
            continue
        variant = box.style["font_variant_caps"]
        if variant in ("normal", None):
            continue
        try:
            tags = feature_tags(box)
        except FacesUnavailable:  # pragma: no cover - environment dependent
            return []
        if "smcp" in tags:
            continue
        runs = None
        try:
            from .faces import resolved_runs

            runs = resolved_runs(box)
        except FacesUnavailable:  # pragma: no cover
            pass
        family = runs[0][1] if runs else "the resolved face"
        if family in seen:
            continue
        seen.add(family)
        out.append(
            Finding(
                "fake-small-caps",
                WARN,
                n,
                f"small caps asked of {family}, which has no smcp table",
                "pango scales capitals instead, which reads as a weight error; "
                "set the passage in a face that has real small caps, or drop "
                "the small caps",
            )
        )
    return out
```

- [ ] **Step 4: Run the tests, then the corpus**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k small_caps -v`
Expected: both PASS.

Then: `folio check examples/exhibition/document.html` and `examples/case-study/document.html`
Expected: **`fake-small-caps` fires** — those are `editorial` documents and the
opening line of each is synthetic. That is the repair this rule exists for.

- [ ] **Step 5: Decide `editorial`'s opening line, and look at it**

Two honest options; pick by rendering both and comparing page 2 of `exhibition`:

- **Drop it.** Delete `p.lead + p::first-line { font-variant: small-caps }` from
  `editorial.css:111`. The opening line then matches the body, which is what
  most books do.
- **Earn it.** Set that one line in a face that has `smcp`. `Noto Serif` has
  both `smcp` and `onum` on this host, but it is a different design from P052
  and mixing serifs on one line is its own defect — check it on the page before
  choosing this.

Recommendation: drop it. A synthetic small cap is worse than no small cap, and
folio does not bundle a face that has real ones.

- [ ] **Step 6: SKILL.md entry**

Add to the group Phase 1 created for the character rules:

```markdown
- `fake-small-caps` — small caps asked of a face with no `smcp` table. Pango
  synthesises them by scaling capitals, which reads as a weight error rather
  than a style: too light and too wide for the size they imitate. None of the
  Latin faces folio resolves — Inter, P052, DejaVu Serif — has the feature, so
  this is a decision about the passage, not a setting to turn on. Set it in a
  face that has real small caps, or drop them.
```

- [ ] **Step 7: Full suite, corpus clean, commit**

```bash
cd /data/abhi/projects/folio && python -m pytest -p no:cacheprovider
for d in examples/*/; do folio check "$d/document.html" 2>/dev/null | tail -1; done
git add -A src tests skill
git commit -m "feat(check): fake-small-caps, and editorial stops faking them"
```

---

### Task 4: The changelog

- [ ] **Step 1: Write the `[Unreleased]` entry**

It must say three things plainly:

- `font-fallback` was **replaced, not extended**, and a document that passed on
  a machine missing its fonts will now report. That is the intent.
- `fake-small-caps` is a **repair**: `editorial`'s opening line had been
  synthetic since the theme was written, and no rule could see it because
  geometry was correct.
- The mechanism reads the resolved face rather than the stylesheet, which is the
  same move `check.py` made for geometry, applied to type.

- [ ] **Step 2: Commit**

---

## Carried over from Phase 1

- **The look pass is unfinished:** 5 of 31 example pages were read. Phase 2
  changes `editorial`'s opening line, so `exhibition`, `case-study` and
  `lookbook` need looking at again regardless.
- **The Phase 1 spec is stale in two places** — it proposes an 8-line prose
  floor (the code uses 6, from the measured gap) and `--measure` in `ch` (the
  code uses 130mm, because `ch` gave one page three right edges). The changelog
  and the CSS comments carry the corrected reasoning; the spec on disk does not.
