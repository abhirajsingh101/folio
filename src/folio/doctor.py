"""Diagnose what folio can and cannot do on this machine, and say how to fix it.

WeasyPrint binds Pango, cairo and GDK-PixBuf through ctypes at import time.
Those are *system* libraries; pip cannot install them. That single fact is the
most common reason a document toolchain fails on someone else's laptop, so
folio treats it as a first-class, diagnosable state rather than a traceback.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

OK, WARN, FAIL = "ok", "warn", "fail"

_MARK = {OK: "✓", WARN: "!", FAIL: "✗"}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    fix: list[str] = field(default_factory=list)


def _system() -> str:
    s = platform.system()
    if s == "Linux":
        # distinguish the package manager, since the fix differs
        for mgr, path in (
            ("apt", "/usr/bin/apt-get"),
            ("dnf", "/usr/bin/dnf"),
            ("pacman", "/usr/bin/pacman"),
            ("apk", "/sbin/apk"),
        ):
            if os.path.exists(path):
                return f"linux-{mgr}"
        return "linux"
    return {"Darwin": "macos", "Windows": "windows"}.get(s, "unknown")


NATIVE_FIX = {
    "linux-apt": [
        "sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b "
        "libcairo2 libgdk-pixbuf-2.0-0"
    ],
    "linux-dnf": ["sudo dnf install -y pango cairo gdk-pixbuf2"],
    "linux-pacman": ["sudo pacman -S --needed pango cairo gdk-pixbuf2"],
    "linux-apk": ["sudo apk add pango cairo gdk-pixbuf ttf-dejavu"],
    "linux": [
        "Install the pango, cairo and gdk-pixbuf runtime libraries with your package manager."
    ],
    "macos": [
        "brew install pango cairo gdk-pixbuf libffi",
        '# Apple silicon: export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib"',
    ],
    "windows": [
        "Install MSYS2 from https://www.msys2.org, then in its shell run:",
        "  pacman -S mingw-w64-x86_64-pango",
        "Add C:\\msys64\\mingw64\\bin to PATH.",
    ],
    "unknown": ["Install pango, cairo and gdk-pixbuf for your platform."],
}

CHROME_BINARIES = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "microsoft-edge",
    "brave-browser",
]
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome() -> str | None:
    """A Chromium-family binary usable for print-to-PDF, if one exists."""
    if os.environ.get("FOLIO_CHROME"):
        return os.environ["FOLIO_CHROME"]
    for name in CHROME_BINARIES:
        p = shutil.which(name)
        if p:
            return p
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    try:  # playwright ships its own chromium
        from playwright.sync_api import sync_playwright  # noqa: F401

        return "playwright"
    except Exception:
        return None


def check_weasyprint() -> Check:
    if importlib.util.find_spec("weasyprint") is None:
        return Check(
            "WeasyPrint", FAIL, "not installed", ["pip install weasyprint", *NATIVE_FIX[_system()]]
        )
    try:
        import weasyprint

        return Check("WeasyPrint", OK, f"v{getattr(weasyprint, '__version__', '?')}")
    except OSError as e:
        # the signature failure: python package present, native libs absent
        return Check(
            "WeasyPrint",
            FAIL,
            f"installed but native libraries missing — {e}",
            NATIVE_FIX[_system()],
        )
    except Exception as e:  # pragma: no cover - defensive
        return Check(
            "WeasyPrint", FAIL, f"import failed — {type(e).__name__}: {e}", NATIVE_FIX[_system()]
        )


def check_chrome() -> Check:
    p = find_chrome()
    if not p:
        return Check(
            "Chromium fallback",
            WARN,
            "no Chromium-family browser found",
            ["Install Chrome/Chromium, or: pip install playwright && playwright install chromium"],
        )
    return Check("Chromium fallback", OK, p)


def check_matplotlib() -> Check:
    if importlib.util.find_spec("matplotlib") is None:
        return Check(
            "Charts (matplotlib)",
            WARN,
            "not installed — charts.py will not run",
            ["pip install matplotlib"],
        )
    return Check("Charts (matplotlib)", OK, "")


def check_fonts() -> Check:
    """Best effort. Missing fonts degrade gracefully, so this is never fatal."""
    wanted = {"Inter": False, "JetBrains Mono": False, "P052": False, "Noto Sans KR": False}
    fc = shutil.which("fc-list")
    if fc:
        try:
            out = subprocess.run(
                [fc, ":", "family"], capture_output=True, text=True, timeout=10
            ).stdout
            for name in wanted:
                wanted[name] = name.lower() in out.lower()
        except Exception:
            pass
    elif _system() == "macos":
        for name in wanted:  # macOS has Palatino/Helvetica equivalents built in
            wanted[name] = name == "P052"
    missing = [n for n, found in wanted.items() if not found]
    if not fc and _system() != "macos":
        return Check(
            "Fonts",
            WARN,
            "cannot enumerate fonts on this platform",
            ["Optional: install Inter and JetBrains Mono for the intended look."],
        )
    if missing:
        return Check(
            "Fonts",
            WARN,
            f"missing {', '.join(missing)} — falling back",
            [
                "Optional. Output stays professional; see docs/GOTCHAS.md.",
                "Best look: install Inter, JetBrains Mono, and a Palatino-class serif.",
            ],
        )
    return Check("Fonts", OK, "all preferred faces present")


def run() -> tuple[list[Check], bool]:
    """Return every check and whether at least one renderer works."""
    checks = [
        Check(
            "Python",
            OK if sys.version_info >= (3, 10) else FAIL,
            platform.python_version(),
            [] if sys.version_info >= (3, 10) else ["folio needs Python 3.10 or newer."],
        ),
        check_weasyprint(),
        check_chrome(),
        check_matplotlib(),
        check_fonts(),
    ]
    can_render = any(
        c.name in ("WeasyPrint", "Chromium fallback") and c.status == OK for c in checks
    )
    return checks, can_render


def report(checks: list[Check], can_render: bool) -> None:
    print(f"folio doctor — {platform.system()} {platform.machine()}\n")
    for c in checks:
        line = f"  {_MARK[c.status]} {c.name:<22} {c.detail}"
        print(line.rstrip())
    print()
    if can_render:
        primary = next((c for c in checks if c.name == "WeasyPrint" and c.status == OK), None)
        if primary:
            print("Ready. Rendering with WeasyPrint (full print support).")
        else:
            print(
                "Ready, with reduced fidelity. WeasyPrint is unavailable, so folio will\n"
                "use Chromium: running headers, page numbers and named pages are lost.\n"
                "Fix WeasyPrint for the intended output."
            )
    else:
        print("Not ready — no renderer available.")

    fixes = [c for c in checks if c.fix and c.status != OK]
    if fixes:
        print("\nTo fix:")
        for c in fixes:
            print(f"\n  {c.name}")
            for line in c.fix:
                print(f"    {line}")
