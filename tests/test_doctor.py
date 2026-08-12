"""The doctor is the difference between 'broken' and 'broken, here is the fix'."""

from __future__ import annotations

import importlib.util

import pytest

from folio import doctor


@pytest.fixture
def without(monkeypatch):
    """Hide importable modules from the doctor's probes."""
    real_find_spec = importlib.util.find_spec

    def hide(*names: str):
        hidden = set(names)

        def fake(target, *args, **kwargs):
            if target in hidden:
                return None
            return real_find_spec(target, *args, **kwargs)

        monkeypatch.setattr(importlib.util, "find_spec", fake)

    return hide


def test_every_platform_has_a_native_fix():
    """A user on any platform must get an actionable command, never silence."""
    for key, fix in doctor.NATIVE_FIX.items():
        assert fix, f"{key} has no remediation"
        assert all(isinstance(line, str) and line.strip() for line in fix)


def test_system_detection_returns_a_known_key():
    assert doctor._system() in doctor.NATIVE_FIX


def test_run_returns_checks_and_a_verdict():
    checks, can_render = doctor.run()
    names = {c.name for c in checks}
    assert {"Python", "WeasyPrint", "Chromium fallback"} <= names
    assert isinstance(can_render, bool)


def test_every_check_has_a_valid_status():
    checks, _ = doctor.run()
    for c in checks:
        assert c.status in (doctor.OK, doctor.WARN, doctor.FAIL), c


def test_failing_checks_carry_a_fix():
    """A failure with no remedy is the thing this module exists to prevent."""
    checks, _ = doctor.run()
    for c in checks:
        if c.status == doctor.FAIL:
            assert c.fix, f"{c.name} failed without telling the user what to do"


def test_report_renders_without_error(capsys):
    checks, can_render = doctor.run()
    doctor.report(checks, can_render)
    out = capsys.readouterr().out
    assert "folio doctor" in out
    assert "Python" in out


def test_missing_charts_hint_names_the_extra(without):
    """`pip install matplotlib` is the wrong lesson.

    It works, but it teaches that folio's pieces are installed one loose
    package at a time — so the next gap sends the reader back to a search
    engine. Naming the extra teaches the mechanism, and matches what
    `theme.use()` says when the same gap is hit from the other direction.
    """
    without("matplotlib")
    check = doctor.check_matplotlib()

    assert check.status == doctor.WARN
    assert any("folio-press[charts]" in line for line in check.fix), check.fix


def test_missing_weasyprint_hint_names_the_extra_and_keeps_the_native_fix(without):
    """The extra is the right pip line, but pip alone never finishes the job.

    WeasyPrint's native libraries are outside pip's reach entirely, so the
    platform commands have to survive the rewording — they are the half of
    this remedy that pip cannot perform.
    """
    without("weasyprint")
    check = doctor.check_weasyprint()

    assert check.status == doctor.FAIL
    assert any("folio-press[weasyprint]" in line for line in check.fix), check.fix
    for line in doctor.NATIVE_FIX[doctor._system()]:
        assert line in check.fix, f"lost the native fix: {line}"


def test_no_hint_installs_folios_own_pieces_by_bare_name(without):
    """One phrasing everywhere: folio's pieces arrive as extras of folio.

    Guards the pair against drifting apart again — a hint reworded in one
    check and not the other is how they diverged in the first place.
    """
    without("matplotlib", "weasyprint")

    for check in (doctor.check_matplotlib(), doctor.check_weasyprint()):
        for line in check.fix:
            for bare in ("pip install matplotlib", "pip install weasyprint"):
                assert bare not in line, f"{check.name} still suggests `{bare}`"


def test_every_extra_folio_recommends_is_one_it_declares():
    """A hint naming an extra that does not exist is worse than no hint.

    `pip install 'folio-press[chart]'` fails with a resolver error rather than
    a typo, and the reader has no reason to suspect the tool of being wrong
    about its own packaging. The hints and pyproject are two files that must
    agree, which is the same shape as the version drift this suite already
    guards.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():  # pragma: no cover - installed without sources
        pytest.skip("pyproject not present")

    # Regex rather than tomllib, which is 3.11+ while folio supports 3.10.
    body = pyproject.read_text(encoding="utf-8")
    block = body.split("[project.optional-dependencies]")[1].split("\n[")[0]
    declared = set(re.findall(r"^([\w-]+) = \[", block, re.M))
    assert declared, "no extras parsed out of pyproject"

    recommended = set()
    for path in (root / "src" / "folio").rglob("*.py"):
        recommended |= set(re.findall(r"folio-press\[([\w-]+)\]", path.read_text(encoding="utf-8")))
    assert recommended, "nothing recommends an extra any more — did the hints move?"

    undeclared = recommended - declared
    assert not undeclared, f"recommends extras pyproject does not declare: {sorted(undeclared)}"


def test_fonts_never_fatal():
    """Missing fonts degrade gracefully, so they must never block rendering."""
    assert doctor.check_fonts().status != doctor.FAIL
