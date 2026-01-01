import os
import zipfile


def create_epub(output_path, chapter_files, toc_xhtml, opf_content, style_css, image_pages, meta):
    with zipfile.ZipFile(output_path, "w") as zf:
        zinfo = zipfile.ZipInfo("mimetype")
        zinfo.compress_type = zipfile.ZIP_STORED
        zf.writestr(zinfo, "application/epub+zip")

        container_xml = '''<?xml version="1.0" encoding="utf-8"?>
<container version="1.0"
           xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf"
              media-type="application/oebps-package+xml" />
  </rootfiles>
</container>
'''
        zf.writestr("META-INF/container.xml", container_xml)

        for idx, (filename, xhtml) in chapter_files.items():
            zf.writestr(f"OEBPS/{filename}", xhtml)

        zf.writestr("OEBPS/toc.xhtml", toc_xhtml)
        zf.writestr("OEBPS/content.opf", opf_content)
        zf.writestr("OEBPS/style.css", style_css)

        for fname, xhtml in image_pages:
            zf.writestr(f"OEBPS/{fname}", xhtml)

        for img in meta.get("images", []):
            img_path = os.path.normpath(img["file"])
            if not os.path.exists(img_path):
                print("Warning: image file not found, skipping:", img.get("file"))
                continue
            zf.write(img_path, f"OEBPS/{os.path.basename(img_path)}")
