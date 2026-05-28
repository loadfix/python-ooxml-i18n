"""Minimal gettext .po reader/writer.

We don't pull `babel` or `polib` — the format is text and the subset
we need (no plural forms, no contexts, no obsolete entries) is small
enough to hand-roll. Supported: ``msgid``/``msgstr`` pairs with
multi-line continuation strings, ``#:`` reference comments, standard
C-style escapes (``\\n`` / ``\\t`` / ``\\r`` / ``\\\\`` / ``\\"``),
and a UTF-8 header entry. Out of scope: ``msgctxt``, plurals, fuzzy
flags, obsolete entries.
"""

from __future__ import annotations

import io
from typing import Dict, Iterable, List, Optional, Tuple

from ooxml_i18n.exceptions import POFileError

#: gettext PO header — written verbatim at the top of every file we
#: emit. Keeps tools like Poedit happy.
_DEFAULT_HEADER = (
    'Content-Type: text/plain; charset=UTF-8\\n'
    'Content-Transfer-Encoding: 8bit\\n'
    'X-Generator: python-ooxml-i18n\\n'
)


def _escape(text: str) -> str:
    """Encode *text* for inclusion in a quoted .po string."""
    out: List[str] = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


_ESCAPE_MAP = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}


def _unescape(s: str) -> str:
    """Decode a quoted .po string body (without the surrounding quotes)."""
    out: List[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\":
            if i + 1 >= n:
                raise POFileError("trailing backslash in quoted string")
            nxt = s[i + 1]
            # Permissive on unknown escapes: gettext itself does that.
            out.append(_ESCAPE_MAP.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _read_quoted(line: str) -> str:
    """Strip surrounding double quotes from a .po body line."""
    line = line.strip()
    if not (line.startswith('"') and line.endswith('"')):
        raise POFileError(f"expected quoted string, got: {line!r}")
    return _unescape(line[1:-1])


def write_pofile(
    entries: Iterable[Tuple[str, str, Optional[str]]],
    path: str,
    *,
    header: Optional[str] = None,
) -> None:
    """Serialise *entries* to *path*.

    Each entry is ``(msgid, msgstr, reference)``. *reference* lands
    as a ``#:`` source-locator comment.
    """
    buf = io.StringIO()
    buf.write('msgid ""\nmsgstr ""\n')
    body = header if header is not None else _DEFAULT_HEADER
    # Fold the header into one continuation line per "\n" terminator.
    for piece in body.split("\\n"):
        if piece == "" and body.endswith("\\n"):
            continue
        buf.write(f'"{piece}\\n"\n')
    buf.write("\n")
    for msgid, msgstr, reference in entries:
        if reference:
            buf.write(f"#: {reference}\n")
        buf.write(f'msgid "{_escape(msgid)}"\n')
        buf.write(f'msgstr "{_escape(msgstr)}"\n\n')
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(buf.getvalue())


def read_pofile(path: str) -> Dict[str, str]:
    """Parse *path*; return ``{msgid: msgstr}`` (header entry dropped).

    Blank ``msgstr`` is preserved — callers can treat it as
    "untranslated, fall back to msgid".
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    out: Dict[str, str] = {}
    i = 0
    n = len(lines)

    def collect(start: int) -> Tuple[str, int]:
        """Read a keyword's quoted body + any continuation lines."""
        _, _, rest = lines[start].strip().partition(" ")
        parts: List[str] = [_read_quoted(rest)]
        j = start + 1
        while j < n:
            nxt = lines[j].strip()
            if nxt.startswith('"') and nxt.endswith('"'):
                parts.append(_read_quoted(nxt))
                j += 1
            else:
                break
        return "".join(parts), j

    while i < n:
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if line.startswith("msgid"):
            msgid, i = collect(i)
            if i >= n:
                raise POFileError("EOF after msgid (expected msgstr)")
            if not lines[i].strip().startswith("msgstr"):
                raise POFileError(f"expected msgstr, got: {lines[i].strip()!r}")
            msgstr, i = collect(i)
            if msgid:
                out[msgid] = msgstr
        else:
            i += 1
    return out
