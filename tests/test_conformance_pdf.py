"""A document can declare what kind of PDF it needs to be."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("weasyprint", reason="PDF variants are a WeasyPrint feature")

from folio.build import build, detect_pdf_variant  # noqa: E402


def _readable(pdf: Path) -> bytes:
    """PDF bytes with every Flate stream inflated.

    Metadata and the XMP packet live inside compressed streams, so searching
    the raw file finds nothing and proves nothing — which is exactly how the
    first version of these assertions failed against a working implementation.
    """
    import re
    import zlib

    data = pdf.read_bytes()
    out = [data]
    for chunk in re.findall(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            out.append(zlib.decompress(chunk))
        except zlib.error:
            pass
    return b"".join(out)

DOC = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Archive me</title></head>'
    '<body{attr}><p>A document that says what it is for.</p></body></html>'
)


def _write(tmp_path: Path, attr: str = "") -> Path:
    src = tmp_path / "document.html"
    src.write_text(DOC.format(attr=attr), encoding="utf-8")
    return src


def test_a_document_declares_its_variant():
    assert detect_pdf_variant('<body data-pdf="archival">') == "pdf/a-3b"
    assert detect_pdf_variant('<body data-pdf="accessible">') == "pdf/ua-1"
    assert detect_pdf_variant('<body data-pdf="pdf/a-2b">') == "pdf/a-2b"
    assert detect_pdf_variant("<body>") is None


def test_an_unknown_variant_is_refused_rather_than_ignored():
    from folio.build import BuildError

    with pytest.raises(BuildError, match="unknown"):
        detect_pdf_variant('<body data-pdf="pdf/z-9">')


def test_an_archival_document_declares_pdfa_in_its_metadata(tmp_path):
    """Declared, not certified. WeasyPrint does not guarantee validity, so the
    claim folio makes is that the file says what it is — checked by looking for
    the PDF/A identification schema in the XMP packet."""
    build(_write(tmp_path, ' data-pdf="archival"'), also_html=False, quiet=True)
    data = _readable(tmp_path / "document.pdf")
    assert b"pdfaid" in data, "no PDF/A identification in the XMP"


def test_an_ordinary_document_claims_nothing(tmp_path):
    build(_write(tmp_path), also_html=False, quiet=True)
    assert b"pdfaid" not in _readable(tmp_path / "document.pdf")


def test_the_title_reaches_the_pdf(tmp_path):
    build(_write(tmp_path), also_html=False, quiet=True)
    assert b"Archive me" in _readable(tmp_path / "document.pdf")
