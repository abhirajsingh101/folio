"""Which face actually set a run of text.

Every other measurement folio takes reads the layout tree, which records what
the stylesheet asked for. This one reads what pango chose, which is a different
thing whenever the asked-for family is not installed: a font stack falls
through per glyph, and when it runs out fontconfig answers — never failing,
never asking, and for Korean on Linux commonly answering with a Chinese face.

The route is not the obvious one, and each step of it is counter-intuitive:

  * WeasyPrint frees a text box's pango layout after layout (`deactivate` does
    `del self.layout`). `reactivate(style)` rebuilds it, which is exactly what
    the draw stage calls before painting — so the shaping read here is the
    shaping the PDF receives.
  * `hb_font_get_face` is not declared in WeasyPrint's cffi surface.
  * `pango_fc_font_map_get_hb_face` lives in libpangoft2, not libpango.
    Calling it on `pango` raises `undefined symbol`.
  * Both its arguments need explicit casts, or cffi refuses the call.

No new dependency: the GSUB feature list is parsed with `struct` rather than
fontTools, because `pyproject.toml` promises a broken install is still a
working one.
"""

from __future__ import annotations

import struct


class FacesUnavailable(RuntimeError):
    """Raised when the resolved face cannot be read on this platform."""


def _ffi():
    try:
        from weasyprint.text.ffi import ffi, harfbuzz, pango, pangoft2
    except Exception as exc:  # pragma: no cover - environment dependent
        raise FacesUnavailable("WeasyPrint's pango bindings are unavailable") from exc
    return ffi, pango, pangoft2, harfbuzz


def _first_line(textbox):
    """The pango line for this box, reactivating the layout if it was freed."""
    layout = textbox.pango_layout
    if not hasattr(layout, "layout"):
        layout.reactivate(textbox.style)
    line, _ = layout.get_first_line()
    return layout, line


def resolved_runs(textbox) -> list[tuple[str, str]]:
    """[(text, family)] per pango run — the face that set each piece."""
    ffi, pango, _pangoft2, _harfbuzz = _ffi()
    layout, line = _first_line(textbox)
    utf8 = layout.text.encode()
    out: list[tuple[str, str]] = []
    run = line.runs[0]
    while run != ffi.NULL:
        item = run.data.item
        run = run.next
        piece = utf8[item.offset : item.offset + item.length].decode("utf-8", "replace")
        description = ffi.gc(
            pango.pango_font_describe(item.analysis.font),
            pango.pango_font_description_free,
        )
        family = ffi.string(pango.pango_font_description_get_family(description)).decode()
        out.append((piece, family))
    return out


def _hb_face(font):
    """The harfbuzz face behind a pango font.

    See the module docstring: this is the one route that works, and getting
    either the library or the casts wrong raises rather than quietly returning
    something else.
    """
    ffi, pango, pangoft2, _harfbuzz = _ffi()
    font_map = pango.pango_font_get_font_map(font)
    return pangoft2.pango_fc_font_map_get_hb_face(
        ffi.cast("PangoFcFontMap *", font_map), ffi.cast("PangoFcFont *", font)
    )


def feature_tags(textbox) -> set[str]:
    """OpenType GSUB feature tags of the face that set this box's first run.

    The GSUB header holds the FeatureList offset at byte 6, and a FeatureList
    is a count followed by fixed six-byte records whose first four bytes are
    the tag. Twenty lines, and no dependency.
    """
    ffi, _pango, _pangoft2, harfbuzz = _ffi()
    _layout, line = _first_line(textbox)
    face = _hb_face(line.runs[0].data.item.analysis.font)
    blob = harfbuzz.hb_face_reference_table(face, harfbuzz.hb_tag_from_string(b"GSUB", -1))
    try:
        if not harfbuzz.hb_blob_get_length(blob):
            return set()
        with ffi.new("unsigned int *") as length:
            data = ffi.unpack(harfbuzz.hb_blob_get_data(blob, length), int(length[0]))
    finally:
        harfbuzz.hb_blob_destroy(blob)
    if len(data) < 10:
        return set()
    (feature_list,) = struct.unpack_from(">H", data, 6)
    (count,) = struct.unpack_from(">H", data, feature_list)
    return {
        struct.unpack_from(">4s", data, feature_list + 2 + i * 6)[0].decode("ascii", "replace")
        for i in range(count)
    }
