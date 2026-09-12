"""yaml2epub.py

シンプルな YAML -> EPUB3 変換スクリプトの薄いエントリポイント。

使い方:
  python yaml2epub.py metadata.yaml out.epub

実体は `yaml2epub/` パッケージにある。このファイルは CLI 入口を
`yaml2epub.pipeline.main` へただ転送するだけ。
"""

import sys

from yaml2epub.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
