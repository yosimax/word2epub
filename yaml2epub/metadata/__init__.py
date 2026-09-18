"""Metadata normalization for legacy yaml2epub specifications."""


def _normalize_legacy_metadata(meta: dict | None) -> dict:
    """Normalize legacy metadata aliases used by older yaml2epub specifications.

    The historical instruction file uses `seriestitle` and `specialthanks`-style
    naming. The current code expects `series_title` and `special_thanks`.
    This helper keeps both forms working during migration.
    """
    if not isinstance(meta, dict):
        return meta or {}

    if "series_title" not in meta and "seriestitle" in meta:
        meta["series_title"] = meta["seriestitle"]
    if "special_thanks" not in meta and "specialthanks" in meta:
        meta["special_thanks"] = meta["specialthanks"]
    if "title" not in meta and "book_title" in meta:
        meta["title"] = meta["book_title"]
    if "book_title" not in meta and "title" in meta:
        meta["book_title"] = meta["title"]
    return meta
