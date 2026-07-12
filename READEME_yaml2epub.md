# yaml2epub.py — README

簡潔な説明: `yaml2epub.py` は `TEMPLATE/book-template` を元に、YAMLで定義したメタデータと文書を集めて EPUB3 を生成するスクリプトです。

**使い方**
- **コマンド**: `python yaml2epub.py metadata.yaml [out.epub]`
- **引数**: `metadata.yaml` — メタデータファイル（必須）、`out.epub` — 出力ファイル名（省略時は `out.epub`）
- **依存**: `PyYAML` が必須。`jinja2` はオプション（奥付のテンプレートレンダリングで利用）。

**入力ファイル形式のサンプル**
以下は `metadata.yaml` の最小サンプル例です:

```yaml
title: サンプル作品
book_title: サンプル作品（長いタイトル）
series_title: シリーズ名
creator01: 著者名
publisher: 出版社名
image:
  cover: images/cover.jpg
  backcover: images/back.jpg
documents:
  frontmatter: frontmatter.yaml
  contents:
    - chapter: chapter001.yaml
    - chapter: chapter002.yaml
colophon:
  text: colophon.yaml
  created_at: NOW_YMD
```

chapter001.yaml の例（本文は `contents` に改行で段落区切り）:

```yaml
page_title: 第一章　はじめに
contents: |
  これは本文の最初の段落。

  続いて二つ目の段落。
```

**より具体的には、sample_yaml配下のmetadata.ymlなどを参照のこと**

**実装されている機能**
- **テンプレートベース生成**: `TEMPLATE/book-template` の中身をコピーして出力用ディレクトリを作成。
- **タイトル反映**: XHTML テンプレート内の `<title>` をメタデータのタイトルで置換。
- **表紙・裏表紙画像取り込み**: `image.cover` / `image.backcover` を `item/image/` にコピーし、対応する XHTML の `src` を更新。
- **本文挿入（章）**: YAML/HTML/プレーンテキストの章ファイルを読み、段落（空行区切り）を XHTML に変換して任意の数の章を生成。
- **前付・注意書き・奥付・広告**: `frontmatter` / `caution` / `colophon` / `advertisement` をテンプレートの該当ページに挿入。
- **OPF の動的更新**: 画像、XHTML、nav を走査して `standard.opf` の manifest と spine を再構築。
- **目次更新**: `navigation-documents.xhtml` と `p-toc.xhtml` を生成・更新して章一覧を反映。
- **EPUB 生成**: `mimetype` を先頭でストアし、ZIP（EPUB）を作成。
- **Jinja2 サポート**: 奥付（YAMLテンプレート）で `jinja2` がある場合はレンダリングを試行（無ければシンプル置換にフォールバック）。

**実装されていない機能 / 制約事項**
- **画像変換・リサイズなし**: 画像形式の変換や自動リサイズは行いません。
- **HTML サニタイズ未実装**: 外部 HTML をそのまま挿入するため、入力の整合性は利用者側で担保してください。
- **限られたメタデータ処理**: OPF 内のメタデータは主要な項目に限定して上書きします（細かい EPUB メタは未対応）。
- **広告キー名**: コード内では `advertisement` を参照します。設定時は `advertisement` キーを使用してください。
- **エラーハンドリング**: ベストエフォートで例外を握りつぶす箇所があり、詳細なエラー報告は限定的です。
- **テンプレート依存**: `TEMPLATE/book-template` 構造に依存するため、別テンプレートを使う場合は互換性に注意してください。

**拡張案（今後の改善候補）**
- **画像の自動変換／最適化**: cover/backcover のリサイズや WebP 変換など。
- **CLI オプション化**: 詳細オプション（出力名、テンプレートパス、verbose モードなど）を追加。
- **検証とテスト**: 入力 YAML と生成 EPUB の自動テスト、CI 連携。
- **詳細メタデータ対応**: OPF の全メタタグやカスタムメタへの対応拡張。
- **TOC 階層化**: 多階層の目次（サブチャプター）に対応。

**その他の情報・参照**
- **スクリプト本体**: [yaml2epub.py](yaml2epub.py)
- **テンプレート**: `TEMPLATE/book-template` ディレクトリを参照してください。

**追加の YAML フィールド一覧（詳細）**
以下は `metadata.yaml` や関連ファイルで利用できるフィールドとフォーマットの一覧です。相対パスはメタデータファイルの配置ディレクトリ基準で解決されます。

- `title` / `book_title` : 書名。`book_title` があれば表紙タイトル生成に使用されます。
- `series_title` : シリーズ名（任意）。
- `creator01`, `creator02` : 著者名や協力者（OPF の `dc:creator` に反映）。
- `publisher` : 出版社（OPF の `dc:publisher` に反映）。
- `image` (マップ): 画像ファイル指定。
  - `cover`: 表紙画像パス（例: `images/cover.jpg`）
  - `backcover`: 裏表紙画像パス
- `documents` (マップ): ドキュメント指定。
  - `frontmatter`: 前付ファイルパス (文字列) かオブジェクト（例: `{ text: "frontmatter.yaml", image: "fm.jpg" }`）
  - `contents`: 章のリスト。各要素は文字列（章ファイルパス）かオブジェクト（例: `{ chapter: "chapter001.yaml" }`）
- 各章ファイル（例: `chapter001.yaml`）:
  - YAML フォーマット: `page_title`（任意）と `contents`（複数段落は空行で区切る）
  - もしくは HTML/XHTML/プレーンテキストファイルを直接指定可能
- `caution` : 注意書きテキスト（文字列）。テンプレートの `p-caution.xhtml` に挿入されます。
- `colophon` : 奥付指定（オブジェクトまたは文字列パス）。
  - オブジェクト例: `{ text: "colophon.yaml", version: "1.0", created_at: "NOW_YMD", copyright: "© 著者" }`
  - `created_at: NOW_YMD` を指定すると現在日付で展開されます。
  - YAML 奥付は Jinja2 テンプレートでレンダリング可能（`jinja2` インストール時）。
- `advertisement` : 広告ページ指定（文字列パスかオブジェクト `{ text: ... }`）。文字列 `'NONE'` を指定すると広告ページを削除します。
- 自動生成される項目:
  - OPF の `dc:identifier` は自動的に `urn:uuid:...` を生成して置換されます。
  - OPF の `dcterms:modified` は現在の UTC 時刻で更新されます。

## セットアップ
以下はこのリポジトリで再現可能な開発環境を作るための手順です。`requirements.txt` / `requirements-dev.txt` と `pyproject.toml` がルートにあります。

1) 仮想環境を作る（推奨）

- Windows (PowerShell):
```powershell
python -m venv .venv
.# 初回のみ: 実行ポリシーが厳しい場合は管理者で `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` を検討
.\.venv\Scripts\Activate.ps1
```

- macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

2) Poetry を使わない（`pip-tools` + requirements を利用）

- pip-tools が必要（ローカル仮想環境で実行）:
```bash
pip install --upgrade pip pip-tools
pip install -r requirements.txt
# 開発用ツール
pip install -r requirements-dev.txt
```

- 依存を更新したい場合（トップレベルを編集して再コンパイル）:
```bash
# requirements.in / requirements-dev.in を編集
pip-compile requirements.in --output-file=requirements.txt
pip-compile requirements-dev.in --output-file=requirements-dev.txt
```

3) Poetry を使う方法

- Poetry をインストール（おすすめ: pip または公式インストーラ）:
```bash
pip install --user poetry
# または: curl -sSL https://install.python-poetry.org | python -
```

- 依存のインストール（`pyproject.toml` に基づく）:
```bash
poetry install
```

- 開発用シェルを使って実行する例:
```bash
poetry shell
python yaml2epub.py metadata.yaml out.epub
```

- Poetry から `requirements.txt` を出力したい場合:
```bash
poetry export -f requirements.txt --without-hashes --output=requirements.txt
poetry export -f requirements.txt --with dev --without-hashes --output=requirements-dev.txt
```

- `poetry.lock` を更新する場合:
```bash
poetry lock --no-interaction
```

- 注意: `pyproject.toml` を変更したら、必ず `poetry lock` を実行して `poetry.lock` を更新してください。

- `poetry export` を使うと、`pyproject.toml` / `poetry.lock` の状態を `requirements.txt` 系ファイルに反映できます。

4) Docker（オプション）

- OS 間の差異（特にバイナリ依存）が問題になる場合、Docker コンテナで実行環境を固定すると確実です。ルートにある `Dockerfile` はシンプルなサンプルです。

Docker イメージのビルド例:

```bash
# 標準ビルド（ランタイムのみ）
docker build -t yaml2epub:latest .

# 開発用依存も含めてビルドする場合
docker build --build-arg INSTALL_DEV=true -t yaml2epub:dev .
```

コンテナでの実行例（カレントディレクトリをボリュームマウントしてメタデータを渡す）:

- Linux / macOS:
```bash
docker run --rm -v "$(pwd)":/work -w /work yaml2epub:latest metadata.yaml out.epub
```

- Windows PowerShell:
```powershell
docker run --rm -v ${PWD}:/work -w /work yaml2epub:latest metadata.yaml out.epub
```

注意事項:

- `lxml` 等はネイティブ拡張をビルドするために追加のシステムパッケージが必要です。サンプル `Dockerfile` では Debian ベースのビルドツール／ヘッダをインストールしています。ビルドが重い場合は、プラットフォーム用の wheel を用意するか、別のベースイメージ（manylinux ベースなど）を検討してください。
- Docker が使えない環境で検証する場合は、コンテナの代わりに `pyproject.toml` や `requirements.txt` を使ってローカル仮想環境で再現してください。

5) 注意点

- `pip freeze` を直接使うと、開発者ローカルの不要パッケージが混入することがあるので避ける（クリーンな仮想環境でも実行するなら可）。
- Windows と Linux でビルドされるバイナリホイールは異なるため、本番配布や CI では該当 OS 上で `pip install` するか Docker を使ってください。

