import chardet


def detect_encoding(path):
    """
    Detect encoding of a Word HTML file and return (encoding, raw_bytes).
    """
    with open(path, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "cp932"
    return encoding, raw
