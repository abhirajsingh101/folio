"""Locate packaged assets without assuming where folio was installed.

Everything resolves relative to this module, so folio works identically from a
source checkout, an editable install, a wheel, or a zipapp.

The stylesheet is composed at build time from two layers: `base.css`, which is
structure and never varies, and one theme from `themes/`, which is look. See
base.css for the token contract between them.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

_ROOT = files(__package__)

DEFAULT_THEME = "report"


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


def template_text(name: str) -> str:
    return asset_path("templates", name).read_text(encoding="utf-8")


def doc_text(name: str) -> str:
    """Reference docs ship with the wheel so `folio components` works offline."""
    packaged = asset_path("docs", name)
    if packaged.exists():
        return packaged.read_text(encoding="utf-8")
    repo = Path(__file__).resolve().parents[3] / "docs" / name
    if repo.exists():
        return repo.read_text(encoding="utf-8")
    raise FileNotFoundError(f"reference doc not found: {name}")
