"""CLI entry point and overall conversion pipeline."""

from __future__ import annotations

import os
import shutil
import tempfile

try:
    import yaml  # type: ignore[import-untyped]
except Exception:
    print("PyYAML が必要です。pip install pyyaml を実行してください。")
    raise

from yaml2epub.epub.package import (_generate_document_content,
                                    _process_images,
                                    _setup_temporary_directory,
                                    _update_manifest_and_spine,
                                    make_epub_from_template)
from yaml2epub.metadata import _normalize_legacy_metadata


def main(argv: list[str]) -> int:
    """Main entry point for yaml2epub conversion.

    Args:
        argv (list[str]): Command-line arguments.

    Returns:
        int: Exit code (0 for success, 1-2 for error).
    """
    if len(argv) < 2:
        print("usage: yaml2epub.py metadata.yaml [out.epub]")
        return 2
    meta_path = argv[1]
    out_epub = argv[2] if len(argv) >= 3 else "out.epub"

    if not os.path.exists(meta_path):
        print(f"metadata file not found: {meta_path}")
        return 1

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    meta = _normalize_legacy_metadata(meta)

    # Set up temporary directory
    tmpdir = tempfile.mkdtemp(prefix="yaml2epub_")
    try:
        _setup_temporary_directory(tmpdir)

        # Process images
        _process_images(tmpdir, meta, meta_path)

        # Generate document content and chapters
        include_advertisement, include_backmatter, chapters_info = (
            _generate_document_content(tmpdir, meta, meta_path)
        )

        # Determine frontmatter and caution inclusion
        docs = meta.get("documents", {}) or {}
        include_frontmatter = bool(docs.get("frontmatter"))
        include_caution = bool(meta.get("caution"))

        # Update OPF manifest/spine and navigation
        _update_manifest_and_spine(
            tmpdir,
            meta,
            chapters_info,
            include_frontmatter,
            include_caution,
            include_backmatter,
            include_advertisement,
        )

        # Build final EPUB
        make_epub_from_template(tmpdir, out_epub)
        print(f"wrote {out_epub}")

    finally:
        # Best-effort cleanup of the temporary directory; a failure here must not mask
        # the original conversion result.
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    return 0
