"""EPUB package assembly: template copy, images, content, OPF/NAV, zip."""

from __future__ import annotations

import gzip
import os
import re
import shutil
import zipfile
from typing import cast

from yaml2epub.epub.constants import (DEFAULT_TITLE, IMAGE_DIR, NAV_FILE,
                                      NONE_TEXT, NS_OPF, OPF_FILE,
                                      TEMPLATE_DIR, XHTML_ADVERTISEMENT,
                                      XHTML_BACKCOVER, XHTML_BACKMATTER,
                                      XHTML_CAUTION, XHTML_COLOPHON,
                                      XHTML_COVER, XHTML_DIR,
                                      XHTML_FRONTMATTER, XHTML_TITLEPAGE,
                                      XHTML_TOC)
from yaml2epub.epub.navigation import update_navigation
from yaml2epub.epub.opf import update_opf_dynamic
from yaml2epub.epub.pages import (generate_chapter_xhtmls,
                                  insert_advertisement, insert_backmatter,
                                  insert_caution, insert_colophon,
                                  insert_frontmatter, insert_titlepage)
from yaml2epub.epub.xhtml import (add_stylesheets_to_xhtml,
                                  replace_title_in_xhtml)
from yaml2epub.utils import read_text_file, warn, write_text_file


def make_epub_from_template(tmpdir: str, out_epub: str) -> None:
    # create EPUB (mimetype first, uncompressed)
    root = os.path.join(tmpdir)
    mimetype_path = os.path.join(root, "mimetype")
    opf_path = os.path.join(root, OPF_FILE)
    manifest_hrefs = set()

    # build an allow-list from the OPF manifest so the final archive includes only
    # files that the EPUB package actually declares.
    if os.path.exists(opf_path):
        import xml.etree.ElementTree as ET

        tree = ET.parse(opf_path)
        package = tree.getroot()
        for item in package.findall(f".//{{{NS_OPF}}}item"):
            href = item.get("href")
            if href:
                href = href.replace("\\", "/")
                # OPF href values are relative to item/standard.opf, so the final
                # ZIP entry path must be rooted under item/.
                manifest_hrefs.add(f"item/{href}")

    # add required root-level files explicitly
    manifest_hrefs.add("item/standard.opf")
    manifest_hrefs.add("META-INF/container.xml")
    manifest_hrefs.add("mimetype")

    # Try to remove the existing output first. This is an idempotent pre-delete;
    # if it fails because the file is locked, ZipFile raises a clearer error below.
    try:
        if os.path.exists(out_epub):
            os.remove(out_epub)
    except Exception:
        pass

    try:
        with zipfile.ZipFile(out_epub, "w", compression=zipfile.ZIP_DEFLATED) as z:
            # mimetype must be stored and first
            z.writestr(
                "mimetype",
                read_text_file(mimetype_path),
                compress_type=zipfile.ZIP_STORED,
            )

            for href in sorted(manifest_hrefs):
                if href == "mimetype":
                    continue
                path = os.path.join(root, href)
                if not os.path.exists(path):
                    continue
                # EPUB ZIP entry names must use forward slashes regardless of host OS.
                arcname = href.replace("\\", "/")
                z.write(path, arcname)
    except PermissionError as e:
        # often caused by the destination file being opened by another program
        raise PermissionError(
            f"could not write EPUB '{out_epub}'; please close it if open and retry"
        ) from e


def _setup_temporary_directory(tmpdir: str) -> None:
    """Set up the temporary directory by copying template and cleaning up template images.

    Args:
        tmpdir (str): Temporary directory path.
    """
    # Copy template to tmpdir. The first call uses ``dirs_exist_ok`` when available;
    # the second is a plain-copy fallback, so its failure is not swallowed silently.
    try:
        shutil.copytree(TEMPLATE_DIR, os.path.join(tmpdir), dirs_exist_ok=True)
    except Exception:
        shutil.copytree(TEMPLATE_DIR, tmpdir)

    # Remove template-provided images so only user-supplied images are included
    template_image_dir = os.path.join(tmpdir, IMAGE_DIR)
    if os.path.isdir(template_image_dir):
        for fn in os.listdir(template_image_dir):
            fp = os.path.join(template_image_dir, fn)
            try:
                if os.path.isfile(fp) or os.path.islink(fp):
                    os.remove(fp)
                elif os.path.isdir(fp):
                    shutil.rmtree(fp)
            except Exception:
                # ignore; best-effort cleanup
                pass


def _process_images(tmpdir: str, meta: dict, meta_path: str) -> tuple[bool, bool]:
    """Process images (cover and backcover) from metadata.

    Args:
        tmpdir (str): Temporary directory path.
        meta (dict): Metadata dictionary.
        meta_path (str): Path to metadata file.

    Returns:
        tuple[bool, bool]: (cover_provided, backcover_provided)
    """
    images = meta.get("image", {}) or {}
    image_dir = os.path.join(tmpdir, IMAGE_DIR)
    os.makedirs(image_dir, exist_ok=True)

    xhtml_dir = os.path.join(tmpdir, XHTML_DIR)
    cover_file = os.path.join(xhtml_dir, XHTML_COVER)
    back_file = os.path.join(xhtml_dir, XHTML_BACKCOVER)

    # Copy user-specified cover/backcover without converting filenames
    cover_provided = False
    backcover_provided = False
    meta_dir = os.path.dirname(os.path.abspath(meta_path))

    if "cover" in images:
        src = images["cover"]
        src_path = src if os.path.isabs(src) else os.path.join(meta_dir, src)
        if os.path.exists(src_path):
            basename = os.path.basename(src_path)
            dest_path = os.path.join(image_dir, basename)
            # Handle SVGZ files: decompress to SVG
            if basename.lower().endswith(".svgz"):
                svg_basename = basename[:-1]  # remove 'z'
                dest_path = os.path.join(image_dir, svg_basename)
                with gzip.open(src_path, "rb") as f_in:
                    with open(dest_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(src_path, dest_path)
            cover_provided = True

    if "backcover" in images:
        src = images["backcover"]
        src_path = src if os.path.isabs(src) else os.path.join(meta_dir, src)
        if os.path.exists(src_path):
            basename = os.path.basename(src_path)
            dest_path = os.path.join(image_dir, basename)
            # Handle SVGZ files: decompress to SVG
            if basename.lower().endswith(".svgz"):
                svg_basename = basename[:-1]  # remove 'z'
                dest_path = os.path.join(image_dir, svg_basename)
                with gzip.open(src_path, "rb") as f_in:
                    with open(dest_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(src_path, dest_path)
            backcover_provided = True

    # In some workflows the XHTML for the back cover is generated later (see
    # `_generate_document_content`).  `_process_images` wants to update the
    # <img> element in that file, so make sure a copy of the cover template
    # exists before attempting to modify it.  If `_generate_document_content`
    # later creates the backcover.xhtml again the `not os.path.exists(back_file)`
    # guard will prevent overwriting our updated copy.
    if backcover_provided:
        try:
            if os.path.exists(cover_file) and not os.path.exists(back_file):
                shutil.copy2(cover_file, back_file)
        except Exception as exc:
            warn(f"failed to seed {XHTML_BACKCOVER} from {XHTML_COVER}: {exc}")

    # Remove p-cover.xhtml/p-backcover.xhtml if corresponding images not provided.
    # Best-effort cleanup: OPF/NAV still exclude the missing image pages.
    try:
        if not cover_provided and os.path.exists(cover_file):
            os.remove(cover_file)
        if not backcover_provided and os.path.exists(back_file):
            os.remove(back_file)
    except Exception:
        pass

    # Update p-cover.xhtml/p-backcover.xhtml image src to actual filenames
    try:
        if cover_provided:
            cover_src = images.get("cover")
            cover_fname = os.path.basename(cover_src)  # type: ignore[arg-type]
            if cover_fname.lower().endswith(".svgz"):
                cover_fname = cover_fname[:-1]  # remove 'z'
            if (
                cover_fname
                and os.path.exists(os.path.join(image_dir, cover_fname))
                and os.path.exists(cover_file)
            ):
                s = read_text_file(cover_file)
                s = re.sub(
                    r'src="\.\./image/[^\"]+"', f'src="../image/{cover_fname}"', s
                )
                write_text_file(cover_file, s)
        if backcover_provided:
            back_src = images.get("backcover")
            back_fname = os.path.basename(back_src)  # type: ignore[arg-type]
            if back_fname.lower().endswith(".svgz"):
                back_fname = back_fname[:-1]  # remove 'z'
            if (
                back_fname
                and os.path.exists(os.path.join(image_dir, back_fname))
                and os.path.exists(back_file)
            ):
                s = read_text_file(back_file)
                s = re.sub(
                    r'src="\.\./image/[^\"]+"', f'src="../image/{back_fname}"', s
                )
                write_text_file(back_file, s)
    except Exception as exc:
        warn(f"failed to update cover/backcover image references: {exc}")

    return cover_provided, backcover_provided


def _generate_document_content(
    tmpdir: str, meta: dict, meta_path: str
) -> tuple[bool, bool, list[dict]]:
    """Generate document content (frontmatter, backmatter, etc.) and chapters.

    Args:
        tmpdir (str): Temporary directory path.
        meta (dict): Metadata dictionary.
        meta_path (str): Path to metadata file.

    Returns:
        tuple[bool, bool, list[dict]]: (include_advertisement, include_backmatter, chapters_info)
    """
    meta_dir = os.path.dirname(os.path.abspath(meta_path))
    xhtml_dir = os.path.join(tmpdir, XHTML_DIR)
    image_dir = os.path.join(tmpdir, IMAGE_DIR)

    # Replace title in xhtml templates (support book_title key)
    title = meta.get("title") or meta.get("book_title", DEFAULT_TITLE)
    replace_title_in_xhtml(tmpdir, title)

    # Generate title page body from metadata (book_title and series_title)
    try:
        insert_titlepage(xhtml_dir, meta)
    except Exception as exc:
        warn(f"titlepage generation failed; continuing without it: {exc}")

    # Create back cover xhtml by copying p-cover.xhtml -> p-backcover.xhtml (if present)
    cover_src = os.path.join(xhtml_dir, XHTML_COVER)
    back_src = os.path.join(xhtml_dir, XHTML_BACKCOVER)
    try:
        if os.path.exists(cover_src) and not os.path.exists(back_src):
            shutil.copy2(cover_src, back_src)
    except Exception as exc:
        warn(f"failed to copy {XHTML_COVER} -> {XHTML_BACKCOVER}: {exc}")

    # Copy any stylesheets specified in metadata into item/style and inject links
    copied_styles: list[str] = []
    styles_spec = meta.get("stylesheets") or []
    if styles_spec:
        style_dir = os.path.join(tmpdir, "item", "style")
        os.makedirs(style_dir, exist_ok=True)
        for s in styles_spec:
            if not s:
                continue
            src = s if os.path.isabs(s) else os.path.join(meta_dir, s)
            if os.path.exists(src):
                try:
                    dst = os.path.join(style_dir, os.path.basename(src))
                    shutil.copy2(src, dst)
                    copied_styles.append(os.path.basename(src))
                except Exception as exc:
                    warn(f"failed to copy stylesheet {os.path.basename(src)}: {exc}")

    # Insert documents: frontmatter/caution/backmatter/colophon/advertisement
    docs = meta.get("documents", {}) or {}
    front = docs.get("frontmatter")
    back = docs.get("backmatter")

    # br_convert flag from metadata controls paragraph breaks inside YAML contents
    br_flag = bool(meta.get("br_convert"))

    insert_frontmatter(xhtml_dir, front, meta_dir, image_dir, br_convert=br_flag)
    insert_caution(xhtml_dir, meta.get("caution"))
    insert_backmatter(xhtml_dir, back, meta_dir, image_dir, br_convert=br_flag)
    insert_colophon(xhtml_dir, meta.get("colophon"), meta_dir, meta)
    insert_advertisement(xhtml_dir, meta.get("advertisement"), meta_dir, meta)

    # Check if advertisement should be included (NONE = exclude)
    adv_spec = meta.get("advertisement")
    adv_text = adv_spec.get("text") if isinstance(adv_spec, dict) else adv_spec
    include_advertisement = adv_text != NONE_TEXT
    include_backmatter = bool(back)

    # Inject chapters (support arbitrary number)
    contents = docs.get("contents", []) or []
    raw_chapters = [d.get("chapter") if isinstance(d, dict) else d for d in contents]
    filtered_chapters = [c for c in raw_chapters if c]
    chapters = cast("list[str]", filtered_chapters)
    # Resolve chapter paths relative to metadata file
    chapters = [c if os.path.isabs(c) else os.path.join(meta_dir, c) for c in chapters]
    chapters_info = generate_chapter_xhtmls(xhtml_dir, chapters, br_flag)

    if copied_styles:
        add_stylesheets_to_xhtml(xhtml_dir, copied_styles)

    # Remove unused p-XXX.xhtml files from template that were not generated.
    # Best-effort cleanup: the OPF allow-list still excludes stale pages if a file
    # cannot be removed from the temporary directory.
    try:
        existing = [n for n in os.listdir(xhtml_dir) if n.endswith(".xhtml")]
        keep = set([os.path.basename(ch["href"]) for ch in chapters_info])
        keep.update(
            (
                XHTML_COVER,
                XHTML_TITLEPAGE,
                XHTML_FRONTMATTER,
                XHTML_CAUTION,
                XHTML_TOC,
                XHTML_COLOPHON,
                XHTML_ADVERTISEMENT,
                XHTML_BACKCOVER,
            )
        )
        # Also keep backmatter if present
        if include_backmatter:
            keep.add(XHTML_BACKMATTER)
        for fn in existing:
            if fn.startswith("p-") and fn not in keep:
                fp = os.path.join(xhtml_dir, fn)
                try:
                    os.remove(fp)
                except Exception:
                    pass
    except Exception:
        pass

    return include_advertisement, include_backmatter, chapters_info


def _update_manifest_and_spine(
    tmpdir: str,
    meta: dict,
    chapters_info: list[dict],
    include_frontmatter: bool,
    include_caution: bool,
    include_backmatter: bool,
    include_advertisement: bool,
) -> None:
    """Update OPF manifest/spine and navigation documents.

    Args:
        tmpdir (str): Temporary directory path.
        meta (dict): Metadata dictionary.
        chapters_info (list[dict]): Chapter information list.
        include_frontmatter (bool): Whether frontmatter is included.
        include_caution (bool): Whether caution is included.
        include_backmatter (bool): Whether backmatter is included.
        include_advertisement (bool): Whether advertisement is included.
    """
    # Update OPF dynamically
    opf_path = os.path.join(tmpdir, OPF_FILE)
    if os.path.exists(opf_path):
        update_opf_dynamic(
            opf_path,
            meta,
            chapters_info,
            include_frontmatter,
            include_caution,
            include_backmatter,
            include_advertisement,
        )

    # Update navigation
    nav_path = os.path.join(tmpdir, NAV_FILE)
    if os.path.exists(nav_path):
        update_navigation(nav_path, chapters_info)
