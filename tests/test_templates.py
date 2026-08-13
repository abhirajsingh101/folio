"""The scaffolds, and the promise that adding one cannot be done halfway.

`folio init` had a single document baked into it — a progress report — which is
one of the seven shapes the skill routes to. Every other document type had to
be improvised from the component list, which is the drift the kit exists to
stop: the scaffold is the one piece of folio a user reads before they read
anything else, so a missing one is not a missing convenience.

Scaffolds are discovered from the directory, so adding one is adding a folder.
The manifest is what stops a folder arriving with no description — the failure
already visible in `folio themes`, whose blurbs live in a dict in the CLI with
an empty-string fallback, so a fifth theme would list as a bare name.
"""

from __future__ import annotations

import json

import pytest

from folio import build as B
from folio.assets import (
    DEFAULT_TEMPLATE,
    asset_path,
    template_blurb,
    template_files,
    template_names,
    template_path,
    template_text,
)

# ── discovery ─────────────────────────────────────────────────────────────


def test_the_report_scaffold_is_the_default_and_lists_first():
    """`folio init` with no argument must stay the progress report it was."""
    assert DEFAULT_TEMPLATE == "report"
    assert template_names()[0] == "report"


def test_the_manifest_and_the_directory_never_diverge():
    """Both directions matter.

    A folder with no entry lists with no description; an entry with no folder
    advertises a scaffold that `folio init` cannot produce.
    """
    manifest = json.loads(asset_path("templates", "manifest.json").read_text(encoding="utf-8"))
    assert set(template_names()) == set(manifest)


def test_every_scaffold_is_described_in_one_line():
    for name in template_names():
        blurb = template_blurb(name)
        assert blurb.strip(), f"{name} has no description"
        assert "\n" not in blurb, f"{name}'s description is not one line"


def test_every_scaffold_ships_a_document():
    for name in template_names():
        assert template_text(name, "document.html").lstrip().startswith("<!DOCTYPE html>")


def test_every_scaffold_declares_a_theme_that_exists():
    """A document is self-describing, so a scaffold states its direction.

    `detect_theme` raises on a name no theme file backs, which is the typo
    this catches; the attribute itself has to be there or `--theme` has
    nothing to rewrite and the scaffold silently ships as `report`.
    """
    for name in template_names():
        html = template_text(name, "document.html")
        assert 'data-theme="' in html, f"{name} does not declare its theme"
        B.detect_theme(html)


def test_an_unknown_scaffold_names_the_ones_that_exist():
    with pytest.raises(ValueError) as e:
        template_path("brochure")
    assert "brochure" in str(e.value)
    for name in template_names():
        assert name in str(e.value)


def test_no_scaffold_assumes_where_folio_was_installed():
    """A scaffold is copied into the user's project and must stand alone."""
    for name in template_names():
        for f in template_files(name):
            text = f.read_text(encoding="utf-8")
            assert ".local/share" not in text
            assert "Path.home()" not in text


# ── init ──────────────────────────────────────────────────────────────────


def test_init_writes_every_file_the_scaffold_ships(tmp_path):
    written = B.init(tmp_path, template="report")
    assert {p.name for p in written} == {"document.html", "charts.py"}


def test_a_scaffold_with_no_charts_writes_no_charts(tmp_path):
    """An invoice has nothing to plot, and a stray charts.py invites one."""
    B.init(tmp_path, template="invoice")
    assert (tmp_path / "document.html").exists()
    assert not (tmp_path / "charts.py").exists()


def test_a_scaffold_keeps_its_own_theme_when_none_is_asked_for(tmp_path):
    """The routing table's pairing is the scaffold's default, not the kit's."""
    B.init(tmp_path, template="invoice")
    assert B.detect_theme((tmp_path / "document.html").read_text(encoding="utf-8")) == "minimal"


def test_the_theme_flag_rewrites_the_declaration_rather_than_adding_one(tmp_path):
    """Two `data-theme` attributes would leave the winner up to the parser."""
    B.init(tmp_path, template="invoice", theme="editorial")
    html = (tmp_path / "document.html").read_text(encoding="utf-8")
    assert html.count("data-theme") == 1
    assert B.detect_theme(html) == "editorial"


def test_an_unknown_scaffold_writes_nothing(tmp_path):
    with pytest.raises(ValueError):
        B.init(tmp_path, template="brochure")
    assert not list(tmp_path.iterdir())


# ── the command line ──────────────────────────────────────────────────────


def test_the_templates_command_prints_every_scaffold_with_its_description(capsys):
    from folio.cli import main

    assert main(["templates"]) == 0
    out = capsys.readouterr().out
    for name in template_names():
        assert name in out
        assert template_blurb(name) in out


def test_init_refuses_an_unknown_scaffold_and_lists_the_real_ones(tmp_path, capsys):
    """An agent that mistypes must be told the valid values, not a traceback."""
    from folio.cli import main

    with pytest.raises(SystemExit) as e:
        main(["init", str(tmp_path), "--template", "brochure"])
    message = str(e.value)
    assert "brochure" in message
    for name in template_names():
        assert name in message
    assert not list(tmp_path.iterdir())
