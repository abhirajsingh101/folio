"""Locate packaged assets without assuming where folio was installed.

Everything resolves relative to this module, so folio works identically from a
source checkout, an editable install, a wheel, or a zipapp.

The stylesheet is composed at build time from two layers: `base.css`, which is
structure and never varies, and one theme from `themes/`, which is look. See
base.css for the token contract between them.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

_ROOT = files(__package__)

DEFAULT_THEME = "report"
DEFAULT_TEMPLATE = "report"

# Reference docs the CLI prints. Kept here rather than in cli.py so the wheel
# packaging can be tested against the same list: `doc_text` falls back to the
# repo, so a doc missing from the build only breaks for people who installed
# from PyPI.
SERVED_DOCS = {
    "components": "COMPONENTS.md",
    "gotchas": "GOTCHAS.md",
    "imagery": "IMAGERY.md",
}


def asset_path(*parts: str) -> Path:
    """Filesystem path to a packaged asset."""
    p = _ROOT
    for part in parts:
        p = p / part
    return Path(str(p))


def theme_names() -> list[str]:
    """Every installed design direction, default first."""
    found = sorted(p.stem for p in asset_path("themes").glob("*.css"))
    if DEFAULT_THEME in found:
        found.remove(DEFAULT_THEME)
        found.insert(0, DEFAULT_THEME)
    return found


def theme_path(name: str) -> Path:
    p = asset_path("themes", f"{name}.css")
    if not p.exists():
        raise ValueError(f"unknown theme {name!r} — choose from: {', '.join(theme_names())}")
    return p


def base_path() -> Path:
    return asset_path("base.css")


def css_path() -> Path:
    """Kept for `folio css`; points at the structural layer."""
    return base_path()


def rtl_path() -> Path:
    return asset_path("rtl.css")


def css_text(theme: str = DEFAULT_THEME, rtl: bool = False) -> str:
    """The full stylesheet: structure, the chosen look, then RTL if needed."""
    css = (
        f"/* ── folio base (structure) ── */\n{base_path().read_text(encoding='utf-8')}\n\n"
        f"/* ── folio theme: {theme} ── */\n{theme_path(theme).read_text(encoding='utf-8')}"
    )
    if rtl:
        css += f"\n\n/* ── folio rtl mirror ── */\n{rtl_path().read_text(encoding='utf-8')}"
    return css


def template_names() -> list[str]:
    """Every installed scaffold, default first.

    Discovery is a glob, so a new document type is a new folder — nothing to
    register in code and nothing that can be half-added. What the folder cannot
    carry is a description, which is why the manifest exists beside it.
    """
    found = sorted(p.parent.name for p in asset_path("templates").glob("*/document.html"))
    if DEFAULT_TEMPLATE in found:
        found.remove(DEFAULT_TEMPLATE)
        found.insert(0, DEFAULT_TEMPLATE)
    return found


def template_path(name: str) -> Path:
    p = asset_path("templates", name)
    if not (p / "document.html").exists():
        raise ValueError(f"unknown template {name!r} — choose from: {', '.join(template_names())}")
    return p


def template_files(name: str) -> list[Path]:
    """Everything a scaffold ships, in the order it should be written.

    The files are named for where they land, so `init` copies rather than
    maps: a scaffold with no charts simply has no `charts.py`, instead of the
    caller knowing which types own which files.
    """
    return sorted(p for p in template_path(name).iterdir() if p.is_file())


def template_blurb(name: str) -> str:
    """The one line `folio templates` prints. Kept in a manifest beside the
    scaffolds so adding a folder without describing it fails the suite."""
    manifest = json.loads(asset_path("templates", "manifest.json").read_text(encoding="utf-8"))
    return manifest.get(name, "")


def template_text(name: str, filename: str) -> str:
    return (template_path(name) / filename).read_text(encoding="utf-8")


def doc_text(name: str) -> str:
    """Reference docs ship with the wheel so `folio components` works offline."""
    packaged = asset_path("docs", name)
    if packaged.exists():
        return packaged.read_text(encoding="utf-8")
    repo = Path(__file__).resolve().parents[3] / "docs" / name
    if repo.exists():
        return repo.read_text(encoding="utf-8")
    raise FileNotFoundError(f"reference doc not found: {name}")
