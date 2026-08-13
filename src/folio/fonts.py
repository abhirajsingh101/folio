"""Fetch a face for a script this machine cannot set.

folio bundles no fonts, and that stays true: covering the world would mean
shipping tens of megabytes to everyone so that a few can set Japanese. But
`folio fonts <file>` will tell you Tamil has no face and then leave you to it,
and on a machine with no package manager — which is most Windows and plenty of
locked-down macOS — "install Noto Sans Tamil" is not a step, it is an
afternoon. A report that names a gap it cannot close is half a feature.

So this is opt-in and explicit: it runs only when asked, only for the script
asked for, and only into the user's own font directory. Nothing is fetched at
build time, and nothing is ever written outside the user's home.

Everything here is Noto under the SIL Open Font License, from the `google/fonts`
repository. The filenames are held in a table rather than derived because each
family names its own variable axes — `NotoSansKR[wght].ttf` beside
`NotoSansThai[wdth,wght].ttf` — and a derived URL would 404 on half the world.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path

BASE = "https://github.com/google/fonts/raw/main/ofl"

# script -> ((family name, upstream directory, filename), ...)
#
# Sans and serif both, because half the themes set body copy in a serif and a
# serif document with a sans Korean face in it is still two documents. The
# family names must match `SCRIPT_INFO`, or a fetched face would not be named
# by any stack folio writes.
DOWNLOADS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "hangul": (
        ("Noto Sans KR", "notosanskr", "NotoSansKR[wght].ttf"),
        ("Noto Serif KR", "notoserifkr", "NotoSerifKR[wght].ttf"),
    ),
    "kana": (
        ("Noto Sans JP", "notosansjp", "NotoSansJP[wght].ttf"),
        ("Noto Serif JP", "notoserifjp", "NotoSerifJP[wght].ttf"),
    ),
    "han": (
        ("Noto Sans SC", "notosanssc", "NotoSansSC[wght].ttf"),
        ("Noto Serif SC", "notoserifsc", "NotoSerifSC[wght].ttf"),
    ),
    "arabic": (
        ("Noto Sans Arabic", "notosansarabic", "NotoSansArabic[wdth,wght].ttf"),
        ("Noto Naskh Arabic", "notonaskharabic", "NotoNaskhArabic[wght].ttf"),
    ),
    "hebrew": (
        ("Noto Sans Hebrew", "notosanshebrew", "NotoSansHebrew[wdth,wght].ttf"),
        ("Noto Serif Hebrew", "notoserifhebrew", "NotoSerifHebrew[wdth,wght].ttf"),
    ),
    "devanagari": (
        ("Noto Sans Devanagari", "notosansdevanagari", "NotoSansDevanagari[wdth,wght].ttf"),
        ("Noto Serif Devanagari", "notoserifdevanagari", "NotoSerifDevanagari[wdth,wght].ttf"),
    ),
    "bengali": (
        ("Noto Sans Bengali", "notosansbengali", "NotoSansBengali[wdth,wght].ttf"),
        ("Noto Serif Bengali", "notoserifbengali", "NotoSerifBengali[wdth,wght].ttf"),
    ),
    "tamil": (
        ("Noto Sans Tamil", "notosanstamil", "NotoSansTamil[wdth,wght].ttf"),
        ("Noto Serif Tamil", "notoseriftamil", "NotoSerifTamil[wdth,wght].ttf"),
    ),
    "thai": (
        ("Noto Sans Thai", "notosansthai", "NotoSansThai[wdth,wght].ttf"),
        ("Noto Serif Thai", "notoserifthai", "NotoSerifThai[wdth,wght].ttf"),
    ),
    "cyrillic": (
        ("Noto Sans", "notosans", "NotoSans[wdth,wght].ttf"),
        ("Noto Serif", "notoserif", "NotoSerif[wdth,wght].ttf"),
    ),
    "greek": (
        ("Noto Sans", "notosans", "NotoSans[wdth,wght].ttf"),
        ("Noto Serif", "notoserif", "NotoSerif[wdth,wght].ttf"),
    ),
}

# What a font file starts with. An HTTP 200 carrying an error page is the
# failure this catches: `.ttf` full of `<!DOCTYPE html>` installs perfectly
# happily and renders as nothing at all.
MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf", b"wOFF", b"wOF2")

LICENCE = "Noto is licensed under the SIL Open Font License 1.1."


class FontInstallError(RuntimeError):
    pass


def user_font_dir() -> Path:
    """Where a font goes for this user alone. Never a system directory."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Fonts"
    if system == "Windows":
        base = Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts"
        return base
    return Path.home() / ".local" / "share" / "fonts"


def _fetch(url: str) -> bytes:
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    try:
        with urlopen(Request(url, headers={"User-Agent": "folio"}), timeout=120) as r:
            return r.read()
    except URLError as exc:  # pragma: no cover - network dependent
        raise FontInstallError(
            f"could not reach {url}\n  {exc}\n"
            "  folio never needs the network to build a document — only to "
            "fetch a face you asked for."
        ) from exc


def resolve(script: str) -> str:
    """Accept either a script name (`hangul`) or a language code (`ko`)."""
    from .scripts import SCRIPT_INFO

    key = script.strip().lower()
    if key in DOWNLOADS:
        return key
    for name, info in SCRIPT_INFO.items():
        if info[0] == key and name in DOWNLOADS:
            return name
    raise FontInstallError(
        f"no font list for {script!r}\n  available: {', '.join(sorted(DOWNLOADS))}"
    )


def install(
    script: str,
    *,
    target: Path | None = None,
    fetch: Callable[[str], bytes] = _fetch,
    have: Iterable[str] | None = None,
    refresh: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """Fetch the faces covering `script`. Returns what was written.

    Already-installed families are skipped, so running it twice is free rather
    than 34MB — which is what Korean costs, and reason enough not to re-fetch
    on a whim.
    """
    key = resolve(script)
    directory = Path(target) if target else user_font_dir()
    if have is None:
        from .doctor import installed_families

        have = installed_families() or set()
    present = {f.lower() for f in have}

    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for family, folder, filename in DOWNLOADS[key]:
        if family.lower() in present:
            if on_progress:
                on_progress(f"  have      {family}")
            continue
        url = f"{BASE}/{folder}/{filename.replace('[', '%5B').replace(']', '%5D')}"
        if on_progress:
            on_progress(f"  fetching  {family}")
        data = fetch(url)
        if not data.startswith(MAGIC):
            raise FontInstallError(
                f"what came back for {family} is not a font\n"
                f"  {url}\n"
                "  the upstream path has probably moved; install it by hand "
                "from https://fonts.google.com/noto"
            )
        out = directory / filename
        out.write_bytes(data)
        written.append(out)
        if on_progress:
            on_progress(f"  installed {out}  ({len(data) / 1e6:.1f} MB)")

    if written and refresh:
        _refresh_font_cache(directory)
    return written


def _refresh_font_cache(directory: Path) -> None:
    """Best effort: a font nothing has indexed is a font nothing can use.

    macOS and Windows pick up a user font directory on their own; only
    fontconfig needs telling, and if it is absent there is nothing to tell.
    """
    fc = shutil.which("fc-cache")
    if not fc:
        return
    try:
        subprocess.run([fc, "-f", str(directory)], capture_output=True, timeout=120)
    except Exception:  # pragma: no cover - best effort by definition
        pass
