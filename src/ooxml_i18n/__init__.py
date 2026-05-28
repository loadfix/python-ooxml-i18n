"""Localisation toolkit for the loadfix python-ooxml family.

A pure-Python helper that lifts user-visible strings out of an OOXML
document, ships them through a standard gettext ``.po`` for offline
translation, then injects the translations back into a copy of the
source. Works across docx / pptx / xlsx / vsdx without needing the
parent library to be installed.

See ``README.md`` for the worked example. Public API:
:func:`extract_strings`, :func:`apply_translations`,
:func:`set_language`, :class:`Strings`,
:class:`OoxmlI18nError` and friends.

Scope (0.1.0): run-level text leaves only — every ``w:t`` / ``a:t``
/ ``s:t`` / ``vsdx:Text`` element. Out of scope: field-code
internals, drawing canvas tooltips, embedded charts.
"""

from __future__ import annotations

from ooxml_i18n.core import apply_translations, extract_strings, set_language
from ooxml_i18n.exceptions import OoxmlI18nError, POFileError, UnsupportedFormatError
from ooxml_i18n.format import detect_format, known_format_tags
from ooxml_i18n.strings import Strings

__version__ = "0.1.0.dev0"

__all__ = [
    "OoxmlI18nError",
    "POFileError",
    "Strings",
    "UnsupportedFormatError",
    "__version__",
    "apply_translations",
    "detect_format",
    "extract_strings",
    "known_format_tags",
    "set_language",
]
