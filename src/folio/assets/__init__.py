"""Locate packaged assets without assuming where folio was installed.

Everything resolves relative to this module, so folio works identically from a
source checkout, an editable install, a wheel, or a zipapp.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

_ROOT = files(__package__)


def asset_path(*parts: str) -> Path:
    """Filesystem path to a packaged asset."""
    p = _ROOT
    for part in parts:
        p = p / part
    return Path(str(p))


def css_path() -> Path:
    return asset_path("folio.css")


def css_text() -> str:
    return css_path().read_text(encoding="utf-8")


def template_text(name: str) -> str:
    return asset_path("templates", name).read_text(encoding="utf-8")


def doc_text(name: str) -> str:
    """Reference docs are shipped with the wheel so `folio components` works offline."""
    packaged = asset_path("docs", name)
    if packaged.exists():
        return packaged.read_text(encoding="utf-8")
    # source checkout: docs/ lives at the repo root
    repo = Path(__file__).resolve().parents[3] / "docs" / name
    if repo.exists():
        return repo.read_text(encoding="utf-8")
    raise FileNotFoundError(f"reference doc not found: {name}")
