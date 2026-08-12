"""Tests that do not require a working renderer, plus renderer tests that skip."""

from __future__ import annotations

import shutil

import pytest

from folio import build as B
from folio.assets import css_path, css_text, doc_text, template_text
from folio.renderers import ChromiumRenderer, RenderError, WeasyRenderer, pick
from folio.scripts import detect as detect_scripts

HAS_WEASY = WeasyRenderer().available()
HAS_CHROME = ChromiumRenderer().available()
ANY_RENDERER = HAS_WEASY or HAS_CHROME


# ── assets resolve wherever folio is installed ────────────────────────────


def test_css_ships_and_is_nonempty():
    assert css_path().exists()
    assert "--brand" in css_text()


def test_templates_ship():
    assert "<!DOCTYPE html>" in template_text("starter.html")
    assert "from folio import theme" in template_text("starter_charts.py")


def test_reference_docs_resolve():
    assert "component vocabulary" in doc_text("COMPONENTS.md").lower()
    assert doc_text("GOTCHAS.md").strip()


def test_every_served_doc_resolves():
    from folio.assets import SERVED_DOCS

    for command, name in SERVED_DOCS.items():
        assert doc_text(name).strip(), f"`folio {command}` has nothing to print"


def test_every_served_doc_ships_in_the_wheel():
    """`doc_text` falls back to the repo when a doc is not packaged.

    That fallback is what makes this worth a test: forget the force-include
    and everything works locally and in CI, while `folio components` raises
    FileNotFoundError for everyone who installed from PyPI.
    """
    from pathlib import Path

    import tomllib

    from folio.assets import SERVED_DOCS

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if not pyproject.exists():  # pragma: no cover - installed without sources
        pytest.skip("pyproject not present")
    cfg = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    shipped = cfg["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for name in SERVED_DOCS.values():
        assert f"docs/{name}" in shipped, f"{name} would be missing from the wheel"


def test_starter_template_has_no_absolute_paths():
    """The scaffold must not assume where folio was installed."""
    text = template_text("starter_charts.py")
    assert ".local/share" not in text
    assert "Path.home()" not in text


# ── document assembly ─────────────────────────────────────────────────────


def test_fragment_gets_wrapped(tmp_path):
    src = tmp_path / "note.html"
    src.write_text("<p>hello</p>", encoding="utf-8")
    raw = src.read_text(encoding="utf-8")
    out = B._wrap(raw, src, detect_scripts(raw))
    assert out.startswith("<!DOCTYPE html>")
    assert 'lang="en"' in out
    assert "<p>hello</p>" in out


def test_korean_fragment_gets_ko_lang(tmp_path):
    src = tmp_path / "note.html"
    src.write_text("<p>액추에이터 보고서</p>", encoding="utf-8")
    raw = src.read_text(encoding="utf-8")
    assert 'lang="ko"' in B._wrap(raw, src, detect_scripts(raw))


def test_full_document_keeps_its_own_lang_and_dir(tmp_path):
    """An author's explicit declaration is never second-guessed."""
    src = tmp_path / "doc.html"
    html = '<!DOCTYPE html><html lang="fr" dir="ltr"><head></head><body>x</body></html>'
    src.write_text(html, encoding="utf-8")
    assert B._wrap(html, src, detect_scripts(html)) == html


def test_full_document_without_lang_gets_one_stamped(tmp_path):
    """Per-script line breaking keys off <html lang>, so it must be present."""
    src = tmp_path / "doc.html"
    html = "<!DOCTYPE html><html><head></head><body><p>これは日本語の文書です。</p></body></html>"
    src.write_text(html, encoding="utf-8")
    out = B._wrap(html, src, detect_scripts(html))
    assert 'lang="ja"' in out
    assert "<p>これは日本語の文書です。</p>" in out


def test_rtl_document_gets_dir_stamped(tmp_path):
    src = tmp_path / "doc.html"
    html = (
        "<!DOCTYPE html><html><head></head><body><p>هذا تقرير تجريبي عن الجودة.</p></body></html>"
    )
    src.write_text(html, encoding="utf-8")
    out = B._wrap(html, src, detect_scripts(html))
    assert 'dir="rtl"' in out and 'lang="ar"' in out


def test_css_injected_before_head_close():
    out = B._inject("<html><head><title>t</title></head><body></body></html>", "p{}")
    assert out.index("<style>") < out.index("</head>")


def test_brand_css_is_appended_after_kit(tmp_path):
    src = tmp_path / "doc.html"
    src.write_text("<p>x</p>", encoding="utf-8")
    (tmp_path / "brand.css").write_text(":root{--brand:#123456}", encoding="utf-8")
    css = B._stylesheet(src, "report")
    assert css.index("#003F87") < css.index("#123456"), "brand.css must be appended last"


def test_images_are_inlined_for_standalone_html(tmp_path):
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    out = B._embed_assets('<img src="a.png">', tmp_path)
    assert out.startswith('<img src="data:image/png;base64,')


def test_remote_and_data_urls_untouched(tmp_path):
    for url in ("https://x.test/a.png", "data:image/png;base64,AAAA"):
        html = f'<img src="{url}">'
        assert B._embed_assets(html, tmp_path) == html


# ── the bug that ate a source file ────────────────────────────────────────


@pytest.mark.skipif(not ANY_RENDERER, reason="no renderer available")
def test_build_never_overwrites_its_own_source(tmp_path):
    src = tmp_path / "doc.html"
    original = "<p>precious</p>"
    src.write_text(original, encoding="utf-8")
    B.build(src, quiet=True)
    assert src.read_text(encoding="utf-8") == original, "build clobbered the source document"


@pytest.mark.skipif(not ANY_RENDERER, reason="no renderer available")
def test_standalone_page_uses_a_distinct_name(tmp_path):
    src = tmp_path / "doc.html"
    src.write_text("<p>x</p>", encoding="utf-8")
    res = B.build(src, quiet=True)
    assert res.page is not None
    assert res.page != src
    assert res.page.name == "doc.page.html"


def test_explicit_output_equal_to_source_is_refused(tmp_path):
    src = tmp_path / "doc.html"
    src.write_text("<p>x</p>", encoding="utf-8")
    with pytest.raises(B.BuildError, match="overwrite the source"):
        B.build(src, out=src, quiet=True)


# ── charts hook ───────────────────────────────────────────────────────────


def test_charts_failure_is_reported(tmp_path):
    src = tmp_path / "doc.html"
    src.write_text("<p>x</p>", encoding="utf-8")
    (tmp_path / "charts.py").write_text("raise SystemExit(3)", encoding="utf-8")
    with pytest.raises(B.BuildError, match="charts.py failed"):
        B.run_charts(src, quiet=True)


def test_missing_charts_is_not_an_error(tmp_path):
    src = tmp_path / "doc.html"
    src.write_text("<p>x</p>", encoding="utf-8")
    B.run_charts(src, quiet=True)  # must not raise


# ── renderers ─────────────────────────────────────────────────────────────


def test_unknown_renderer_is_rejected():
    with pytest.raises(RenderError, match="unknown renderer"):
        pick("inkjet")


@pytest.mark.skipif(not ANY_RENDERER, reason="no renderer available")
def test_pick_returns_something_available():
    assert pick().available()


@pytest.mark.skipif(not HAS_WEASY, reason="weasyprint unavailable")
def test_weasyprint_declares_full_print_support():
    assert WeasyRenderer().full_print_support is True


@pytest.mark.skipif(not HAS_CHROME, reason="no chromium available")
def test_chromium_actually_renders(tmp_path):
    """Regression: the fallback hung to timeout on CI runners (v0.1.0)."""
    src = tmp_path / "doc.html"
    src.write_text(
        "<!DOCTYPE html><html><head></head><body><p>x</p></body></html>", encoding="utf-8"
    )
    res = B.build(src, prefer="chromium", quiet=True)
    assert res.pdf.read_bytes().startswith(b"%PDF")
    assert res.degraded is True


def test_chromium_is_marked_degraded():
    """The fallback must never claim print fidelity it does not have."""
    assert ChromiumRenderer.full_print_support is False


# ── end to end ────────────────────────────────────────────────────────────


@pytest.mark.skipif(not ANY_RENDERER, reason="no renderer available")
def test_init_then_build_produces_a_pdf(tmp_path):
    B.init(tmp_path)
    src = tmp_path / "document.html"
    assert src.exists() and (tmp_path / "charts.py").exists()
    # the scaffold's charts need matplotlib; drop it if absent
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        (tmp_path / "charts.py").unlink()
    res = B.build(src, quiet=True)
    assert res.pdf.exists()
    assert res.pdf.read_bytes().startswith(b"%PDF")


@pytest.mark.skipif(not ANY_RENDERER, reason="no renderer available")
def test_init_does_not_clobber_without_force(tmp_path):
    (tmp_path / "document.html").write_text("mine", encoding="utf-8")
    B.init(tmp_path)
    assert (tmp_path / "document.html").read_text(encoding="utf-8") == "mine"
    B.init(tmp_path, force=True)
    assert (tmp_path / "document.html").read_text(encoding="utf-8") != "mine"


@pytest.mark.skipif(
    not shutil.which("pdftotext") or not HAS_WEASY, reason="needs pdftotext and weasyprint"
)
def test_page_furniture_renders(tmp_path):
    """Running header and page counter are the whole reason WeasyPrint is default."""
    import subprocess

    src = tmp_path / "doc.html"
    src.write_text(
        "<!DOCTYPE html><html><head></head>"
        '<body data-title="RUNHEAD" data-footer="FOOTNOTE">'
        '<div class="section-wrap"><h2 class="section" id="a" data-section="Alpha">'
        '<span class="idx">SECTION 01</span>Alpha</h2><p>body</p></div>'
        "</body></html>",
        encoding="utf-8",
    )
    res = B.build(src, prefer="weasyprint", quiet=True)
    text = subprocess.run(
        ["pdftotext", str(res.pdf), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    assert "RUNHEAD" in text
    assert "FOOTNOTE" in text
    assert "Alpha" in text
