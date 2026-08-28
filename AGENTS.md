# AGENTS.md — word2epub

YAML → EPUB3 変換スクリプト。実質1ファイル(`yaml2epub.py`)が全部のロジックを持つ。

## 最重要: 入口と構造
- 唯一の実コードはルートの `yaml2epub.py`。CLI 入口は `main()`(1358行目)。
- `yaml2epub/` ディレクトリは**空のダミー**(`epub/` `metadata/` `utils/` に中身なし)。パッケージとして import せず、`yaml2epub.py` を**ファイルパスから直接ロード**すること。`tests/conftest.py` の `_load_module` がこれを避けるために行っている。
- 出力は `TEMPLATE/book-template` をコピペして書き換える方式。`TEMPLATE/book-template` の中身は一切**変更禁止**(`yaml2epub.py_instruction.md` 参照)。

## 開発コマンド
- 実行: `python yaml2epub.py metadata.yaml [out.epub]`（out省略→`out.epub`）。
- テスト: `.venv/bin/python -m pytest`（`pyproject.toml` に `testpaths=["tests"]`）。24件(e2e15 + unit9)が通る。
- 整形/lint/型チェックは**`.venv` に未インストール**。初回で `pip install -r requirements-dev.txt` が必要。
  通し: `black yaml2epub.py && isort yaml2epub.py && ruff check yaml2epub.py && mypy yaml2epub.py`。
- 依存管理は **pip-tools + requirements**（`pip-compile requirements.in`）。`poetry.lock` もあるが Poetry 推奨ではない。`pyproject.toml` 変更後は `pip-compile` 再実行。

## 環境
- `.venv` あり、Python 3.14（`.python-version`）。ランタイム依存: PyYAML必須、jinja2 オプション(colophon テンプレート用)、lxml オプション。
- `noshared/` は gitignore 対象の個人物（別プロジェクト等）。作業対象外。

## 規約（`.github/copilot-instructions.md`）
- レビュー・コメントは日本語。ソース内コメントは**英語＋日本語両方**。
- ファイル/変数/関数: snake_case、クラス: CamelCase、定数: UPPER_SNAKE_CASE。
- 公開クラス/関数には Docstring（引数・戻り値・例外明記）。

## 既知の挙動・フック
- `_normalize_legacy_metadata`（78行目）でレガシーキーを正規化: `seriestitle`→`series_title`、`specialthanks`→`special_thanks`、`book_title`/`title` 相互。古い spec の YAML を流用する際は必須。
- 詳細な YAML フィールド・機能一覧は `READEME_yaml2epub.md` 参照（このファイルには載せない）。
