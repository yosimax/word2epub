"""EPUB package structure and shared constants."""

import os

# The single-file script resolved TEMPLATE_DIR from its own location. In the
# package, constants.py lives three levels deep (yaml2epub/epub/), so resolve
# the repository root explicitly rather than from __file__.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATE_DIR = os.path.join(REPO_ROOT, "TEMPLATE", "book-template")

# File structure constants
ITEM_DIR = "item"
XHTML_DIR = "item/xhtml"
IMAGE_DIR = "item/image"
META_INF_DIR = "META-INF"

# XHTML file IDs and names
XHTML_COVER = "p-cover.xhtml"
XHTML_FRONTMATTER = "p-fmatter-001.xhtml"
XHTML_TITLEPAGE = "p-titlepage.xhtml"
XHTML_CAUTION = "p-caution.xhtml"
XHTML_TOC = "p-toc.xhtml"
XHTML_BACKMATTER = "p-bmatter-001.xhtml"
XHTML_COLOPHON = "p-colophon.xhtml"
XHTML_ADVERTISEMENT = "p-ad-001.xhtml"
XHTML_BACKCOVER = "p-backcover.xhtml"

# OPF file
OPF_FILE = "item/standard.opf"

# Navigation file
NAV_FILE = "item/navigation-documents.xhtml"

# XML namespaces
NS_OPF = "http://www.idpf.org/2007/opf"
NS_DC = "http://purl.org/dc/elements/1.1/"

# Default values
DEFAULT_TITLE = "作品名未設定"

# Magic values used while generating document content
NONE_TEXT = "NONE"
DEFAULT_BODY_CLASS = "p-text"
TOC_LABEL = "目次"
