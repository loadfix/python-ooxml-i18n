"""Document-language setter.

Each parent format pins the ambient document language on a different
anchor — see :data:`~ooxml_i18n.constants.DOCX_LANG_XPATH` &c. for the
specifics. This module's :func:`apply_language` owns the rewrite plus
the ``[Content_Types].xml`` left-untouched invariant.
"""

from __future__ import annotations

import zipfile
from typing import Optional

from lxml import etree

from ooxml_i18n.constants import (
    DOCX_LANG_PART,
    DOCX_LANG_XPATH,
    NSMAP,
    PPTX_LANG_PART,
    PPTX_LANG_XPATH,
    VSDX_LANG_PART,
    VSDX_LANG_XPATH,
    W_NS,
    XLSX_LANG_PART,
    XML_NS,
)


def _parser() -> etree.XMLParser:
    return etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)


def _serialise(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _set_docx_lang(zin: zipfile.ZipFile, lang: str) -> Optional[bytes]:
    """Mutate ``word/styles.xml``'s default ``w:lang`` triple."""
    try:
        xml_bytes = zin.read(DOCX_LANG_PART)
    except KeyError:
        return None
    root = etree.fromstring(xml_bytes, parser=_parser())
    lang_elts = root.xpath(DOCX_LANG_XPATH, namespaces=NSMAP)
    if not lang_elts:
        # No default lang yet — synthesise one inside the existing
        # rPrDefault > rPr (creating the chain if needed).
        defaults = root.xpath(".//w:docDefaults", namespaces=NSMAP)
        if not defaults:
            return None
        rpr_default = defaults[0].find(f"{{{W_NS}}}rPrDefault")
        if rpr_default is None:
            rpr_default = etree.SubElement(defaults[0], f"{{{W_NS}}}rPrDefault")
        rpr = rpr_default.find(f"{{{W_NS}}}rPr")
        if rpr is None:
            rpr = etree.SubElement(rpr_default, f"{{{W_NS}}}rPr")
        lang_elt = etree.SubElement(rpr, f"{{{W_NS}}}lang")
    else:
        lang_elt = lang_elts[0]
    # Office writes lang on three attributes (Latin / EastAsia / cs);
    # rewriting all three keeps run-level behaviour consistent.
    lang_elt.set(f"{{{W_NS}}}val", lang)
    lang_elt.set(f"{{{W_NS}}}eastAsia", lang)
    lang_elt.set(f"{{{W_NS}}}bidi", lang)
    return _serialise(root)


def _set_pptx_lang(zin: zipfile.ZipFile, lang: str) -> Optional[bytes]:
    """Set ``a:defRPr/@lang`` inside ``ppt/presentation.xml``."""
    try:
        xml_bytes = zin.read(PPTX_LANG_PART)
    except KeyError:
        return None
    root = etree.fromstring(xml_bytes, parser=_parser())
    # First, the cheap path: per-presentation default rPr.
    elts = root.xpath(PPTX_LANG_XPATH, namespaces=NSMAP)
    touched = False
    for elt in elts:
        elt.set("lang", lang)
        touched = True
    # Also update the presentation-level @defaultTextStyle children
    # (lvl1pPr through lvl9pPr, since Office writes nine levels).
    for elt in root.xpath(".//p:defaultTextStyle/*/a:defRPr", namespaces=NSMAP):
        elt.set("lang", lang)
        touched = True
    if not touched:
        # As a last resort, drop a lang attr on the document root —
        # the schema defines a presentation-level "lang" attribute.
        root.set("lang", lang)
    return _serialise(root)


def _set_xlsx_lang(zin: zipfile.ZipFile, lang: str) -> Optional[bytes]:
    """Annotate ``xl/workbook.xml``'s root with a language hint."""
    try:
        xml_bytes = zin.read(XLSX_LANG_PART)
    except KeyError:
        return None
    root = etree.fromstring(xml_bytes, parser=_parser())
    # SpreadsheetML has no first-class doc-language attribute; the
    # accepted convention is xml:lang on the workbook root, which
    # Office tolerates and Calc honours for spell-check selection.
    root.set(f"{{{XML_NS}}}lang", lang)
    return _serialise(root)


def _set_vsdx_lang(zin: zipfile.ZipFile, lang: str) -> Optional[bytes]:
    """Mutate ``visio/document.xml``'s DocumentSettings/@DefaultLangID."""
    try:
        xml_bytes = zin.read(VSDX_LANG_PART)
    except KeyError:
        return None
    root = etree.fromstring(xml_bytes, parser=_parser())
    settings = root.xpath(VSDX_LANG_XPATH, namespaces=NSMAP)
    if not settings:
        return None
    settings[0].set("DefaultLangID", lang)
    settings[0].set(f"{{{XML_NS}}}lang", lang)
    return _serialise(root)


_SETTERS = {
    "docx": _set_docx_lang,
    "pptx": _set_pptx_lang,
    "xlsx": _set_xlsx_lang,
    "vsdx": _set_vsdx_lang,
}


def apply_language(src: str, format_tag: str, lang: str, dst: str) -> None:
    """Copy *src* → *dst* and rewrite the document language to *lang*.

    The package is otherwise byte-for-byte preserved: every member that
    isn't the language anchor is streamed through unchanged. We rebuild
    the zip rather than mutating in place because zipfile cannot edit
    a member's bytes once written.
    """
    setter = _SETTERS[format_tag]
    with zipfile.ZipFile(src) as zin:
        new_bytes = setter(zin, lang)
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if new_bytes is not None and info.filename == _lang_part(format_tag):
                    data = new_bytes
                zout.writestr(info, data)


def _lang_part(format_tag: str) -> str:
    return {
        "docx": DOCX_LANG_PART,
        "pptx": PPTX_LANG_PART,
        "xlsx": XLSX_LANG_PART,
        "vsdx": VSDX_LANG_PART,
    }[format_tag]
