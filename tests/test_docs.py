"""The documentation must describe the thing that actually ships.

Every guard in this suite until now pointed inwards, at the interface an agent
reads: the skill must route to every scaffold, every rule the checker emits
must be named in the skill. The outward-facing surfaces had none, and it showed
— `essay` shipped in 0.6.0 and the README went on offering six scaffolds until
0.6.2, through two releases and a reader's first screen.

These hold the other direction. None of them found a defect on the day they
were written, which is the point: this is the class of drift that arrives
quietly between releases, one addition at a time.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from folio.assets import base_path, css_text, theme_names

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
COMPONENTS = ROOT / "docs" / "COMPONENTS.md"


def _table(text: str, header: str) -> str:
    """One markdown table, from its header row to the blank line after it."""
    start = text.index(header)
    return text[start : start + text[start:].index("\n\n")]


def _documented_classes() -> set[str]:
    """Every class an author is shown using, across the HTML examples."""
    found: set[str] = set()
    for block in re.findall(r"```html\n(.*?)```", COMPONENTS.read_text(encoding="utf-8"), re.S):
        for attr in re.findall(r'class="([^"]+)"', block):
            found.update(attr.split())
    return found


def test_the_readme_theme_table_lists_every_theme():
    if not README.exists():  # pragma: no cover - sdist without the README
        pytest.skip("README not present")
    table = _table(README.read_text(encoding="utf-8"), "| theme | what it is |")
    missing = [t for t in theme_names() if f"`{t}`" not in table]
    assert not missing, f"the README theme table omits: {missing}"


def test_every_class_the_components_doc_shows_is_actually_styled():
    """A component that renders unstyled is worse than one that does not exist.

    `folio components` is what an agent reads before authoring, and it is taken
    literally. A class that was renamed in the CSS and left in the prose
    produces a document that builds, passes every check, and quietly loses the
    look of whatever the block was meant to be.
    """
    if not COMPONENTS.exists():  # pragma: no cover - sdist without docs
        pytest.skip("components doc not present")
    css = "\n".join(css_text(theme) for theme in theme_names())
    unstyled = sorted(c for c in _documented_classes() if f".{c}" not in css)
    assert not unstyled, f"documented but styled by no theme: {unstyled}"


def test_every_component_class_in_the_kit_is_documented():
    """The mirror: a class that ships and is never mentioned cannot be used.

    Anything defined at the top level of `base.css` is part of the vocabulary
    by construction — that file carries no look of its own, only structure — so
    an entry missing from `folio components` is a component nobody will reach
    for, and a component nobody reaches for is one the next author reinvents
    inline.
    """
    if not COMPONENTS.exists():  # pragma: no cover - sdist without docs
        pytest.skip("components doc not present")
    text = COMPONENTS.read_text(encoding="utf-8")
    defined = set(
        re.findall(r"^\.([a-z][a-z0-9-]+)", base_path().read_text(encoding="utf-8"), re.M)
    )
    missing = sorted(c for c in defined if c not in text)
    assert not missing, f"shipped in base.css, absent from `folio components`: {missing}"
