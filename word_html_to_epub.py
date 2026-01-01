import os
import yaml
import uuid
from datetime import datetime
import zipfile
from bs4 import BeautifulSoup
import chardet

def load_metadata(metadata_path):
    if not os.path.isfile(metadata_path):
        print(f"Warning: metadata file '{metadata_path}' not found. Using defaults.")
        return {}

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    meta = {}

    # title
    if isinstance(data.get("title"), list) and data["title"]:
        meta["title"] = data["title"][0].get("text", "").strip()
    else:
        meta["title"] = "タイトル未設定"

    # author
    if isinstance(data.get("creator"), list) and data["creator"]:
        meta["author"] = data["creator"][0].get("text", "").strip()
    else:
        meta["author"] = "著者未設定"

    # page-progression-direction
    ppd = data.get("page-progression-direction", "rtl")
    meta["ppd"] = ppd if ppd in ("rtl", "ltr") else "rtl"

    # images
    meta["images"] = data.get("images", [])

    return meta

import chardet

def detect_encoding(path):
    """
    Word HTML の文字コードを判定する。
    Shift_JIS(CP932) を含め自動判定し、決定した encoding と生バイト列を返す。
    """
    with open(path, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "cp932"
    return encoding, raw

from bs4 import BeautifulSoup

def parse_word_html_and_split_chapters(html_content):
    """
    Word HTML をパースし、class="CHAPTER" の <p> を起点に章分割する。

    戻り値:
      chapters: [
        {
          "index": 1,
          "title": "Prelude 序章",
          "nodes": [ <p class="CHAPTER">..., <p>..., ... ],
        },
        {
          "index": 2,
          "title": "CHAPTER ONE - The Forging 鍛造",
          "nodes": [ ... ],
        },
        ...
      ]
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Word固有の属性を軽く削る（※ここで全部やり切らず、後でXHTML生成時に再整形も可）
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for attr in list(attrs.keys()):
            if attr.startswith("mso-") or (
                attr in ["lang", "class", "style"] and "mso-" in str(attrs[attr])
            ):
                del tag.attrs[attr]
        tag.name = tag.name.lower()

    # <o:p> を除去
    for o_tag in soup.find_all("o:p"):
        o_tag.unwrap()

    # body を対象にする（なければ soup 全体）
    body = soup.body or soup

    # body の直下ノードを順に見ていき、CHAPTER で分割
    nodes = [node for node in body.descendants if getattr(node, "name", None)]
    
    chapters = []
    current_chapter = None
    
    for node in nodes:
    
        # class="CHAPTER" の <p> を検出
        if node.name == "p" and "CHAPTER" in str(node.get("class")):
    
            # すでに章が進行中なら確定
            if current_chapter is not None:
                chapters.append(current_chapter)
    
            # 新しい章開始
            # 英語部分（span lang="EN-US"）
            en_span = node.find("span", attrs={"lang": "EN-US"})
            en_text = en_span.get_text(strip=True) if en_span else ""
            
            # 日本語部分（span の後のテキスト）
            jp_text = node.get_text(strip=True)
            if en_text:
                jp_text = jp_text.replace(en_text, "", 1).strip()
            
            # 英語 + " - " + 日本語
            if en_text and jp_text:
                title_text = f"{en_text} - {jp_text}"
            else:
                title_text = en_text or jp_text
            
            current_chapter = {
                "index": len(chapters) + 1,
                "title": title_text,
                "nodes": [node],
            }
    
        else:
            # 章が始まっていれば本文として追加
            if current_chapter is not None:
                current_chapter["nodes"].append(node)
    
    # 最後の章を追加
    if current_chapter is not None:
        chapters.append(current_chapter)
    
    return chapters

def remove_orphan_en_spans(chapter):
    """
    Word HTML が勝手に生成する「段落外に飛び出した EN-US span」を削除する。
    例:
      </p><span lang="EN-US">"Winter of the World"</span>
    のようなノードを除去する。
    """
    cleaned = []
    for node in chapter["nodes"]:
        # <span lang="EN-US">…</span> が単独で存在する場合は削除
        if (
            node.name == "span"
            and node.get("lang") == "EN-US"
            and node.get_text(strip=True) != ""  # 空白だけの span は別処理
        ):
            # これは段落外の孤立 span なのでスキップ
            continue

        # 空白だけの span（&nbsp;）も削除
        if (
            node.name == "span"
            and node.get("lang") == "EN-US"
            and node.get_text(strip=True) == ""
        ):
            continue

        cleaned.append(node)

    chapter["nodes"] = cleaned
    return chapter

def clean_word_garbage(chapter):
    """
    Word HTML が生成する不要タグを削除・正規化する。
    - <o:p> の削除
    - <span style="mso-spacerun:yes"> の削除
    - <p class="MsoNormal"> の正規化
    """

    cleaned = []

    for node in chapter["nodes"]:

        # --- <o:p> の削除 ---
        if node.name == "o:p":
            continue

        # --- <span style="mso-spacerun:yes"> の削除 ---
        if (
            node.name == "span"
            and node.get("style")
            and "mso-spacerun:yes" in node.get("style")
        ):
            continue

        # --- <p class="MsoNormal"> の正規化 ---
        if node.name == "p" and node.get("class") == ["MsoNormal"]:
            node.attrs.pop("class", None)

        cleaned.append(node)

    chapter["nodes"] = cleaned
    return chapter


def load_html_and_split_chapters(input_html_path):
    """
    ファイルパスを受け取り:
      - エンコーディング判定
      - デコード
      - 章分割
    まで行って chapter リストを返す。
    """
    encoding, raw = detect_encoding(input_html_path)
    print(f"Detected encoding: {encoding}")
    html_content = raw.decode(encoding, errors="ignore")

    chapters = parse_word_html_and_split_chapters(html_content)

    if not chapters:
        print("Warning: No chapters (class='CHAPTER') found.")
    else:
        print(f"Found {len(chapters)} chapters.")

    return chapters

# --- 重複タイトル削除ロジック ---
def remove_duplicate_title_span(chapter):
    """
    章タイトルの <p class="CHAPTER"> の直後にある
    英語タイトル / 日本語タイトル の重複 span を削除する。
    """
    if not chapter["nodes"]:
        return chapter

    first = chapter["nodes"][0]  # <p class="CHAPTER">...</p>
    if first.name != "p":
        return chapter

    # --- 英語タイトル抽出 ---
    en_span = first.find("span", attrs={"lang": "EN-US"})
    en_text = en_span.get_text(strip=True) if en_span else ""

    # --- 日本語タイトル抽出 ---
    # 英語部分を除いた残りが日本語タイトル
    full_text = first.get_text(strip=True)
    jp_text = full_text.replace(en_text, "", 1).strip() if en_text else full_text

    new_nodes = [first]

    for node in chapter["nodes"][1:]:

        # --- 英語タイトルの重複 span を削除 ---
        if (
            en_text
            and node.name == "span"
            and node.get("lang") == "EN-US"
            and node.get_text(strip=True) == en_text
        ):
            continue

        # --- 日本語タイトルの重複 span を削除 ---
        if (
            jp_text
            and node.name == "span"
            and node.get_text(strip=True) == jp_text
        ):
            continue

        new_nodes.append(node)

    chapter["nodes"] = new_nodes
    return chapter

import re
from bs4 import NavigableString, Tag

def clean_span_and_ruby(chapter):
    """
    Word HTML の <span> を整理し、必要に応じて <em>/<strong> に変換し、
    さらにルビ（括弧 → <ruby>）を自動変換する。
    """

    cleaned = []

    for node in chapter["nodes"]:

        # --- <span> の整理 ---
        if isinstance(node, Tag) and node.name == "span":

            text = node.get_text(strip=False)

            # 1) 空白だけの span は削除
            if text.strip() == "":
                continue

            # 2) mso-* 系 style は削除
            style = node.get("style", "")
            if "mso-" in style:
                continue

            # 3) font-size / font-family などの装飾 span は削除
            if any(x in style for x in ["font-size", "font-family"]):
                # span を外して中身だけ残す
                cleaned.append(NavigableString(text))
                continue

            # 4) italic → <em>
            if "italic" in style:
                em = Tag(name="em")
                em.string = text
                cleaned.append(em)
                continue

            # 5) bold → <strong>
            if "bold" in style:
                strong = Tag(name="strong")
                strong.string = text
                cleaned.append(strong)
                continue

            # 6) lang="EN-US" は残す（意味がある）
            if node.get("lang") == "EN-US":
                cleaned.append(node)
                continue

            # 7) その他の span は削除（中身だけ残す）
            cleaned.append(NavigableString(text))
            continue

        # --- ルビ変換（括弧 → <ruby>） ---
        if isinstance(node, NavigableString):
            text = str(node)

            # パターン：漢字（かな）
            ruby_pattern = r"([一-龥々〆ヵヶ]+)（([ぁ-ゖ]+)）"

            def ruby_repl(match):
                kanji = match.group(1)
                kana = match.group(2)
                return f"<ruby>{kanji}<rt>{kana}</rt></ruby>"

            if re.search(ruby_pattern, text):
                new_html = re.sub(ruby_pattern, ruby_repl, text)
                cleaned.append(BeautifulSoup(new_html, "html.parser"))
                continue

        cleaned.append(node)

    chapter["nodes"] = cleaned
    return chapter


def build_chapter_xhtml(chapter, css_filename="style.css"):
    """
    1章分の XHTML を生成する。
    chapter = {
        "index": 1,
        "title": "Prelude 序章",
        "nodes": [...],
    }
    """
    # ノードを HTML 文字列に変換
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
    """
    章ごとに content-01.xhtml のようなファイル名を割り当てる。
    """
    filenames = {}
    for chap in chapters:
        idx = chap["index"]
        filenames[idx] = f"content-{idx:02d}.xhtml"
    return filenames

def generate_all_chapter_xhtml(chapters):
    """
    章リストから、章ごとの XHTML を生成して辞書で返す。
    戻り値:
      {
        1: ("content-01.xhtml", "<xml...>"),
        2: ("content-02.xhtml", "<xml...>"),
        ...
      }
    """
    filenames = generate_chapter_filenames(chapters)
    result = {}

    for chap in chapters:
        idx = chap["index"]
        filename = filenames[idx]
        xhtml = build_chapter_xhtml(chap)
        result[idx] = (filename, xhtml)

    return result

def build_toc_xhtml(chapters, chapter_filenames):
    """
    EPUB3 の toc.xhtml を生成する。
    chapters: 章リスト
    chapter_filenames: { index: "content-01.xhtml", ... }
    """
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
    <img src="{image_filename}" alt="" style="max-width:100%; height:auto;" />
  </div>
</body>
</html>
'''

def build_opf(meta, chapter_filenames, image_pages):
    """
    content.opf を生成する。

    meta: load_metadata() の戻り値
      - meta["title"]
      - meta["author"]
      - meta["ppd"]
      - meta["images"] (オプション)

    chapter_filenames: { index: "content-01.xhtml", ... }

    image_pages: [("image.xhtml", "<xhtml...>"), ...]
    """
    title = meta["title"]
    author = meta["author"]
    ppd = meta["ppd"]

    unique_id = f"urn:uuid:{uuid.uuid4()}"
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---------- manifest ----------
    manifest_items = []

    # 章ファイル
    for idx, filename in chapter_filenames.items():
        item_id = f"chap{idx}"
        manifest_items.append(
            f'    <item id="{item_id}" href="{filename}" media-type="application/xhtml+xml" />'
        )

    # nav (toc.xhtml)
    manifest_items.append(
        '    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav" />'
    )

    # 画像ページ (image.xhtml など)
    for i, (fname, _) in enumerate(image_pages):
        manifest_items.append(
            f'    <item id="imgpage{i}" href="{fname}" media-type="application/xhtml+xml" />'
        )

    # 画像ファイル (metadata の images セクション)
    for img in meta.get("images", []):
        # ここでは JPEG 前提。PNG 等も使うなら拡張子で振り分けてもよい
        manifest_items.append(
            f'    <item id="imgfile_{img["file"]}" href="{img["file"]}" media-type="image/jpeg" />'
        )

    # CSS
    manifest_items.append(
        '    <item id="style" href="style.css" media-type="text/css" />'
    )

    # ---------- spine ----------
    spine_items = []

    # 章を spine に並べる
    #for idx in sorted(chapter_filenames.keys()):
    #    spine_items.append(f'    <itemref idref="chap{idx}" />')

    # ※「目次の次に画像を差し込みたい」という意図なら、
    #   実際に「読書順」を toc → image → 本文 にしたいか、
    #   それとも「ファイル構造上 toc, image を置きたいだけか」で分かれます。
    # ここでは「spine 上では通常どおり章だけ」のままにしておきます。
    # もし spine 上でも image ページを入れたければ、たとえばこうする：
    #
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

def create_epub(output_path, chapter_files, toc_xhtml, opf_content, style_css, image_pages, meta):
    with zipfile.ZipFile(output_path, "w") as zf:
        # mimetype（無圧縮）
        zinfo = zipfile.ZipInfo("mimetype")
        zinfo.compress_type = zipfile.ZIP_STORED
        zf.writestr(zinfo, "application/epub+zip")

        # META-INF/container.xml
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

        # 章 XHTML
        for idx, (filename, xhtml) in chapter_files.items():
            zf.writestr(f"OEBPS/{filename}", xhtml)

        # toc, opf, css
        zf.writestr("OEBPS/toc.xhtml", toc_xhtml)
        zf.writestr("OEBPS/content.opf", opf_content)
        zf.writestr("OEBPS/style.css", style_css)

        # 画像ページ
        for fname, xhtml in image_pages:
            zf.writestr(f"OEBPS/{fname}", xhtml)

        # 画像ファイル本体
        for img in meta.get("images", []):
            zf.write(img["file"], f"OEBPS/{img['file']}")


def main():
    import sys

    if len(sys.argv) != 4:
        print("Usage: python word_html_to_epub.py input.html output.epub metadata.md")
        return

    input_html = sys.argv[1]
    output_epub = sys.argv[2]
    metadata_path = sys.argv[3]

    print("Detected encoding:", detect_encoding(input_html)[0])

    # 1. metadata 読み込み
    meta = load_metadata(metadata_path)
    print("Metadata loaded:", meta)

    # 2. HTML 読み込み + 章分割
    chapters = load_html_and_split_chapters(input_html)
    # 重複タイトル span を削除
    for chap in chapters:
        remove_duplicate_title_span(chap)
        remove_orphan_en_spans(chap)
        clean_word_garbage(chap)
        clean_span_and_ruby(chap)
    
        # --- 章タイトル内部の span もクリーンアップ ---
        first = chap["nodes"][0]
        if first.name == "p" and "CHAPTER" in first.get("class", []):
            # p の中の span をすべて処理
            for span in first.find_all("span"):
                style = span.get("style", "")
    
                # font-size / font-family / mso-* を削除
                if (
                    "font-size" in style
                    or "font-family" in style
                    or "mso-" in style
                ):
                    span.unwrap()  # span を外して中身だけ残す
    
                # italic → <em>
                elif "italic" in style:
                    em = first.new_tag("em")
                    em.string = span.get_text()
                    span.replace_with(em)
    
                # bold → <strong>
                elif "bold" in style:
                    strong = first.new_tag("strong")
                    strong.string = span.get_text()
                    span.replace_with(strong)
    
    print(f"Found {len(chapters)} chapters.")
    for chap in chapters:
        print(chap["index"], chap["title"])

    # 3. 章ごとの XHTML 生成
    chapter_files = generate_all_chapter_xhtml(chapters)
    chapter_filenames = {idx: filename for idx, (filename, _) in chapter_files.items()}

    # 4. toc.xhtml 生成
    toc_xhtml = build_toc_xhtml(chapters, chapter_filenames)

    # 画像ページの生成（metadata に images がある場合）
    image_pages = []
    for img in meta.get("images", []):
        if img.get("type") == "insert_after_toc":
            image_filename = img["file"]
            image_xhtml = build_image_xhtml(image_filename)
            image_pages.append(("image.xhtml", image_xhtml))

    # 5. content.opf 生成
    opf_content = build_opf(meta, chapter_filenames, image_pages)

    # 6. style.css（縦書き・右開き対応）
    style_css = """
@charset "UTF-8";
body {
  writing-mode: vertical-rl;
  -epub-writing-mode: vertical-rl;
  line-height: 1.8;
  font-family: "YuMincho", serif;
}
p {
  margin: 0 0 1em 0;
}
"""

    # 7. EPUB 生成
    create_epub(output_epub, chapter_files, toc_xhtml, opf_content, style_css, image_pages, meta)

    print(f"EPUB created: {output_epub}")

if __name__ == "__main__":
    main()
