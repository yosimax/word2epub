"""yaml2epub.py

シンプルな YAML -> EPUB3 変換スクリプト。

使い方:
  python yaml2epub.py metadata.yaml out.epub

このスクリプトは `TEMPLATE/book-template` を元にして EPUB を作成します。
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import zipfile
import uuid
from datetime import datetime
import re

try:
    import yaml
except Exception:
    print("PyYAML が必要です。pip install pyyaml を実行してください。")
    raise


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "TEMPLATE", "book-template")


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def replace_title_in_xhtml(dirpath: str, title: str) -> None:
    xhtml_dir = os.path.join(dirpath, "item", "xhtml")
    if not os.path.isdir(xhtml_dir):
        return
    for name in os.listdir(xhtml_dir):
        if not name.endswith(".xhtml"):
            continue
        p = os.path.join(xhtml_dir, name)
        s = read_text_file(p)
        s = s.replace("<title>作品名</title>", f"<title>{title}</title>")
        s = s.replace("<title>Navigation</title>", "<title>Navigation</title>")
        write_text_file(p, s)


def insert_frontmatter(xhtml_dir: str, spec: dict | None, meta_dir: str, image_dir: str) -> None:
    if not spec:
        return
    text = spec.get('text') if isinstance(spec, dict) else spec
    image = spec.get('image') if isinstance(spec, dict) else None

    # resolve paths
    text_path = None
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)

    # prepare body
    body_html = ''
    label = 'frontmatter'
    if text_path and os.path.exists(text_path):
        if text_path.lower().endswith(('.yaml', '.yml')):
            with open(text_path, 'r', encoding='utf-8') as f:
                try:
                    data = yaml.safe_load(f) or {}
                except Exception:
                    data = {}
            contents = data.get('contents', '')
            paras = [p.strip() for p in contents.split('\n\n') if p.strip()]
            body_html = '\n'.join(f"<p>{p.replace('\n', '<br/>')}</p>" for p in paras)
            if 'page_title' in data:
                body_html = f"<p class=\"tobira-midashi\">{data['page_title']}</p>\n" + body_html
                label = data.get('page_title')
        elif text_path.lower().endswith(('.html', '.xhtml', '.htm')):
            body_html = read_text_file(text_path)
            label = os.path.splitext(os.path.basename(text_path))[0]
        else:
            txt = read_text_file(text_path)
            paras = [ln.strip() for ln in txt.split('\n\n') if ln.strip()]
            body_html = '\n'.join(f"<p>{p}</p>" for p in paras)
            label = os.path.splitext(os.path.basename(text_path))[0]
    # add image if present
    if image:
        img_path = image if os.path.isabs(image) else os.path.join(meta_dir, image)
        if os.path.exists(img_path):
            shutil.copy2(img_path, os.path.join(image_dir, os.path.basename(img_path)))
            img_tag = f'<p><img class="fit" src="../image/{os.path.basename(img_path)}" alt=""/></p>'
            body_html = img_tag + '\n' + body_html

    # write into p-fmatter-001.xhtml using template
    tpl = os.path.join(xhtml_dir, 'p-fmatter-001.xhtml')
    target = os.path.join(xhtml_dir, 'p-fmatter-001.xhtml')
    template = read_text_file(tpl) if os.path.exists(tpl) else None
    if template and '<body' in template:
        start = template.find('>', template.find('<body')) + 1
        end = template.rfind('</body>')
        new = template[:start] + '\n' + body_html + '\n' + template[end:]
        write_text_file(target, new)
    else:
        write_text_file(target, f"<html><body>{body_html}</body></html>")


def insert_caution(xhtml_dir: str, caution_text: str) -> None:
    if not caution_text:
        return
    tpl = os.path.join(xhtml_dir, 'p-caution.xhtml')
    template = read_text_file(tpl) if os.path.exists(tpl) else None
    body_html = f"<p>{caution_text}</p>"
    if template and '<body' in template:
        start = template.find('>', template.find('<body')) + 1
        end = template.rfind('</body>')
        new = template[:start] + '\n' + body_html + '\n' + template[end:]
        write_text_file(tpl, new)
    else:
        write_text_file(tpl, f"<html><body>{body_html}</body></html>")


def insert_colophon(xhtml_dir: str, colophon_spec: dict | None, meta_dir: str, meta: dict | None = None) -> None:
    if not colophon_spec:
        return
    text = colophon_spec.get('text') if isinstance(colophon_spec, dict) else None
    text_path = None
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)

    body_html = ''
    if text_path and os.path.exists(text_path):
        if text_path.lower().endswith(('.yaml', '.yml')):
            # read and render template (Jinja2 if available)
            with open(text_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            rendered = None
            # build render context: top-level meta keys + colophon keys (flattened)
            render_context = {}
            if isinstance(meta, dict):
                render_context.update(meta)
                c = meta.get('colophon')
                if isinstance(c, dict):
                    render_context.update(c)
            # expand NOW_YMD to current date if present
            if render_context.get('created_at') == 'NOW_YMD':
                render_context['created_at'] = datetime.now().strftime('%Y-%m-%d')
            try:
                from jinja2 import Environment

                env = Environment()
                rendered = env.from_string(raw).render(**render_context)
            except Exception:
                # fallback simple replacement for {{ key }}
                rendered = raw
                try:
                    for k, v in (render_context.items() if isinstance(render_context, dict) else []):
                        rendered = rendered.replace('{{ ' + k + ' }}', str(v))
                except Exception:
                    pass
            try:
                data = yaml.safe_load(rendered) or {}
            except Exception:
                data = {}

            # preserve YAML key order when building HTML
            parts = []
            for k, v in (data.items() if isinstance(data, dict) else []):
                if v is None:
                    continue
                s = str(v).strip()
                if not s:
                    continue
                paras = [p.strip() for p in s.split('\n\n') if p.strip()]
                for p in paras:
                    parts.append(f"<p>{p.replace('\n', '<br/>')}</p>")
            body_html = '\n'.join(parts)
        else:
            body_html = read_text_file(text_path)

    # add version/created_at/copyright if present in spec but not included above
    extras = []
    version = colophon_spec.get('version') if isinstance(colophon_spec, dict) else None
    created_at = colophon_spec.get('created_at') if isinstance(colophon_spec, dict) else None
    copyright_text = colophon_spec.get('copyright') if isinstance(colophon_spec, dict) else None
    if created_at == 'NOW_YMD':
        created_at = datetime.now().strftime('%Y-%m-%d')
    if not body_html:
        if version:
            extras.append(f"版数: {version}")
        if created_at:
            extras.append(f"作成日: {created_at}")
        if copyright_text:
            extras.append(copyright_text)
        if extras:
            body_html = body_html + '\n' + '\n'.join(f"<p>{e}</p>" for e in extras)

    tpl = os.path.join(xhtml_dir, 'p-colophon.xhtml')
    template = read_text_file(tpl) if os.path.exists(tpl) else None
    if template and '<body' in template:
        start = template.find('>', template.find('<body')) + 1
        end = template.rfind('</body>')
        new = template[:start] + '\n' + body_html + '\n' + template[end:]
        write_text_file(tpl, new)
    else:
        write_text_file(tpl, f"<html><body>{body_html}</body></html>")


def insert_advertisement(xhtml_dir: str, adv_spec: dict | None, meta_dir: str, meta: dict | None = None) -> None:
    if not adv_spec:
        return
    text = adv_spec.get('text') if isinstance(adv_spec, dict) else adv_spec
    tpl = os.path.join(xhtml_dir, 'p-ad-001.xhtml')
    if text == 'NONE':
        # remove p-ad-001.xhtml entirely (do not create/include advertisement page)
        try:
            if os.path.exists(tpl):
                os.remove(tpl)
        except Exception:
            pass
        return
    body_html = ''
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)
        if os.path.exists(text_path):
            if text_path.lower().endswith(('.yaml', '.yml')):
                with open(text_path, 'r', encoding='utf-8') as f:
                    try:
                        data = yaml.safe_load(f) or {}
                    except Exception:
                        data = {}
                contents = data.get('contents') or data.get('text') or ''
                if isinstance(contents, list):
                    contents = '\n\n'.join(contents)
                paras = [p.strip() for p in str(contents).split('\n\n') if p.strip()]
                body_html = '\n'.join(f"<p>{p.replace('\n', '<br/>')}</p>" for p in paras)
            else:
                body_html = read_text_file(text_path)

    if not body_html:
        return

    template = read_text_file(tpl) if os.path.exists(tpl) else None
    if template and '<body' in template:
        start = template.find('>', template.find('<body')) + 1
        end = template.rfind('</body>')
        new = template[:start] + '\n' + body_html + '\n' + template[end:]
        write_text_file(tpl, new)
    else:
        write_text_file(tpl, f"<html><body>{body_html}</body></html>")


def insert_titlepage(xhtml_dir: str, meta: dict | None) -> None:
    """Create/replace p-titlepage.xhtml body using metadata `book_title` and `series_title`.

    Both titles are placed on separate lines, centered vertically and horizontally,
    with larger font sizes and horizontal writing mode.
    """
    if not meta:
        return
    book_title = meta.get('book_title') or meta.get('title') or ''
    series_title = meta.get('series_title') or ''

    tpl = os.path.join(xhtml_dir, 'p-titlepage.xhtml')
    template = read_text_file(tpl) if os.path.exists(tpl) else None

    # build centered two-line layout
    body_html = '<div class="titlepage" style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;text-align:center;writing-mode:horizontal-tb;">'
    if book_title:
        body_html += f"<h1 class=\"book-title\" style=\"font-size:48px;margin:0;\">{book_title}</h1>"
    if series_title:
        body_html += f"<h2 class=\"series-title\" style=\"font-size:32px;margin:0;margin-top:0.5em;\">{series_title}</h2>"
    body_html += '</div>'

    if template and '<body' in template:
        start = template.find('>', template.find('<body')) + 1
        end = template.rfind('</body>')
        new = template[:start] + '\n' + body_html + '\n' + template[end:]
        write_text_file(tpl, new)
    else:
        write_text_file(tpl, f"<html><body>{body_html}</body></html>")


def _replace_title_in_string(s: str, title: str) -> str:
    """Replace first <title>...</title> occurrence with provided title."""
    idx = s.find('<title')
    if idx == -1:
        return s
    gt = s.find('>', idx)
    if gt == -1:
        return s
    end = s.find('</title>', gt)
    if end == -1:
        return s
    return s[: gt + 1] + title + s[end:]


def generate_chapter_xhtmls(xhtml_dir: str, chapters: list[str]) -> list[dict]:
    """Generate xhtml files for arbitrary number of chapters.

    Returns list of dicts: {"id": "p-001", "href": "xhtml/p-001.xhtml", "label": "title"}
    """
    os.makedirs(xhtml_dir, exist_ok=True)
    # choose a template to base pages on (prefer p-001.xhtml)
    template_path = os.path.join(xhtml_dir, "p-001.xhtml")
    template = read_text_file(template_path) if os.path.exists(template_path) else None

    created = []
    for i, chap in enumerate(chapters, start=1):
        page_id = f"p-{i:03d}"
        filename = f"{page_id}.xhtml"
        target_path = os.path.join(xhtml_dir, filename)

        label = filename
        body_html = ""

        if os.path.exists(chap):
            if chap.lower().endswith(('.yaml', '.yml')):
                with open(chap, 'r', encoding='utf-8') as f:
                    try:
                        data = yaml.safe_load(f) or {}
                    except Exception:
                        data = {}
                label = data.get('page_title', os.path.splitext(os.path.basename(chap))[0])
                contents = data.get('contents', '')
                # split into paragraphs by blank lines
                paras = [p.strip() for p in contents.split('\n\n') if p.strip()]
                body_html = '\n'.join(f"<p>{p.replace('\n', '<br/>')}</p>" for p in paras)
                # add a heading if page_title exists
                if 'page_title' in data:
                    body_html = f"<p class=\"tobira-midashi\" id=\"toc-{i:03d}\">{data['page_title']}</p>\n" + body_html
            elif chap.lower().endswith(('.html', '.xhtml', '.htm')):
                body_html = read_text_file(chap)
                label = os.path.splitext(os.path.basename(chap))[0]
            else:
                # plain text
                txt = read_text_file(chap)
                paras = [ln.strip() for ln in txt.split('\n\n') if ln.strip()]
                body_html = '\n'.join(f"<p>{p}</p>" for p in paras)
                label = os.path.splitext(os.path.basename(chap))[0]
        else:
            body_html = f"<p>Missing file: {chap}</p>"

        if template and '<body' in template:
            start = template.find('>', template.find('<body')) + 1
            end = template.rfind('</body>')
            new = template[:start] + '\n' + body_html + '\n' + template[end:]
            # set the <title> to the page title/label
            new = _replace_title_in_string(new, label)
            write_text_file(target_path, new)
        else:
            content = f"<html><head><title>{label}</title></head><body>{body_html}</body></html>"
            write_text_file(target_path, content)

        created.append({"id": page_id, "href": f"xhtml/{filename}", "label": label})

    return created


def update_opf_dynamic(opf_path: str, meta: dict, chapters_info: list[dict], include_frontmatter: bool, include_caution: bool) -> None:
    import xml.etree.ElementTree as ET

    ns = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    ET.register_namespace('', ns['opf'])
    ET.register_namespace('dc', ns['dc'])

    tree = ET.parse(opf_path)
    root = tree.getroot()

    # update basic metadata entries
    for title_el in root.findall('.//{http://purl.org/dc/elements/1.1/}title'):
        title_val = meta.get('title') or meta.get('book_title')
        if title_val:
            title_el.text = title_val
    for creator in root.findall('.//{http://purl.org/dc/elements/1.1/}creator'):
        cid = creator.get('id')
        if cid == 'creator01' and 'creator01' in meta:
            creator.text = meta['creator01']
        if cid == 'creator02' and 'creator02' in meta:
            creator.text = meta['creator02']
    for pub in root.findall('.//{http://purl.org/dc/elements/1.1/}publisher'):
        if 'publisher' in meta:
            pub.text = meta['publisher']

    # identifier
    for ident in root.findall('.//{http://purl.org/dc/elements/1.1/}identifier'):
        if ident.get('id') == 'unique-id':
            ident.text = f"urn:uuid:{uuid.uuid4()}"

    # modified
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for meta_el in root.findall('.//{http://www.idpf.org/2007/opf}meta'):
        if meta_el.get('property') == 'dcterms:modified':
            meta_el.text = now

    manifest = root.find('{http://www.idpf.org/2007/opf}manifest')
    if manifest is None:
        return

    # preserve existing nav/style items when possible
    existing_items = { (it.get('href') or ''): it for it in manifest.findall('{http://www.idpf.org/2007/opf}item') }

    # build a new manifest element and populate it in logical groups with comments
    new_manifest = ET.Element('{http://www.idpf.org/2007/opf}manifest')

    def make_item(item_id, href, media_type='application/xhtml+xml', properties=None):
        el = ET.Element('{http://www.idpf.org/2007/opf}item')
        el.set('id', item_id)
        el.set('href', href)
        el.set('media-type', media_type)
        if properties:
            el.set('properties', properties)
        return el

    # navigation
    new_manifest.append(ET.Comment(' navigation '))
    nav_href = None
    for href, it in existing_items.items():
        props = it.get('properties') or ''
        if 'nav' in props:
            new_manifest.append(it)
            nav_href = href
            break
    if nav_href is None:
        new_manifest.append(make_item('toc', 'navigation-documents.xhtml', 'application/xhtml+xml', 'nav'))

    # styles
    new_manifest.append(ET.Comment(' style '))
    for href, it in existing_items.items():
        if href.startswith('style/') or it.get('media-type') == 'text/css':
            new_manifest.append(it)

    # images: scan output image directory and add any images present
    new_manifest.append(ET.Comment(' image '))
    image_folder = os.path.join(os.path.dirname(opf_path), 'image')
    img_id_map = {}
    if os.path.isdir(image_folder):
        files = sorted(os.listdir(image_folder))
        cnt = 1
        used_ids = set()
        for fn in files:
            href = f'image/{fn}'
            base, ext = os.path.splitext(fn)
            ext = ext.lower()
            media = 'image/jpeg'
            if ext == '.png':
                media = 'image/png'
            elif ext == '.svg':
                media = 'image/svg+xml'
            elif ext == '.gif':
                media = 'image/gif'
            elif ext in ('.jpg', '.jpeg'):
                media = 'image/jpeg'
            # choose id: prefer 'backcover' for filenames containing 'back', 'cover' for cover
            props = None
            if 'back' in base.lower():
                item_id = 'backcover'
            elif 'cover' in base.lower():
                item_id = 'cover'
                props = 'cover-image'
            else:
                item_id = re.sub('[^0-9A-Za-z_-]', '-', base)
                if not item_id:
                    item_id = f'img-{cnt}'
            # ensure unique id
            orig_id = item_id
            i = 1
            while item_id in used_ids:
                item_id = f"{orig_id}-{i}"
                i += 1
            used_ids.add(item_id)
            img_id_map[href] = item_id
            el = make_item(item_id, href, media, props)
            new_manifest.append(el)
            cnt += 1

    # xhtml
    new_manifest.append(ET.Comment(' xhtml '))
    # keep cover only if file exists
    def add_xhtml_if_exists(item_id, href, properties=None):
        full = os.path.join(os.path.dirname(opf_path), href)
        if os.path.exists(full):
            new_manifest.append(make_item(item_id, href, 'application/xhtml+xml', properties))

    add_xhtml_if_exists('p-cover', 'xhtml/p-cover.xhtml')
    if include_frontmatter:
        add_xhtml_if_exists('p-fmatter-001', 'xhtml/p-fmatter-001.xhtml')
    add_xhtml_if_exists('p-titlepage', 'xhtml/p-titlepage.xhtml')
    if include_caution:
        add_xhtml_if_exists('p-caution', 'xhtml/p-caution.xhtml')
    add_xhtml_if_exists('p-toc', 'xhtml/p-toc.xhtml')

    for ch in chapters_info:
        add_xhtml_if_exists(ch['id'], ch['href'])

    add_xhtml_if_exists('p-colophon', 'xhtml/p-colophon.xhtml')
    add_xhtml_if_exists('p-ad-001', 'xhtml/p-ad-001.xhtml')
    add_xhtml_if_exists('p-backcover', 'xhtml/p-backcover.xhtml')

    # replace old manifest with new_manifest preserving position
    parent = root
    children = list(parent)
    idx = children.index(manifest)
    parent.remove(manifest)
    parent.insert(idx, new_manifest)

    spine = root.find('{http://www.idpf.org/2007/opf}spine')
    if spine is None:
        return
    for ir in list(spine.findall('{http://www.idpf.org/2007/opf}itemref')):
        spine.remove(ir)

    def add_itemref(idref, props=None):
        ir = ET.Element('{http://www.idpf.org/2007/opf}itemref')
        ir.set('linear', 'yes')
        ir.set('idref', idref)
        if props:
            ir.set('properties', props)
        else:
            ir.set('properties', 'page-spread-left')
        spine.append(ir)

    add_itemref('p-cover')
    if include_frontmatter:
        add_itemref('p-fmatter-001')
    add_itemref('p-titlepage')
    if include_caution:
        add_itemref('p-caution')
    add_itemref('p-toc')
    for ch in chapters_info:
        add_itemref(ch['id'])
    add_itemref('p-colophon')
    add_itemref('p-ad-001')
    add_itemref('p-backcover')

    tree.write(opf_path, encoding='utf-8', xml_declaration=True)


def update_opf_basic(opf_path: str, meta: dict) -> None:
    s = read_text_file(opf_path)
    # title
    if "title" in meta:
        s = s.replace("<dc:title id=\"title\">作品名１</dc:title>", f"<dc:title id=\"title\">{meta['title']}</dc:title>")
    # creators
    if "creator01" in meta:
        s = s.replace("<dc:creator id=\"creator01\">著作者名１</dc:creator>", f"<dc:creator id=\"creator01\">{meta['creator01']}</dc:creator>")
    if "creator02" in meta:
        s = s.replace("<dc:creator id=\"creator02\">著作者名２</dc:creator>", f"<dc:creator id=\"creator02\">{meta['creator02']}</dc:creator>")
    if "publisher" in meta:
        s = s.replace("<dc:publisher id=\"publisher\">出版社名</dc:publisher>", f"<dc:publisher id=\"publisher\">{meta['publisher']}</dc:publisher>")
    # identifier
    uid = f"urn:uuid:{uuid.uuid4()}"
    s = s.replace(
        s[s.find("<dc:identifier id=\"unique-id\">") : s.find("</dc:identifier>") + len("</dc:identifier>")],
        f"<dc:identifier id=\"unique-id\">{uid}</dc:identifier>",
    )
    # modified
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if "<meta property=\"dcterms:modified\">" in s:
        start = s.find("<meta property=\"dcterms:modified\">")
        end = s.find("</meta>", start) + len("</meta>")
        s = s[:start] + f"<meta property=\"dcterms:modified\">{now}</meta>" + s[end:]
    else:
        # insert before </metadata>
        s = s.replace("</metadata>", f"<meta property=\"dcterms:modified\">{now}</meta>\n</metadata>")

    write_text_file(opf_path, s)


def update_navigation(nav_path: str, chapters_info: list[dict]) -> None:
    # navigation-documents.xhtml should only contain cover, toc and colophon (template style)
    nav_template = read_text_file(nav_path) if os.path.exists(nav_path) else None
    nav_items = [
        '<li><a href="xhtml/p-cover.xhtml">表紙</a></li>',
        '<li><a href="xhtml/p-toc.xhtml">目次</a></li>',
        '<li><a href="xhtml/p-colophon.xhtml">奥付</a></li>',
    ]
    nav_ol = "\n".join(nav_items)
    if nav_template and '<ol>' in nav_template:
        start = nav_template.find('<ol>')
        end = nav_template.find('</ol>', start)
        if start != -1 and end != -1:
            nav_template = nav_template[: start + len('<ol>')] + '\n' + nav_ol + '\n' + nav_template[end:]
            write_text_file(nav_path, nav_template)
    else:
        # fallback simple nav
        nav_html = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">\n<head>\n<meta charset="UTF-8"/>\n<title>Navigation</title>\n</head>\n<body>\n<nav epub:type="toc" id="toc">\n<h1>Navigation</h1>\n<ol>\n' + nav_ol + '\n</ol>\n</nav>\n</body>\n</html>'
        write_text_file(nav_path, nav_html)

    # update p-toc.xhtml: create chapter-only TOC using chapters_info
    xhtml_dir = os.path.join(os.path.dirname(nav_path), 'xhtml')
    toc_path = os.path.join(xhtml_dir, 'p-toc.xhtml')
    if os.path.exists(toc_path):
        s2 = read_text_file(toc_path)
        # build chapter-only links
        lines = []
        for ch in chapters_info:
            href = os.path.basename(ch['href'])
            # if label contains newlines or is long, keep plain label
            label = ch.get('label') or ch['id']
            # assume each chapter may have an id anchor like #toc-001
            # if generated, use that anchor
            # extract id number from ch['id'] (p-001 -> 001)
            m = None
            try:
                m = int(ch['id'].split('-')[-1])
            except Exception:
                m = None
            if m:
                anchor = f"#toc-{m:03d}"
            else:
                anchor = ''
            link = f'<p><a href="{href}{anchor}">{label}</a></p>' if anchor else f'<p><a href="{href}">{label}</a></p>'
            lines.append(link)
        toc_body = '\n'.join(lines)
        # replace between the first <h1 ..> and closing </div> or between known markers
        if '<ol>' in s2 and '</ol>' in s2:
            start = s2.find('<ol>')
            end = s2.find('</ol>', start)
            s2 = s2[: start + len('<ol>')] + '\n' + '\n'.join([f'<li><a href="{os.path.basename(ch["href"])}">{ch.get("label") or ch.get("id")}</a></li>' for ch in chapters_info]) + '\n' + s2[end:]
            write_text_file(toc_path, s2)
        else:
            # fallback: replace main content body
            if '<div class="main">' in s2 and '</div>' in s2:
                st = s2.find('<div class="main">')
                en = s2.find('</div>', st)
                newdiv = '<div class="main">\n\n<h1 class="mokuji-midashi">　目次見出し</h1>\n' + toc_body + '\n</div>'
                s2 = s2[:st] + newdiv + s2[en+6:]
                write_text_file(toc_path, s2)


def make_epub_from_template(tmpdir: str, out_epub: str) -> None:
    # create EPUB (mimetype first, uncompressed)
    template_item = os.path.join(tmpdir, "item")
    root = os.path.join(tmpdir)
    mimetype_path = os.path.join(root, "mimetype")
    # build list of files
    # try to remove existing output file first (may fail if file is locked by another process)
    try:
        if os.path.exists(out_epub):
            os.remove(out_epub)
    except Exception:
        # let ZipFile raise a clear PermissionError if file is locked
        pass

    with zipfile.ZipFile(out_epub, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # mimetype must be stored and first
        z.writestr("mimetype", read_text_file(mimetype_path), compress_type=zipfile.ZIP_STORED)
        for base, dirs, files in os.walk(root):
            for fn in files:
                path = os.path.join(base, fn)
                arcname = os.path.relpath(path, root)
                if arcname == "mimetype":
                    continue
                z.write(path, arcname)


def main(argv: list[str]) -> int:
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

    # copy template to tmpdir
    tmpdir = tempfile.mkdtemp(prefix="yaml2epub_")
    try:
        shutil.copytree(TEMPLATE_DIR, os.path.join(tmpdir), dirs_exist_ok=True)
    except Exception:
        # older Python copytree fallback
        shutil.copytree(TEMPLATE_DIR, tmpdir)

    # remove template-provided images so only user-supplied images are included
    template_image_dir = os.path.join(tmpdir, 'item', 'image')
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

    # replace title in xhtml templates (support book_title key)
    title = meta.get("title") or meta.get("book_title", "作品名未設定")
    replace_title_in_xhtml(tmpdir, title)
    # generate title page body from metadata (book_title and series_title)
    try:
        insert_titlepage(os.path.join(tmpdir, 'item', 'xhtml'), meta)
    except Exception:
        pass

    # create back cover xhtml by copying p-cover.xhtml -> p-backcover.xhtml (if present)
    xhtml_dir = os.path.join(tmpdir, 'item', 'xhtml')
    cover_src = os.path.join(xhtml_dir, 'p-cover.xhtml')
    back_src = os.path.join(xhtml_dir, 'p-backcover.xhtml')
    try:
        if os.path.exists(cover_src) and not os.path.exists(back_src):
            shutil.copy2(cover_src, back_src)
    except Exception:
        pass

    # handle images
    images = meta.get("image", {}) or {}
    image_dir = os.path.join(tmpdir, "item", "image")
    os.makedirs(image_dir, exist_ok=True)
    # copy user-specified cover/backcover without converting filenames
    cover_provided = False
    backcover_provided = False
    if "cover" in images:
        src = images["cover"]
        src_path = src if os.path.isabs(src) else os.path.join(os.path.dirname(os.path.abspath(meta_path)), src)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(image_dir, os.path.basename(src_path)))
            cover_provided = True
    if "backcover" in images:
        src = images["backcover"]
        src_path = src if os.path.isabs(src) else os.path.join(os.path.dirname(os.path.abspath(meta_path)), src)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(image_dir, os.path.basename(src_path)))
            backcover_provided = True

    # remove p-cover.xhtml/p-backcover.xhtml if corresponding images not provided
    xhtml_dir = os.path.join(tmpdir, 'item', 'xhtml')
    cover_file = os.path.join(xhtml_dir, 'p-cover.xhtml')
    back_file = os.path.join(xhtml_dir, 'p-backcover.xhtml')
    try:
        if not cover_provided and os.path.exists(cover_file):
            os.remove(cover_file)
        if not backcover_provided and os.path.exists(back_file):
            os.remove(back_file)
    except Exception:
        pass
    # if cover/backcover provided, update p-cover.xhtml/p-backcover.xhtml image src to actual filenames
    try:
        if cover_provided:
            # find the provided cover filename
            cover_fname = os.path.basename(images.get('cover'))
            if cover_fname and os.path.exists(os.path.join(image_dir, cover_fname)) and os.path.exists(cover_file):
                s = read_text_file(cover_file)
                s = re.sub(r'src="\.\./image/[^\"]+"', f'src="../image/{cover_fname}"', s)
                write_text_file(cover_file, s)
        if backcover_provided:
            back_fname = os.path.basename(images.get('backcover'))
            if back_fname and os.path.exists(os.path.join(image_dir, back_fname)) and os.path.exists(back_file):
                s = read_text_file(back_file)
                s = re.sub(r'src="\.\./image/[^\"]+"', f'src="../image/{back_fname}"', s)
                write_text_file(back_file, s)
    except Exception:
        pass

    # insert frontmatter/caution/colophon
    meta_dir = os.path.dirname(os.path.abspath(meta_path))
    docs = meta.get("documents", {}) or {}
    front = docs.get('frontmatter')
    insert_frontmatter(os.path.join(tmpdir, 'item', 'xhtml'), front, meta_dir, os.path.join(tmpdir, 'item', 'image'))
    insert_caution(os.path.join(tmpdir, 'item', 'xhtml'), meta.get('caution'))
    insert_colophon(os.path.join(tmpdir, 'item', 'xhtml'), meta.get('colophon'), meta_dir, meta)
    insert_advertisement(os.path.join(tmpdir, 'item', 'xhtml'), meta.get('advatizement'), meta_dir, meta)


    # inject chapters (support arbitrary number)
    docs = meta.get("documents", {}) or {}
    contents = docs.get("contents", []) or []
    chapters = [d.get("chapter") if isinstance(d, dict) else d for d in contents]
    chapters = [c for c in chapters if c]
    # resolve chapter paths relative to metadata file
    meta_dir = os.path.dirname(os.path.abspath(meta_path))
    chapters = [c if os.path.isabs(c) else os.path.join(meta_dir, c) for c in chapters]
    xhtml_dir = os.path.join(tmpdir, "item", "xhtml")
    chapters_info = generate_chapter_xhtmls(xhtml_dir, chapters)

    # remove unused p-XXX.xhtml files from template that were not generated
    try:
        existing = [n for n in os.listdir(xhtml_dir) if n.endswith('.xhtml')]
        keep = set([os.path.basename(ch['href']) for ch in chapters_info])
        keep.update(('p-cover.xhtml','p-titlepage.xhtml','p-fmatter-001.xhtml','p-caution.xhtml','p-toc.xhtml','p-colophon.xhtml','p-ad-001.xhtml','p-backcover.xhtml','p-titlepage.xhtml'))
        for fn in existing:
            if fn.startswith('p-') and fn not in keep:
                fp = os.path.join(xhtml_dir, fn)
                try:
                    os.remove(fp)
                except Exception:
                    pass
    except Exception:
        pass

    # update opf dynamically
    opf_path = os.path.join(tmpdir, "item", "standard.opf")
    include_frontmatter = bool(docs.get('frontmatter'))
    include_caution = bool(meta.get('caution'))
    if os.path.exists(opf_path):
        update_opf_dynamic(opf_path, meta, chapters_info, include_frontmatter, include_caution)

    # update nav
    nav_path = os.path.join(tmpdir, "item", "navigation-documents.xhtml")
    if os.path.exists(nav_path):
        update_navigation(nav_path, chapters_info)

    # build final epub
    out_path = out_epub
    make_epub_from_template(tmpdir, out_path)

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
