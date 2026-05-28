"""End-to-end extract / apply round-trip per parent format."""

from __future__ import annotations

import zipfile

import pytest
from lxml import etree

from ooxml_i18n import (
    Strings,
    apply_translations,
    extract_strings,
    set_language,
)
from ooxml_i18n.constants import (
    A_NS,
    NSMAP,
    S_NS,
    V_NS,
    W_NS,
    XML_NS,
)
from tests.unit._builders import build_docx, build_pptx, build_vsdx, build_xlsx


def _read_part(path: str, member: str) -> etree._Element:
    with zipfile.ZipFile(path) as zf:
        return etree.fromstring(zf.read(member))


class DescribeDocx:
    def it_extracts_run_text_with_stable_keys(self, tmp_path):
        docx = str(tmp_path / "in.docx")
        build_docx(docx, ["alpha", "bravo", "charlie"])
        first = extract_strings(docx)
        second = extract_strings(docx)
        assert first.format == "docx"
        assert list(first.values()) == ["alpha", "bravo", "charlie"]
        # Keys are deterministic across runs.
        assert first.keys() == second.keys()
        assert all("word/document.xml" in k for k in first.keys())

    def it_round_trips_through_po_and_apply(self, tmp_path):
        src = str(tmp_path / "in.docx")
        po = str(tmp_path / "es.po")
        out = str(tmp_path / "out.docx")
        build_docx(src, ["hello", "world"])

        extract_strings(src).to_pofile(po)
        loaded = Strings.from_pofile(po, format="docx")
        translated = Strings(
            {k: ("hola" if v == "hello" else "mundo") for k, v in loaded.items()},
            format="docx",
        )
        apply_translations(src, translated, output=out)
        assert list(extract_strings(out).values()) == ["hola", "mundo"]

    def it_skips_keys_not_present_in_the_source(self, tmp_path):
        src = str(tmp_path / "in.docx")
        out = str(tmp_path / "out.docx")
        build_docx(src, ["hello"])
        ghost = Strings(
            {"word/document.xml#99": "ghost", "word/document.xml#0": "hola"},
            format="docx",
        )
        apply_translations(src, ghost, output=out)
        assert list(extract_strings(out).values()) == ["hola"]

    def it_rejects_a_format_mismatch_on_apply(self, tmp_path):
        src = str(tmp_path / "in.docx")
        out = str(tmp_path / "out.docx")
        build_docx(src, ["hello"])
        with pytest.raises(ValueError):
            apply_translations(
                src, Strings({"word/document.xml#0": "x"}, format="pptx"), output=out
            )


class DescribePptx:
    def it_extracts_text_from_slides(self, tmp_path):
        pptx = str(tmp_path / "in.pptx")
        build_pptx(pptx, [["slide-one-line-one"], ["slide-two-line-one", "slide-two-line-two"]])
        strings = extract_strings(pptx)
        assert strings.format == "pptx"
        # Two slides, three runs total.
        assert len(strings) == 3
        # Slide 1 keys come before slide 2 because zip members are sorted.
        keys = strings.keys()
        assert "slide1" in keys[0]
        assert "slide2" in keys[-1]

    def it_round_trips_a_translation(self, tmp_path):
        src = str(tmp_path / "in.pptx")
        out = str(tmp_path / "out.pptx")
        build_pptx(src, [["hello"], ["world"]])
        strings = extract_strings(src)
        translated = Strings(
            {k: v.upper() for k, v in strings.items()}, format="pptx"
        )
        apply_translations(src, translated, output=out)
        applied = extract_strings(out)
        assert list(applied.values()) == ["HELLO", "WORLD"]


class DescribeXlsx:
    def it_extracts_shared_strings(self, tmp_path):
        xlsx = str(tmp_path / "in.xlsx")
        build_xlsx(xlsx, ["alpha", "bravo", "charlie"])
        strings = extract_strings(xlsx)
        assert strings.format == "xlsx"
        assert list(strings.values()) == ["alpha", "bravo", "charlie"]

    def it_round_trips_a_translation(self, tmp_path):
        src = str(tmp_path / "in.xlsx")
        out = str(tmp_path / "out.xlsx")
        build_xlsx(src, ["hello", "world"])
        strings = extract_strings(src)
        translated = Strings({k: v[::-1] for k, v in strings.items()}, format="xlsx")
        apply_translations(src, translated, output=out)
        applied = extract_strings(out)
        assert list(applied.values()) == ["olleh", "dlrow"]


class DescribeVsdx:
    def it_extracts_shape_text_from_pages(self, tmp_path):
        vsdx = str(tmp_path / "in.vsdx")
        build_vsdx(vsdx, [(1, "process"), (1, "decision"), (2, "end")])
        strings = extract_strings(vsdx)
        assert strings.format == "vsdx"
        assert sorted(strings.values()) == ["decision", "end", "process"]

    def it_round_trips_a_translation(self, tmp_path):
        src = str(tmp_path / "in.vsdx")
        out = str(tmp_path / "out.vsdx")
        build_vsdx(src, [(1, "start"), (1, "end")])
        strings = extract_strings(src)
        translated = Strings({k: v.upper() for k, v in strings.items()}, format="vsdx")
        apply_translations(src, translated, output=out)
        assert sorted(extract_strings(out).values()) == ["END", "START"]


class DescribeSetLanguageDocx:
    def it_rewrites_the_default_lang_triple(self, tmp_path):
        path = str(tmp_path / "in.docx")
        build_docx(path, ["hello"])
        set_language(path, "es-ES")
        styles = _read_part(path, "word/styles.xml")
        lang_elt = styles.xpath(
            ".//w:docDefaults/w:rPrDefault/w:rPr/w:lang", namespaces=NSMAP
        )[0]
        assert lang_elt.get(f"{{{W_NS}}}val") == "es-ES"
        assert lang_elt.get(f"{{{W_NS}}}eastAsia") == "es-ES"

    def it_writes_to_a_separate_output(self, tmp_path):
        src = str(tmp_path / "in.docx")
        out = str(tmp_path / "out.docx")
        build_docx(src, ["hello"])
        set_language(src, "fr-FR", output=out)

        # Source untouched, output rewritten.
        src_lang = _read_part(src, "word/styles.xml").xpath(
            ".//w:docDefaults/w:rPrDefault/w:rPr/w:lang", namespaces=NSMAP
        )[0]
        out_lang = _read_part(out, "word/styles.xml").xpath(
            ".//w:docDefaults/w:rPrDefault/w:rPr/w:lang", namespaces=NSMAP
        )[0]
        assert src_lang.get(f"{{{W_NS}}}val") == "en-US"
        assert out_lang.get(f"{{{W_NS}}}val") == "fr-FR"


class DescribeSetLanguagePptx:
    def it_rewrites_default_text_style_lang(self, tmp_path):
        path = str(tmp_path / "in.pptx")
        build_pptx(path, [["hi"]])
        set_language(path, "es-ES")
        pres = _read_part(path, "ppt/presentation.xml")
        defrpr = pres.xpath(".//a:defRPr", namespaces=NSMAP)[0]
        assert defrpr.get("lang") == "es-ES"


class DescribeSetLanguageXlsx:
    def it_writes_xml_lang_on_workbook_root(self, tmp_path):
        path = str(tmp_path / "in.xlsx")
        build_xlsx(path, ["hi"])
        set_language(path, "es-ES")
        wb = _read_part(path, "xl/workbook.xml")
        assert wb.get(f"{{{XML_NS}}}lang") == "es-ES"


class DescribeSetLanguageVsdx:
    def it_rewrites_documentsettings(self, tmp_path):
        path = str(tmp_path / "in.vsdx")
        build_vsdx(path, [(1, "hi")])
        set_language(path, "es-ES")
        doc = _read_part(path, "visio/document.xml")
        settings = doc.xpath(".//v:DocumentSettings", namespaces=NSMAP)[0]
        assert settings.get("DefaultLangID") == "es-ES"
        assert settings.get(f"{{{XML_NS}}}lang") == "es-ES"


class DescribeWorkedExample:
    """The exact flow shown in the package README — extract, write,
    edit, apply, language-set."""

    def it_drives_the_full_pipeline(self, tmp_path):
        src = str(tmp_path / "report.docx")
        po_en = str(tmp_path / "report.en.po")
        po_es = str(tmp_path / "report.es.po")
        out = str(tmp_path / "report-es.docx")

        build_docx(src, ["The quarterly report.", "Revenue was strong."])

        # 1) Extract
        strings = extract_strings(src)
        assert len(strings) == 2

        # 2) Write the source-side .po
        strings.to_pofile(po_en)

        # 3) Translator edits: open en.po, copy to es.po with msgstrs.
        with open(po_en, encoding="utf-8") as f:
            body = f.read()
        es_body = body.replace(
            'msgstr "The quarterly report."', 'msgstr "El informe trimestral."'
        ).replace(
            'msgstr "Revenue was strong."', 'msgstr "Los ingresos fueron sólidos."'
        )
        with open(po_es, "w", encoding="utf-8") as f:
            f.write(es_body)

        # 4) Load and apply.
        es = Strings.from_pofile(po_es, format="docx")
        apply_translations(src, es, output=out)

        # 5) Lock the language.
        set_language(out, "es-ES")

        # Verify the output is fully translated and mono-lingual.
        applied = extract_strings(out)
        assert sorted(applied.values()) == [
            "El informe trimestral.",
            "Los ingresos fueron sólidos.",
        ]
        styles = _read_part(out, "word/styles.xml")
        lang = styles.xpath(
            ".//w:docDefaults/w:rPrDefault/w:rPr/w:lang/@w:val", namespaces=NSMAP
        )[0]
        assert lang == "es-ES"
