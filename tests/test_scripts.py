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


def _resolved(css: str, prop: str) -> str:
    """A declaration with its `var()` references replaced by their defaults.

    What a stack falls through to is a property of the resolved chain, not of
    the line as written — a `var()` can quietly introduce a face from a
    different classification, and the declaration still reads correctly.
    """
    import re

    decl = re.search(rf"{prop}:([^;]+);", css).group(1)
    for _ in range(4):  # nested, but shallow
        refs = re.findall(r"var\((--[\w-]+)\)", decl)
        if not refs:
            break
        for ref in refs:
            value = re.search(rf"{ref}:([^;]+);", css).group(1).strip()
            decl = decl.replace(f"var({ref})", value)
    return decl


def test_the_mono_stack_never_falls_through_to_a_proportional_face():
    """The regression the script splice introduced, caught on its own machine.

    `--font-mono` was given `var(--script-sans)` so a Korean comment inside a
    code block would find a face. For a Latin document that variable holds
    `sans-serif`, which sat *before* `monospace` in the chain — so a machine
    without JetBrains Mono set its code in a proportional face, and every
    column in a `technical` table lost its alignment. Invisible here, because
    this machine has JetBrains Mono and never reaches the fallback.
    """
    resolved = _resolved(css_text(), "--font-mono")
    assert "sans-serif" not in resolved, resolved
    assert "monospace" in resolved


@pytest.mark.parametrize("theme", ["report", "editorial", "minimal", "technical"])
def test_the_script_splice_never_pre_empts_the_platform_generic(theme):
    """A Latin document must resolve to the stack it had before any of this.

    The splice is inert for Latin only if each variable defaults to the generic
    of its own classification *and* sits after the platform generic. Put it
    first and `sans-serif` wins ahead of `system-ui`, which on macOS is the
    difference between Helvetica and San Francisco — a change to every Latin
    document, made silently, while adding support for a script it does not use.
    """
    css = css_text(theme)
    for prop, platform, generic in (
        ("--font-ui", "system-ui", "sans-serif"),
        ("--font-mono", "ui-monospace", "monospace"),
    ):
        resolved = _resolved(css, prop)
        assert platform in resolved, f"{theme}/{prop} lost its platform generic"
        assert resolved.index(platform) < resolved.index(generic), (
            f"{theme}/{prop}: {generic} pre-empts {platform} — {resolved}"
        )


def test_a_korean_document_gets_a_monospaced_korean_face():
    """A code block in a Korean document still has to hold its grid."""
    from folio.scripts import detect, script_font_css

    assert "Noto Sans Mono CJK KR" in script_font_css(detect(SAMPLES["ko"]))


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


# ── fetching a face for a script the machine does not have ────────────────


def test_every_script_folio_can_report_missing_can_also_be_fetched():
    """A report that names a gap it cannot close is half a feature.

    `check_document_fonts` will tell you Tamil has no face; `--install tamil`
    has to be able to answer that. The table is explicit rather than derived
    because the upstream filename carries the variable axes, and they differ
    per family — `NotoSansKR[wght].ttf` beside `NotoSansThai[wdth,wght].ttf`.
    """
    from folio.fonts import DOWNLOADS
    from folio.scripts import SCRIPT_INFO

    reportable = {s for s in SCRIPT_INFO if s != "latin"}
    assert reportable <= set(DOWNLOADS), f"no download for: {sorted(reportable - set(DOWNLOADS))}"


def test_a_downloaded_file_that_is_not_a_font_is_refused(tmp_path):
    """The failure that would otherwise install an error page as a typeface.

    A moved URL answers 200 with HTML on plenty of hosts, and a `.ttf` full of
    `<!DOCTYPE html>` installs perfectly happily and renders as nothing. The
    first four bytes say what a file really is.
    """
    from folio import fonts

    def fetch(url: str) -> bytes:
        return b"<!DOCTYPE html><title>404</title>"

    with pytest.raises(fonts.FontInstallError, match="not a font"):
        fonts.install("thai", target=tmp_path, fetch=fetch, refresh=False, have=set())


def test_a_fetched_face_lands_in_the_target_directory(tmp_path):
    from folio import fonts

    def fetch(url: str) -> bytes:
        return b"\x00\x01\x00\x00" + b"padding" * 8  # a TrueType magic number

    written = fonts.install("thai", target=tmp_path, fetch=fetch, refresh=False, have=set())
    assert written, "nothing was written"
    for path in written:
        assert path.exists() and path.parent == tmp_path
        assert path.suffix == ".ttf"


def test_a_face_already_installed_is_not_fetched_again(tmp_path):
    """Re-running the command must be free, not 34MB."""
    from folio import fonts

    calls = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return b"OTTO" + b"padding" * 8

    fonts.install("thai", target=tmp_path, fetch=fetch, refresh=False, have={"noto sans thai"})
    assert not any("NotoSansThai" in u for u in calls), "refetched a face already present"


def test_an_unknown_script_names_the_ones_that_exist(tmp_path):
    from folio import fonts

    with pytest.raises(fonts.FontInstallError, match="thai"):
        fonts.install("klingon", target=tmp_path, fetch=lambda u: b"", refresh=False, have=set())


def test_the_kit_faces_the_doctor_asks_for_can_all_be_installed():
    """`folio doctor` says "missing Inter" and must be able to answer for it.

    The kit's own three faces are what decide whether a Latin document looks
    the way folio intends, and until now the report named them without being
    able to fetch them — the same half-a-feature the script install closed.
    """
    from folio.doctor import KIT_FACES
    from folio.fonts import DOWNLOADS

    installable = {family for family, _, _ in DOWNLOADS["kit"]}
    assert set(KIT_FACES) <= installable, f"cannot install: {set(KIT_FACES) - installable}"


def test_every_download_names_a_licence_folio_can_print():
    """Two licences now, and the command states the one that applies.

    Noto is OFL; P052 is AGPL with an exemption that permits embedding in a
    PDF regardless of the document's own licence, which is precisely what a
    typesetting kit does with it. Getting that wrong in either direction is
    the kind of mistake nobody notices until it matters.
    """
    from folio.fonts import DOWNLOADS, LICENCES

    for script, entries in DOWNLOADS.items():
        for family, _, licence in entries:
            assert licence in LICENCES, f"{script}/{family} names licence {licence!r}"


def test_installing_the_kit_fetches_its_own_faces(tmp_path):
    from folio import fonts

    fetched = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return b"OTTO" + b"padding" * 8

    fonts.install("kit", target=tmp_path, fetch=fetch, refresh=False, have=set())
    assert any("Inter" in u for u in fetched)
    assert any("JetBrainsMono" in u for u in fetched)
    assert any("P052" in u for u in fetched)


def test_every_style_of_an_installed_family_is_skipped(tmp_path):
    """P052 arrives as four files and fontconfig calls them all one family.

    Naming the styles separately in the table would mean a machine that has
    P052 re-fetches its italic and both bolds on every run — the "re-running
    is free" property quietly false for the one family that ships as a set.
    """
    from folio import fonts

    fetched = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return b"OTTO" + b"padding" * 8

    fonts.install(
        "kit",
        target=tmp_path,
        fetch=fetch,
        refresh=False,
        have={"inter", "jetbrains mono", "p052"},
    )
    assert not fetched, f"refetched faces already present: {fetched}"
