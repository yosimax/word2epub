import os
import uuid
from datetime import datetime


def build_chapter_xhtml(chapter, css_filename="style.css"):
    body_html = "".join(str(node) for node in chapter["nodes"])

    xhtml = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="ja" xml:lang="ja">
<head>
  <meta charset="utf-8" />
  <title>{chapter["title"]}</title>
  <link rel="stylesheet" type="text/css" href="{css_filename}" />
</head>
<body>
{body_html}
</body>
</html>
'''
    return xhtml


def generate_chapter_filenames(chapters):
    filenames = {}
    for chap in chapters:
        idx = chap["index"]
        filenames[idx] = f"content-{idx:02d}.xhtml"
    return filenames


def generate_all_chapter_xhtml(chapters):
    filenames = generate_chapter_filenames(chapters)
    result = {}

    for chap in chapters:
        idx = chap["index"]
        filename = filenames[idx]
        xhtml = build_chapter_xhtml(chap)
        result[idx] = (filename, xhtml)

    return result


def build_toc_xhtml(chapters, chapter_filenames):
    items = []
    for chap in chapters:
        idx = chap["index"]
        title = chap["title"]
        href = chapter_filenames[idx]
        items.append(f'      <li><a href="{href}">{title}</a></li>')

    toc = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      lang="ja" xml:lang="ja">
<head>
  <meta charset="utf-8" />
  <title>目次</title>
  <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目次</h1>
    <ol>
{chr(10).join(items)}
    </ol>
  </nav>
</body>
</html>
'''
    return toc


def build_image_xhtml(image_filename):
        img_src = os.path.basename(image_filename)
        return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="ja" xml:lang="ja">
<head>
  <meta charset="utf-8" />
  <title>Image</title>
  <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body>
  <div style="text-align:center;">
        <img src="{img_src}" alt="" style="max-width:100%; height:auto;" />
  </div>
</body>
</html>
'''


def build_opf(meta, chapter_filenames, image_pages):
    title = meta["title"]
    author = meta["author"]
    ppd = meta["ppd"]

    unique_id = f"urn:uuid:{uuid.uuid4()}"
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest_items = []

    for idx, filename in chapter_filenames.items():
        item_id = f"chap{idx}"
        manifest_items.append(
            f'    <item id="{item_id}" href="{filename}" media-type="application/xhtml+xml" />'
        )

    manifest_items.append(
        '    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav" />'
    )

    for i, (fname, _) in enumerate(image_pages):
        manifest_items.append(
            f'    <item id="imgpage{i}" href="{fname}" media-type="application/xhtml+xml" />'
        )

    # 画像ファイル (metadata の images セクション)
    for img in meta.get("images", []):
        img_file = os.path.basename(img.get("file", ""))
        # 拡張子から簡易的に MIME を判定
        ext = os.path.splitext(img_file)[1].lower()
        if ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        elif ext == ".gif":
            mime = "image/gif"
        else:
            mime = "application/octet-stream"

        # id はファイル名を安全な形式で使う
        item_id = f"imgfile_{os.path.splitext(img_file)[0]}"
        manifest_items.append(
            f'    <item id="{item_id}" href="{img_file}" media-type="{mime}" />'
        )

    manifest_items.append(
        '    <item id="style" href="style.css" media-type="text/css" />'
    )

    spine_items = []
    spine_items.append('    <itemref idref="toc" />')
    for i, (fname, _) in enumerate(image_pages):
        spine_items.append(f'    <itemref idref="imgpage{i}" />')
    for idx in sorted(chapter_filenames.keys()):
        spine_items.append(f'    <itemref idref="chap{idx}" />')

    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         unique-identifier="BookId"
         version="3.0">
  <metadata>
    <dc:identifier id="BookId">{unique_id}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>ja</dc:language>
    <dc:creator>{author}</dc:creator>
    <dc:date>{now}</dc:date>

    <meta property="rendition:layout">reflowable</meta>
    <meta property="rendition:orientation">auto</meta>
    <meta property="rendition:spread">auto</meta>
  </metadata>

  <manifest>
{chr(10).join(manifest_items)}
  </manifest>

  <spine page-progression-direction="{ppd}">
{chr(10).join(spine_items)}
  </spine>
</package>
'''
    return opf
