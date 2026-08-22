"""End-to-end regression tests: convert sample_yaml/metadata.yaml to an EPUB.

These tests lock the current (correct) behavior so future refactoring cannot
silently regress the produced EPUB package.
"""
import os
import re
import zipfile

import pytest

from conftest import REPO_ROOT


@pytest.fixture(scope="module")
def epub_path(module, tmp_path_factory):
    out = tmp_path_factory.mktemp("epub") / "out.epub"
    meta = os.path.join(REPO_ROOT, "sample_yaml", "metadata.yaml")
    # main() reads argv[1]/argv[2] (CLI: sys.argv[0]=script, [1]=meta, [2]=out)
    assert module.main(["yaml2epub.py", meta, out]) == 0
    return out


@pytest.fixture(scope="module")
def z(epub_path):
    return zipfile.ZipFile(epub_path, "r")


@pytest.fixture(scope="module")
def manifest(z):
    return _read_entry(z, "item/standard.opf")


def _read_entry(z: zipfile.ZipFile, name: str) -> str:
    assert name in z.namelist(), f"missing entry {name!r} in {z.namelist()}"
    return z.read(name).decode("utf-8")


def _spine_ids(z: zipfile.ZipFile) -> list[str]:
    spine = re.search(r"<spine[^>]*>(.*?)</spine>", _read_entry(z, "item/standard.opf"), re.S)
    assert spine, "spine not found in manifest"
    ids = []
    for ref in re.findall(r"<itemref[^>]*>", spine.group(1)):
        for part in ref.split():
            if part.startswith("idref="):
                ids.append(part[len("idref="):].strip('"'))
    return ids


def _item_ids(manifest: str) -> list[str]:
    return re.findall(r'<item[^>]*id="([^"]+)"', manifest)


def test_mimetype_first_and_stored(z):
    assert z.namelist()[0] == "mimetype"
    first = z.infolist()[0]
    assert first.compress_type == zipfile.ZIP_STORED


def test_no_advertisement_entry(z):
    # advertisement text is NONE in the sample metadata, so p-ad-001 must be absent
    assert not any("ad-001" in n for n in z.namelist())


def test_expected_xhtml_entries(z):
    xhtml = [n for n in z.namelist() if n.endswith(".xhtml")]
    assert set(xhtml) == {
        "item/xhtml/p-cover.xhtml",
        "item/xhtml/p-fmatter-001.xhtml",
        "item/xhtml/p-titlepage.xhtml",
        "item/xhtml/p-caution.xhtml",
        "item/xhtml/p-toc.xhtml",
        "item/xhtml/p-001.xhtml",
        "item/xhtml/p-002.xhtml",
        "item/xhtml/p-003.xhtml",
        "item/xhtml/p-004.xhtml",
        "item/xhtml/p-005.xhtml",
        "item/xhtml/p-bmatter-001.xhtml",
        "item/xhtml/p-colophon.xhtml",
        "item/xhtml/p-backcover.xhtml",
        "item/navigation-documents.xhtml",
    }


def test_chapter_labels(z):
    toc = _read_entry(z, "item/xhtml/p-toc.xhtml")
    for label in ("あらすじ、概要", "扉", "第一章　はじめに", "第二章", "第三章"):
        assert label in toc, f"label {label!r} missing from TOC"


def test_colophon_jinja_rendered(z):
    colophon = _read_entry(z, "item/xhtml/p-colophon.xhtml")
    # Jinja2 {{ book_title }} must be expanded to the sample title
    assert "yaml2epubのサンプル" in colophon
    # NOW_YMD created_at must be expanded to a real date
    assert "作成日" in colophon
    # copyright block must be present
    assert "©" in colophon


def test_spine_order(z):
    expected = [
        "p-cover",
        "p-fmatter-001",
        "p-titlepage",
        "p-caution",
        "p-toc",
        "p-001",
        "p-002",
        "p-003",
        "p-004",
        "p-005",
        "p-bmatter-001",
        "p-colophon",
        "p-backcover",
    ]
    assert _spine_ids(z) == expected


def test_manifest_matches_spine(manifest, z):
    # every spine itemref must have a corresponding manifest item
    ids = _item_ids(manifest)
    for ref in _spine_ids(z):
        assert ref in ids, f"spine itemref {ref!r} has no manifest entry"


def test_stylesheet_injected(z):
    # user-supplied style-ja-en.css must be linked into at least one xhtml
    body = _read_entry(z, "item/xhtml/p-001.xhtml")
    assert "style-ja-en.css" in body


def test_images_present(z):
    for img in ("cover.png", "back_cover.png", "sample_textmap.jpg",
                "sample_textmap1.jpg", "sample_textmap2.jpg"):
        assert f"item/image/{img}" in z.namelist()


def test_backcover_rendered(z):
    back = _read_entry(z, "item/xhtml/p-backcover.xhtml")
    assert "back_cover.png" in back


def test_navigation_documents(z):
    nav = _read_entry(z, "item/navigation-documents.xhtml")
    assert 'epub:type="toc"' in nav
    assert 'epub:type="landmarks"' in nav
    for label in ("表紙", "目次", "あとがき", "奥付"):
        assert label in nav


def test_container_points_to_opf(z):
    container = _read_entry(z, "META-INF/container.xml")
    # ElementTree pretty-prints attributes onto separate lines, so match the
    # full-path value rather than the whole <rootfile .../> tag.
    assert 'full-path="item/standard.opf"' in container


def test_all_xhtml_wellformed_xml(z):
    import xml.etree.ElementTree as ET
    for name in z.namelist():
        if name.endswith(".xhtml"):
            ET.fromstring(z.read(name))  # raises on malformed XML


def test_no_template_images_leaked(z):
    # template-provided images must be cleaned up and replaced by user images
    leaked = [n for n in z.namelist() if n.startswith("item/image/") and n.endswith(("img", "ad", "gaiji", "kuchie", "logo"))]
    assert leaked == []


def test_vertical_direction_applied(z):
    # synopsis chapter is Vertical; html class must reflect writing-mode
    body = _read_entry(z, "item/xhtml/p-001.xhtml")
    assert 'writing-mode: vertical-rl' in body or 'class="vrtl"' in body
