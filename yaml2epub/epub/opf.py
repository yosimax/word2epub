"""OPF (package document) generation and updates."""

from __future__ import annotations

import os
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from yaml2epub.utils import read_text_file, write_text_file


def update_opf_dynamic(
    opf_path: str,
    meta: dict,
    chapters_info: list[dict],
    include_frontmatter: bool,
    include_caution: bool,
    include_backmatter: bool = False,
    include_advertisement: bool = True,
) -> None:
    ns = {
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    ET.register_namespace("", ns["opf"])
    ET.register_namespace("dc", ns["dc"])

    tree = ET.parse(opf_path)
    root = tree.getroot()

    # update basic metadata entries
    for title_el in root.findall(".//{http://purl.org/dc/elements/1.1/}title"):
        title_val = meta.get("title") or meta.get("book_title")
        if title_val:
            title_el.text = title_val
    for creator in root.findall(".//{http://purl.org/dc/elements/1.1/}creator"):
        cid = creator.get("id")
        if cid == "creator01" and "creator01" in meta:
            creator.text = meta["creator01"]
        if cid == "creator02" and "creator02" in meta:
            creator.text = meta["creator02"]
    for pub in root.findall(".//{http://purl.org/dc/elements/1.1/}publisher"):
        if "publisher" in meta:
            pub.text = meta["publisher"]

    # identifier
    for ident in root.findall(".//{http://purl.org/dc/elements/1.1/}identifier"):
        if ident.get("id") == "unique-id":
            ident.text = f"urn:uuid:{uuid.uuid4()}"

    # modified
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for meta_el in root.findall(".//{http://www.idpf.org/2007/opf}meta"):
        if meta_el.get("property") == "dcterms:modified":
            meta_el.text = now

    manifest = root.find("{http://www.idpf.org/2007/opf}manifest")
    if manifest is None:
        return

    # preserve existing nav/style items when possible
    existing_items = {
        (it.get("href") or ""): it
        for it in manifest.findall("{http://www.idpf.org/2007/opf}item")
    }

    # build a new manifest element and populate it in logical groups with comments
    new_manifest = ET.Element("{http://www.idpf.org/2007/opf}manifest")

    def make_item(item_id, href, media_type="application/xhtml+xml", properties=None):
        el = ET.Element("{http://www.idpf.org/2007/opf}item")
        el.set("id", item_id)
        el.set("href", href)
        el.set("media-type", media_type)
        if properties:
            el.set("properties", properties)
        return el

    # navigation
    new_manifest.append(ET.Comment(" navigation "))
    nav_href = None
    for href, it in existing_items.items():
        props = it.get("properties") or ""
        if "nav" in props:
            new_manifest.append(it)
            nav_href = href
            break
    if nav_href is None:
        new_manifest.append(
            make_item(
                "toc", "navigation-documents.xhtml", "application/xhtml+xml", "nav"
            )
        )

    # styles
    new_manifest.append(ET.Comment(" style "))
    # preserve only the actual stylesheet items that belong to the generated output.
    # Template-side item2/css etc. must not be propagated into the new manifest.
    style_added_hrefs = set()
    used_style_ids = set()
    for href, it in existing_items.items():
        if href.startswith("style/"):
            new_manifest.append(it)
            style_added_hrefs.add(href)
            if it.get("id"):
                used_style_ids.add(it.get("id"))
    # also scan the actual style folder on disk and add any css files not present in manifest
    style_folder = os.path.join(os.path.dirname(opf_path), "style")
    if os.path.isdir(style_folder):
        files = sorted(os.listdir(style_folder))
        for fn in files:
            if not fn.lower().endswith(".css"):
                continue
            href = f"style/{fn}"
            if href in style_added_hrefs:
                continue
            base = os.path.splitext(fn)[0]
            item_id = re.sub("[^0-9A-Za-z_-]", "-", base)
            if not item_id:
                item_id = f"style-{uuid.uuid4().hex[:8]}"
            # ensure unique id
            orig_id = item_id
            i = 1
            while item_id in used_style_ids:
                item_id = f"{orig_id}-{i}"
                i += 1
            used_style_ids.add(item_id)
            el = make_item(item_id, href, "text/css")
            new_manifest.append(el)

    # images: scan output image directory and add any images present
    new_manifest.append(ET.Comment(" image "))
    image_folder = os.path.join(os.path.dirname(opf_path), "image")
    img_id_map = {}
    if os.path.isdir(image_folder):
        files = sorted(os.listdir(image_folder))
        cnt = 1
        used_ids = set()
        for fn in files:
            href = f"image/{fn}"
            base, ext = os.path.splitext(fn)
            ext = ext.lower()
            media = "image/jpeg"
            if ext == ".png":
                media = "image/png"
            elif ext == ".svg":
                media = "image/svg+xml"
            elif ext == ".gif":
                media = "image/gif"
            elif ext in (".jpg", ".jpeg"):
                media = "image/jpeg"
            # choose id: prefer 'backcover' for filenames containing 'back', 'cover' for cover
            image_props: str | None = None
            if "back" in base.lower():
                item_id = "backcover"
            elif "cover" in base.lower():
                item_id = "cover"
                image_props = "cover-image"
            else:
                item_id = re.sub("[^0-9A-Za-z_-]", "-", base)
                if not item_id:
                    item_id = f"img-{cnt}"
            # ensure unique id
            orig_id = item_id
            i = 1
            while item_id in used_ids:
                item_id = f"{orig_id}-{i}"
                i += 1
            used_ids.add(item_id)
            img_id_map[href] = item_id
            el = make_item(item_id, href, media, image_props)
            new_manifest.append(el)
            cnt += 1

    # xhtml
    new_manifest.append(ET.Comment(" xhtml "))

    # keep cover only if file exists
    def add_xhtml_if_exists(item_id, href, properties=None):
        full = os.path.join(os.path.dirname(opf_path), href)
        if os.path.exists(full):
            new_manifest.append(
                make_item(item_id, href, "application/xhtml+xml", properties)
            )

    add_xhtml_if_exists("p-cover", "xhtml/p-cover.xhtml")
    if include_frontmatter:
        add_xhtml_if_exists("p-fmatter-001", "xhtml/p-fmatter-001.xhtml")
    add_xhtml_if_exists("p-titlepage", "xhtml/p-titlepage.xhtml")
    if include_caution:
        add_xhtml_if_exists("p-caution", "xhtml/p-caution.xhtml")
    add_xhtml_if_exists("p-toc", "xhtml/p-toc.xhtml")

    for ch in chapters_info:
        add_xhtml_if_exists(ch["id"], ch["href"])

    if include_backmatter:
        add_xhtml_if_exists("p-bmatter-001", "xhtml/p-bmatter-001.xhtml")

    add_xhtml_if_exists("p-colophon", "xhtml/p-colophon.xhtml")
    if include_advertisement:
        add_xhtml_if_exists("p-ad-001", "xhtml/p-ad-001.xhtml")
    add_xhtml_if_exists("p-backcover", "xhtml/p-backcover.xhtml")

    # replace old manifest with new_manifest preserving position
    parent = root
    children = list(parent)
    idx = children.index(manifest)
    parent.remove(manifest)
    parent.insert(idx, new_manifest)

    spine = root.find("{http://www.idpf.org/2007/opf}spine")
    if spine is None:
        return
    for ir in list(spine.findall("{http://www.idpf.org/2007/opf}itemref")):
        spine.remove(ir)

    def add_itemref(idref, props=None):
        ir = ET.Element("{http://www.idpf.org/2007/opf}itemref")
        ir.set("linear", "yes")
        ir.set("idref", idref)
        if props:
            ir.set("properties", props)
        else:
            ir.set("properties", "page-spread-left")
        spine.append(ir)

    add_itemref("p-cover")
    if include_frontmatter:
        add_itemref("p-fmatter-001")
    add_itemref("p-titlepage")
    if include_caution:
        add_itemref("p-caution")
    add_itemref("p-toc")
    for ch in chapters_info:
        add_itemref(ch["id"])
    if include_backmatter:
        add_itemref("p-bmatter-001")
    add_itemref("p-colophon")
    if include_advertisement:
        add_itemref("p-ad-001")
    add_itemref("p-backcover")

    tree.write(opf_path, encoding="utf-8", xml_declaration=True)


def update_opf_basic(opf_path: str, meta: dict) -> None:
    s = read_text_file(opf_path)
    # title
    if "title" in meta:
        s = s.replace(
            '<dc:title id="title">作品名１</dc:title>',
            f"<dc:title id=\"title\">{meta['title']}</dc:title>",
        )
    # creators
    if "creator01" in meta:
        s = s.replace(
            '<dc:creator id="creator01">著作者名１</dc:creator>',
            f"<dc:creator id=\"creator01\">{meta['creator01']}</dc:creator>",
        )
    if "creator02" in meta:
        s = s.replace(
            '<dc:creator id="creator02">著作者名２</dc:creator>',
            f"<dc:creator id=\"creator02\">{meta['creator02']}</dc:creator>",
        )
    if "publisher" in meta:
        s = s.replace(
            '<dc:publisher id="publisher">出版社名</dc:publisher>',
            f"<dc:publisher id=\"publisher\">{meta['publisher']}</dc:publisher>",
        )
    # identifier
    uid = f"urn:uuid:{uuid.uuid4()}"
    s = s.replace(
        s[
            s.find('<dc:identifier id="unique-id">') : s.find("</dc:identifier>")
            + len("</dc:identifier>")
        ],
        f'<dc:identifier id="unique-id">{uid}</dc:identifier>',
    )
    # modified
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if '<meta property="dcterms:modified">' in s:
        start = s.find('<meta property="dcterms:modified">')
        end = s.find("</meta>", start) + len("</meta>")
        s = s[:start] + f'<meta property="dcterms:modified">{now}</meta>' + s[end:]
    else:
        # insert before </metadata>
        s = s.replace(
            "</metadata>",
            f'<meta property="dcterms:modified">{now}</meta>\n</metadata>',
        )

    write_text_file(opf_path, s)
