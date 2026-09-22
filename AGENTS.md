# AGENTS.md — word2epub

YAML → EPUB3 変換スクリプト。ルートの `yaml2epub.py` は薄い CLI ラッパで、実装は `yaml2epub/` パッケージにある。

## 最重要: 入口と構造
- CLI 入口はルートの `yaml2epub.py`。これは `yaml2epub.pipeline.main()` を呼ぶだけの薄いラッパー。
- 実装パッケージは `yaml2epub/`(`epub/`, `metadata/`, `utils/`)。ユニットテストはパッケージを直接 import する。e2e は従来どおりルート `yaml2epub.py` をファイルパスからロードして `main()` を呼ぶ。
- 出力は `TEMPLATE/book-template` をコピペして書き換える方式。`TEMPLATE/book-template` の中身は一切**変更禁止**（テンプレート構造・ページ順序は `READEME_yaml2epub.md` の「テンプレート構造とページ順序」節参照）。

## 開発コマンド
- 実行: `python yaml2epub.py metadata.yaml [out.epub]`（out省略→`out.epub`）。
- テスト: `.venv/bin/python -m pytest`（`pyproject.toml` に `testpaths=["tests"]`）。37件(e2e15 + unit22)が通る。
- 整形/lint/型チェックは初回で `pip install -r requirements-dev.txt` が必要。
  通し: `.venv/bin/black yaml2epub.py yaml2epub tests && .venv/bin/isort yaml2epub.py yaml2epub tests && .venv/bin/ruff check yaml2epub.py yaml2epub tests && .venv/bin/mypy yaml2epub.py && .venv/bin/mypy tests`。
- 依存管理は **pip-tools + requirements**（`pip-compile requirements.in`）。`poetry.lock` もあるが Poetry 推奨ではない。`pyproject.toml` 変更後は `pip-compile` 再実行。

## 環境
- `.venv` あり、Python 3.14（`.python-version`）。ランタイム依存: PyYAML必須、jinja2 オプション(colophon テンプレート用)、lxml オプション。
- `noshared/` は gitignore 対象の個人物（別プロジェクト等）。作業対象外。
- `TEMPLATE/book-template` も **git 管理外**（`.gitignore` の `book-template` パターン）。ローカル資産であり、テスト・実行にはローカルに存在することが前提。

## 規約（`.github/copilot-instructions.md`）
- レビュー・コメントは日本語。ソース内コメントは**英語＋日本語両方**。
- ファイル/変数/関数: snake_case、クラス: CamelCase、定数: UPPER_SNAKE_CASE。
- 公開クラス/関数には Docstring（引数・戻り値・例外明記）。

## 既知の挙動・フック
- `_normalize_legacy_metadata`（`yaml2epub/metadata/__init__.py`）でレガシーキーを正規化: `seriestitle`→`series_title`、`specialthanks`→`special_thanks`、`book_title`/`title` 相互。古い spec の YAML を流用する際は必須。
- 詳細な YAML フィールド・機能一覧は `READEME_yaml2epub.md` 参照（このファイルには載せない）。

## リファクタリング履歴
- 単一ファイル→パッケージ化のリファクタリングは**完了**し main にマージ済み(PR #8)。実施内容は `REFACTORING_DONE.md` 参照。WIP 文書が未コミットで残っていることはない。
