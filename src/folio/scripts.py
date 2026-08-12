"""Which writing systems a document uses, and what typography they need.

folio does not assume Latin. A document is inspected for the scripts actually
present, and that decides three things: the `lang` and `dir` on <html>, the
line-breaking rules applied, and which fonts the machine needs.

Deliberately no font is bundled. Covering the world would mean shipping tens of
megabytes to everyone so that a few can set Japanese — so folio reports what a
given document needs and leaves installing it to the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RTL_LANGS = {"ar", "he", "fa", "ur"}

# Ordered: the first match with the highest count wins the primary language.
# Ranges are the common blocks, not exhaustive — enough to identify a script.
SCRIPT_RANGES: list[tuple[str, str]] = [
    ("hangul", r"[가-힯ᄀ-ᇿ㄰-㆏]"),
    ("kana", r"[぀-ヿ]"),
    ("han", r"[一-鿿㐀-䶿]"),
    ("arabic", r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"),
    ("hebrew", r"[֐-׿]"),
    ("devanagari", r"[ऀ-\u0963\u0966-ॿ]"),  # excl. danda U+0964/5, shared Indic
    ("bengali", r"[ঀ-৿]"),
    ("tamil", r"[஀-௿]"),
    ("thai", r"[฀-๿]"),
    ("cyrillic", r"[Ѐ-ӿ]"),
    ("greek", r"[Ͱ-Ͽ]"),
    ("latin", r"[A-Za-zÀ-ɏ]"),
]
_COMPILED = [(name, re.compile(rx)) for name, rx in SCRIPT_RANGES]

# script -> (lang, human name, font families that cover it)
SCRIPT_INFO: dict[str, tuple[str, str, list[str]]] = {
    "hangul": ("ko", "Korean", ["Noto Sans KR", "Noto Sans CJK KR"]),
    "kana": ("ja", "Japanese", ["Noto Sans JP", "Noto Sans CJK JP"]),
    "han": ("zh", "Chinese", ["Noto Sans SC", "Noto Sans CJK SC"]),
    "arabic": ("ar", "Arabic", ["Noto Sans Arabic", "Noto Naskh Arabic"]),
    "hebrew": ("he", "Hebrew", ["Noto Sans Hebrew"]),
    "devanagari": ("hi", "Devanagari", ["Noto Sans Devanagari"]),
    "bengali": ("bn", "Bengali", ["Noto Sans Bengali"]),
    "tamil": ("ta", "Tamil", ["Noto Sans Tamil"]),
    "thai": ("th", "Thai", ["Noto Sans Thai"]),
    "cyrillic": ("ru", "Cyrillic", ["Inter", "Noto Sans"]),
    "greek": ("el", "Greek", ["Inter", "Noto Sans"]),
    "latin": ("en", "Latin", ["Inter", "P052", "DejaVu Sans"]),
}

# A non-Latin script takes over only if it carries a real share of the text,
# not a stray glyph. Latin fragments inside CJK documents are the norm —
# product names, identifiers, units — so share matters more than raw count.
_MIN_PRIMARY_CHARS = 5
_MIN_PRIMARY_SHARE = 0.15


@dataclass
class Profile:
    """What a document's scripts imply for typesetting."""

    scripts: list[str] = field(default_factory=list)  # present, most-used first
    lang: str = "en"
    direction: str = "ltr"

    @property
    def is_rtl(self) -> bool:
        return self.direction == "rtl"

    @property
    def fonts_needed(self) -> dict[str, list[str]]:
        """script name -> font families that would cover it."""
        return {s: SCRIPT_INFO[s][2] for s in self.scripts if s in SCRIPT_INFO}

    def describe(self) -> str:
        names = [SCRIPT_INFO[s][1] for s in self.scripts if s in SCRIPT_INFO]
        base = ", ".join(names) if names else "none detected"
        return f"{base} → lang={self.lang} dir={self.direction}"


def _strip_markup(html: str) -> str:
    """Only prose counts. Tag names and CSS would make every document Latin."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"&[a-zA-Z#0-9]+;", " ", html)


def _primary(ranked: list[str], counts: dict[str, int]) -> str:
    """The script that should decide typography.

    Latin only wins by default. Any other script takes over once it carries a
    meaningful share, because a Korean or Japanese document peppered with
    English identifiers is still a Korean or Japanese document — and getting
    that wrong costs it `word-break: keep-all`, which breaks words mid-syllable.
    """
    total = sum(counts.values())
    if not total:
        return "latin"
    for s in ranked:
        if s == "latin":
            continue
        if counts[s] >= _MIN_PRIMARY_CHARS and counts[s] / total >= _MIN_PRIMARY_SHARE:
            return s
    return ranked[0] if ranked else "latin"


def detect(html: str) -> Profile:
    """Inspect a document and decide its language and direction.

    An explicit `lang` on <html> always wins — the author knows better than a
    heuristic, particularly for Chinese vs Japanese, which share Han.
    """
    text = _strip_markup(html)
    counts = {name: len(rx.findall(text)) for name, rx in _COMPILED}
    present = [s for s, n in counts.items() if n > 0]

    # Han appears inside Japanese too; kana is the discriminator.
    if counts["kana"] >= _MIN_PRIMARY_CHARS and "han" in present:
        present.remove("han")

    ranked = sorted(present, key=lambda s: counts[s], reverse=True)

    declared = re.search(r"<html[^>]*\blang=[\"']([\w-]+)[\"']", html, re.I)
    if declared:
        lang = declared.group(1).lower()
    else:
        lang = SCRIPT_INFO.get(_primary(ranked, counts), ("en",))[0]

    declared_dir = re.search(r"<html[^>]*\bdir=[\"'](ltr|rtl)[\"']", html, re.I)
    direction = (
        declared_dir.group(1).lower()
        if declared_dir
        else ("rtl" if lang.split("-")[0] in RTL_LANGS else "ltr")
    )
    return Profile(scripts=ranked, lang=lang, direction=direction)
