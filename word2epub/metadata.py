import os
import yaml


def load_metadata(metadata_path):
    """Load metadata from a YAML/Markdown-like file.

    Returns a dict with keys: title, author, ppd (page-progression-direction), images
    """
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
