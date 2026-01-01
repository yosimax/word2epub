# word2epub

Simple tool to convert Word HTML (saved from Word) into EPUB3.

Usage:

- With explicit metadata file:

```
python word_html_to_epub.py input.html output.epub sample/metadata.yaml
```

- Auto-detect metadata (script searches `metadata.yaml` / `metadata.md` next to `input.html` or in current directory):

```
python word_html_to_epub.py sample/sampleBook.htm sample/out.epub
```

Notes:
- `metadata.yaml` is preferred; if not found the script will look for `metadata.md`.
- Images referenced in metadata are included in the EPUB manifest; missing files are skipped with a warning.
