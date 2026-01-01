"""Thin CLI wrapper that uses the word2epub package."""
import sys
from word2epub import (
    load_metadata,
    detect_encoding,
    load_html_and_split_chapters,
    remove_duplicate_title_span,
    remove_orphan_en_spans,
    clean_word_garbage,
    clean_span_and_ruby,
    generate_all_chapter_xhtml,
    build_toc_xhtml,
    build_image_xhtml,
    build_opf,
    create_epub,
)


def main():
    if not (3 <= len(sys.argv) <= 4):
        print("Usage: python word_html_to_epub.py input.html output.epub [metadata.yaml]")
        return

    input_html = sys.argv[1]
    output_epub = sys.argv[2]
    metadata_path = None

    # If user provided metadata path, use it. Otherwise auto-detect.
    if len(sys.argv) == 4:
        metadata_path = sys.argv[3]
    else:
        # Search candidates: same dir as input, then cwd
        import os

        input_dir = os.path.dirname(os.path.abspath(input_html))
        candidates = [
            os.path.join(input_dir, "metadata.yaml"),
            os.path.join(os.getcwd(), "metadata.yaml"),
        ]
        for p in candidates:
            if os.path.exists(p):
                metadata_path = p
                break

    if metadata_path is None:
        print("Warning: metadata file not found; proceeding with defaults.")
        meta = {}
    else:
        print("Using metadata:", metadata_path)
        meta = load_metadata(metadata_path)
        # remember metadata file directory so image paths in metadata
        # can be resolved relative to the metadata file
        import os

        meta_dir = os.path.dirname(os.path.abspath(metadata_path))
        meta["_meta_dir"] = meta_dir
    if meta:
        print("Detected encoding:", detect_encoding(input_html)[0])
        print("Metadata loaded:", meta)
    else:
        print("Detected encoding:", detect_encoding(input_html)[0])

    chapters = load_html_and_split_chapters(input_html)

    for chap in chapters:
        remove_duplicate_title_span(chap)
        remove_orphan_en_spans(chap)
        clean_word_garbage(chap)
        clean_span_and_ruby(chap)

        # 章タイトル内の簡易変換
        first = chap["nodes"][0]
        if getattr(first, "name", None) == "p" and "CHAPTER" in first.get("class", []):
            for span in first.find_all("span"):
                style = span.get("style", "")
                if (
                    "font-size" in style
                    or "font-family" in style
                    or "mso-" in style
                ):
                    span.unwrap()
                elif "italic" in style:
                    em = first.new_tag("em")
                    em.string = span.get_text()
                    span.replace_with(em)
                elif "bold" in style:
                    strong = first.new_tag("strong")
                    strong.string = span.get_text()
                    span.replace_with(strong)

    print(f"Found {len(chapters)} chapters.")
    for chap in chapters:
        print(chap["index"], chap["title"])

    chapter_files = generate_all_chapter_xhtml(chapters)
    chapter_filenames = {idx: filename for idx, (filename, _) in chapter_files.items()}

    toc_xhtml = build_toc_xhtml(chapters, chapter_filenames)

    image_pages = []
    for img in meta.get("images", []):
        if img.get("type") == "insert_after_toc":
            image_filename = img["file"]
            image_xhtml = build_image_xhtml(image_filename)
            image_pages.append(("image.xhtml", image_xhtml))

    opf_content = build_opf(meta, chapter_filenames, image_pages)

    style_css = """
@charset "UTF-8";
body {
  writing-mode: vertical-rl;
  -epub-writing-mode: vertical-rl;
  line-height: 1.8;
  font-family: "YuMincho", serif;
}
p {
  margin: 0 0 1em 0;
}
"""

    create_epub(output_epub, chapter_files, toc_xhtml, opf_content, style_css, image_pages, meta)

    print(f"EPUB created: {output_epub}")


if __name__ == "__main__":
    main()
