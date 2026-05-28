"""The :class:`Strings` value object — dict-like with .po round-tripping."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Tuple

from ooxml_i18n.pofile import read_pofile, write_pofile


class Strings:
    """Ordered ``{key: text}`` map with .po I/O.

    Dict-like (``len`` / ``in`` / ``[]`` / ``.items`` / ``.keys`` /
    ``.values`` / ``.update`` / ``.copy``) plus two extras:

    - The *parent format tag* (``docx`` / ``pptx`` / ``xlsx`` /
      ``vsdx``) the strings came from, so :func:`apply_translations`
      can fail fast on a mismatch.
    - A *reference locator* per key, surfaced as ``#:`` comments in
      .po output so translators can see context.
    """

    __slots__ = ("_data", "_refs", "_format")

    def __init__(
        self,
        items: Optional[Dict[str, str]] = None,
        *,
        format: Optional[str] = None,
        references: Optional[Dict[str, str]] = None,
    ) -> None:
        self._data: Dict[str, str] = dict(items or {})
        self._refs: Dict[str, str] = dict(references or {})
        self._format: Optional[str] = format

    # --- container protocol ---------------------------------------------

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self._refs.pop(key, None)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Strings):
            return self._data == other._data
        if isinstance(other, dict):
            return self._data == other
        return NotImplemented

    def __repr__(self) -> str:
        fmt = f" format={self._format!r}" if self._format else ""
        return f"Strings({len(self._data)} entries{fmt})"

    # --- dict-style helpers ---------------------------------------------

    def keys(self) -> List[str]:
        """Return a list of keys in insertion order."""
        return list(self._data)

    def values(self) -> List[str]:
        """Return a list of values in insertion order."""
        return list(self._data.values())

    def items(self) -> List[Tuple[str, str]]:
        """Return a list of ``(key, value)`` pairs in insertion order."""
        return list(self._data.items())

    def get(self, key: str, default: Any = None) -> Any:
        """``dict.get`` for the underlying mapping."""
        return self._data.get(key, default)

    def update(self, other: Any) -> None:
        """Bulk-update entries from another :class:`Strings` or dict."""
        if isinstance(other, Strings):
            self._data.update(other._data)
            self._refs.update(other._refs)
        else:
            self._data.update(other)

    def copy(self) -> Strings:
        """Return a shallow copy preserving format + references."""
        return Strings(self._data, format=self._format, references=self._refs)

    # --- metadata --------------------------------------------------------

    @property
    def format(self) -> Optional[str]:
        """Parent-format tag the strings were extracted from."""
        return self._format

    def reference(self, key: str) -> Optional[str]:
        """Return the source-locator comment for *key*, if any."""
        return self._refs.get(key)

    def set_reference(self, key: str, ref: str) -> None:
        """Attach (or replace) a source locator for *key*."""
        self._refs[key] = ref

    # --- .po I/O ---------------------------------------------------------

    def to_pofile(self, path: str) -> None:
        """Serialise to *path* in standard gettext .po format.

        Initial values double as both ``msgid`` and ``msgstr`` —
        translators replace each ``msgstr`` with the target language.
        """
        entries = [(k, v, self._refs.get(k)) for k, v in self._data.items()]
        write_pofile(entries, path)

    @classmethod
    def from_pofile(cls, path: str, *, format: Optional[str] = None) -> Strings:
        """Load *path* into a fresh :class:`Strings`.

        Untranslated entries (blank ``msgstr``) are dropped so they
        don't blank the source text on apply.
        """
        kept = {k: v for k, v in read_pofile(path).items() if v != ""}
        return cls(kept, format=format)
