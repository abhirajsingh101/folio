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

from .assets import DEFAULT_TEMPLATE, DEFAULT_THEME, css_text, template_files, theme_names
from .renderers import Renderer, pick
from .scripts import Profile, script_font_css
from .scripts import detect as detect_scripts

SKELETON = """<!DOCTYPE html>
<html lang="{lang}" dir="{dir}"><head><meta charset="utf-8"><title>{title}</title></head>
<body data-title="{title}" data-footer="">
{body}
</body></html>"""
_THEME_ATTR = re.compile(r"<body[^>]*\bdata-theme=[\"']([\w-]+)[\"']", re.I)


class BuildError(RuntimeError):
    pass


@dataclass
class Result:
    pdf: Path
    page: Path | None
    renderer: str
    degraded: bool
    profile: Profile | None = None


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


_PDF_ATTR = re.compile(r"<body[^>]*\bdata-pdf=[\"']([\w/.-]+)[\"']", re.I)

# What a document can ask to be. The two aliases are the cases that actually
# come up — a deliverable that must survive in an archive, and one that must be
# readable by assistive technology — and the raw variant names are accepted for
# anyone who knows exactly which conformance level they are being asked for.
#
# `folio` declares; it does not certify. WeasyPrint states that its output is
# not guaranteed to satisfy these specifications, so what a `data-pdf` document
# gets is a file that identifies itself correctly and is structured to have a
# chance of validating. Run a validator before promising anyone else.
PDF_VARIANTS = {
    "archival": "pdf/a-3b",
    "accessible": "pdf/ua-1",
}
_RAW_VARIANTS = frozenset(
    {
        "pdf/a-1b", "pdf/a-2b", "pdf/a-3b", "pdf/a-4b",
        "pdf/a-2u", "pdf/a-3u", "pdf/a-4u",
        "pdf/ua-1",
    }
)


def detect_pdf_variant(html: str) -> str | None:
    """What kind of PDF this document says it needs to be.

    A document property rather than a build flag, for the same reason
    `data-furniture` is one: an invoice is an invoice wherever it is rebuilt,
    and a flag has to be remembered every time. An archival deliverable that
    only conforms when someone remembers the flag is not an archival
    deliverable.
    """
    m = _PDF_ATTR.search(html)
    if not m:
        return None
    asked = m.group(1).lower()
    if asked in PDF_VARIANTS:
        return PDF_VARIANTS[asked]
    if asked in _RAW_VARIANTS:
        return asked
    raise BuildError(
        f"unknown PDF variant {asked!r} in <body data-pdf=…>\n"
        f"  aliases: {', '.join(sorted(PDF_VARIANTS))}\n"
        f"  variants: {', '.join(sorted(_RAW_VARIANTS))}"
    )


def _stylesheet(src: Path, theme: str, prof: Profile | None = None) -> str:
    """Kit, then the document's own scripts, then the project's brand.

    Order is the whole point: each layer must be able to override the one
    before it. Script faces sit between the two because a document does not
    choose its writing system, while a `brand.css` that names a face has
    chosen deliberately and must win.
    """
    css = css_text(theme, rtl=bool(prof and prof.is_rtl))
    if prof is not None:
        script_css = script_font_css(prof)
        if script_css:
            css += f"\n\n{script_css}"
    brand = src.parent / "brand.css"
    if brand.exists():
        css += f"\n\n/* ── project brand.css ── */\n{brand.read_text(encoding='utf-8')}"
    return css


def _wrap(html: str, src: Path, prof: Profile) -> str:
    """Wrap a fragment, or stamp lang/dir onto a full document that omits them."""
    if "<html" in html.lower():
        if not re.search(r"<html[^>]*\blang=", html, re.I):
            html = re.sub(r"<html\b", f'<html lang="{prof.lang}"', html, count=1, flags=re.I)
        if prof.is_rtl and not re.search(r"<html[^>]*\bdir=", html, re.I):
            html = re.sub(r"<html\b", '<html dir="rtl"', html, count=1, flags=re.I)
        return html
    title = src.stem.replace("-", " ").replace("_", " ").title()
    return SKELETON.format(lang=prof.lang, dir=prof.direction, title=title, body=html)


_FOOTNOTE = re.compile(r'(<span[^>]*\bclass="[^"]*\bfn\b[^"]*"[^>]*>)(.*?)(</span>)', re.S | re.I)


def flatten_footnotes(html: str) -> str:
    """Collapse whitespace inside a footnote before it is rendered.

    A renderer bug, worked around here because no stylesheet can reach it:
    WeasyPrint turns a newline inside a `float: footnote` element into a hard
    line break, so a note wrapped across two source lines sets as two ragged
    lines at the foot of the page. Confirmed as the renderer's rather than the
    kit's — `float: footnote` with no folio CSS at all does it, and the same
    text in a plain span does not.

    An author should be able to wrap a note in their editor like any other
    prose, so the whitespace is normalised at build time. Only whitespace runs
    are touched; markup inside the note is left exactly as written.
    """
    return _FOOTNOTE.sub(
        lambda m: m.group(1) + re.sub(r"\s+", " ", m.group(2)) + m.group(3), html
    )


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


def prepare(src: Path) -> tuple[str, str]:
    """Assemble the final HTML exactly as `build` would. Returns (html, theme).

    Shared so `folio check` measures the document that would actually ship,
    not an approximation of it.
    """
    src = src.resolve()
    if not src.exists():
        raise BuildError(f"not found: {src}")
    raw = src.read_text(encoding="utf-8")
    theme = detect_theme(raw)
    prof = detect_scripts(raw)
    run_charts(src, quiet=True, theme=theme)
    return _inject(_wrap(flatten_footnotes(raw), src, prof), _stylesheet(src, theme, prof)), theme


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
    prof = detect_scripts(raw)
    run_charts(src, quiet, theme)

    doc = _inject(_wrap(flatten_footnotes(raw), src, prof), _stylesheet(src, theme, prof))
    if not quiet:
        print(f"  theme     {theme}")
        print(f"  scripts   {prof.describe()}")

    pdf = (out or src.with_suffix(".pdf")).resolve()
    if pdf == src:
        raise BuildError("output would overwrite the source document")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    renderer.render(doc, src.parent, pdf, detect_pdf_variant(raw))
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
    return Result(pdf, page, renderer.name, degraded, prof)


def retheme(html: str, theme: str) -> str:
    """Point a document at a different design direction.

    Scaffolds declare their own — an invoice is `minimal`, a runbook is
    `technical` — so `--theme` rewrites a declaration rather than adding one.
    Adding a second `data-theme` would leave which one wins to the parser.
    """
    if _THEME_ATTR.search(html):
        return _THEME_ATTR.sub(lambda m: m.group(0).replace(m.group(1), theme, 1), html, count=1)
    return re.sub(r"<body\b", f'<body data-theme="{theme}"', html, count=1, flags=re.I)


def init(
    target: Path,
    *,
    force: bool = False,
    theme: str | None = None,
    template: str = DEFAULT_TEMPLATE,
) -> list[Path]:
    """Scaffold a document beside whatever project you are in.

    `theme` of None keeps whatever direction the scaffold was designed in.
    """
    files = template_files(template)  # before mkdir: an unknown type writes nothing
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for src in files:
        dst = target / src.name
        if dst.exists() and not force:
            print(f"  skip      {src.name} (exists — use --force to overwrite)")
            continue
        body = src.read_text(encoding="utf-8")
        if theme and src.suffix == ".html":
            body = retheme(body, theme)
        dst.write_text(body, encoding="utf-8")
        print(f"  create    {dst}")
        written.append(dst)
    return written
