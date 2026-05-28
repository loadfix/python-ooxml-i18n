"""Tests for format detection."""

from __future__ import annotations

import zipfile

import pytest

from ooxml_i18n.exceptions import UnsupportedFormatError
from ooxml_i18n.format import detect_format, format_for_extension, known_format_tags
from tests.unit._builders import build_docx, build_pptx, build_vsdx, build_xlsx


class DescribeSuffixFastPath:
    def it_recognises_each_parent(self):
        assert format_for_extension(".docx") == "docx"
        assert format_for_extension(".pptx") == "pptx"
        assert format_for_extension(".xlsx") == "xlsx"
        assert format_for_extension(".vsdx") == "vsdx"

    def it_recognises_macro_and_template_variants(self):
        assert format_for_extension(".docm") == "docx"
        assert format_for_extension(".pptm") == "pptx"
        assert format_for_extension(".xlsm") == "xlsx"
        assert format_for_extension(".vsdm") == "vsdx"

    def it_returns_none_for_unknown_extensions(self):
        assert format_for_extension(".odt") is None

    def it_lists_known_format_tags(self):
        assert known_format_tags() == ("docx", "pptx", "xlsx", "vsdx")


class DescribeContentBasedFallback:
    def it_detects_docx_with_unknown_suffix(self, tmp_path):
        f = tmp_path / "report.zip"
        build_docx(str(f), ["hello"])
        assert detect_format(str(f)) == "docx"

    def it_detects_pptx_with_unknown_suffix(self, tmp_path):
        f = tmp_path / "deck.zip"
        build_pptx(str(f), [["hello"]])
        assert detect_format(str(f)) == "pptx"

    def it_detects_xlsx_with_unknown_suffix(self, tmp_path):
        f = tmp_path / "book.zip"
        build_xlsx(str(f), ["hello"])
        assert detect_format(str(f)) == "xlsx"

    def it_detects_vsdx_with_unknown_suffix(self, tmp_path):
        f = tmp_path / "dgm.zip"
        build_vsdx(str(f), [(1, "hello")])
        assert detect_format(str(f)) == "vsdx"

    def it_raises_for_random_zip(self, tmp_path):
        f = tmp_path / "bogus.zip"
        with zipfile.ZipFile(str(f), "w") as zf:
            zf.writestr("hello.txt", "world")
        with pytest.raises(UnsupportedFormatError):
            detect_format(str(f))

    def it_raises_for_non_zip(self, tmp_path):
        f = tmp_path / "bogus.zip"
        f.write_bytes(b"not a zip")
        with pytest.raises(UnsupportedFormatError):
            detect_format(str(f))
