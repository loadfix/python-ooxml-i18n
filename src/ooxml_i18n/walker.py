"""Walk text-bearing leaves across the four OOXML parents.

The :func:`walk_part` generator yields ``(key, text, locator)`` tuples
for every match of the format-specific XPath against a single part.
The key is a stable opaque locator — ``<part>#<index>`` — built from
the part's zip-member path and the zero-based occurrence index of the
leaf within that part's XPath result. Two runs against the same input
yield the same keys, which is what lets ``apply_translations`` look
the values back up after a .po round-trip.

:func:`apply_to_part` does the inverse: rewrite a part's XML in place,
replacing ``leaf.text`` whenever a key in *replacements* matches.
"""

from __future__ import annotations

from typing import Dict, Iterator, Optional, Tuple

from lxml import etree

from ooxml_i18n.constants import (
    DOCX_PART_PATTERNS,
    DOCX_XPATH,
    NSMAP,
    PPTX_PART_PATTERNS,
    PPTX_XPATH,
    VSDX_PART_PATTERNS,
    VSDX_XPATH,
    XLSX_PART_PATTERNS_DRAWING,
    XLSX_PART_PATTERNS_SHARED,
    XLSX_XPATH_DRAWING,
    XLSX_XPATH_SHARED,
)

#: A walker yield value: ``(key, text, locator)``.
WalkHit = Tuple[str, str, str]


def _xml_parser() -> etree.XMLParser:
    """lxml parser with whitespace retained + entity expansion off."""
    return etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)


def part_xpath(format_tag: str, part_name: str) -> str:
    """Return the xpath used to locate text leaves in *part_name*."""
    if format_tag == "docx":
        return DOCX_XPATH
    if format_tag == "pptx":
        return PPTX_XPATH
    if format_tag == "xlsx":
        return XLSX_XPATH_SHARED if "sharedStrings" in part_name else XLSX_XPATH_DRAWING
    if format_tag == "vsdx":
        return VSDX_XPATH
    raise ValueError(f"unknown format tag: {format_tag!r}")


def part_patterns(format_tag: str) -> Tuple[str, ...]:
    """Return the zip-member-name patterns for *format_tag*."""
    if format_tag == "docx":
        return DOCX_PART_PATTERNS
    if format_tag == "pptx":
        return PPTX_PART_PATTERNS
    if format_tag == "xlsx":
        return XLSX_PART_PATTERNS_SHARED + XLSX_PART_PATTERNS_DRAWING
    if format_tag == "vsdx":
        return VSDX_PART_PATTERNS
    raise ValueError(f"unknown format tag: {format_tag!r}")


def walk_part(format_tag: str, part_name: str, xml_bytes: bytes) -> Iterator[WalkHit]:
    """Yield ``(key, text, locator)`` for every text leaf in *part*.

    Empty leaves are skipped — translators don't need to see them and
    round-tripping risks introducing whitespace diffs the caller
    didn't ask for.
    """
    xpath = part_xpath(format_tag, part_name)
    root = etree.fromstring(xml_bytes, parser=_xml_parser())
    for idx, leaf in enumerate(root.xpath(xpath, namespaces=NSMAP)):
        if not isinstance(leaf, etree._Element):  # pragma: no cover - xpath shape guard
            continue
        text = leaf.text or ""
        if text == "":
            continue
        yield f"{part_name}#{idx}", text, part_name


def apply_to_part(
    format_tag: str,
    part_name: str,
    xml_bytes: bytes,
    replacements: Dict[str, str],
) -> Optional[bytes]:
    """Apply *replacements* to *xml_bytes* for *part_name*.

    Returns the mutated XML bytes if any replacement landed, ``None``
    if the part was untouched. The serialiser keeps the XML
    declaration and standalone marker because Office is strict about
    both.
    """
    xpath = part_xpath(format_tag, part_name)
    root = etree.fromstring(xml_bytes, parser=_xml_parser())
    touched = False
    for idx, leaf in enumerate(root.xpath(xpath, namespaces=NSMAP)):
        if not isinstance(leaf, etree._Element):  # pragma: no cover - xpath shape guard
            continue
        key = f"{part_name}#{idx}"
        if key in replacements:
            leaf.text = replacements[key]
            touched = True
    if not touched:
        return None
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
