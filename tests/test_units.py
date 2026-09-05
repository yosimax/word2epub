"""Unit tests for individual helpers in yaml2epub.py."""
import gzip
import os
import re

import pytest

from conftest import REPO_ROOT, _load_module


module = _load_module("yaml2epub", os.path.join(REPO_ROOT, "yaml2epub.py"))


def test_compute_style_value_none():
    assert module._compute_style_value(None) == ""


def test_compute_style_value_vertical():
    assert (
        module._compute_style_value("Vertical")
        == "writing-mode: vertical-rl; -epub-writing-mode: vertical-rl;"
    )


def test_compute_style_value_horizontal():
    assert (
        module._compute_style_value("Horizontal")
        == "writing-mode: horizontal-tb; -epub-writing-mode: horizontal-tb;"
    )


def test_compute_style_value_case_insensitive():
    result = module._compute_style_value("VERTICAL")
    assert "vertical-rl" in result


def test_normalize_legacy_metadata_seriestitle_alias():
    meta = {"seriestitle": "シリーズX"}
    out = module._normalize_legacy_metadata(meta)
    assert out["series_title"] == "シリーズX"
    # the alias is copied in; the legacy key is left untouched
    assert out["seriestitle"] == "シリーズX"


def test_normalize_legacy_metadata_specialthanks_alias():
    meta = {"specialthanks": "感謝"}
    out = module._normalize_legacy_metadata(meta)
    assert out["special_thanks"] == "感謝"


def test_normalize_legacy_metadata_non_dict():
    assert module._normalize_legacy_metadata(None) == {}
    # a truthy non-dict is returned as-is
    assert module._normalize_legacy_metadata("x") == "x"


def test_normalize_legacy_metadata_noop():
    meta = {"title": "T", "series_title": "S", "special_thanks": "G"}
    out = module._normalize_legacy_metadata(meta)
    assert out == meta


def test_update_navigation_writes_files(module, tmp_path):
    # mirror the real layout: nav lives in item/ and p-toc.xhtml template in item/xhtml/
    xhtml_dir = tmp_path / "item" / "xhtml"
    xhtml_dir.mkdir(parents=True)
    (xhtml_dir / "p-toc.xhtml").write_text(
        "<html><head></head><body class=\"p-toc\"></body></html>", encoding="utf-8"
    )
    nav = tmp_path / "item" / "navigation-documents.xhtml"
    chapters = [{"id": "p-001", "href": "xhtml/p-001.xhtml", "label": "第一章"}]
    module.update_navigation(str(nav), chapters)

    assert nav.exists()
    body = nav.read_text(encoding="utf-8")
    assert 'epub:type="toc"' in body
    assert 'epub:type="landmarks"' in body
    assert "表紙" in body and "奥付" in body

    # p-toc.xhtml should be regenerated with the chapter list
    toc = xhtml_dir / "p-toc.xhtml"
    assert toc.exists()
    toc_body = toc.read_text(encoding="utf-8")
    assert "第一章" in toc_body
    assert "toc-001" in toc_body  # anchor id

    # chapter link uses basename + anchor id
    assert 'href="p-001.xhtml#toc-001"' in toc_body


def test_apply_body_template_preserves_head(module, tmp_path):
    template = (
        '<html class="old"><head><title>old</title>'
        '<link rel="stylesheet" href="../style/book-style.css"/></head>'
        '<body class="p-text"><div class="main">OLD</div></body></html>'
    )
    out = module._apply_body_template(template, "<p>NEW</p>", "p-body", "Vertical")
    # head / stylesheet shell must be preserved
    assert "<head>" in out
    assert '<link rel="stylesheet" href="../style/book-style.css"/>' in out
    # html class corrected to vertical writing-mode class
    assert 'class="vrtl"' in out
    assert 'class="old"' not in out
    # body class replaced and body content swapped
    assert 'class="p-body"' in out
    assert "OLD" not in out
    assert "<p>NEW</p>" in out


def test_apply_body_template_style_merge(module):
    template = (
        '<html class="vrtl"><head><title>old</title></head>'
        '<body class="p-text" style="color: red;">OLD</body></html>'
    )
    out = module._apply_body_template(template, "<p>NEW</p>", "p-body", "Vertical")
    # existing style preserved, writing-mode merged without duplication
    assert 'style="color: red; writing-mode: vertical-rl; -epub-writing-mode: vertical-rl;"' in out
    assert out.count("writing-mode: vertical-rl; -epub-writing-mode: vertical-rl;") == 1


def test_apply_body_template_no_body_fallback(module):
    # template without <body triggers fallback to _build_xhtml_document
    template = '<html><head><title>old</title></head></html>'
    out = module._apply_body_template(template, "<p>NEW</p>", "p-body", "Vertical")
    assert "<body" in out
    assert 'class="p-body"' in out
    assert "<p>NEW</p>" in out


def test_insert_svgz_decompress(module, tmp_path):
    xhtml_dir = tmp_path / "xhtml"
    xhtml_dir.mkdir()
    (xhtml_dir / "p-fmatter-001.xhtml").write_text("<html><body class=\"p-fmatter\"></body></html>")
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    image_dir = tmp_path / "image"
    image_dir.mkdir()
    svg_bytes = b"<svg>hello</svg>"
    svgz_path = meta_dir / "pic.svgz"
    with gzip.open(svgz_path, "wb") as f:
        f.write(svg_bytes)
    spec = {"text": "intro", "image": [str(svgz_path)]}
    module._insert_document_section(str(xhtml_dir), spec, str(meta_dir), str(image_dir), "out.xhtml")
    assert (image_dir / "pic.svg").exists()
    assert not (image_dir / "pic.svgz").exists()


def test_insert_html_raw_vs_plain_wrapped(module, tmp_path):
    # .html/.xhtml/.htm branch keeps raw markup; plain-text branch wraps in <p>.
    xhtml_dir = tmp_path / "xhtml"
    xhtml_dir.mkdir()
    (xhtml_dir / "p-fmatter-001.xhtml").write_text("<html><body class=\"x\"></body></html>")
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    content = "Para one\n\nPara two"
    html_path = meta_dir / "page.html"
    txt_path = meta_dir / "page.txt"
    html_path.write_text(content)
    txt_path.write_text(content)

    img1 = tmp_path / "img1"
    img1.mkdir()
    img2 = tmp_path / "img2"
    img2.mkdir()
    module._insert_document_section(str(xhtml_dir), {"text": str(html_path)}, str(meta_dir), str(img1), "out.html", template_filename="p-fmatter-001.xhtml")
    module._insert_document_section(str(xhtml_dir), {"text": str(txt_path)}, str(meta_dir), str(img2), "out.txt", template_filename="p-fmatter-001.xhtml")

    html_out = (xhtml_dir / "out.html").read_text(encoding="utf-8")
    txt_out = (xhtml_dir / "out.txt").read_text(encoding="utf-8")
    assert "Para one" in html_out and "<p>Para one" not in html_out
    assert "<p>Para one</p>" in txt_out
