"""XHTML document computation, building, and rendering."""

from __future__ import annotations

import os
import re

from yaml2epub.epub.constants import DEFAULT_BODY_CLASS
from yaml2epub.utils import read_text_file, warn, write_text_file


def _is_vertical(direction: str | None) -> bool:
    """Return True when the writing direction is vertical.

    Args:
        direction (str | None): Direction string (e.g. 'Vertical', 'horizontal-tb').

    Returns:
        bool: True for vertical writing mode, False otherwise.
    """
    if not direction:
        return False
    return direction.lower().startswith("v")


def _compute_style_value(direction: str | None) -> str:
    """Compute the CSS writing-mode value for the given direction.

    Args:
        direction (str | None): Direction string (e.g. 'Vertical', 'horizontal-tb').

    Returns:
        str: The CSS style string for writing-mode.
    """
    if not direction:
        return ""
    if _is_vertical(direction):
        return "writing-mode: vertical-rl; -epub-writing-mode: vertical-rl;"
    return "writing-mode: horizontal-tb; -epub-writing-mode: horizontal-tb;"


def _compute_html_class(direction: str | None) -> str:
    """Return the HTML ``class`` value for the given writing direction.

    Vertical writing mode uses ``vrtl``; any other direction (including ``None``)
    uses ``hltr``. Centralizes the direction->class mapping so the XHTML builders
    cannot drift out of sync.

    Args:
        direction (str | None): Direction string (e.g. 'Vertical', 'Horizontal').

    Returns:
        str: 'vrtl' for vertical writing mode, 'hltr' otherwise.
    """
    return "vrtl" if _is_vertical(direction) else "hltr"


def _replace_title_in_string(s: str, title: str) -> str:
    """Replace the first ``<title>`` occurrence in a single document string.

    This is the lowest-level helper used by both directory-wide updates and
    per-document rendering. It does not touch any files itself.

    Args:
        s (str): XHTML document text.
        title (str): Replacement title text.

    Returns:
        str: Updated document text, or the original text when no title tag exists.
    """
    idx = s.find("<title")
    if idx == -1:
        return s
    gt = s.find(">", idx)
    if gt == -1:
        return s
    end = s.find("</title>", gt)
    if end == -1:
        return s
    return s[: gt + 1] + title + s[end:]


def replace_title_in_xhtml(dirpath: str, title: str) -> None:
    """Rewrite ``<title>`` in every existing XHTML file under ``dirpath``.

    This is the directory-wide pass used before page generation so template
    documents inherit the book title from metadata. It intentionally does not
    know about individual pages; per-page rendering uses ``_render_document``
    with its explicit ``replace_title`` flag instead.

    Args:
        dirpath (str): Temporary package root containing ``item/xhtml``.
        title (str): Title to apply to every XHTML file found.
    """
    xhtml_dir = os.path.join(dirpath, "item", "xhtml")
    if not os.path.isdir(xhtml_dir):
        return
    for name in os.listdir(xhtml_dir):
        if not name.endswith(".xhtml"):
            continue
        p = os.path.join(xhtml_dir, name)
        s = read_text_file(p)
        s = _replace_title_in_string(s, title)
        write_text_file(p, s)


def add_stylesheets_to_xhtml(xhtml_dir: str, styles: list[str]) -> None:
    """Insert <link> tags for given stylesheet filenames into all xhtml files in xhtml_dir.

    `styles` is a list of stylesheet basenames (e.g. ['style-ja-en.css']). Links are added
    with href "../style/{filename}" so that xhtml under `item/xhtml` references files
    under `item/style`.
    """
    if not styles:
        return
    # ensure basenames
    styles = [os.path.basename(s) for s in styles if s]
    try:
        names = os.listdir(xhtml_dir)
    except Exception as exc:
        warn(f"cannot list {xhtml_dir} for stylesheet injection: {exc}")
        return
    for name in names:
        if not name.endswith(".xhtml"):
            continue
        p = os.path.join(xhtml_dir, name)
        try:
            s = read_text_file(p)
        except Exception as exc:
            warn(f"skipping stylesheet injection for {name}: {exc}")
            continue
        # build link tags for missing styles
        links = []
        for fn in styles:
            href = f"../style/{fn}"
            if href not in s:
                links.append(f'<link rel="stylesheet" type="text/css" href="{href}"/>')
        if not links:
            continue
        # insert before </head>
        if "</head>" in s:
            s = s.replace("</head>", "\n" + "\n".join(links) + "\n</head>")
            try:
                write_text_file(p, s)
            except Exception as exc:
                warn(f"failed to update stylesheet links in {name}: {exc}")


def _build_xhtml_document(
    body_html: str,
    title: str,
    body_class: str | None = None,
    direction: str | None = None,
    stylesheets: list[str] | None = None,
) -> str:
    """Build a minimal but valid XHTML document from the provided body content.

    The generated document always carries the XHTML namespace declarations so that
    EPUB readers receive a proper XHTML 1.1/EPUB-compatible document instead of a
    loose HTML fragment.
    """
    style_value = _compute_style_value(direction)
    html_class = _compute_html_class(direction)
    cls = body_class or DEFAULT_BODY_CLASS
    style_attr = f' style="{style_value}"' if style_value else ""
    link_tags = ""
    if stylesheets:
        for fn in stylesheets:
            if not fn:
                continue
            link_tags += f'<link rel="stylesheet" type="text/css" href="../style/{os.path.basename(fn)}"/>\n'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        f'<html xmlns="http://www.w3.org/1999/xhtml" '
        f'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja" class="{html_class}">\n'
        "<head>\n"
        '<meta charset="UTF-8"/>\n'
        f"<title>{title}</title>\n"
        f"{link_tags}"
        "</head>\n"
        f'<body class="{cls}"{style_attr}>\n'
        f"{body_html}\n"
        "</body>\n"
        "</html>\n"
    )


def _apply_body_template(
    template: str | None, body_html: str, body_class: str | None, direction: str | None
) -> str:
    """Apply the given body content into a template shell while preserving the EPUB/XHTML wrapper.

    The legacy pipeline is template-first: the outer `<html>`, `<head>`, and
    `<body>` opening attributes are kept from the original template, while the
    body content itself is regenerated from metadata. That preserves document
    styling, lang/class attributes, and stylesheet links that are required by
    the old sample template.
    """
    style_value = _compute_style_value(direction)
    cls = body_class or DEFAULT_BODY_CLASS
    html_class = _compute_html_class(direction)

    if not template or "<body" not in template:
        return _build_xhtml_document(
            body_html, title="document", body_class=cls, direction=direction
        )

    html_idx = template.find("<html")
    if html_idx != -1:
        html_gt = template.find(">", html_idx)
        if html_gt != -1:
            html_opening = template[html_idx : html_gt + 1]
            html_new_opening = html_opening
            if 'class="' in html_new_opening:
                html_new_opening = re.sub(
                    r'class="([^"]*)"',
                    f'class="{html_class}"',
                    html_new_opening,
                    count=1,
                )
            else:
                html_new_opening = html_new_opening[:-1] + f' class="{html_class}">'
            template = template[:html_idx] + html_new_opening + template[html_gt + 1 :]

    idx = template.find("<body")
    gt = template.find(">", idx)
    if gt == -1:
        return _build_xhtml_document(
            body_html, title="document", body_class=cls, direction=direction
        )

    opening = template[idx : gt + 1]
    new_opening = opening

    # replace class attribute with cls
    if 'class="' in new_opening:
        new_opening = re.sub(r'class="([^"]*)"', f'class="{cls}"', new_opening, count=1)
    else:
        new_opening = new_opening[:-1] + f' class="{cls}">'

    # ensure style includes style_value without duplicating existing writing-mode declarations
    if style_value:
        if 'style="' in new_opening:

            def _update_style(match: re.Match[str]) -> str:
                existing = match.group(1)
                if style_value in existing:
                    return f'style="{existing}"'
                combined = f"{existing.strip()} {style_value}".strip()
                return f'style="{combined}"'

            new_opening = re.sub(
                r'style="([^"]*)"', _update_style, new_opening, count=1
            )
        else:
            new_opening = new_opening[:-1] + f' style="{style_value}">'

    new_template = template[:idx] + new_opening + template[gt + 1 :]
    start = new_template.find(">", new_template.find("<body")) + 1
    end = new_template.rfind("</body>")
    if start == -1 or end == -1:
        return _build_xhtml_document(
            body_html, title="document", body_class=cls, direction=direction
        )
    return new_template[:start] + "\n" + body_html + "\n" + new_template[end:]


def _render_document(
    template_path: str | None,
    body_html: str,
    title: str,
    body_class: str | None,
    direction: str | None,
    output_path: str,
    *,
    replace_title: bool = True,
) -> None:
    """Render ``body_html`` into an XHTML document and write it to ``output_path``.

    When ``template_path`` exists the template shell (``<html>``/``<head>``) is
    preserved and only the body is replaced; otherwise a minimal document is built.
    The ``<title>`` is rewritten with ``title`` only when ``replace_title`` is set,
    so callers that must keep the template title (caution/colophon/advertisement)
    pass ``replace_title=False`` to preserve the exact previous behavior. This is
    the per-document counterpart of the directory-wide ``replace_title_in_xhtml``
    pass; both ultimately delegate to ``_replace_title_in_string``.

    Args:
        template_path (str | None): Path to an XHTML template, or None.
        body_html (str): Body content to inject.
        title (str): Title for the ``<title>`` tag (used when building from scratch
            and when ``replace_title`` is True).
        body_class (str | None): Class attribute for the ``<body>`` tag.
        direction (str | None): Writing direction ('Vertical', 'Horizontal', ...).
        output_path (str): Destination path to write the rendered document.
        replace_title (bool): Whether to overwrite the ``<title>`` with ``title``.

    Returns:
        None
    """
    template = (
        read_text_file(template_path)
        if template_path and os.path.exists(template_path)
        else None
    )
    if template:
        new = _apply_body_template(template, body_html, body_class, direction)
    else:
        new = _build_xhtml_document(
            body_html, title=title, body_class=body_class, direction=direction
        )
    if replace_title:
        new = _replace_title_in_string(new, title)
    write_text_file(output_path, new)
