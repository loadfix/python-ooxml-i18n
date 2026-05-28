"""Hand-rolled minimal-OOXML builders for unit tests.

Avoiding dependencies on the parent libraries keeps this package
testable in isolation — and equally importantly, keeps each fixture
small enough to read at a glance.
"""

from __future__ import annotations

import zipfile
from typing import List, Tuple


def _write_zip(path: str, members: List[Tuple[str, str]]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in members:
            zf.writestr(name, body)


def _rels_root(target: str, rel_type: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{rel_type}" Target="{target}"/></Relationships>'
    )


def _ct_xml(*overrides: Tuple[str, str]) -> str:
    body = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
    )
    for part, ct in overrides:
        body += f'<Override PartName="{part}" ContentType="{ct}"/>'
    return body + "</Types>"


_R_OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
_R_VISIO = "http://schemas.microsoft.com/visio/2010/relationships/document"

_DOCX_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr><w:lang w:val="en-US"/></w:rPr>'
    '</w:rPrDefault></w:docDefaults></w:styles>'
)

_PPTX_PRESENTATION = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    '<p:defaultTextStyle><a:lvl1pPr><a:defRPr lang="en-US"/></a:lvl1pPr></p:defaultTextStyle>'
    '</p:presentation>'
)

_XLSX_WORKBOOK = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'
)

_VSDX_DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2011/1/core">'
    '<DocumentSettings DefaultLangID="1033"/></VisioDocument>'
)


def build_docx(path: str, paragraphs: List[str]) -> None:
    """Write a minimal .docx with one paragraph per *paragraphs* entry."""
    runs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>' for t in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{runs}</w:body></w:document>'
    )
    _write_zip(path, [
        ("[Content_Types].xml", _ct_xml(
            ("/word/document.xml",
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
            ("/word/styles.xml",
             "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"),
        )),
        ("_rels/.rels", _rels_root("word/document.xml", _R_OFFICE)),
        ("word/document.xml", document),
        ("word/styles.xml", _DOCX_STYLES),
    ])


def build_pptx(path: str, slide_paragraphs: List[List[str]]) -> None:
    """Write a minimal .pptx — one slide per outer-list entry."""
    overrides: List[Tuple[str, str]] = [
        ("/ppt/presentation.xml",
         "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
    ]
    members: List[Tuple[str, str]] = []
    for n, runs in enumerate(slide_paragraphs, start=1):
        paragraphs = "".join(f'<a:p><a:r><a:t>{t}</a:t></a:r></a:p>' for t in runs)
        slide = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
            ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:cSld><p:spTree><p:sp><p:txBody>{paragraphs}'
            '</p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
        )
        overrides.append((f"/ppt/slides/slide{n}.xml",
                          "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"))
        members.append((f"ppt/slides/slide{n}.xml", slide))
    _write_zip(path, [
        ("[Content_Types].xml", _ct_xml(*overrides)),
        ("_rels/.rels", _rels_root("ppt/presentation.xml", _R_OFFICE)),
        ("ppt/presentation.xml", _PPTX_PRESENTATION),
        *members,
    ])


def build_xlsx(path: str, shared_strings: List[str]) -> None:
    """Write a minimal .xlsx with the given shared strings."""
    si = "".join(f"<si><t>{t}</t></si>" for t in shared_strings)
    sst = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        f' count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{si}</sst>'
    )
    _write_zip(path, [
        ("[Content_Types].xml", _ct_xml(
            ("/xl/workbook.xml",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
            ("/xl/sharedStrings.xml",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"),
        )),
        ("_rels/.rels", _rels_root("xl/workbook.xml", _R_OFFICE)),
        ("xl/workbook.xml", _XLSX_WORKBOOK),
        ("xl/sharedStrings.xml", sst),
    ])


def build_vsdx(path: str, page_texts: List[Tuple[int, str]]) -> None:
    """Write a minimal .vsdx with one shape per *page_texts* entry."""
    by_page: dict = {}
    for pid, text in page_texts:
        by_page.setdefault(pid, []).append(text)
    overrides: List[Tuple[str, str]] = [
        ("/visio/document.xml", "application/vnd.ms-visio.drawing.main+xml"),
    ]
    members: List[Tuple[str, str]] = []
    for pid, texts in sorted(by_page.items()):
        shapes = "".join(
            f"<Shape ID='{i + 1}'><Text>{t}</Text></Shape>"
            for i, t in enumerate(texts)
        )
        page = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<PageContents xmlns="http://schemas.microsoft.com/office/visio/2011/1/core">'
            f'<Shapes>{shapes}</Shapes></PageContents>'
        )
        overrides.append((f"/visio/pages/page{pid}.xml",
                          "application/vnd.ms-visio.page+xml"))
        members.append((f"visio/pages/page{pid}.xml", page))
    _write_zip(path, [
        ("[Content_Types].xml", _ct_xml(*overrides)),
        ("_rels/.rels", _rels_root("visio/document.xml", _R_VISIO)),
        ("visio/document.xml", _VSDX_DOCUMENT),
        *members,
    ])
