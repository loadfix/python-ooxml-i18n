"""Namespace URIs and per-format string locators used by ``ooxml_i18n``.

The four parents store user-visible text in different element shapes.
Rather than depend on every ``CT_*`` class across the family, this
package walks the raw XML with lxml. It needs only:

- The XML namespace URIs for the four formats.
- An XPath that selects the text-bearing leaves inside any one part.

Both live here as constants so the walker stays pure data-driven.
"""

from __future__ import annotations

# --- XML namespaces -----------------------------------------------------

#: WordprocessingML main namespace (``w:``).
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

#: PresentationML main namespace (``p:``).
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"

#: SpreadsheetML main namespace (``s:``, but the spec also uses no prefix).
S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

#: DrawingML main namespace (``a:``) — shared text inside pptx + xlsx
#: shapes.
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

#: Visio core namespace (``vsdx:``, but unprefixed in real packages).
V_NS = "http://schemas.microsoft.com/office/visio/2011/1/core"

#: ``xml:`` namespace — used for ``xml:lang``.
XML_NS = "http://www.w3.org/XML/1998/namespace"

#: nsmap fed into every lxml ``xpath()`` call.
NSMAP = {
    "w": W_NS,
    "p": P_NS,
    "s": S_NS,
    "a": A_NS,
    "v": V_NS,
    "xml": XML_NS,
}


# --- Text-bearing locators ---------------------------------------------
# XPaths run against the root element of one part. ``w:instrText`` is
# excluded from ``DOCX_XPATH`` because it carries field codes, not
# display text. Visio's ``Text`` element contains a ``<cp>`` separated
# mixed-content stream — we read+write the string content only.

DOCX_XPATH = ".//w:t"
PPTX_XPATH = ".//a:t"
XLSX_XPATH_SHARED = ".//s:t"
XLSX_XPATH_DRAWING = ".//a:t"
VSDX_XPATH = ".//v:Text"


# --- Part filters -------------------------------------------------------
# Only parts that *can* carry user-visible text — skipping theme.xml,
# app.xml, content-type tables, etc. tightens the .po surface.
DOCX_PART_PATTERNS = (
    "word/document.xml",
    "word/header",
    "word/footer",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/comments.xml",
    "word/glossary/document.xml",
)

PPTX_PART_PATTERNS = (
    "ppt/slides/slide",
    "ppt/notesSlides/notesSlide",
    "ppt/slideLayouts/slideLayout",
    "ppt/slideMasters/slideMaster",
    "ppt/notesMasters/notesMaster",
    "ppt/handoutMasters/handoutMaster",
    "ppt/comments/comment",
    "ppt/diagrams/data",
)

XLSX_PART_PATTERNS_SHARED = ("xl/sharedStrings.xml",)
XLSX_PART_PATTERNS_DRAWING = ("xl/drawings/drawing", "xl/charts/chart")

VSDX_PART_PATTERNS = (
    "visio/pages/page",
    "visio/masters/master",
)


# --- Document-language anchors -----------------------------------------
# ``set_language()`` writes a single document-level tag per format
# without touching run-level overrides.

DOCX_LANG_PART = "word/styles.xml"
DOCX_LANG_XPATH = ".//w:docDefaults/w:rPrDefault/w:rPr/w:lang"

PPTX_LANG_PART = "ppt/presentation.xml"
PPTX_LANG_XPATH = ".//p:defaultTextStyle/a:lvl1pPr/a:defRPr"

#: xlsx has no first-class doc-language attribute. We use ``xml:lang``
#: on the workbook root — Office tolerates it, Calc honours it.
XLSX_LANG_PART = "xl/workbook.xml"

VSDX_LANG_PART = "visio/document.xml"
VSDX_LANG_XPATH = ".//v:DocumentSettings"


# --- File-extension to format mapping -----------------------------------

#: Recognised parent formats keyed by lower-case suffix. The values are
#: the short tags used internally to dispatch walkers / lang-setters.
FORMAT_BY_SUFFIX = {
    ".docx": "docx",
    ".docm": "docx",
    ".dotx": "docx",
    ".dotm": "docx",
    ".pptx": "pptx",
    ".pptm": "pptx",
    ".potx": "pptx",
    ".potm": "pptx",
    ".ppsx": "pptx",
    ".ppsm": "pptx",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".xltx": "xlsx",
    ".xltm": "xlsx",
    ".vsdx": "vsdx",
    ".vsdm": "vsdx",
    ".vstx": "vsdx",
    ".vstm": "vsdx",
}
