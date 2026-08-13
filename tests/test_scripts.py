"""folio must not assume Latin. These pin the behaviour for a global audience."""

from __future__ import annotations

import pytest

from folio import doctor
from folio.assets import css_text, rtl_path
from folio.scripts import RTL_LANGS, detect

SAMPLES = {
    "en": "<p>The quick brown fox jumps over the lazy dog again and again today.</p>",
    "ko": "<p>액추에이터 특성 보고서입니다. 토크와 위치를 측정하고 분석합니다.</p>",
    "ja": "<p>これはテストです。日本語の文書を組版し、品質を確認します。</p>",
    "zh": "<p>这是一个测试文档。我们需要排版中文内容并检查质量。</p>",
    "ar": "<p>هذا تقرير تجريبي عن جودة الطباعة والتنسيق في المستندات.</p>",
    "he": "<p>זהו מסמך בדיקה לאיכות ההדפסה והעיצוב של מסמכים שונים.</p>",
    "th": "<p>นี่คือเอกสารทดสอบสำหรับการจัดพิมพ์และการตรวจสอบคุณภาพ</p>",
    "hi": "<p>यह एक परीक्षण दस्तावेज़ है जिसमें मुद्रण गुणवत्ता की जाँच होती है।</p>",
    "bn": "<p>এটি একটি পরীক্ষার নথি যেখানে মুদ্রণের গুণমান পরীক্ষা করা হয়।</p>",
    "ru": "<p>Это тестовый документ для проверки качества вёрстки и печати.</p>",
}


@pytest.mark.parametrize("expected,html", SAMPLES.items())
def test_language_detected(expected, html):
    assert detect(html).lang == expected


@pytest.mark.parametrize("lang", ["ar", "he"])
def test_rtl_scripts_set_direction(lang):
    assert detect(SAMPLES[lang]).is_rtl


@pytest.mark.parametrize("lang", ["en", "ko", "ja", "zh", "th", "hi", "ru"])
def test_ltr_scripts_stay_ltr(lang):
    assert not detect(SAMPLES[lang]).is_rtl


def test_latin_fragments_do_not_hijack_a_cjk_document():
    """The common real case: a Korean report full of English identifiers.

    Getting this wrong costs the document `word-break: keep-all`, which breaks
    Korean mid-word.
    """
    html = (
        "<p>PhACT Studio 진행 보고서입니다. 액추에이터 특성을 측정하고 "
        "분석합니다. Deploy frequency doubled this quarter.</p>"
    )
    assert detect(html).lang == "ko"


def test_a_single_foreign_name_does_not_flip_the_language():
    html = "<p>The report was written by 김민준 and covers the whole quarter in detail.</p>"
    assert detect(html).lang == "en"


def test_shared_indic_punctuation_is_not_devanagari():
    """The danda U+0964 sits in the Devanagari block but is used across Indic."""
    assert detect(SAMPLES["bn"]).scripts == ["bengali"]


def test_declared_language_beats_the_heuristic():
    """Han cannot distinguish Chinese from Japanese; the author can."""
    html = '<html lang="zh-TW"><body><p>報告書の品質</p></body></html>'
    assert detect(html).lang == "zh-tw"


def test_markup_is_not_counted_as_latin():
    html = '<div class="cover"><span data-theme="report">문서</span></div>'
    assert detect(html).lang == "ko"


def test_empty_document_is_latin():
    assert detect("").lang == "en"


# ── stylesheet consequences ───────────────────────────────────────────────


@pytest.mark.parametrize("lang", ["ko", "ja", "zh", "th", "ar", "he", "hi"])
def test_non_latin_scripts_never_hyphenate(lang):
    """Latin hyphenation applied to these scripts is broken typography."""
    css = css_text()
    block = css[css.index("── Writing systems") :]
    assert f":lang({lang})" in block


def test_rtl_layer_only_ships_when_needed():
    assert "folio rtl mirror" not in css_text("report", rtl=False)
    assert "folio rtl mirror" in css_text("report", rtl=True)


def test_rtl_layer_mirrors_every_left_accent():
    """Logical properties are unsupported, so each physical offset needs one."""
    rtl = rtl_path().read_text(encoding="utf-8")
    for sel in (".metric", ".callout", ".pullquote", "pre", ".timeline", "ul.tick", "ol.steps"):
        assert sel in rtl, f"{sel} is not mirrored for RTL"
    # past the header comment, which names them only to explain their absence
    rules = rtl[rtl.index("/* ── Cover") :]
    for logical in ("border-inline-start", "padding-inline-start", "margin-inline"):
        assert logical not in rules, f"{logical} is silently ignored by WeasyPrint"


def test_rtl_langs_are_the_four_major_ones():
    assert RTL_LANGS == {"ar", "he", "fa", "ur"}


# ── the detected script decides the fonts ─────────────────────────────────


def test_a_korean_document_asks_for_korean_faces():
    """The gap this closes: folio knew, reported, and then did not act.

    `detect` found Korean, `folio fonts` listed the families that cover it, and
    the stylesheet handed WeasyPrint a body stack of P052, Palatino, Georgia,
    serif — not one of which has a Hangul glyph. Every theme therefore set
    Korean body text in whatever fontconfig reached for, which on this machine
    is a *Chinese* face, in a document whose UI type was already correctly in
    Noto Sans CJK KR. Two faces, one document, and no rule can see it: fonts
    are not geometry.
    """
    from folio.scripts import detect, script_font_css

    css = script_font_css(detect(SAMPLES["ko"]))
    assert "Noto Sans CJK KR" in css, "the packaged name Linux actually ships is missing"
    assert "Noto Serif CJK KR" in css, "a serif theme needs a serif companion, not a sans one"


def test_a_latin_document_overrides_nothing():
    """A Latin document must be byte-identical to what it was before."""
    from folio.scripts import detect, script_font_css

    assert script_font_css(detect(SAMPLES["en"])) == ""


@pytest.mark.parametrize("lang", ["ja", "zh", "ar", "he", "th", "hi", "bn"])
def test_every_non_latin_script_gets_a_face_named(lang):
    """Korean is the one that was measured; the gap was never Korean-specific."""
    from folio.scripts import detect, script_font_css

    css = script_font_css(detect(SAMPLES[lang]))
    assert "Noto" in css, f"{lang} names no font family"


# ── font coverage reporting ───────────────────────────────────────────────


def test_missing_font_is_reported_as_a_failure(monkeypatch):
    """A script with no font renders as boxes — that must be loud, not silent."""
    monkeypatch.setattr(doctor, "installed_families", lambda: {"inter", "dejavu sans"})
    checks = doctor.check_document_fonts(SAMPLES["ja"])
    failed = [c for c in checks if c.status == doctor.FAIL]
    assert failed, "missing Japanese font was not reported"
    assert "boxes" in failed[0].detail
    assert failed[0].fix, "no install guidance offered"


def test_present_font_is_reported_as_ok(monkeypatch):
    monkeypatch.setattr(doctor, "installed_families", lambda: {"noto sans jp"})
    checks = doctor.check_document_fonts(SAMPLES["ja"])
    assert not [c for c in checks if c.status == doctor.FAIL]


def test_unknowable_font_list_is_a_warning_not_a_failure(monkeypatch):
    """On a platform we cannot enumerate, never claim the document is broken."""
    monkeypatch.setattr(doctor, "installed_families", lambda: None)
    checks = doctor.check_document_fonts(SAMPLES["ja"])
    assert not [c for c in checks if c.status == doctor.FAIL]
    assert [c for c in checks if c.status == doctor.WARN]


def test_every_platform_has_font_install_guidance():
    for key, cmd in doctor.FONT_INSTALL.items():
        assert cmd.strip(), f"{key} has no font guidance"


def test_cli_output_survives_a_legacy_codepage(tmp_path, capsys):
    """Windows consoles are cp1252; folio prints arrows, marks and CJK."""
    from folio.cli import _force_utf8_output

    _force_utf8_output()  # must not raise, on any platform
    src = tmp_path / "doc.html"
    src.write_text(SAMPLES["ja"], encoding="utf-8")
    from folio.cli import main

    assert main(["fonts", str(src)]) in (0, 1)
    assert "Japanese" in capsys.readouterr().out
