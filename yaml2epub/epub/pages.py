"""Document section insertion and chapter generation."""

from __future__ import annotations

import gzip
import os
import shutil
from datetime import datetime

import yaml  # type: ignore[import-untyped]

from yaml2epub.epub.constants import NONE_TEXT
from yaml2epub.epub.xhtml import _render_document
from yaml2epub.utils import read_text_file, warn


def _insert_document_section(
    xhtml_dir: str,
    spec: dict | None,
    meta_dir: str,
    image_dir: str,
    output_filename: str,
    label_default: str = "document",
    template_filename: str = "p-fmatter-001.xhtml",
    br_convert: bool = False,
) -> None:
    """Insert a document section (frontmatter, backmatter, etc.).

    Common implementation for document sections with similar structure.

    Args:
        xhtml_dir (str): Directory containing XHTML files.
        spec (dict | None): Specification for the document section.
        meta_dir (str): Directory containing metadata files.
        image_dir (str): Directory to store images.
        output_filename (str): Output XHTML filename (e.g., "p-fmatter-001.xhtml").
        label_default (str): Default label for the section if not specified.
        template_filename (str): Template XHTML filename to use as base.
    """
    if not spec:
        return
    text = spec.get("text") if isinstance(spec, dict) else spec
    # allow either a single image path or list of paths
    img_spec = spec.get("image") if isinstance(spec, dict) else None
    images: list[str] = []
    if img_spec:
        if isinstance(img_spec, list):
            images = img_spec
        else:
            images = [img_spec]

    # resolve paths
    text_path = None
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)

    # prepare body
    body_html = ""
    label = label_default
    # default direction/body_class from spec (if provided)
    spec_direction = spec.get("direction") if isinstance(spec, dict) else None
    spec_body_class = spec.get("body_class") if isinstance(spec, dict) else None
    direction = None
    body_class = None

    if text_path and os.path.exists(text_path):
        if text_path.lower().endswith((".yaml", ".yml")):
            with open(text_path, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f) or {}
                except Exception as exc:
                    # Keep the pipeline running when a content YAML is unreadable;
                    # an empty body is safer than aborting the whole EPUB build.
                    warn(
                        f"failed to parse {text_path} as YAML ({exc}); using empty document"
                    )
                    data = {}
            # allow YAML to override direction/body_class
            direction = data.get("direction") or spec_direction
            body_class = data.get("body_class") or spec_body_class
            contents = data.get("contents", "")
            # split into paragraphs by blank lines
            paras = [p.strip() for p in contents.split("\n\n") if p.strip()]
            if br_convert:
                # convert remaining single-line breaks to <br/>
                paras = [p.replace("\n", "<br/>") for p in paras]
            # first paragraph indented
            if paras:
                body_html = f"<p>{paras[0]}</p>\n" + "\n".join(
                    f"<p>{p}</p>" for p in paras[1:]
                )
            if "page_title" in data:
                body_html = (
                    f"<p class=\"tobira-midashi\">{data['page_title']}</p>\n"
                    + body_html
                )
                label = data.get("page_title")  # type: ignore[assignment]
        elif text_path.lower().endswith((".html", ".xhtml", ".htm")):
            body_html = read_text_file(text_path)
            label = os.path.splitext(os.path.basename(text_path))[0]
            # no YAML parsing, fall back to spec-provided direction/body_class
            direction = spec_direction
            body_class = spec_body_class
        else:
            txt = read_text_file(text_path)
            paras = [ln.strip() for ln in txt.split("\n\n") if ln.strip()]
            if br_convert:
                paras = [p.replace("\n", "<br/>") for p in paras]
            body_html = "\n".join(f"<p>{p}</p>" for p in paras)
            label = os.path.splitext(os.path.basename(text_path))[0]
            direction = spec_direction
            body_class = spec_body_class
    else:
        direction = spec_direction
        body_class = spec_body_class

    # add any images if present - collect in order before prepending
    image_tags = []
    for image in images:
        img_path = image if os.path.isabs(image) else os.path.join(meta_dir, image)
        if os.path.exists(img_path):
            basename = os.path.basename(img_path)
            dest_path = os.path.join(image_dir, basename)
            # Handle SVGZ files: decompress to SVG
            if basename.lower().endswith(".svgz"):
                svg_basename = basename[:-1]  # remove 'z'
                dest_path = os.path.join(image_dir, svg_basename)
                with gzip.open(img_path, "rb") as f_in:
                    with open(dest_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                img_src = f"../image/{svg_basename}"
            else:
                shutil.copy2(img_path, dest_path)
                img_src = f"../image/{basename}"
            img_tag = f'<p><img class="fit" src="{img_src}" alt=""/></p>'
            image_tags.append(img_tag)
    # prepend all images in original order
    if image_tags:
        body_html = "\n".join(image_tags) + "\n" + body_html

    # preserve the template shell/head and only replace the body content.
    tpl = os.path.join(xhtml_dir, template_filename)
    target = os.path.join(xhtml_dir, output_filename)
    _render_document(
        tpl,
        body_html,
        label or label_default,
        body_class,
        direction,
        target,
        replace_title=True,
    )


def insert_frontmatter(
    xhtml_dir: str,
    spec: dict | None,
    meta_dir: str,
    image_dir: str,
    br_convert: bool = False,
) -> None:
    """Insert frontmatter content into p-fmatter-<index>.xhtml.

    The argument `spec` is a path (str) or a dict with `text` / `image` keys.
    Unlike other document sections, caution uses inline text only so it keeps
    its own dedicated logic above.
    """
    _insert_document_section(
        xhtml_dir,
        spec,
        meta_dir,
        image_dir,
        output_filename="p-fmatter-001.xhtml",
        label_default="frontmatter",
        template_filename="p-fmatter-001.xhtml",
        br_convert=br_convert,
    )


def insert_backmatter(
    xhtml_dir: str,
    spec: dict | None,
    meta_dir: str,
    image_dir: str,
    br_convert: bool = False,
) -> None:
    """Insert backmatter content into p-bmatter-001.xhtml.

    Args:
        xhtml_dir (str): Directory holding XHTML templates.
        spec (dict | None | str): Path to YAML/HTML text, or dict with at least `text`.
        meta_dir (str): Directory of metadata files.
        image_dir (str): Directory of images.
        br_convert (bool): Replace single LF with ``<br/>`` when converting.
    """
    _insert_document_section(
        xhtml_dir,
        spec,
        meta_dir,
        image_dir,
        output_filename="p-bmatter-001.xhtml",
        label_default="backmatter",
        template_filename="p-bmatter-001.xhtml",
        br_convert=br_convert,
    )


def insert_caution(xhtml_dir: str, caution_text: str | None) -> None:
    if not caution_text:
        return
    tpl = os.path.join(xhtml_dir, "p-caution.xhtml")
    body_html = f"<p>{caution_text}</p>"
    _render_document(tpl, body_html, "caution", None, None, tpl, replace_title=False)


def insert_colophon(
    xhtml_dir: str, colophon_spec: dict | None, meta_dir: str, meta: dict | None = None
) -> None:
    if not colophon_spec:
        return
    text = colophon_spec.get("text") if isinstance(colophon_spec, dict) else None
    text_path = None
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)

    body_html = ""
    direction = None
    body_class = None
    if text_path and os.path.exists(text_path):
        if text_path.lower().endswith((".yaml", ".yml")):
            # read and render template (Jinja2 if available)
            with open(text_path, "r", encoding="utf-8") as f:
                raw = f.read()
            rendered = None
            # build render context: top-level meta keys + colophon keys (flattened)
            render_context = {}
            if isinstance(meta, dict):
                render_context.update(meta)
                c = meta.get("colophon")
                if isinstance(c, dict):
                    render_context.update(c)
            # expand NOW_YMD to current date if present
            if render_context.get("created_at") == "NOW_YMD":
                render_context["created_at"] = datetime.now().strftime("%Y-%m-%d")
            try:
                from jinja2 import Environment

                env = Environment()
                rendered = env.from_string(raw).render(**render_context)
            except Exception as exc:
                # Jinja2 is optional; fall back to naive placeholder replacement.
                warn(
                    f"Jinja2 rendering failed for {text_path} ({exc}); "
                    "falling back to simple replacement"
                )
                rendered = raw
                try:
                    for k, v in (
                        render_context.items()
                        if isinstance(render_context, dict)
                        else []
                    ):
                        rendered = rendered.replace("{{ " + k + " }}", str(v))
                except Exception:
                    # Best effort: keep the raw template if even simple replacement fails.
                    pass
            try:
                data = yaml.safe_load(rendered) or {}
            except Exception as exc:
                warn(
                    f"failed to parse rendered {text_path} as YAML ({exc}); "
                    "using empty colophon document"
                )
                data = {}

            # get direction/body_class from YAML if present
            direction = data.get("direction")
            body_class = data.get("body_class")

            # preserve YAML key order when building HTML
            parts = []
            for k, v in (data.items() if isinstance(data, dict) else []):
                if v is None:
                    continue
                s = str(v).strip()
                if not s:
                    continue
                paras = [p.strip() for p in s.split("\n\n") if p.strip()]
                for p in paras:
                    parts.append(f"<p>{p.replace('\n', '<br/>')}</p>")
            body_html = "\n".join(parts)
        else:
            body_html = read_text_file(text_path)

    # add version/created_at/copyright if present in spec but not included above
    extras = []
    version = colophon_spec.get("version") if isinstance(colophon_spec, dict) else None
    created_at = (
        colophon_spec.get("created_at") if isinstance(colophon_spec, dict) else None
    )
    copyright_text = (
        colophon_spec.get("copyright") if isinstance(colophon_spec, dict) else None
    )
    if created_at == "NOW_YMD":
        created_at = datetime.now().strftime("%Y-%m-%d")
    if not body_html:
        if version:
            extras.append(f"版数: {version}")
        if created_at:
            extras.append(f"作成日: {created_at}")
        if copyright_text:
            extras.append(copyright_text)
        if extras:
            body_html = body_html + "\n" + "\n".join(f"<p>{e}</p>" for e in extras)

    # allow override from colophon_spec if not in YAML
    if not direction and isinstance(colophon_spec, dict):
        direction = colophon_spec.get("direction")
    if not body_class and isinstance(colophon_spec, dict):
        body_class = colophon_spec.get("body_class")

    tpl = os.path.join(xhtml_dir, "p-colophon.xhtml")
    _render_document(
        tpl, body_html, "colophon", body_class, direction, tpl, replace_title=False
    )


def insert_advertisement(
    xhtml_dir: str, adv_spec: dict | None, meta_dir: str, meta: dict | None = None
) -> None:
    if not adv_spec:
        return
    text = adv_spec.get("text") if isinstance(adv_spec, dict) else adv_spec
    tpl = os.path.join(xhtml_dir, "p-ad-001.xhtml")
    if text == NONE_TEXT:
        # remove p-ad-001.xhtml entirely (do not create/include advertisement page)
        try:
            if os.path.exists(tpl):
                os.remove(tpl)
        except Exception:
            # Best-effort removal: the OPF allow-list still excludes the page even if
            # the stale file remains in the temporary directory.
            pass
        return
    body_html = ""
    direction = None
    body_class = None
    if text:
        text_path = text if os.path.isabs(text) else os.path.join(meta_dir, text)
        if os.path.exists(text_path):
            if text_path.lower().endswith((".yaml", ".yml")):
                with open(text_path, "r", encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f) or {}
                    except Exception as exc:
                        warn(
                            f"failed to parse {text_path} as YAML ({exc}); "
                            "using empty advertisement document"
                        )
                        data = {}
                # allow direction/body_class in advertisement yaml
                direction = data.get("direction")
                body_class = data.get("body_class")
                contents = data.get("contents") or data.get("text") or ""
                if isinstance(contents, list):
                    contents = "\n\n".join(contents)
                paras = [p.strip() for p in str(contents).split("\n\n") if p.strip()]
                body_html = "\n".join(
                    f"<p>{p.replace('\n', '<br/>')}</p>" for p in paras
                )
            else:
                body_html = read_text_file(text_path)

    if not body_html:
        return

    # allow override from adv_spec
    if not direction and isinstance(adv_spec, dict):
        direction = adv_spec.get("direction")
    if not body_class and isinstance(adv_spec, dict):
        body_class = adv_spec.get("body_class")

    _render_document(
        tpl, body_html, "advertisement", body_class, direction, tpl, replace_title=False
    )


def insert_titlepage(xhtml_dir: str, meta: dict | None) -> None:
    """Create/replace p-titlepage.xhtml body using metadata `book_title` and `series_title`.

    Both titles are placed on separate lines, centered vertically and horizontally,
    with larger font sizes and horizontal writing mode.
    """
    if not meta:
        return
    book_title = meta.get("book_title") or meta.get("title") or ""
    series_title = meta.get("series_title") or ""

    # build centered two-line layout
    body_html = '<div class="titlepage" style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;text-align:center;writing-mode:horizontal-tb;">'
    if book_title:
        body_html += (
            f'<h1 class="book-title" style="font-size:48px;margin:0;">{book_title}</h1>'
        )
    if series_title:
        body_html += f'<h2 class="series-title" style="font-size:32px;margin:0;margin-top:0.5em;">{series_title}</h2>'
    body_html += "</div>"

    # allow meta-level overrides
    direction = meta.get("direction") if isinstance(meta, dict) else None
    body_class = meta.get("body_class") if isinstance(meta, dict) else None

    tpl = os.path.join(xhtml_dir, "p-titlepage.xhtml")
    _render_document(
        tpl,
        body_html,
        book_title or "titlepage",
        body_class,
        direction,
        tpl,
        replace_title=True,
    )


def generate_chapter_xhtmls(
    xhtml_dir: str, chapters: list[str], br_convert: bool = False
) -> list[dict]:
    """Generate xhtml files for arbitrary number of chapters.

    Returns list of dicts: {"id": "p-001", "href": "xhtml/p-001.xhtml", "label": "title"}
    """
    os.makedirs(xhtml_dir, exist_ok=True)
    created = []
    for i, chap in enumerate(chapters, start=1):
        page_id = f"p-{i:03d}"
        filename = f"{page_id}.xhtml"
        target_path = os.path.join(xhtml_dir, filename)

        label = filename
        body_html = ""
        direction = None
        body_class = None

        if os.path.exists(chap):
            if chap.lower().endswith((".yaml", ".yml")):
                with open(chap, "r", encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f) or {}
                    except Exception as exc:
                        warn(
                            f"failed to parse {chap} as YAML ({exc}); using empty chapter document"
                        )
                        data = {}
                label = data.get(
                    "page_title", os.path.splitext(os.path.basename(chap))[0]
                )
                contents = data.get("contents", "")
                # capture direction/body_class from chapter YAML
                direction = data.get("direction")
                body_class = data.get("body_class")
                # split into paragraphs by blank lines
                paras = [p.strip() for p in contents.split("\n\n") if p.strip()]
                if br_convert:
                    paras = [p.replace("\n", "<br/>") for p in paras]
                # first paragraph indented
                if paras:
                    body_html = f"<p>{paras[0]}</p>\n" + "\n".join(
                        f"<p>{p}</p>" for p in paras[1:]
                    )
                else:
                    body_html = ""
                # add a heading if page_title exists
                if "page_title" in data:
                    body_html = (
                        f"<p class=\"tobira-midashi\" id=\"toc-{i:03d}\">{data['page_title']}</p>\n"
                        + body_html
                    )
            elif chap.lower().endswith((".html", ".xhtml", ".htm")):
                body_html = read_text_file(chap)
                label = os.path.splitext(os.path.basename(chap))[0]
                # no YAML, keep defaults
            else:
                # plain text
                txt = read_text_file(chap)
                paras = [ln.strip() for ln in txt.split("\n\n") if ln.strip()]
                if br_convert:
                    paras = [p.replace("\n", "<br/>") for p in paras]
                body_html = "\n".join(f"<p>{p}</p>" for p in paras)
                label = os.path.splitext(os.path.basename(chap))[0]
        else:
            body_html = f"<p>Missing file: {chap}</p>"

        if os.path.exists(os.path.join(xhtml_dir, "p-001.xhtml")):
            template = read_text_file(os.path.join(xhtml_dir, "p-001.xhtml"))
        else:
            template = None
        _render_document(
            template,
            body_html,
            label,
            body_class,
            direction,
            target_path,
            replace_title=True,
        )

        created.append({"id": page_id, "href": f"xhtml/{filename}", "label": label})

    return created
