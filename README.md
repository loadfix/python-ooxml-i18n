# python-ooxml-i18n

Localisation toolkit for the loadfix `python-ooxml` family — extract
user-visible strings out of an OOXML document, ship them through a
standard gettext `.po` file for offline translation, and apply the
translations back into a copy of the source. Works across all four
parents — `.docx`, `.pptx`, `.xlsx`, `.vsdx` — without needing any of
the parent libraries to be installed.

```
pip install python-ooxml-i18n
```

## Why

OOXML packages bury user-visible strings behind a wall of namespace
prefixes (`w:t`, `a:t`, `s:t`, `vsdx:Text`) and a fan of part files
(`word/document.xml`, `ppt/slides/slide*.xml`, …). Translation tools
expect a flat key-value `.po` — this package bridges the gap and stays
out of the way.

## Worked example

```python
from ooxml_i18n import (
    Strings,
    apply_translations,
    extract_strings,
    set_language,
)

# 1) Extract user-visible text from a docx for translation. The
#    return value is a Strings — dict-like, with stable opaque keys
#    so you can edit translations and re-apply against the source.
strings = extract_strings("report.docx")

# 2) Round-trip via a generic gettext .po file. Each msgstr is
#    pre-filled with the source text; translators just edit the
#    msgstr lines.
strings.to_pofile("report.en.po")

# 3) After translation, load the translated .po. Empty msgstr
#    entries are skipped so a half-translated draft doesn't blank
#    the source.
es = Strings.from_pofile("report.es.po", format="docx")

# 4) Apply: produces a fresh document with each tracked string
#    replaced. Untranslated keys (and keys not present in the
#    source) pass through unchanged.
apply_translations("report.docx", es, output="report-es.docx")

# 5) Lock the document language so spell-check and CJK font
#    fallback follow the translated content.
set_language("report-es.docx", "es-ES")
```

The same five lines work against `.pptx`, `.xlsx`, and `.vsdx`
sources — `extract_strings` introspects the zip to figure out which
parent it's looking at.

## Public surface

- **`extract_strings(path)`** → `Strings`. Walks every text-bearing
  leaf in the package and yields stable `<part>#<index>` keys.
- **`apply_translations(source, strings, output)`**. Streams the
  source zip to *output*, replacing each match. Members untouched by
  the translation (themes, media, relationships, …) are copied
  byte-for-byte.
- **`set_language(path, lang, *, output=None)`**. Rewrites the
  document-level language anchor for the format. Run-level overrides
  are intentionally preserved — multilingual documents stay
  multilingual.
- **`Strings`**. Dict-like (`len`, `in`, `[]`, `.items()`, `.keys()`,
  `.values()`, `.update()`, `.copy()`) plus `.to_pofile(path)` and
  the classmethod `Strings.from_pofile(path, *, format=None)`.

## Where text lives, per parent

| Parent | XPath leaf  | Parts walked                                                                                                |
|--------|-------------|-------------------------------------------------------------------------------------------------------------|
| docx   | `w:t`       | `word/document.xml`, headers, footers, footnotes, endnotes, comments, glossary                              |
| pptx   | `a:t`       | every slide, layout, master, notes-slide, notes-master, handout-master, comment, diagram-data part          |
| xlsx   | `s:t` + `a:t` | `xl/sharedStrings.xml` (cell text) plus drawing/chart parts (shape text)                                  |
| vsdx   | `vsdx:Text` | every page and master under `visio/`                                                                        |

## Where the language anchor lives

| Parent | Anchor                                                                                  |
|--------|------------------------------------------------------------------------------------------|
| docx   | `w:docDefaults/w:rPrDefault/w:rPr/w:lang` (val + eastAsia + bidi) in `word/styles.xml`   |
| pptx   | `a:defRPr/@lang` on every level of `p:defaultTextStyle` in `ppt/presentation.xml`        |
| xlsx   | `xml:lang` on the `<workbook>` root in `xl/workbook.xml`                                 |
| vsdx   | `DocumentSettings/@DefaultLangID` plus `xml:lang` in `visio/document.xml`                |

## Scope (0.1.0)

- Run-level text leaves only — every `w:t` / `a:t` / `s:t` /
  `vsdx:Text` element.
- Pure Python, two runtime deps: `lxml` and `typing-extensions`. We
  read and write `.po` ourselves rather than pull `babel` or `polib`
  into the dependency closure.
- Out of scope: field-code internals, drawing canvas tooltips,
  embedded XLSX charts inside docx (they carry text but Office
  round-trips them through their own pipeline already).

## Licence

Apache-2.0. See `LICENSE`.
