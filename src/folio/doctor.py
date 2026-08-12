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

# Ordered by reliability for headless print-to-pdf. Distro `chromium` is
# often snap-confined and cannot read files outside its sandbox, so real
# Chrome comes first.
CHROME_BINARIES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium-browser",
    "chromium",
    "microsoft-edge",
    "brave-browser",
]
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _playwright_ready() -> bool:
    """Playwright with an installed browser — the reliable fallback.

    It bundles its own Chromium and drives it over DevTools rather than the
    command line, which is why it works on hosts where `chrome --print-to-pdf`
    silently hangs.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            return bool(p.chromium.executable_path)
    except Exception:
        return False


def find_chrome() -> str | None:
    """A usable print-to-PDF engine, most reliable first."""
    if os.environ.get("FOLIO_CHROME"):
        return os.environ["FOLIO_CHROME"]
    if _playwright_ready():
        return "playwright"
    for name in CHROME_BINARIES:
        p = shutil.which(name)
        if p:
            return p
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
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
            [
                "pip install playwright && playwright install chromium  (recommended)",
                "…or install Google Chrome.",
            ],
        )
    if p == "playwright":
        return Check("Chromium fallback", OK, "playwright (bundled browser)")
    return Check(
        "Chromium fallback",
        WARN,
        f"{p} — command-line printing, unreliable on some hosts",
        ["More reliable: pip install playwright && playwright install chromium"],
    )


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


# ── Script-aware font coverage ────────────────────────────────────────────

FONT_INSTALL = {
    "linux-apt": "sudo apt-get install -y fonts-noto-core fonts-noto-cjk",
    "linux-dnf": "sudo dnf install -y google-noto-fonts-common google-noto-cjk-fonts",
    "linux-pacman": "sudo pacman -S --needed noto-fonts noto-fonts-cjk",
    "linux-apk": "sudo apk add font-noto font-noto-cjk",
    "linux": "Install the Noto font families with your package manager.",
    "macos": "Most scripts ship with macOS. For the rest: brew install --cask font-noto-sans-cjk",
    "windows": "Settings → Time & Language → Language → add the language pack,\n"
    "    or download the family from https://fonts.google.com/noto",
    "unknown": "Install the relevant Noto family: https://fonts.google.com/noto",
}


def installed_families() -> set[str] | None:
    """Lower-cased font families known to the system, or None if unknowable."""
    fc = shutil.which("fc-list")
    if not fc:
        return None
    try:
        out = subprocess.run([fc, ":", "family"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return None
    fams = set()
    for line in out.splitlines():
        for part in line.split(","):
            fams.add(part.strip().lower())
    return fams


def check_document_fonts(html: str) -> list[Check]:
    """Whether this machine can actually set the scripts this document uses.

    folio bundles no fonts. Shipping every writing system would mean tens of
    megabytes for everyone so that a few can set Japanese, so coverage is
    reported per document and installed only if needed.
    """
    from .scripts import SCRIPT_INFO, detect

    prof = detect(html)
    have = installed_families()
    checks: list[Check] = [Check("Scripts", OK, prof.describe())]

    for script, families in prof.fonts_needed.items():
        label = SCRIPT_INFO[script][1]
        if have is None:
            checks.append(
                Check(
                    f"  {label}",
                    WARN,
                    "cannot enumerate fonts on this platform",
                    [f"If {label} renders as boxes: {FONT_INSTALL[_system()]}"],
                )
            )
            continue
        hit = next((f for f in families if f.lower() in have), None)
        if hit:
            checks.append(Check(f"  {label}", OK, hit))
        else:
            checks.append(
                Check(
                    f"  {label}",
                    FAIL,
                    f"no font covers it — text will render as boxes "
                    f"(want one of: {', '.join(families)})",
                    [FONT_INSTALL[_system()]],
                )
            )
    return checks
