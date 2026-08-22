"""Unit tests for individual helpers in yaml2epub.py."""
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
