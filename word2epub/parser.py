import re
from bs4 import BeautifulSoup, NavigableString, Tag
from .encoding import detect_encoding


def parse_word_html_and_split_chapters(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 軽微な属性削除
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

    body = soup.body or soup

    nodes = [node for node in body.descendants if getattr(node, "name", None)]

    chapters = []
    current_chapter = None

    for node in nodes:
        if node.name == "p" and "CHAPTER" in str(node.get("class")):
            if current_chapter is not None:
                chapters.append(current_chapter)

            en_span = node.find("span", attrs={"lang": "EN-US"})
            en_text = en_span.get_text(strip=True) if en_span else ""

            jp_text = node.get_text(strip=True)
            if en_text:
                jp_text = jp_text.replace(en_text, "", 1).strip()

            if en_text and jp_text:
                title_text = f"{en_text} - {jp_text}"
            else:
                title_text = en_text or jp_text

            current_chapter = {"index": len(chapters) + 1, "title": title_text, "nodes": [node]}
        else:
            if current_chapter is not None:
                current_chapter["nodes"].append(node)

    if current_chapter is not None:
        chapters.append(current_chapter)

    return chapters


def remove_orphan_en_spans(chapter):
    cleaned = []
    for node in chapter["nodes"]:
        if (
            node.name == "span"
            and node.get("lang") == "EN-US"
            and node.get_text(strip=True) != ""
        ):
            continue

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
    cleaned = []

    for node in chapter["nodes"]:
        if node.name == "o:p":
            continue

        if (
            node.name == "span"
            and node.get("style")
            and "mso-spacerun:yes" in node.get("style")
        ):
            continue

        if node.name == "p" and node.get("class") == ["MsoNormal"]:
            node.attrs.pop("class", None)

        cleaned.append(node)

    chapter["nodes"] = cleaned
    return chapter


def remove_duplicate_title_span(chapter):
    if not chapter["nodes"]:
        return chapter

    first = chapter["nodes"][0]
    if first.name != "p":
        return chapter

    en_span = first.find("span", attrs={"lang": "EN-US"})
    en_text = en_span.get_text(strip=True) if en_span else ""

    full_text = first.get_text(strip=True)
    jp_text = full_text.replace(en_text, "", 1).strip() if en_text else full_text

    new_nodes = [first]

    for node in chapter["nodes"][1:]:
        if (
            en_text
            and node.name == "span"
            and node.get("lang") == "EN-US"
            and node.get_text(strip=True) == en_text
        ):
            continue

        if (
            jp_text
            and node.name == "span"
            and node.get_text(strip=True) == jp_text
        ):
            continue

        new_nodes.append(node)

    chapter["nodes"] = new_nodes
    return chapter


def clean_span_and_ruby(chapter):
    cleaned = []

    for node in chapter["nodes"]:

        if isinstance(node, Tag) and node.name == "span":
            text = node.get_text(strip=False)

            if text.strip() == "":
                continue

            style = node.get("style", "")
            if "mso-" in style:
                continue

            if any(x in style for x in ["font-size", "font-family"]):
                cleaned.append(NavigableString(text))
                continue

            if "italic" in style:
                em = Tag(name="em")
                em.string = text
                cleaned.append(em)
                continue

            if "bold" in style:
                strong = Tag(name="strong")
                strong.string = text
                cleaned.append(strong)
                continue

            if node.get("lang") == "EN-US":
                cleaned.append(node)
                continue

            cleaned.append(NavigableString(text))
            continue

        if isinstance(node, NavigableString):
            text = str(node)
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


def load_html_and_split_chapters(input_html_path):
    encoding, raw = detect_encoding(input_html_path)
    print(f"Detected encoding: {encoding}")
    html_content = raw.decode(encoding, errors="ignore")

    chapters = parse_word_html_and_split_chapters(html_content)

    if not chapters:
        print("Warning: No chapters (class='CHAPTER') found.")
    else:
        print(f"Found {len(chapters)} chapters.")

    return chapters
