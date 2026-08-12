"""folio command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__

EPILOG = """\
examples:
  folio doctor                     check this machine and print exact fixes
  folio init                       scaffold document.html + charts.py here
  folio build document.html        render document.pdf + document.page.html
  folio build doc.html -o out.pdf  choose the output path
  folio build doc.html --check     render, measure, and lay out the pages to read
  folio preview document.pdf       one PNG per page — then actually look at them
  folio components                 the component vocabulary (read before authoring)
  folio css                        path to the design system stylesheet

docs: https://github.com/abhirajsingh101/folio
"""


def _print_pages(pdf: Path) -> None:
    """Lay the pages out and say where they are.

    The checker measures geometry, contrast and conformance; it cannot see that
    a chart is the wrong type or a caption states the obvious. Only reading the
    pages catches that, and it is the pass that gets skipped — so the images
    are produced here rather than behind a command nobody runs.
    """
    from .preview import render_pages

    pages = render_pages(pdf)
    if not pages:
        return
    print(f"\n  pages     {pages[0].parent}  ({len(pages)} png)")
    print("            read every one — the checker cannot see taste")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="folio",
        description="Print-ready documents from HTML — one design system, no AI slop.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"folio {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    sub.add_parser("doctor", help="check dependencies and print platform-specific fixes")

    i = sub.add_parser("init", help="scaffold a new document")
    i.add_argument("dir", nargs="?", default=".", help="target directory (default: .)")
    i.add_argument("--force", action="store_true", help="overwrite existing files")
    i.add_argument("--theme", help="design direction (see `folio themes`)")

    b = sub.add_parser("build", help="render a document to PDF")
    b.add_argument("file", help="source .html document")
    b.add_argument("-o", "--out", help="output PDF path")
    b.add_argument("--no-html", action="store_true", help="skip the standalone HTML page")
    b.add_argument(
        "--renderer",
        choices=["weasyprint", "chromium"],
        help="force a renderer (default: best available)",
    )
    b.add_argument(
        "--check", action="store_true", help="measure the rendered layout and report defects"
    )
    b.add_argument("-q", "--quiet", action="store_true")

    f = sub.add_parser("fonts", help="check font coverage for a document's scripts")
    f.add_argument("file", nargs="?", help="document to inspect (default: whole system)")

    c = sub.add_parser("check", help="measure the rendered layout for real defects")
    c.add_argument("file", help="source .html document")
    c.add_argument("--strict", action="store_true", help="fail on warnings too")

    from .preview import PREVIEW_DPI

    v = sub.add_parser("preview", help="render a built PDF to one PNG per page, and look at them")
    v.add_argument("file", help="built .pdf (or the .html it came from)")
    v.add_argument("--dpi", type=int, default=PREVIEW_DPI, help=f"default {PREVIEW_DPI}")

    sub.add_parser("themes", help="list the available design directions")
    sub.add_parser("components", help="print the component vocabulary")
    sub.add_parser("gotchas", help="print the renderer gotchas reference")
    sub.add_parser("css", help="print the path to the design system stylesheet")
    return p


def _force_utf8_output() -> None:
    """Windows consoles default to a legacy codepage (cp1252).

    folio prints script names, status marks and non-Latin text, none of which
    survive that. Without this a Korean or Japanese document cannot even be
    reported on, let alone built.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - exotic streams
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    args = _parser().parse_args(argv)

    if args.cmd is None:
        _parser().print_help()
        return 0

    if args.cmd == "doctor":
        from . import doctor

        checks, can_render = doctor.run()
        doctor.report(checks, can_render)
        return 0 if can_render else 1

    if args.cmd == "check":
        from .build import BuildError, prepare
        from .check import ERROR, CheckUnavailable, inspect, summarise

        src = Path(args.file)
        try:
            doc, _ = prepare(src)
            findings = inspect(doc, src.parent)
        except (BuildError, CheckUnavailable) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"folio check — {src.name}\n")
        for f in findings:
            print(f)
            if f.hint:
                print(f"        → {f.hint}")
        print(f"\n{summarise(findings)}")
        errors = [f for f in findings if f.severity == ERROR]
        return 1 if errors or (args.strict and findings) else 0

    if args.cmd == "fonts":
        from . import doctor as D

        if args.file:
            src = Path(args.file)
            if not src.exists():
                sys.exit(f"not found: {src}")
            print(f"folio fonts — {src.name}\n")
            checks = D.check_document_fonts(src.read_text(encoding="utf-8"))
        else:
            print("folio fonts — system\n")
            checks = [D.check_fonts()]
        for c in checks:
            print(f"  {D._MARK[c.status]} {c.name:<18} {c.detail}".rstrip())
        gaps = [c for c in checks if c.status == D.FAIL]
        if gaps:
            print("\nTo fix:")
            for line in dict.fromkeys(x for c in gaps for x in c.fix):
                print(f"    {line}")
        else:
            print("\nEvery script in this document has a font that covers it.")
        return 1 if gaps else 0

    if args.cmd == "themes":
        from .assets import DEFAULT_THEME, theme_names

        blurb = {
            "report": "corporate and confident; serif body, soft filled surfaces",
            "editorial": "magazine; large serif display, rules not fills, wide gutters",
            "technical": "dense engineering memo; small sans, monospace labels, boxed tables",
            "minimal": "Swiss; sans throughout, near-monochrome, space instead of borders",
        }
        for t in theme_names():
            mark = "  (default)" if t == DEFAULT_THEME else ""
            print(f"  {t:<11} {blurb.get(t, '')}{mark}")
        print('\nSet with `folio init --theme <name>`, or <body data-theme="<name>">.')
        return 0

    if args.cmd == "css":
        from .assets import css_path

        print(css_path())
        return 0

    if args.cmd in ("components", "gotchas"):
        from .assets import doc_text

        name = "COMPONENTS.md" if args.cmd == "components" else "GOTCHAS.md"
        print(doc_text(name))
        return 0

    if args.cmd == "init":
        from .assets import DEFAULT_THEME, theme_names
        from .build import init

        theme = args.theme or DEFAULT_THEME
        if theme not in theme_names():
            sys.exit(f"unknown theme {theme!r} — choose from: {', '.join(theme_names())}")
        target = Path(args.dir).resolve()
        init(target, force=args.force, theme=theme)
        print(f"\nNext:  folio build {Path(args.dir) / 'document.html'}")
        return 0

    if args.cmd == "build":
        from .build import BuildError, build, prepare
        from .renderers import RenderError

        src = Path(args.file)
        if not args.quiet:
            print(f"folio  {src.name}")
        try:
            build(
                src,
                Path(args.out) if args.out else None,
                also_html=not args.no_html,
                prefer=args.renderer,
                quiet=args.quiet,
            )
        except (BuildError, RenderError) as e:
            print(f"\nerror: {e}", file=sys.stderr)
            return 1
        if args.check:
            from .check import ERROR, CheckUnavailable, inspect, summarise

            try:
                doc, _ = prepare(src)
                findings = inspect(doc, src.resolve().parent)
            except CheckUnavailable as e:
                print(f"\n  ! check skipped: {e}")
                return 0
            print()
            for f in findings:
                print(f)
                if f.hint:
                    print(f"        → {f.hint}")
            print(f"  {summarise(findings)}")
            _print_pages(src.resolve().with_suffix(".pdf") if not args.out else Path(args.out))
            return 1 if any(f.severity == ERROR for f in findings) else 0
        return 0

    if args.cmd == "preview":
        src = Path(args.file)
        pdf = src if src.suffix.lower() == ".pdf" else src.with_suffix(".pdf")
        if not pdf.exists():
            print(f"error: {pdf} does not exist — run `folio build` first", file=sys.stderr)
            return 1
        from .preview import render_pages

        pages = render_pages(pdf, dpi=args.dpi)
        if not pages:
            print("error: could not render pages — is poppler installed?", file=sys.stderr)
            return 1
        print(f"folio preview — {pdf.name}\n")
        for page in pages:
            print(f"  {page}")
        return 0

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
