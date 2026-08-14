# Quality Phase 1 — The Floor: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four new `folio check` rules that measure typographic characters and
the measure, then the repairs that turn them green across the nine examples and
seven scaffolds.

**Architecture:** Three character rules share one mechanism — walk the laid-out
text boxes, skip anything inside a code element, report once per rule per page.
`measure` is a document-level rule alongside `heading-skip` and `type-drift`: it
takes the modal font size of `<p>` line boxes as body copy and medians their
length. The repairs follow the rules, never the other way round, so every fix is
watched to fail first.

**Tech Stack:** Python 3.10+, WeasyPrint (layout tree), pytest, CSS custom
properties.

## Global Constraints

- **No new dependency.** `pyproject.toml` declares `dependencies = []` on
  purpose; a broken install must still be a working install. Everything here
  uses the standard library and WeasyPrint's already-present layout tree.
- **Every rule needs a SKILL.md entry.** `tests/test_skill.py::test_every_rule_the_checker_can_emit_is_named_in_the_skill`
  greps `check.py` for `Finding(\s*\n?\s*"([a-z][a-z-]+)"` and fails if the name
  is not in SKILL.md as `` `rule-name` ``. Fold the doc edit into the same task
  as the rule, or the suite goes red.
- **Rules measure the rendered document,** never the source file. Every check
  here reads WeasyPrint's layout tree.
- **All four new rules are `WARN`,** never `ERROR`. Each has a legitimate
  exception; an error people learn to expect is worse than a warning they read.
- **Code elements are exempt from every character rule:** `code`, `pre`, `kbd`,
  `samp`, `tt`, `var`. This is measured, not defensive — folio's own corpus
  contains `recon report --since 7d` and `SELECT now() - last_replay`.
- **Commit style:** `type(scope): lowercase summary`, e.g.
  `feat(check): straight-quote, the oldest tell in the trade`. No emoji, no
  Co-Authored-By trailer (this repo's history has none).
- **The canon:** 45–90 characters per line, leading 120–145% of point size.

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/folio/check.py` | All four rules, their helpers and constants; wired into `inspect()` | 1, 2, 3 |
| `tests/test_check.py` | Golden pair per rule, plus every exemption | 1, 2, 3 |
| `skill/SKILL.md` | One prose entry per rule — enforced by a test | 1, 2, 3 |
| `examples/*/document.html` | The apostrophe and quote repairs | 4 |
| `src/folio/assets/templates/*/document.html` | Same repairs in the scaffolds | 4 |
| `src/folio/assets/base.css` | `--measure` token, the prose cap, hyphenation limits | 5, 7 |
| `src/folio/assets/themes/*.css` | Per-theme measure and leading | 5, 6 |
| `CHANGELOG.md` | The `[Unreleased]` entry | 8 |

`check.py` is 1125 lines and organised by section banner. Add the character
rules and `measure` under the existing `# ── checks ──` and
`# ── conformance ──` banners respectively; do not restructure the file.

---

### Task 1: The character-rule mechanism, and `straight-quote`

**Files:**
- Modify: `src/folio/check.py` — constants near the top, helpers and the check
  under `# ── checks ──`, one line in `inspect()`
- Modify: `tests/test_check.py`
- Modify: `skill/SKILL.md`
- Test: `tests/test_check.py`

**Interfaces:**
- Consumes: `_walk`, `_is_text`, `_parent_map`, `Finding`, `WARN` — all already
  in `check.py`.
- Produces: `CODE_TAGS: frozenset[str]`, `_in_code(box, parents: dict) -> bool`,
  `_snippet(text: str, at: int, width: int = 28) -> str`,
  `CHARACTER_RULES: tuple[tuple[str, re.Pattern, str, str], ...]`,
  `_check_characters(root, n, parents: dict) -> list[Finding]`. Tasks 2 relies
  on `CHARACTER_RULES` being the single table the check iterates.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_check.py`, at the end of the file:

```python
# ── typographic characters ────────────────────────────────────────────────


def test_straight_apostrophe_in_prose_is_reported():
    assert "straight-quote" in rules(doc("<p>Meridian's platform team knew.</p>"))


def test_curly_apostrophe_is_silent():
    assert "straight-quote" not in rules(doc("<p>Meridian’s platform team knew.</p>"))


def test_straight_marks_after_a_digit_are_feet_and_inches():
    """Butterick's rule 26 runs the other way: these are *meant* to be straight."""
    assert "straight-quote" not in rules(doc("<p>The press bed is 5' 10\" across.</p>"))


def test_a_straight_quote_inside_code_is_a_string_literal():
    assert "straight-quote" not in rules(doc("<p>Run <code>echo 'hi'</code> first.</p>"))


def test_a_page_with_many_straight_quotes_reports_once():
    """Eighteen findings on one page is a report nobody reads to the end."""
    body = "<p>" + "Meridian's team knew what Halloran's press did. " * 6 + "</p>"
    found = [f for f in inspect(doc(body), Path("/tmp")) if f.rule == "straight-quote"]
    assert len(found) == 1
    assert "more on this page" in found[0].detail
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "straight or feet or code_is_a_string" -v`
Expected: 5 FAILED — the rule does not exist, so `"straight-quote"` is never in
the set and `found` is empty.

- [ ] **Step 3: Add the constants**

In `src/folio/check.py`, after the `SAME_SIZE_PCT` constant (around line 58) and
before the `MM = 96 / 25.4` line, insert:

```python
# Elements whose text is not prose. A `--` in one of these is a command flag
# and a `-` is a minus — measured, not assumed: folio's own corpus holds
# `recon report --since 7d` and `SELECT now() - last_replay`, both correct.
CODE_TAGS = frozenset({"code", "pre", "kbd", "samp", "tt", "var"})
```

- [ ] **Step 4: Add the rule table and helpers**

In `src/folio/check.py`, under the `# ── checks ──` banner, immediately before
`def _check_half_bleed`, insert:

```python
# Marks a typewriter had and a typesetter does not. Straight marks are correct
# after a digit — 5' 10" is feet and inches, and curling those is the defect.
_STRAIGHT_QUOTE = re.compile(r"(?<![0-9])['\"]")
_TYPEWRITER_DASH = re.compile(r"--")
_DOT_ELLIPSIS = re.compile(r"(?<!\.)\.\.\.(?!\.)")

# (rule, pattern, what to call it, what to do about it)
CHARACTER_RULES: tuple[tuple[str, re.Pattern, str, str], ...] = (
    (
        "straight-quote",
        _STRAIGHT_QUOTE,
        "a straight quote",
        "’ for an apostrophe, “ ” for quotes; feet and inches stay straight",
    ),
)


def _in_code(box, parents: dict) -> bool:
    """Is this text inside an element where a typewriter mark is the right mark?"""
    node = box
    while node is not None:
        if getattr(node, "element_tag", None) in CODE_TAGS:
            return True
        node = parents.get(id(node))
    return False


def _snippet(text: str, at: int, width: int = 28) -> str:
    """The mark with enough either side of it to find in the source."""
    start = max(0, at - width // 2)
    piece = text[start : at + width // 2].strip()
    lead = "…" if start > 0 else ""
    tail = "…" if at + width // 2 < len(text) else ""
    return f"{lead}{piece}{tail}"


def _check_characters(root, n, parents: dict) -> list[Finding]:
    """Typographic marks, which are the one thing a reader sees before the words.

    Every other rule here asks whether a measurement is in range. This one asks
    which character was typed — closer to `font-fallback` than to the geometry
    rules, and reported for the same reason: the page is perfectly well formed
    and reads as amateur anyway. A straight apostrophe in a serif face is a
    foot mark, and it is the most reliable tell there is.

    One finding per rule per page. Eighteen of these on a page, which is what
    the quarterly-report actually held, is a report nobody reads to the end.
    """
    first: dict[str, tuple[str, int]] = {}
    counts: dict[str, int] = {}
    for box in _walk(root):
        if not _is_text(box) or _in_code(box, parents):
            continue
        text = box.text
        for rule, pattern, _label, _hint in CHARACTER_RULES:
            for match in pattern.finditer(text):
                counts[rule] = counts.get(rule, 0) + 1
                first.setdefault(rule, (text, match.start()))
    out = []
    for rule, _pattern, label, hint in CHARACTER_RULES:
        if rule not in counts:
            continue
        text, at = first[rule]
        more = counts[rule] - 1
        detail = f"{label} in “{_snippet(text, at)}”"
        if more:
            detail += f" (+{more} more on this page)"
        out.append(Finding(rule, WARN, n, detail, hint))
    return out
```

- [ ] **Step 5: Wire it into `inspect()`**

In `src/folio/check.py`, in the per-page loop inside `inspect()`, immediately
after the `findings += _check_font_fallback(root, i, profile.scripts)` line, add:

```python
        findings += _check_characters(root, i, parents)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "straight or feet or code_is_a_string" -v`
Expected: 5 PASSED.

- [ ] **Step 7: Document the rule in SKILL.md**

In `skill/SKILL.md`, after the `font-fallback` entry and before the
`One rule measures *where* a block sits` line, insert:

```markdown
Three rules read the characters rather than the geometry:

- `straight-quote` — a `'` or `"` in prose. In a serif face a straight
  apostrophe is a foot mark, which is why it is the most reliable amateur tell
  in typesetting. Use `’` for an apostrophe and `“ ”` for a quotation. Marks
  after a digit are left alone: `5' 10"` is feet and inches, and curling those
  would be the defect. Text inside `code`, `pre`, `kbd`, `samp`, `tt` and `var`
  is exempt — a straight quote in a shell command is the right quote.
```

- [ ] **Step 8: Run the full suite**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: the new tests pass and `test_every_rule_the_checker_can_emit_is_named_in_the_skill`
passes. **Expect failures in `tests/test_docs.py` or any example-based test that
asserts the shipped examples are clean** — the examples genuinely contain 33
straight quotes and Task 4 is what fixes them. Note which tests fail; do not fix
them here.

- [ ] **Step 9: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/check.py tests/test_check.py skill/SKILL.md
git commit -m "feat(check): straight-quote, the oldest tell in the trade

A straight apostrophe in a serif face is a foot mark. folio has shipped 33
of them across seven examples and six across three scaffolds, through seven
releases, under a green check — because every rule until now measured
geometry, and a wrong mark has perfectly correct geometry.

Exempt after a digit, where straight is right, and inside code elements,
where the corpus itself supplies the evidence: recon report --since 7d."
```

---

### Task 2: `dash` and `dot-ellipsis`

**Files:**
- Modify: `src/folio/check.py` — two rows in `CHARACTER_RULES`
- Modify: `tests/test_check.py`
- Modify: `skill/SKILL.md`

**Interfaces:**
- Consumes: `CHARACTER_RULES`, `_check_characters`, `_TYPEWRITER_DASH`,
  `_DOT_ELLIPSIS` from Task 1.
- Produces: nothing new. Both rules ride the Task 1 mechanism unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_check.py`, after the Task 1 tests:

```python
def test_double_hyphen_in_prose_is_reported():
    assert "dash" in rules(doc("<p>The result -- and it was a result -- held.</p>"))


def test_an_em_dash_is_silent():
    assert "dash" not in rules(doc("<p>The result — and it was a result — held.</p>"))


def test_a_command_flag_is_not_a_dash():
    """The evidence for this exemption is folio's own runbook."""
    assert "dash" not in rules(doc("<p>Run <code>recon report --since 7d</code> nightly.</p>"))


def test_three_periods_are_reported():
    assert "dot-ellipsis" in rules(doc("<p>It went on... and on.</p>"))


def test_a_real_ellipsis_is_silent():
    assert "dot-ellipsis" not in rules(doc("<p>It went on… and on.</p>"))


def test_a_leader_of_dots_is_not_an_ellipsis():
    """Four or more is a leader or a redaction, not a mistyped ellipsis."""
    assert "dot-ellipsis" not in rules(doc("<p>Chapter one....... 14</p>"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "dash or ellipsis or periods" -v`
Expected: `test_double_hyphen_in_prose_is_reported` and
`test_three_periods_are_reported` FAIL (the rules do not exist yet); the four
silence tests pass vacuously. That is the correct starting state — the two that
must fail, fail.

- [ ] **Step 3: Add the two rows**

In `src/folio/check.py`, extend `CHARACTER_RULES` to:

```python
CHARACTER_RULES: tuple[tuple[str, re.Pattern, str, str], ...] = (
    (
        "straight-quote",
        _STRAIGHT_QUOTE,
        "a straight quote",
        "’ for an apostrophe, “ ” for quotes; feet and inches stay straight",
    ),
    (
        "dash",
        _TYPEWRITER_DASH,
        "“--” doing a dash's work",
        "— for a break in thought, – for a range; -- is a typewriter habit",
    ),
    (
        "dot-ellipsis",
        _DOT_ELLIPSIS,
        "three periods where an ellipsis belongs",
        "… is one character (U+2026), and it keeps its own spacing",
    ),
)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "dash or ellipsis or periods" -v`
Expected: 6 PASSED.

- [ ] **Step 5: Document both rules in SKILL.md**

In `skill/SKILL.md`, immediately after the `straight-quote` entry added in
Task 1, insert:

```markdown
- `dash` — `--` standing in for a dash. Two hyphens is a typewriter working
  around a key it did not have. Use `—` for a break in thought and `–` for a
  range. Exempt inside code, where `--since` is a flag.
- `dot-ellipsis` — three periods where `…` belongs. The single character keeps
  its own spacing and cannot be broken across a line. Four or more dots are a
  leader or a redaction and are left alone.
```

- [ ] **Step 6: Run the full suite**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: same known example failures as Task 1, no new ones.

- [ ] **Step 7: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/check.py tests/test_check.py skill/SKILL.md
git commit -m "feat(check): dash and dot-ellipsis, both insurance

Neither repairs anything: the corpus has no -- in prose and no dotted
ellipsis at all. They ride the mechanism straight-quote already needed, and
they are here so the next document cannot introduce what this one avoided
by luck.

No rule for the spaced hyphen. The one occurrence in the corpus is
SELECT now() - last_replay, a real minus inside code — the evidence for
that rule is the evidence against it."
```

---

### Task 3: `measure`

**Files:**
- Modify: `src/folio/check.py` — `import statistics`, two constants, two
  functions under `# ── conformance ──`, one line in `inspect()`
- Modify: `tests/test_check.py`
- Modify: `skill/SKILL.md`

**Interfaces:**
- Consumes: `_walk`, `_is_text`, `Finding`, `WARN`.
- Produces: `MEASURE_MIN: int`, `MEASURE_MAX: int`, `MIN_BODY_LINES: int`,
  `_body_paragraphs(pages)` yielding `(page_number: int, lines: list[tuple[float, str]])`,
  `_check_measure(pages) -> list[Finding]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_check.py`, after the Task 2 tests:

```python
# ── the measure ───────────────────────────────────────────────────────────

# Repetitive on purpose: what is under test is the column, not the copy. Long
# enough that the median cannot be swung by one line, and that every fixture
# below clears the eight-line floor unless it is meant not to.
PROSE = "<p>" + ("The column is what this fixture measures, not the copy in it. " * 60) + "</p>"

# A page wide enough that no installed face can bring the line under 90
# characters. The fixtures below cap the column in `ch` rather than millimetres
# for the same reason: both ends of the comparison then move with the face.
WIDE = "@page{size:400mm 300mm;margin:10mm}"


def test_a_column_wider_than_the_canon_is_reported():
    html = f"<!DOCTYPE html><html><head><style>{WIDE}</style></head><body>{PROSE}</body></html>"
    assert "measure" in rules(html)


def test_a_column_inside_the_canon_is_silent():
    html = (
        f"<!DOCTYPE html><html><head><style>{WIDE}p{{max-width:60ch}}</style>"
        f"</head><body>{PROSE}</body></html>"
    )
    assert "measure" not in rules(html)


def test_a_column_narrower_than_the_canon_is_reported():
    html = (
        f"<!DOCTYPE html><html><head><style>{WIDE}p{{max-width:20ch}}</style>"
        f"</head><body>{PROSE}</body></html>"
    )
    assert "measure" in rules(html)


def test_a_document_with_almost_no_prose_is_not_measured():
    """A menu has four lines of body copy. A median over four lines is noise."""
    short = "<p>" + ("The column is what this fixture measures. " * 2) + "</p>"
    html = (
        f"<!DOCTYPE html><html><head><style>{WIDE}p{{max-width:20ch}}</style>"
        f"</head><body>{short}</body></html>"
    )
    assert "measure" not in rules(html)


def test_measure_is_reported_once_for_the_whole_document():
    html = f"<!DOCTYPE html><html><head><style>{WIDE}</style></head><body>{PROSE}</body></html>"
    assert len([f for f in inspect(html, Path("/tmp")) if f.rule == "measure"]) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "column or measured or measure_is" -v`
Expected: the three that assert `"measure" in ...` FAIL; the two silence tests
pass vacuously.

- [ ] **Step 3: Add the import and constants**

In `src/folio/check.py`, change the import block at the top from:

```python
import re
from dataclasses import dataclass
from pathlib import Path
```

to:

```python
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
```

Then, immediately after the `SAME_SIZE_PCT` constant and before `CODE_TAGS`
(added in Task 1), insert:

```python
# The comfortable line, in characters. Butterick puts it at 45–90; the book
# guides that disagree, disagree inside that range rather than outside it.
MEASURE_MIN, MEASURE_MAX = 45, 90
# Below this many lines of body copy a document is not prose and the median is
# noise rather than a measurement: `menu` has four lines, `architecture` six.
MIN_BODY_LINES = 8
```

- [ ] **Step 4: Add the check**

In `src/folio/check.py`, under the `# ── conformance ──` banner, immediately
before `def _check_inline_style`, insert:

```python
def _body_paragraphs(pages):
    """(page number, [(font size, line text)]) for every `<p>` laid out.

    Paragraphs rather than every line box, because the last line of a paragraph
    is short by definition — it measures where the sentence ended, not how wide
    the column is — and only the paragraph knows which line that is.
    """
    for number, page in enumerate(pages, start=1):
        for box in _walk(page._page_box):
            if getattr(box, "element_tag", None) != "p":
                continue
            lines = []
            for child in getattr(box, "children", ()) or ():
                if type(child).__name__ != "LineBox":
                    continue
                runs = [t for t in _walk(child) if _is_text(t)]
                if runs:
                    lines.append((runs[0].style["font_size"], "".join(r.text for r in runs)))
            if lines:
                yield number, lines


def _check_measure(pages) -> list[Finding]:
    """How many characters the reader crosses before the line returns.

    The oldest measurement in typesetting and the one folio never took. Too
    wide and the eye loses its place on the return; too narrow and it returns
    so often that the rhythm breaks. Neither shows up in geometry: the column
    is exactly as wide as it was asked to be.

    Body copy is the modal font size among `<p>` lines, which is how a document
    that is mostly tables and captions still gets measured on its prose.
    """
    paragraphs = list(_body_paragraphs(pages))
    sizes = [round(size, 2) for _, lines in paragraphs for size, _ in lines]
    if not sizes:
        return []
    body = statistics.mode(sizes)
    lengths: list[int] = []
    page = 1
    for number, lines in paragraphs:
        for size, text in lines[:-1]:
            if abs(size - body) < 0.05:
                if not lengths:
                    page = number
                lengths.append(len(text))
    if len(lengths) < MIN_BODY_LINES:
        return []
    median = statistics.median(lengths)
    if MEASURE_MIN <= median <= MEASURE_MAX:
        return []
    wide = median > MEASURE_MAX
    return [
        Finding(
            "measure",
            WARN,
            page,
            f"body copy runs {median:.0f} characters a line",
            (
                f"{MEASURE_MIN}–{MEASURE_MAX} is the comfortable range; "
                + (
                    "narrow the column with --measure, or set two"
                    if wide
                    else "widen the column, or set the type smaller"
                )
            ),
        )
    ]
```

- [ ] **Step 5: Wire it into `inspect()`**

In `src/folio/check.py`, in the document-level block of `inspect()`, immediately
after `findings += _check_type_drift(pages)`, add:

```python
    findings += _check_measure(pages)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /data/abhi/projects/folio && python -m pytest tests/test_check.py -k "column or measured or measure_is" -v`
Expected: 5 PASSED.

- [ ] **Step 7: Document the rule in SKILL.md**

In `skill/SKILL.md`, in the list that already holds `type-drift`, immediately
after the `type-drift` entry, insert:

```markdown
- `measure` — body copy runs outside 45–90 characters a line. The oldest
  measurement in typesetting: too wide and the eye loses its place on the
  return, too narrow and it returns so often the rhythm breaks. Reported once
  for the document, from the modal `<p>` size, ignoring each paragraph's last
  line. Narrow the column with `--measure`, or set two. A document with fewer
  than eight lines of body copy is not measured — a menu is not prose.
```

- [ ] **Step 8: Confirm the rule fires on the real corpus**

Run:

```bash
cd /data/abhi/projects/folio
for d in examples/*/; do printf "%-20s " "$(basename $d)"; \
  folio check "$d/document.html" 2>/dev/null | grep -c "measure" ; done
```

Expected: `1` for case-study, exhibition, quarterly-report, runbook and survey;
`0` for architecture, lookbook, menu and programme. If any row disagrees with
that, stop — the rule disagrees with the measurement the spec was built on, and
one of the two is wrong.

- [ ] **Step 9: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/check.py tests/test_check.py skill/SKILL.md
git commit -m "feat(check): measure, which folio had never taken

Body copy in five of the nine examples runs 92-110 characters a line
against a 45-90 canon, and the leading in those same documents sits at
1.58-1.66 against a 1.45 ceiling — not a second defect but the
compensation a designer reaches for when the column is too wide to fix.

Reported once per document, from the modal <p> size, dropping each
paragraph's last line because it measures where the sentence ended.
Documents under eight lines of body copy are left alone: a menu is not
prose, and a median over four lines is noise."
```

---

### Task 4: The apostrophe and quote sweep

**Files:**
- Modify: `examples/case-study/document.html`, `examples/exhibition/document.html`,
  `examples/menu/document.html`, `examples/programme/document.html`,
  `examples/quarterly-report/document.html`, `examples/runbook/document.html`,
  `examples/survey/document.html`
- Modify: `src/folio/assets/templates/case-study/document.html`,
  `src/folio/assets/templates/proposal/document.html`,
  `src/folio/assets/templates/runbook/document.html`

**Interfaces:**
- Consumes: the `straight-quote` rule from Task 1 as the verification oracle.
- Produces: nothing in code.

- [ ] **Step 1: List every occurrence the rule can see**

Run:

```bash
cd /data/abhi/projects/folio
for f in examples/*/document.html src/folio/assets/templates/*/document.html; do
  n=$(folio check "$f" 2>/dev/null | grep -c "straight-quote")
  [ "$n" != "0" ] && echo "$f"
done
```

Save the list. Every file on it must be silent by Step 5.

- [ ] **Step 2: Rewrite the marks with a throwaway script**

The rewrite must not touch anything inside a code element. Write this to the
scratchpad (it is a one-off, **do not commit it**):

```python
# /tmp/curl.py
import re
import sys
from pathlib import Path

# Everything that is NOT a text node: a whole code region, or any single tag.
# Curling must never reach inside either — a document is full of `class="…"`,
# and a rule that curls the closing quote of an attribute destroys the file.
SKIP = re.compile(
    r"<(code|pre|kbd|samp|tt|var|script|style)\b[^>]*>.*?</\1\s*>|<[^>]+>",
    re.S | re.I,
)


def curl(text: str) -> str:
    """Text nodes only. Never called on a tag or a code region."""
    # Apostrophe between letters (don't) or letter-then-s (Meridian's).
    text = re.sub(r"(?<=[A-Za-z])'(?=[A-Za-z])", "’", text)
    # Plural possessive: the students' union.
    text = re.sub(r"(?<=s)'(?=[\s.,;:)])", "’", text)
    # Opening double quote at the start of a text node or after a space;
    # every other one closes. Order matters — openers are claimed first.
    text = re.sub(r'(^|(?<=\s))"', "“", text)
    text = text.replace('"', "”")
    return text


for path in map(Path, sys.argv[1:]):
    source = path.read_text(encoding="utf-8")
    out, last = [], 0
    for m in SKIP.finditer(source):
        out.append(curl(source[last : m.start()]))
        out.append(m.group(0))          # tag or code region, verbatim
        last = m.end()
    out.append(curl(source[last:]))
    path.write_text("".join(out), encoding="utf-8")
    print(f"  curled {path}")
```

**Why the skip pattern matches tags as well as code regions:** an earlier draft
of this script skipped only `<code>…</code>` and curled everything else, which
means the second double-quote substitution reaches `class="lead"` and rewrites
the closing quote of every attribute in the file. Matching every `<…>` and
passing it through verbatim is what keeps the rewrite inside text nodes.

Run it over exactly the files Step 1 listed:

```bash
cd /data/abhi/projects/folio
python /tmp/curl.py $(for f in examples/*/document.html src/folio/assets/templates/*/document.html; do
  n=$(folio check "$f" 2>/dev/null | grep -c "straight-quote"); [ "$n" != "0" ] && echo "$f"; done)
```

- [ ] **Step 3: Read the diff, every hunk**

Run: `cd /data/abhi/projects/folio && git diff`

A regex cannot tell a possessive from a foot mark or an opening quote from a
closing one in every case. Check specifically:

- No `’` or `”` inside an attribute value, a URL, or a class name. If you see
  `class=”lead”` anywhere, stop and revert — the skip pattern failed, most
  likely on a tag containing a `>` inside an attribute value.
- Every `“` has a matching `”`, and they are the right way round. The known
  failure is a quotation broken by markup — `"<em>word</em>"` — where the
  closing mark opens its own text node and gets curled the wrong way.
- Nothing changed inside `<code>`, `<pre>`, or a `style`/`script` block.
- Measurements like `5'` or `10"` were left straight.

Fix anything wrong by hand. **If a hunk looks doubtful, revert that file and do
it by hand** — ten files is not too many to edit, and a backwards quotation mark
is a worse defect than the one being fixed.

- [ ] **Step 4: Verify the rule is silent on every one**

Run:

```bash
cd /data/abhi/projects/folio
for f in examples/*/document.html src/folio/assets/templates/*/document.html; do
  printf "%-52s %s\n" "$f" "$(folio check "$f" 2>/dev/null | grep -c 'straight-quote')"
done
```

Expected: `0` on every row.

- [ ] **Step 5: Run the full suite**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: PASS, including any test that asserts the examples are clean of
`straight-quote`. `measure` findings on five examples remain — Task 5 fixes
those.

- [ ] **Step 6: Commit**

```bash
cd /data/abhi/projects/folio
git add examples src/folio/assets/templates
git commit -m "fix(examples): apostrophes that were foot marks

Thirty-three straight marks across seven examples and six across three
scaffolds, every one of them a possessive — Meridian's, Halloran's,
yesterday's — plus one heading set large reading What \"done\" means for Q4.

The scaffolds mattered more than the examples: three of the seven shipped
the defect to every document started from them."
```

---

### Task 5: The `--measure` token

**Files:**
- Modify: `src/folio/assets/base.css` — one token, one rule, one exemption list
- Modify: `src/folio/assets/themes/editorial.css`, `technical.css`, `minimal.css`
  (only if the verification in Step 5 requires it)

**Interfaces:**
- Consumes: the `measure` rule from Task 3 as the verification oracle.
- Produces: the CSS custom property `--measure`, part of the theme token
  contract.

**Measured before planning — this is what `68ch` does to the five over-wide
examples**, so the implementer knows the target rather than guessing at it:

| example | uncapped | 90ch | 80ch | 72ch | 68ch |
|---|---|---|---|---|---|
| quarterly-report | 110 | 99 | 87 | 79 | **74** |
| survey | 110 | 98 | 87 | 80 | **75** |
| exhibition | 99 | 99 | 88 | 80 | **75** |
| case-study | 96 | 96 | 86 | 76 | **73** |
| runbook | 98 | 98 | 98 | 92 | **86** |

`68ch` brings all five inside 45–90 and cannot affect the four already inside —
`max-width` only narrows. `runbook` lands at 86, inside the range but only just;
it has the fewest body lines of any example (nine), so its median is the least
stable number in the table. Do not chase it lower.

- [ ] **Step 1: Add the token**

In `src/folio/assets/base.css`, in the `:root` token contract, change:

```css
  --fs-body: 9.8pt;
  --lh-body: 1.58;
  --radius: 3px;
```

to:

```css
  --fs-body: 9.8pt;
  --lh-body: 1.58;
  /* The measure: how many characters the reader crosses before the line
     returns. In `ch` so it tracks the face and the size a theme chooses —
     68ch lands around 74 characters in the kit's own faces, inside the 45–90
     the canon asks for. `folio check` measures the result. */
  --measure: 68ch;
  --radius: 3px;
```

- [ ] **Step 2: Cap the prose, and only the prose**

In `src/folio/assets/base.css`, immediately after the
`p { margin: 0 0 0.62em; orphans: 3; widows: 3; }` line, insert:

```css
/* Prose is measured; figures, tables and anything that owns its own width are
   not. Capping everything leaves a ragged right edge that reads as a fault —
   a measured column beside full-width figures reads as a decision. */
p, blockquote { max-width: var(--measure); }
```

- [ ] **Step 3: Verify against the corpus**

Run:

```bash
cd /data/abhi/projects/folio
for d in examples/*/; do printf "%-20s %s\n" "$(basename $d)" \
  "$(folio check "$d/document.html" 2>/dev/null | grep 'measure' || echo ok)"; done
```

Expected: no `measure` finding on any of the nine.

- [ ] **Step 4: Extend the cap to lists**

In `src/folio/assets/base.css`, change the rule added in Step 2 to:

```css
p, blockquote, ul, ol { max-width: var(--measure); }

/* Components that own their width. `.toc` is a flex row whose dotted fill
   stretches to the page edge, so a measured `ol` would pull its page numbers
   into the middle of the page. */
.toc ul, .toc ol, td p, th p, figcaption p, .metric p { max-width: none; }
```

- [ ] **Step 5: Verify nothing else moved**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: PASS.

Then re-run the loop from Step 3. Expected: still no `measure` finding.

Then render and look — a `max-width` on a list can strand a marker or narrow a
column the layout relied on, and no rule here measures that:

```bash
cd /data/abhi/projects/folio
for d in examples/quarterly-report examples/survey examples/runbook; do
  folio build "$d/document.html" --check
done
```

Open the `document.pages/` PNGs for those three and look at every page. If a
list or a table has visibly narrowed where it should not have, add it to the
exemption list in Step 4 rather than dropping the cap.

- [ ] **Step 6: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/assets/base.css
git commit -m "feat(css): --measure, and five documents come inside the canon

Body copy was running 92-110 characters a line in five of nine examples.
One token rather than five corrections: the defect is systemic, and five
separate fixes would have drifted apart by the next release.

Expressed in ch so it tracks whatever face and size a theme sets. Prose is
capped; figures, tables and the contents list keep the full width, because
capping everything leaves a ragged right edge that reads as a fault."
```

---

### Task 6: Leading, now that the column is narrow

**Files:**
- Modify: `src/folio/assets/base.css` (`--lh-body`)
- Modify: `src/folio/assets/themes/editorial.css`, `minimal.css`

**Interfaces:**
- Consumes: the narrowed column from Task 5. This task is only correct *after*
  it — leading at 1.48 on a 110-character line would be worse than what shipped.

This is the most taste-driven change in the phase and the easiest to reject on
its own. Current values, and the canon's 120–145% ceiling:

| theme | `--lh-body` now | proposed |
|---|---|---|
| base / report | 1.58 | 1.48 |
| minimal | 1.62 | 1.50 |
| editorial | 1.66 | 1.52 |
| technical | 1.46 | unchanged — already inside |

`editorial` stays highest on purpose: it sets the largest body size (10.2pt) and
is the most prose-heavy direction.

- [ ] **Step 1: Change the three values**

- `src/folio/assets/base.css`: `--lh-body: 1.58;` → `--lh-body: 1.48;`
- `src/folio/assets/themes/minimal.css:29`: `--lh-body: 1.62;` → `--lh-body: 1.50;`
- `src/folio/assets/themes/editorial.css:24`: `--lh-body: 1.66;` → `--lh-body: 1.52;`

- [ ] **Step 2: Run the suite**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: PASS. Watch for `thin-page` or `page-widow` findings appearing in any
example-based test — tighter leading means fewer pages, and a section that used
to fill its last page may now leave it short.

- [ ] **Step 3: Re-check the whole corpus**

Run:

```bash
cd /data/abhi/projects/folio
for d in examples/*/; do printf "%-20s %s\n" "$(basename $d)" \
  "$(folio check "$d/document.html" 2>/dev/null | tail -1)"; done
```

Expected: every example still reports no layout problems. If `thin-page` or
`page-widow` appears, that is a real consequence of the change: fix the page it
names, or revert this task and keep Task 5. **Do not exempt the rule.**

- [ ] **Step 4: Look at the pages**

Run: `cd /data/abhi/projects/folio && folio build examples/case-study/document.html --check`

Open `examples/case-study/document.pages/` and compare against the same document
before this task (`git stash` it if you need them side by side). The question is
whether the block of text reads as one colour or as stripes. If tighter leading
made it look cramped at this measure, revert; the measure change is the one that
had to happen and this one is optional.

- [ ] **Step 5: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/assets/base.css src/folio/assets/themes
git commit -m "style(themes): leading comes back down, now that the column is narrow

1.58 to 1.48 in the base, 1.62 to 1.50 in minimal, 1.66 to 1.52 in
editorial. Those numbers were never a choice about rhythm — they were
compensation for a 110-character line, which is what a designer reaches for
when the column is too wide to fix. The column is fixed, so the
compensation goes. technical was already at 1.46 and is untouched."
```

---

### Task 7: Hyphenation limits

**Files:**
- Modify: `src/folio/assets/base.css`

**Interfaces:**
- Consumes: nothing. Independent of Tasks 5 and 6.
- Produces: nothing.

Insurance, not a repair. Measured across all nine examples: the longest hyphen
ladder is **one** line and runts are at most two per document. The changelog
must say that rather than imply it fixed something.

- [ ] **Step 1: Add the limits**

In `src/folio/assets/base.css`, in the `body` rule, change:

```css
  hyphens: auto;
  text-align: justify;
```

to:

```css
  hyphens: auto;
  /* Insurance. Nothing in the corpus shows a ladder — the worst is a single
     hyphenated line — but justified text with unbounded hyphenation is one
     narrow column away from a stack of them. Six letters minimum, three
     before the break and three after: shorter than that and the hyphen costs
     more than the fit it buys. */
  hyphenate-limit-chars: 6 3 3;
  text-align: justify;
```

- [ ] **Step 2: Verify nothing regressed**

Run: `cd /data/abhi/projects/folio && python -m pytest -q`
Expected: PASS.

Then confirm the property is actually doing something on this renderer rather
than silently parsing — the same control the spec used for hanging punctuation:

```bash
cd /data/abhi/projects/folio && python - <<'PY'
from weasyprint import HTML
def text(css):
    doc = HTML(string=f"<style>@page{{size:60mm 100mm;margin:5mm}}"
               f"p{{hyphens:auto;font-size:9pt;{css}}}</style>"
               f'<p lang="en">extraordinary complications notwithstanding</p>').render()
    def walk(b):
        yield b
        for c in getattr(b, "children", ()) or (): yield from walk(c)
    return "".join(t.text for t in walk(doc.pages[0]._page_box)
                   if type(t).__name__ == "TextBox")
print("unlimited:", repr(text("")))
print("limited:  ", repr(text("hyphenate-limit-chars:6 3 3")))
PY
```

Expected: the two differ. If they are identical, the property no-ops on this
renderer and this task should be dropped rather than shipped as a claim — say so
in the changelog instead.

- [ ] **Step 3: Commit**

```bash
cd /data/abhi/projects/folio
git add src/folio/assets/base.css
git commit -m "feat(css): bound the hyphenation, before there is a ladder to fix

Insurance. The corpus's worst ladder is a single hyphenated line, so this
repairs nothing; justified text with unbounded hyphenation is simply one
narrow column away from a stack of them, and the column just got narrower."
```

---

### Task 8: The look pass, and the changelog

**Files:**
- Modify: `CHANGELOG.md`
- Modify: any example a page turns out to need

**Interfaces:**
- Consumes: everything above.

A green suite is not evidence about how a page looks. The 0.7.0 look pass found
four false numbers that every rule had passed; this phase changed the measure
and the leading of every document folio ships, so this pass matters more, not
less.

- [ ] **Step 1: Render every example**

```bash
cd /data/abhi/projects/folio
for d in examples/*/; do
  folio build "$d/document.html" --check
  folio preview "$d/document.pdf"
done
```

`build --check` measures; `preview` is what writes one PNG per page into
`<name>.pages/`. Run both — the whole point of this task is the pass that reads
them.

- [ ] **Step 2: Look at all thirty-one pages**

Open each `examples/*/document.pages/*.png` and look at it. Specifically:

- Does the measured column read as a decision or as an accident? A page where
  prose stops at 68ch beside a full-width table should look composed; if the
  right-hand white looks like a mistake, the figure beside it may need to move.
- Are quotation marks the right way round everywhere Task 4 touched?
- Did any page gain or lose a line and strand a heading at its foot?

Fix what you find in the example source, not by exempting a rule.

- [ ] **Step 3: Confirm the corpus is clean**

```bash
cd /data/abhi/projects/folio
for d in examples/*/; do printf "%-20s %s\n" "$(basename $d)" \
  "$(folio check "$d/document.html" 2>/dev/null | tail -1)"; done
python -m pytest -q
```

Expected: "No layout problems found." on all nine, and a green suite.

- [ ] **Step 4: Write the changelog entry**

In `CHANGELOG.md`, under `## [Unreleased]`, above the existing
`### Investigated — the ubuntu · py3.10 two-byte difference` section, add:

```markdown
### Added — four rules that read the characters, not the geometry
Every rule folio had measured a box. These read what was typed, which is the
first thing a reader sees and the last thing a layout tree can tell you about.

- **`straight-quote`** — a repair. Thirty-three straight marks across seven
  examples and six across three scaffolds, almost all of them possessives
  (`Meridian's`, `Halloran's`), plus one heading set large reading
  `What "done" means for Q4`. In a serif face a straight apostrophe is a foot
  mark. All of it shipped through seven releases under a green check. Marks
  after a digit are left alone — `5' 10"` is feet and inches — and code
  elements are exempt, on the evidence of folio's own runbook.
- **`measure`** — a repair. Body copy ran 92–110 characters a line in five of
  the nine examples, against a 45–90 canon. Reported once per document.
- **`dash`** and **`dot-ellipsis`** — insurance, and named as such. The corpus
  contains neither defect. They are here so the next document cannot introduce
  what this one avoided by luck. There is deliberately **no rule for the spaced
  hyphen**: the one occurrence in the corpus is `SELECT now() - last_replay`,
  a real minus inside `<code>`.

### Changed — the measure, and the leading that was compensating for it
`--measure` caps prose at 68ch; figures, tables and the contents list keep the
full width. The five over-wide documents now measure 73–86 characters. Leading
came back with it — 1.58 → 1.48 in the base, 1.62 → 1.50 in `minimal`,
1.66 → 1.52 in `editorial` — because those numbers were never a decision about
rhythm, but what a designer reaches for when the column is too wide to fix.
`technical` was already at 1.46 and is untouched.

**Every shipped example looks different as a result.** All thirty-one pages
were rendered and read one at a time before this went out; `folio check` cannot
see a column that is merely ugly.

Hyphenation is now bounded (`hyphenate-limit-chars: 6 3 3`). Also insurance: the
worst ladder in the corpus is a single hyphenated line.
```

- [ ] **Step 5: Commit**

```bash
cd /data/abhi/projects/folio
git add CHANGELOG.md examples
git commit -m "docs(changelog): the floor, and what it moved

Two repairs and three pieces of insurance, labelled as which. Every
example looks different: the measure changed and the leading came back
with it, and all thirty-one pages were read before this went out."
```

---

## What this phase deliberately does not do

- **No `font-fallback` rewrite.** That is Phase 2, and it replaces a rule
  rather than adding one.
- **No footnotes, recto/verso, bleed, or PDF conformance.** Phase 3.
- **No hanging punctuation, drop caps, or old-style figures.** Measured
  unsupported or unavailable in the installed faces; see the spec's non-goals.
