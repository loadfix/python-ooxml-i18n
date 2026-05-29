# Features

`python-ooxml-i18n` is a pure-Python localisation toolkit that lifts
user-visible strings out of an OOXML package, ships them through a
standard gettext `.po` file for offline translation, and injects the
translated text back into a copy of the source. It works across
`.docx` / `.pptx` / `.xlsx` / `.vsdx` (plus the matching `.docm` /
`.pptm` / `.xlsm` / `.vsdm` macro variants and the `.dotx` / `.potx`
/ `.xltx` / `.vstx` template variants) without depending on any of
the parent libraries — the walker reads the raw XML with `lxml`.

## Source-language detection

Format detection is two-stage: a suffix fast-path
(`FORMAT_BY_SUFFIX` covers the 18 OOXML extensions), then a content
fallback that inspects `[Content_Types].xml` for a parent-specific
discriminator string (`wordprocessingml.document`,
`presentationml.presentation`, `spreadsheetml.sheet`,
`ms-visio.drawing`, plus the matching `.template` variants). This
keeps `extract_strings()` working when a caller renames a package to
`report.zip`.

## Target language list

`set_language(path, lang)` accepts any BCP-47 / RFC-5646 tag (`"fr-FR"`,
`"ja-JP"`, `"pt-BR"`, …). Each parent pins the document-level
language on a different anchor:

| Format | Part | Anchor |
| --- | --- | --- |
| docx | `word/styles.xml` | `w:docDefaults/w:rPrDefault/w:rPr/w:lang` (sets `@val` / `@eastAsia` / `@bidi`) |
| pptx | `ppt/presentation.xml` | every `a:defRPr/@lang` under `defaultTextStyle` |
| xlsx | `xl/workbook.xml` | `xml:lang` on the workbook root (Office tolerates, Calc honours) |
| vsdx | `visio/document.xml` | `DocumentSettings/@DefaultLangID` + `xml:lang` |

Run-level overrides are deliberately **not** rewritten — those are
explicit author choices for multilingual documents.

## Round-trip workflow

```python
from ooxml_i18n import extract_strings, apply_translations, set_language, Strings

# 1. extract → .po
strings = extract_strings("report.docx")
strings.to_pofile("report.fr.po")

# 2. translate report.fr.po offline (Poedit, weblate, gettext tools)

# 3. apply → translated copy
translated = Strings.from_pofile("report.fr.po", format="docx")
apply_translations("report.docx", translated, "report-fr.docx")

# 4. (optional) flip the document-level language
set_language("report-fr.docx", "fr-FR")
```

## Public API

### `extract_strings(path)`

Return a `Strings` over every user-visible run-level text leaf in
the package. Visits parts in lexicographic order; within each part,
leaves in document order. Keys are stable `<part>#<index>`.

```python
from ooxml_i18n import extract_strings
strings = extract_strings("deck.pptx")
print(len(strings), "leaves")
strings.to_pofile("deck.po")
```

### `apply_translations(source, strings, output)`

Copy `source` → `output`, replacing each text leaf whose key matches
an entry in `strings`. Untouched zip members are streamed through
byte-for-byte so Office doesn't show a "modified" prompt. Raises
`ValueError` if `strings.format` doesn't match `source`.

```python
from ooxml_i18n import apply_translations, Strings
fr = Strings.from_pofile("deck.fr.po", format="pptx")
apply_translations("deck.pptx", fr, "deck-fr.pptx")
```

### `set_language(path, lang, *, output=None)`

Set the document-level language. Rewrites in place via a temporary
sibling unless `output` is given.

```python
from ooxml_i18n import set_language
set_language("report.docx", "ja-JP", output="report-ja.docx")
```

### `detect_format(path)`

Return the parent tag (`"docx"` / `"pptx"` / `"xlsx"` / `"vsdx"`).
Raises `UnsupportedFormatError` for non-OOXML inputs.

### `known_format_tags()`

Return the canonical ordered tuple `("docx", "pptx", "xlsx", "vsdx")`.

### `Strings`

Ordered `{key: text}` value object — dict-like (`len` / `in` / `[]` /
`.items` / `.keys` / `.values` / `.update` / `.copy` / `.get`) plus:

- `Strings.format` — the parent tag the strings were extracted from.
- `Strings.reference(key)` / `Strings.set_reference(key, ref)` —
  per-key source locator surfaced as `#:` comments in `.po` output.
- `Strings.to_pofile(path)` — serialise to a gettext `.po` file.
  Initial `msgstr` matches `msgid`; translators replace each.
- `Strings.from_pofile(path, *, format=None)` — load a `.po`. Blank
  `msgstr` entries are dropped so they don't blank the source on apply.

### Exceptions

- `OoxmlI18nError` — base for every error raised by the package.
- `UnsupportedFormatError` — file is not a recognised OOXML container.
- `POFileError` — malformed gettext `.po` input.

## Examples

End-to-end docx round-trip with reference-locator comments:

```python
from ooxml_i18n import Strings, apply_translations, extract_strings

# 1. lift strings; locator comments tell translators which part each came from
src = extract_strings("contract.docx")
src.to_pofile("contract.po")

# 2. someone fills msgstr offline...
fr = Strings.from_pofile("contract.po", format="docx")
fr["word/document.xml#0"] = "Contrat de service"  # post-edit a single key
apply_translations("contract.docx", fr, "contract.fr.docx")
```

Cross-format helper (works the same for pptx / xlsx / vsdx):

```python
from ooxml_i18n import detect_format, extract_strings, set_language

for path in ("brief.docx", "deck.pptx", "model.xlsx", "diagram.vsdx"):
    print(path, "->", detect_format(path), len(extract_strings(path)))
    set_language(path, "de-DE", output=path.replace(".", "-de."))
```
