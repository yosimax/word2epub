"""Small file I/O helpers."""

import os
import sys


def warn(message: str) -> None:
    """Emit a non-fatal warning to standard error.

    Args:
        message (str): Warning text without the leading ``warning:`` prefix.
    """
    print(f"warning: {message}", file=sys.stderr)


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
