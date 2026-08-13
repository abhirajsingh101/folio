"""The skill is an interface, and it must not promise what the CLI cannot do.

An agent reads SKILL.md and takes it literally. A command that does not exist,
or a flag that was renamed, does not fail loudly — the agent improvises around
it, which is worse than an error. These tests hold the prose to the argparse
surface.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "SKILL.md"

pytestmark = pytest.mark.skipif(not SKILL.exists(), reason="skill not present in this tree")


def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def cli_surface() -> tuple[set[str], set[str]]:
    """Every subcommand and every option string argparse actually accepts."""
    from folio.cli import build_parser

    parser = build_parser()
    commands: set[str] = set()
    options: set[str] = {a for action in parser._actions for a in action.option_strings}
    for action in parser._actions:
        choices = getattr(action, "choices", None) or {}
        if hasattr(choices, "items"):
            for name, sub in choices.items():
                commands.add(name)
                options |= {a for act in sub._actions for a in act.option_strings}
    return commands, options


def test_every_command_the_skill_names_exists():
    commands, _ = cli_surface()
    # Only inside code spans/blocks — "folio can do X" in prose is not a command.
    text = skill_text()
    spans = re.findall(r"`([^`\n]+)`", text)
    for block in re.findall(r"```[a-z]*\n(.*?)^```", text, re.S | re.M):
        spans += block.splitlines()
    # An invocation is a span that *starts* with the binary. "folio can produce"
    # inside a sentence is prose that happens to sit in the same line.
    named = {
        m
        for span in spans
        if span.strip().startswith("folio ")
        for m in re.findall(r"^folio ([a-z][a-z-]+)", span.strip())
    }
    unknown = {c for c in named if c not in commands}
    assert not unknown, f"SKILL.md names commands that do not exist: {sorted(unknown)}"


def test_every_flag_the_skill_names_exists():
    _, options = cli_surface()
    # `--brand: #7A1F3D` is a CSS custom property, not a flag; so is `var(--x)`.
    text = re.sub(r"var\(\s*--[a-z-]+\s*\)", "", skill_text())
    # Anchor the whole token before testing for the colon — a bare lookahead
    # backtracks and happily matches `--bran` out of `--brand:`.
    named = {m for m in re.findall(r"(?<![\w-])(--[a-z][a-z-]*[a-z])(?![\w-])(?!\s*:)", text)}
    unknown = {f for f in named if f not in options}
    assert not unknown, f"SKILL.md names flags that do not exist: {sorted(unknown)}"


def test_the_trigger_and_the_scope_do_not_contradict():
    """The trigger advertised invoice; the scope excluded anything under 2 pages.

    An agent that reads both cannot act on either. Short documents are folio's
    work, so the exclusion was the wrong half.
    """
    text = skill_text()
    scope = text[text.index("## Not for") :]
    assert "under ~2 pages" not in scope, "the short-document exclusion is back"
    for short_form in ("invoice", "one-pager"):
        assert short_form in text.split("## Not for")[0], f"{short_form} dropped from the trigger"


def test_every_theme_named_in_the_routing_table_is_installed():
    from folio.assets import theme_names

    text = skill_text()
    table = text[text.index("## Route first") : text.index("## Plan before")]
    named = set(re.findall(r"`(report|editorial|technical|minimal|[a-z]+)`", table))
    installed = set(theme_names())
    # Only judge words that look like theme names — the table also holds commands.
    claimed = named & (installed | {"none", "full"})
    assert installed <= claimed | {"none", "full"}, (
        f"routing table never mentions themes: {sorted(installed - claimed)}"
    )
