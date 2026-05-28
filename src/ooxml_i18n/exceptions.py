"""Exceptions raised by :mod:`ooxml_i18n`.

A small hierarchy rooted at :class:`OoxmlI18nError` so callers can catch
either everything from this package, or a more specific class.
"""

from __future__ import annotations


class OoxmlI18nError(Exception):
    """Base for every error raised by ``ooxml_i18n``."""


class UnsupportedFormatError(OoxmlI18nError):
    """The file at *path* is not a recognised OOXML container.

    The toolkit recognises one of ``.docx`` / ``.pptx`` / ``.xlsx`` /
    ``.vsdx`` / ``.vsdm`` / ``.docm`` / ``.pptm`` / ``.xlsm`` by content,
    not by filename. This error fires when the package layout doesn't
    match any of those.
    """


class POFileError(OoxmlI18nError):
    """Malformed gettext .po input.

    Raised by :meth:`Strings.from_pofile` when the file isn't a valid
    .po stream — unterminated string, missing ``msgid`` before
    ``msgstr``, or invalid escape sequence.
    """
