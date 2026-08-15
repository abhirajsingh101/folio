"""Shared guards.

`folio.faces` reads which face pango actually chose, through symbols cffi
resolves on attribute access. Not every build of pango exports them — CI's does
not, on all four of its platform/version pairs — and when they are missing the
two rules that need them go quiet by design. A test that asserts one of those
rules fires is then unrunnable rather than failing, so it skips on a probe
rather than on a platform name.
"""

from __future__ import annotations

import pytest


def faces_available() -> bool:
    try:
        from folio.faces import FacesUnavailable, _ffi
    except Exception:  # pragma: no cover - environment dependent
        return False
    try:
        _ffi()
    except FacesUnavailable:
        return False
    except Exception:  # pragma: no cover - environment dependent
        return False
    return True


needs_faces = pytest.mark.skipif(
    not faces_available(), reason="this pango does not export the face-resolution symbols"
)


@pytest.fixture(scope="session")
def has_faces() -> bool:
    return faces_available()
