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

# script -> (lang, human name, sans families, serif families)
#
# Two lists, because half the themes set body copy in a serif and a serif
# document with a sans Korean face in it is two documents. Each list is
# ordered: the Google Fonts name first, then the name the same face carries
# when a Linux distribution packages it — `Noto Sans KR` and `Noto Sans CJK KR`
# are the same design, and a machine typically has exactly one of the two.
# Missing that second name is what put a Chinese fallback face into every
# Korean document folio built.
SCRIPT_INFO: dict[str, tuple[str, str, list[str], list[str]]] = {
    "hangul": (
        "ko",
        "Korean",
        ["Noto Sans KR", "Noto Sans CJK KR"],
        ["Noto Serif KR", "Noto Serif CJK KR"],
    ),
    "kana": (
        "ja",
        "Japanese",
        ["Noto Sans JP", "Noto Sans CJK JP"],
        ["Noto Serif JP", "Noto Serif CJK JP"],
    ),
    "han": (
        "zh",
        "Chinese",
        ["Noto Sans SC", "Noto Sans CJK SC"],
        ["Noto Serif SC", "Noto Serif CJK SC"],
    ),
    # Naskh is the traditional calligraphic hand, which is what pairs with a
    # serif; Noto Sans Arabic is the modern grotesque that pairs with a sans.
    "arabic": ("ar", "Arabic", ["Noto Sans Arabic"], ["Noto Naskh Arabic"]),
    "hebrew": ("he", "Hebrew", ["Noto Sans Hebrew"], ["Noto Serif Hebrew"]),
    "devanagari": ("hi", "Devanagari", ["Noto Sans Devanagari"], ["Noto Serif Devanagari"]),
    "bengali": ("bn", "Bengali", ["Noto Sans Bengali"], ["Noto Serif Bengali"]),
    "tamil": ("ta", "Tamil", ["Noto Sans Tamil"], ["Noto Serif Tamil"]),
    "thai": ("th", "Thai", ["Noto Sans Thai"], ["Noto Serif Thai"]),
    "cyrillic": ("ru", "Cyrillic", ["Inter", "Noto Sans"], ["Noto Serif"]),
    "greek": ("el", "Greek", ["Inter", "Noto Sans"], ["Noto Serif"]),
    "latin": ("en", "Latin", ["Inter", "P052", "DejaVu Sans"], ["P052", "DejaVu Serif"]),
}

# Scripts with no italic. Not a shortage of fonts — italic is a Latin
# invention, and these writing systems never developed an equivalent, so a
# slant is not emphasis in them but a distortion of the letterform. Cyrillic
# and Greek are absent deliberately: both have true italics and use them.
NO_ITALIC = frozenset(
    {"hangul", "kana", "han", "arabic", "hebrew", "devanagari", "bengali", "tamil", "thai"}
)

# The three scripts with a monospaced face of their own. Everything else uses
# its sans inside a code block — a proportional face in `pre` is not ideal, but
# it is what exists, and CJK is where the grid actually matters, because the
# glyphs are full-width and a proportional CJK face still breaks the column.
MONO_FAMILIES: dict[str, list[str]] = {
    "hangul": ["Noto Sans Mono CJK KR"],
    "kana": ["Noto Sans Mono CJK JP"],
    "han": ["Noto Sans Mono CJK SC"],
}


def mono_families(script: str) -> list[str]:
    """Faces for this script inside a code block, most specific first.

    One accessor rather than a fifth column in `SCRIPT_INFO`: eight of the
    eleven scripts would have repeated their sans list verbatim, and two copies
    of one list is how the doctor's font check drifted away from this table in
    the first place.
    """
    return MONO_FAMILIES.get(script, []) + SCRIPT_INFO[script][2]


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
        """script name -> font families that would cover it.

        Sans and serif together: the question this answers is whether the text
        renders as boxes, and either face prevents that. Which of the two a
        given passage *should* use is a separate matter, settled by
        `script_font_css`.
        """
        return {s: SCRIPT_INFO[s][2] + SCRIPT_INFO[s][3] for s in self.scripts if s in SCRIPT_INFO}

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


def script_font_css(profile: Profile) -> str:
    """The stylesheet a document's own scripts ask for. Empty for Latin.

    A font stack falls through per glyph, so the Latin faces stay first and
    keep setting Latin: what a document needs is a face for the glyphs Inter
    and P052 do not have, inserted *before* the generic that fontconfig would
    otherwise resolve on its own. Left to fontconfig, `serif` for Korean text
    on a Linux machine resolves to whatever it likes — commonly a Chinese face,
    which is legible and wrong, and wrong in a way no layout rule can see.

    Emitted as two custom properties rather than whole stacks so each theme
    keeps its own Latin typography: `base.css` and the themes splice
    `var(--script-sans)` / `var(--script-serif)` into their stacks, and this
    fills them in.
    """
    scripts = [s for s in profile.scripts if s != "latin" and s in SCRIPT_INFO]
    if not scripts:
        return ""
    sans: list[str] = []
    serif: list[str] = []
    mono: list[str] = []
    for s in scripts:
        for family in SCRIPT_INFO[s][2]:
            if family not in sans:
                sans.append(family)
        for family in SCRIPT_INFO[s][3]:
            if family not in serif:
                serif.append(family)
        for family in mono_families(s):
            if family not in mono:
                mono.append(family)
    names = ", ".join(SCRIPT_INFO[s][1] for s in scripts)
    block = (
        f"/* ── Faces for the scripts in this document: {names} ── */\n"
        ":root {\n"
        f"  --script-sans: {_families(sans)};\n"
        f"  --script-serif: {_families(serif)};\n"
        f"  --script-mono: {_families(mono)};\n"
        "}"
    )
    upright = [s for s in scripts if s in NO_ITALIC]
    if upright:
        langs = ", ".join(
            f"html:lang({lang}) :lang({lang})" for lang in (SCRIPT_INFO[s][0] for s in upright)
        )
        block += (
            "\n\n/* These scripts have no italic. Asked for one, WeasyPrint\n"
            "   synthesises a slant, which reads as a rendering fault rather\n"
            "   than as emphasis — and it cannot be declined: `font-synthesis:\n"
            "   none` is ignored, and `src: local(…)`, which would let the\n"
            "   italic slot be mapped to the upright face, is not resolved at\n"
            "   all. Both measured on WeasyPrint 68. So the request is\n"
            "   withdrawn instead.\n\n"
            "   The cost is Latin inside these documents, which goes upright\n"
            "   too: CSS selects elements, not scripts, and a Korean caption\n"
            "   with an English title in it is one element. Upright Latin in a\n"
            "   Korean caption is unremarkable; slanted Hangul is not. A\n"
            "   document that wants the italic back says so in brand.css,\n"
            "   which is appended after this and wins.\n\n"
            "   The doubled `:lang()` is specificity, not a typo. Language\n"
            "   inherits, so every element in the document matches both halves;\n"
            "   the second one buys a level. The themes' italic declarations\n"
            "   top out at two classes (`.doc-head .sub`, `.cover .sub`), and\n"
            "   one pseudo-class more than that is what it takes to withdraw\n"
            "   them. Held by a test on the laid-out document, so a new rule\n"
            "   that outranks this says so. */\n"
            f"{langs} {{ font-style: normal; }}"
        )
    return block


def _families(names: list[str]) -> str:
    """Quoted, comma-separated — a font-family list, minus the generic.

    The generic stays in the theme's own stack, which is what these are spliced
    into, so a script that has no face installed still falls through to it.
    """
    return ", ".join(f'"{name}"' for name in names)
