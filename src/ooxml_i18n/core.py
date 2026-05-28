"""Top-level functional API: extract / apply / set-language."""

from __future__ import annotations

import shutil
import zipfile
from typing import Optional, Union

from ooxml_i18n.format import coerce_path, detect_format, discover_parts
from ooxml_i18n.lang import apply_language
from ooxml_i18n.strings import Strings
from ooxml_i18n.walker import apply_to_part, part_patterns, walk_part


def extract_strings(path: Union[str, "os.PathLike[str]"]) -> Strings:  # noqa: F821
    """Return a :class:`Strings` over every user-visible text leaf in *path*.

    Visits parts in lexicographic order and, within each part, leaves
    in document order. Keys are stable ``<part>#<index>`` strings —
    each run gets its own entry, so translators see natural sentence
    breakpoints rather than one giant blob per paragraph.
    """
    fpath = coerce_path(path)
    fmt = detect_format(fpath)
    patterns = part_patterns(fmt)

    items: dict = {}
    refs: dict = {}
    with zipfile.ZipFile(fpath) as zf:
        for part_name in discover_parts(zf, patterns):
            xml_bytes = zf.read(part_name)
            for key, text, locator in walk_part(fmt, part_name, xml_bytes):
                items[key] = text
                refs[key] = locator
    return Strings(items, format=fmt, references=refs)


def apply_translations(
    source: Union[str, "os.PathLike[str]"],  # noqa: F821
    strings: Strings,
    output: Union[str, "os.PathLike[str]"],  # noqa: F821
) -> None:
    """Copy *source* → *output*, replacing each text leaf whose key
    matches an entry in *strings*.

    Keys not present in the source are silently skipped — this matters
    for evolving documents where a draft .po was written against an
    earlier revision. Untouched members are streamed through
    byte-for-byte so re-opening in Office doesn't trigger a
    "modified" prompt.
    """
    src_path = coerce_path(source)
    out_path = coerce_path(output)
    fmt = detect_format(src_path)

    if strings.format is not None and strings.format != fmt:
        raise ValueError(
            f"Strings was extracted from a {strings.format} package; "
            f"cannot apply to a {fmt} document."
        )

    patterns = part_patterns(fmt)
    replacements = dict(strings.items())

    with zipfile.ZipFile(src_path) as zin:
        text_parts = set(discover_parts(zin, patterns))
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in text_parts:
                    new_bytes = apply_to_part(fmt, info.filename, data, replacements)
                    if new_bytes is not None:
                        data = new_bytes
                zout.writestr(info, data)


def set_language(
    path: Union[str, "os.PathLike[str]"],  # noqa: F821
    lang: str,
    *,
    output: Optional[Union[str, "os.PathLike[str]"]] = None,  # noqa: F821
) -> None:
    """Set the document language to *lang* (BCP-47 / RFC-5646).

    Rewrites in place via a temporary sibling unless *output* is
    given. Run-level overrides (``a:rPr/@lang`` on a single run,
    ``w:lang`` on a single run's ``w:rPr``) are *not* rewritten — those
    are explicit author choices and Office uses them to allow
    multilingual documents. See ``README.md`` for the per-format
    anchor table.
    """
    src_path = coerce_path(path)
    fmt = detect_format(src_path)
    if output is None:
        # Round-trip via a temp sibling so a write failure doesn't
        # destroy the source.
        tmp = src_path + ".i18n.tmp"
        apply_language(src_path, fmt, lang, tmp)
        shutil.move(tmp, src_path)
    else:
        apply_language(src_path, fmt, lang, coerce_path(output))
