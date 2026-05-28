"""Detect which OOXML parent a file belongs to.

Detection is two-stage:

1. Suffix-based fast path — most OOXML packages on disk have a
   meaningful extension and we honour it.
2. Content-based fallback — if the suffix is unknown, we open the zip
   and inspect ``[Content_Types].xml`` for a parent-specific
   discriminator.

This keeps ``extract_strings`` / ``apply_translations`` working even
when a caller hands us ``report.zip`` or a ``BytesIO`` payload.
"""

from __future__ import annotations

import os
import zipfile
from typing import Optional

from ooxml_i18n.constants import FORMAT_BY_SUFFIX
from ooxml_i18n.exceptions import UnsupportedFormatError


def detect_format(path: str) -> str:
    """Return the parent tag for *path*: ``docx`` / ``pptx`` / ``xlsx`` / ``vsdx``.

    Raises :class:`UnsupportedFormatError` if the file is not one of
    the four parents the toolkit understands.
    """
    suffix = os.path.splitext(path)[1].lower()
    fast = FORMAT_BY_SUFFIX.get(suffix)
    if fast is not None:
        return fast
    return _detect_from_content(path)


def _detect_from_content(path: str) -> str:
    """Inspect ``[Content_Types].xml`` to identify the parent."""
    try:
        with zipfile.ZipFile(path) as zf:
            try:
                ct_xml = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
            except KeyError as e:
                raise UnsupportedFormatError(
                    f"{path}: not an OOXML package (no [Content_Types].xml)"
                ) from e
    except zipfile.BadZipFile as e:
        raise UnsupportedFormatError(f"{path}: not a zip container") from e

    # Match content-type substrings rather than parsing the XML — saves
    # a parse round-trip and is unambiguous because each parent uses
    # one and only one of these strings.
    if "wordprocessingml.document" in ct_xml or "wordprocessingml.template" in ct_xml:
        return "docx"
    if "presentationml.presentation" in ct_xml or "presentationml.template" in ct_xml:
        return "pptx"
    if "spreadsheetml.sheet" in ct_xml or "spreadsheetml.template" in ct_xml:
        return "xlsx"
    if "ms-visio.drawing" in ct_xml or "ms-visio.template" in ct_xml:
        return "vsdx"

    raise UnsupportedFormatError(
        f"{path}: not a recognised OOXML package (unknown content types)"
    )


def discover_parts(zf: zipfile.ZipFile, patterns: tuple) -> list:
    """Return zip member names matching any substring in *patterns*.

    Members are returned in lexicographic order so the key stream is
    deterministic across runs.
    """
    out: list = []
    for name in zf.namelist():
        if not name.endswith(".xml"):
            continue
        if any(pat in name for pat in patterns):
            out.append(name)
    out.sort()
    return out


def coerce_path(p: object) -> str:
    """Accept either ``str`` or ``os.PathLike``; return ``str``."""
    if isinstance(p, (bytes, bytearray, memoryview)):
        raise TypeError("expected a filesystem path, got bytes")
    return os.fspath(p)  # type: ignore[arg-type]


def known_format_tags() -> tuple:
    """Return the canonical ordered tuple of supported parent tags."""
    return ("docx", "pptx", "xlsx", "vsdx")


def format_for_extension(suffix: str) -> Optional[str]:
    """Return the parent tag for *suffix*, or ``None`` if unknown."""
    return FORMAT_BY_SUFFIX.get(suffix.lower())
