"""EPUB navigation document generation."""

from __future__ import annotations

import os

from yaml2epub.epub.constants import TOC_LABEL
from yaml2epub.epub.xhtml import _render_document
from yaml2epub.utils import write_text_file


def update_navigation(nav_path: str, chapters_info: list[dict]) -> None:
    """Rebuild the navigation document from scratch.

    The previous implementation only patched parts of the template navigation
    file, so template sample content could remain in the final EPUB. This
    version always emits a clean, metadata-driven navigation.xhtml document.
    """
    nav_items = [
        '<li><a href="xhtml/p-cover.xhtml">表紙</a></li>',
        f'<li><a href="xhtml/p-toc.xhtml">{TOC_LABEL}</a></li>',
    ]
    back_path = os.path.join(os.path.dirname(nav_path), "xhtml", "p-bmatter-001.xhtml")
    if os.path.exists(back_path):
        nav_items.append('<li><a href="xhtml/p-bmatter-001.xhtml">あとがき</a></li>')
    nav_items.append('<li><a href="xhtml/p-colophon.xhtml">奥付</a></li>')

    nav_ol = "\n".join(nav_items)
    nav_html = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">\n'
        "<head>\n"
        '<meta charset="UTF-8"/>\n'
        "<title>Navigation</title>\n"
        "</head>\n"
        "<body>\n"
        '<nav epub:type="toc" id="toc">\n'
        "<h1>Navigation</h1>\n"
        "<ol>\n"
        f"{nav_ol}\n"
        "</ol>\n"
        "</nav>\n"
        '<nav epub:type="landmarks" id="guide">\n'
        "<h1>Guide</h1>\n"
        "<ol>\n"
        '<li><a epub:type="cover" href="xhtml/p-cover.xhtml">表紙</a></li>\n'
        f'<li><a epub:type="toc" href="xhtml/p-toc.xhtml">{TOC_LABEL}</a></li>\n'
        '<li><a epub:type="bodymatter" href="xhtml/p-titlepage.xhtml">本編</a></li>\n'
        "</ol>\n"
        "</nav>\n"
        "</body>\n"
        "</html>\n"
    )
    write_text_file(nav_path, nav_html)

    # update p-toc.xhtml: create chapter-only TOC using chapters_info
    xhtml_dir = os.path.join(os.path.dirname(nav_path), "xhtml")
    toc_path = os.path.join(xhtml_dir, "p-toc.xhtml")
    if os.path.exists(toc_path):
        lines = []
        for ch in chapters_info:
            href = os.path.basename(ch["href"])
            label = ch.get("label") or ch["id"]
            m = None
            try:
                m = int(ch["id"].split("-")[-1])
            except Exception:
                # Chapter ids are expected to be p-NNN; odd ids simply omit the anchor.
                m = None
            anchor = f"#toc-{m:03d}" if m else ""
            link = (
                f'<p><a href="{href}{anchor}">{label}</a></p>'
                if anchor
                else f'<p><a href="{href}">{label}</a></p>'
            )
            lines.append(link)

        back_href = "p-bmatter-001.xhtml"
        back_file = os.path.join(xhtml_dir, back_href)
        if os.path.exists(back_file):
            lines.append(f'<p><a href="{back_href}">あとがき</a></p>')

        toc_body = (
            '<div class="main">\n\n'
            f'<h1 class="mokuji-midashi">　{TOC_LABEL}</h1>\n'
            + "\n".join(lines)
            + "\n</div>"
        )
        # p-toc.xhtml is the only page that must remain fixed to vertical writing mode.
        _render_document(
            toc_path,
            toc_body,
            TOC_LABEL,
            "p-toc",
            "Vertical",
            toc_path,
            replace_title=True,
        )
