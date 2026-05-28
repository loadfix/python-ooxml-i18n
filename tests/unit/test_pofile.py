"""Tests for the .po reader/writer."""

from __future__ import annotations

import pytest

from ooxml_i18n.exceptions import POFileError
from ooxml_i18n.pofile import _escape, _unescape, read_pofile, write_pofile


class DescribeEscape:
    def it_round_trips_plain_ascii(self):
        assert _escape("hello") == "hello"
        assert _unescape("hello") == "hello"

    def it_escapes_quotes_and_backslashes(self):
        assert _escape('a"b\\c') == 'a\\"b\\\\c'
        assert _unescape('a\\"b\\\\c') == 'a"b\\c'

    def it_escapes_newline_tab_carriage_return(self):
        assert _escape("a\nb\tc\rd") == "a\\nb\\tc\\rd"
        assert _unescape("a\\nb\\tc\\rd") == "a\nb\tc\rd"

    def it_rejects_a_trailing_backslash(self):
        with pytest.raises(POFileError):
            _unescape("foo\\")


class DescribeWriteAndRead:
    def it_round_trips_simple_entries(self, tmp_path):
        path = str(tmp_path / "x.po")
        write_pofile(
            [("hello", "hola", None), ("world", "mundo", "word/document.xml")], path
        )
        result = read_pofile(path)
        assert result == {"hello": "hola", "world": "mundo"}

    def it_skips_the_empty_header_msgid(self, tmp_path):
        path = str(tmp_path / "x.po")
        write_pofile([("k", "v", None)], path)
        result = read_pofile(path)
        # The header msgid "" is dropped, leaving just the real entry.
        assert "" not in result
        assert result == {"k": "v"}

    def it_handles_multiline_continuations(self, tmp_path):
        path = str(tmp_path / "x.po")
        path_w = path
        # Write a hand-crafted .po with continuation strings.
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '\n'
            'msgid "first"\n'
            '"-second"\n'
            'msgstr "alpha"\n'
            '"-beta"\n'
        )
        with open(path_w, "w", encoding="utf-8") as f:
            f.write(content)
        result = read_pofile(path)
        assert result == {"first-second": "alpha-beta"}

    def it_round_trips_unicode_strings(self, tmp_path):
        path = str(tmp_path / "x.po")
        write_pofile([("hello", "Привет", None)], path)
        assert read_pofile(path) == {"hello": "Привет"}

    def it_emits_reference_comments(self, tmp_path):
        path = str(tmp_path / "x.po")
        write_pofile([("k", "v", "word/document.xml")], path)
        with open(path, encoding="utf-8") as f:
            body = f.read()
        assert "#: word/document.xml" in body

    def it_raises_on_msgid_without_msgstr(self, tmp_path):
        path = str(tmp_path / "x.po")
        with open(path, "w", encoding="utf-8") as f:
            f.write('msgid "alone"\n')
        with pytest.raises(POFileError):
            read_pofile(path)
