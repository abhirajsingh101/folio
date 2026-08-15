"""HTML -> PDF, with a fallback so a missing native library never means no output.

WeasyPrint is the intended renderer: it implements the CSS paged-media features
this design system relies on (`@page` margin boxes for running headers and page
counters, named pages, `target-counter` for table-of-contents page numbers).

Chromium implements almost none of that. It is here so that a machine without
Pango still produces a document — degraded, and loudly labelled as such —
rather than a traceback.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import pathname2url


class RenderError(RuntimeError):
    pass


class Renderer:
    name = "base"
    #: whether @page margin boxes, target-counter and named pages work
    full_print_support = False

    def available(self) -> bool:  # pragma: no cover - trivial
        raise NotImplementedError

    def render(
        self, html: str, base_dir: Path, out: Path, variant: str | None = None
    ) -> None:  # pragma: no cover
        raise NotImplementedError


class WeasyRenderer(Renderer):
    name = "weasyprint"
    full_print_support = True

    def available(self) -> bool:
        try:
            import weasyprint  # noqa: F401

            return True
        except Exception:
            return False

    def render(self, html: str, base_dir: Path, out: Path, variant: str | None = None) -> None:
        from weasyprint import HTML

        # Metadata comes from the document's own <head> — WeasyPrint reads
        # <title>, and the author/description/keywords meta tags — so there is
        # nothing to pass here for it. `pdf_variant` is the one thing a
        # document cannot express in markup.
        options = {"pdf_variant": variant} if variant else {}
        HTML(string=html, base_url=str(base_dir)).write_pdf(out, **options)


class ChromiumRenderer(Renderer):
    name = "chromium"
    full_print_support = False

    def __init__(self) -> None:
        from .doctor import find_chrome

        self._bin = find_chrome()

    def available(self) -> bool:
        return self._bin is not None

    def render(
        self, html: str, base_dir: Path, out: Path, variant: str | None = None
    ) -> None:
        # `variant` is accepted and ignored: Chromium's print-to-PDF has no
        # PDF/A or PDF/UA mode. A document that asks for one and is rendered
        # here silently gets an ordinary PDF, which is the same bargain the
        # rest of this renderer makes — `build` already warns that running
        # headers, page numbers and contents references are missing too.
        if not self._bin:
            raise RenderError("no Chromium binary found")
        # write beside the source so relative asset paths still resolve
        with tempfile.NamedTemporaryFile(
            "w", suffix=".folio.html", dir=base_dir, delete=False, encoding="utf-8"
        ) as fh:
            fh.write(html)
            tmp = Path(fh.name)
        try:
            url = urljoin("file:", pathname2url(str(tmp.resolve())))
            if self._bin == "playwright":
                self._via_playwright(url, out)
            else:
                self._via_binary(url, out)
        finally:
            tmp.unlink(missing_ok=True)

    def _via_playwright(self, url: str, out: Path) -> None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto(url, wait_until="networkidle")
            page.pdf(
                path=str(out),
                format="A4",
                print_background=True,
                margin={"top": "20mm", "bottom": "18mm", "left": "18mm", "right": "18mm"},
            )
            b.close()

    # Headless Chrome will sit forever on a CI runner unless it is told not to
    # phone home, not to wait on the network, and to give up on its own. Both
    # spellings of the header flag are passed because Chrome ignores switches
    # it does not recognise — cheaper than probing the version, and it avoids
    # a retry that would double the worst-case hang.
    _FLAGS = [
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--disable-dev-shm-usage",
        "--metrics-recording-only",
        "--mute-audio",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        "--timeout=30000",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
    ]

    def _via_binary(self, url: str, out: Path) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            cmd = [
                self._bin,
                *self._FLAGS,
                f"--user-data-dir={profile}",
                f"--print-to-pdf={out}",
                url,
            ]
            try:
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=45,
                    encoding="utf-8",
                    errors="replace",
                )
            except subprocess.TimeoutExpired as e:
                raise RenderError(
                    "chromium hung while printing and was killed after 45s.\n"
                    "  Command-line printing is unreliable on some hosts. Either\n"
                    "  `pip install playwright && playwright install chromium`,\n"
                    "  or install WeasyPrint. Run `folio doctor`."
                ) from e
            if not out.exists():
                raise RenderError(
                    f"chromium exited {r.returncode} without producing a PDF:\n"
                    f"{(r.stderr or r.stdout)[-800:]}"
                )


def pick(prefer: str | None = None) -> Renderer:
    """The best renderer available, or the one explicitly asked for."""
    candidates = [WeasyRenderer(), ChromiumRenderer()]
    if prefer:
        for c in candidates:
            if c.name == prefer:
                if not c.available():
                    raise RenderError(f"renderer '{prefer}' is not available — run `folio doctor`")
                return c
        raise RenderError(
            f"unknown renderer '{prefer}' (choose from: {', '.join(c.name for c in candidates)})"
        )
    for c in candidates:
        if c.available():
            return c
    raise RenderError(
        "No renderer available.\n"
        "  WeasyPrint needs system libraries pip cannot install, and no\n"
        "  Chromium-family browser was found. Run `folio doctor` for the fix."
    )


def has_pdftoppm() -> bool:
    """Used by `folio preview`; optional."""
    return shutil.which("pdftoppm") is not None
