"""Build a source document into a PDF (and a self-contained HTML page).

The kit stylesheet is injected at build time, so a project's source file never
links it and never drifts from it. A project-local `brand.css` beside the
source is appended afterwards and therefore always wins.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .assets import DEFAULT_THEME, css_text, template_text, theme_names
from .renderers import Renderer, pick

SKELETON = """<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8"><title>{title}</title></head>
<body data-title="{title}" data-footer="">
{body}
</body></html>"""

_HANGUL = re.compile(r"[가-힣]")
_THEME_ATTR = re.compile(r"<body[^>]*\bdata-theme=[\"']([\w-]+)[\"']", re.I)


class BuildError(RuntimeError):
    pass


@dataclass
class Result:
    pdf: Path
    page: Path | None
    renderer: str
    degraded: bool


def detect_theme(html: str) -> str:
    """Themes are declared on <body data-theme=…>, so a document is self-describing."""
    m = _THEME_ATTR.search(html)
    if not m:
        return DEFAULT_THEME
    name = m.group(1)
    if name not in theme_names():
        raise BuildError(
            f"unknown theme {name!r} in <body data-theme=…>\n"
            f"  available: {', '.join(theme_names())}"
        )
    return name


def _stylesheet(src: Path, theme: str) -> str:
    css = css_text(theme)
    brand = src.parent / "brand.css"
    if brand.exists():
        css += f"\n\n/* ── project brand.css ── */\n{brand.read_text(encoding='utf-8')}"
    return css


def _wrap(html: str, src: Path) -> str:
    if "<html" in html.lower():
        return html
    title = src.stem.replace("-", " ").replace("_", " ").title()
    lang = "ko" if _HANGUL.search(html) else "en"
    return SKELETON.format(lang=lang, title=title, body=html)


def _inject(html: str, css: str) -> str:
    tag = f"<style>\n{css}\n</style>"
    if "</head>" in html:
        return html.replace("</head>", f"{tag}\n</head>", 1)
    return tag + html


def run_charts(src: Path, quiet: bool = False, theme: str = DEFAULT_THEME) -> None:
    """Run a sibling charts.py first so figures are never stale.

    The theme is passed through the environment so `theme.use()` picks the
    matching palette without the author wiring anything up.
    """
    script = src.parent / "charts.py"
    if not script.exists():
        return
    if not quiet:
        print(f"  charts    {script.name}")
    env = {**os.environ, "FOLIO_THEME": theme}
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode:
        raise BuildError(f"charts.py failed:\n{r.stdout}\n{r.stderr}")


def _embed_assets(html: str, base: Path) -> str:
    """Inline local images as data URIs so the HTML output is self-contained."""

    def repl(m: re.Match) -> str:
        pre, url, post = m.group(1), m.group(2), m.group(3)
        if url.startswith(("data:", "http:", "https:", "//")):
            return m.group(0)
        f = (base / url).resolve()
        if not f.exists():
            return m.group(0)
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return f"{pre}data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}{post}"

    return re.sub(r'(<img[^>]+src=")([^"]+)(")', repl, html)


def build(
    src: Path,
    out: Path | None = None,
    *,
    also_html: bool = True,
    prefer: str | None = None,
    quiet: bool = False,
) -> Result:
    src = src.resolve()
    if not src.exists():
        raise BuildError(f"not found: {src}")

    renderer: Renderer = pick(prefer)
    raw = src.read_text(encoding="utf-8")
    theme = detect_theme(raw)
    run_charts(src, quiet, theme)

    doc = _inject(_wrap(raw, src), _stylesheet(src, theme))
    if not quiet:
        print(f"  theme     {theme}")

    pdf = (out or src.with_suffix(".pdf")).resolve()
    if pdf == src:
        raise BuildError("output would overwrite the source document")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    renderer.render(doc, src.parent, pdf)
    if not quiet:
        print(f"  pdf       {pdf}")

    page = None
    if also_html:
        page = pdf.with_name(pdf.stem + ".page.html")
        if page == src:  # never clobber the source
            page = pdf.with_name(pdf.stem + ".standalone.html")
        page.write_text(_embed_assets(doc, src.parent), encoding="utf-8")
        if not quiet:
            print(f"  page      {page}")

    degraded = not renderer.full_print_support
    if degraded and not quiet:
        print(
            f"\n  ! rendered with {renderer.name}: running headers, page numbers and\n"
            f"    table-of-contents page references are NOT supported by this\n"
            f"    renderer. Run `folio doctor` to enable WeasyPrint."
        )
    return Result(pdf, page, renderer.name, degraded)


def init(target: Path, *, force: bool = False, theme: str = DEFAULT_THEME) -> list[Path]:
    """Scaffold a document beside whatever project you are in."""
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for tpl, name in (("starter.html", "document.html"), ("starter_charts.py", "charts.py")):
        dst = target / name
        if dst.exists() and not force:
            print(f"  skip      {name} (exists — use --force to overwrite)")
            continue
        body = template_text(tpl)
        if name == "document.html" and theme != DEFAULT_THEME:
            body = body.replace("<body data-title=", f'<body data-theme="{theme}" data-title=')
        dst.write_text(body, encoding="utf-8")
        print(f"  create    {dst}")
        written.append(dst)
    return written
