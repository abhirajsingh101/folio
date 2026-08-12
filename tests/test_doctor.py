"""The doctor is the difference between 'broken' and 'broken, here is the fix'."""

from __future__ import annotations

from folio import doctor


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


def test_fonts_never_fatal():
    """Missing fonts degrade gracefully, so they must never block rendering."""
    assert doctor.check_fonts().status != doctor.FAIL
