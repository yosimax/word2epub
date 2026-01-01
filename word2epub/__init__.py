"""word2epub package exports."""
from .metadata import load_metadata
from .encoding import detect_encoding
from .parser import (
    load_html_and_split_chapters,
    remove_duplicate_title_span,
    remove_orphan_en_spans,
    clean_word_garbage,
    clean_span_and_ruby,
)
from .xhtml import (
    generate_all_chapter_xhtml,
    generate_chapter_filenames,
    build_toc_xhtml,
    build_image_xhtml,
    build_opf,
)
from .epub_writer import create_epub

__all__ = [
    "load_metadata",
    "detect_encoding",
    "load_html_and_split_chapters",
    "remove_duplicate_title_span",
    "remove_orphan_en_spans",
    "clean_word_garbage",
    "clean_span_and_ruby",
    "generate_all_chapter_xhtml",
    "generate_chapter_filenames",
    "build_toc_xhtml",
    "build_image_xhtml",
    "build_opf",
    "create_epub",
]
