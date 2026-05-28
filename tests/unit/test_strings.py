"""Tests for the :class:`Strings` value object."""

from __future__ import annotations

from ooxml_i18n.strings import Strings


class DescribeContainerProtocol:
    def it_supports_len_in_iter_and_get(self):
        s = Strings({"a": "1", "b": "2"})
        assert len(s) == 2
        assert "a" in s
        assert list(iter(s)) == ["a", "b"]
        assert s["a"] == "1"

    def it_compares_equal_to_a_dict(self):
        assert Strings({"a": "1"}) == {"a": "1"}

    def it_supports_assignment_and_deletion(self):
        s = Strings({"a": "1"})
        s["b"] = "2"
        assert s["b"] == "2"
        del s["a"]
        assert "a" not in s

    def it_round_trips_via_copy(self):
        s = Strings({"a": "1"}, format="docx", references={"a": "word/document.xml"})
        c = s.copy()
        assert c == s
        assert c.format == "docx"
        assert c.reference("a") == "word/document.xml"

    def it_updates_from_another_strings(self):
        s = Strings({"a": "1"}, references={"a": "ref1"})
        s.update(Strings({"b": "2"}, references={"b": "ref2"}))
        assert s["b"] == "2"
        assert s.reference("b") == "ref2"


class DescribePoFileRoundTrip:
    def it_round_trips_through_a_temp_file(self, tmp_path):
        s = Strings({"hello": "hello", "world": "world"}, format="docx")
        path = str(tmp_path / "x.po")
        s.to_pofile(path)
        roundtripped = Strings.from_pofile(path)
        # Source values were copied into msgstr at write time, so the
        # round-trip produces an identical mapping.
        assert roundtripped == s

    def it_drops_untranslated_entries_on_load(self, tmp_path):
        path = str(tmp_path / "x.po")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                'msgid ""\n'
                'msgstr ""\n'
                '"Content-Type: text/plain; charset=UTF-8\\n"\n'
                '\n'
                'msgid "hello"\n'
                'msgstr "hola"\n'
                '\n'
                'msgid "world"\n'
                'msgstr ""\n'
            )
        loaded = Strings.from_pofile(path)
        assert loaded == {"hello": "hola"}

    def it_preserves_format_tag_when_supplied(self, tmp_path):
        s = Strings({"a": "1"})
        path = str(tmp_path / "x.po")
        s.to_pofile(path)
        loaded = Strings.from_pofile(path, format="pptx")
        assert loaded.format == "pptx"

    def it_writes_reference_comments(self, tmp_path):
        s = Strings({"a": "1"}, references={"a": "word/document.xml#0"})
        path = str(tmp_path / "x.po")
        s.to_pofile(path)
        with open(path, encoding="utf-8") as f:
            body = f.read()
        assert "#: word/document.xml#0" in body
