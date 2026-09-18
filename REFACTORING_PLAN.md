# REFACTORING_PLAN.md — yaml2epub.py リファクタリング 計画・指示書

> 本ファイルはリファクタリングを**新規セッションで再開**する際に最初読むドキュメント。
> 作成: 2026-09-03(準備段階。着手前のベースラインを記述)。

## 1. 目的と方針(確定済み決定)

- 目的: 単一ファイル `yaml2epub.py`(約1433行)を `yaml2epub/` パッケージに lib 化し、保守性を上げる
  (`yaml2epub.py_instruction.md` の「pythonスクリプトは適宜lib化して保守性が良くなるようなプログラム構造としてください」が根拠)。
- **D1(エントリ)**: ルートの `yaml2epub.py` を**薄い CLI ラッパ**に残す。
  CLI 契約 `python yaml2epub.py metadata.yaml [out.epub]` は不変。
- **D2(スコープ)**: コード移動に加えて**中身クリーンアップも今回に含む**(Step 4)。
- **順序原則**: 「純粋な移動(Step 2) → テスト(Step 3) → 中身クリーンアップ(Step 4)」を**分離**する。
  移動とクリーンアップを混ぜるとテスト失敗の原因特定が困難になるため。
  各段階のゲートは **テスト全件グリーン**(`.venv/bin/python -m pytest`)。

## 2. 現状(2026-09-03 時点)

- 分岐: `Refactoring_try1`
- **未コミットの WIP**(グリーン、29 passed):
  - `yaml2epub.py`: `_render_document`(「テンプレート→body差し替え」の呼び出し6箇所を統合)と
    `_compute_html_class` を抽出。
  - `tests/test_units.py`: 単体テスト5件追加(テスト総数 15 e2e + 14 unit = **29**)。
- ベースライン: 29 passed。実行: `.venv/bin/python -m pytest`
- 空ディレクトリ `yaml2epub/{epub,metadata,utils}` が存在(未トラック。git は空ディレクトリを管理できないため
  Step 2 で実ファイルが乗れば自然にトラックされる)。これが目標構造のスキャフォールド。

## 3. 目標構造と 関数→モジュール 対応表

```
yaml2epub/
├── __init__.py
├── epub/
│   ├── __init__.py
│   ├── constants.py    # TEMPLATE_DIR, ITEM_DIR, XHTML_*, OPF_FILE, NAV_FILE, NS_*, DEFAULT_TITLE
│   ├── xhtml.py        # xhtml ビルダー群
│   ├── pages.py        # ページ挿入群
│   ├── opf.py          # update_opf_dynamic / update_opf_basic
│   ├── navigation.py   # update_navigation
│   └── package.py      # tmpdir セットアップ・画像・ドキュメント生成・OPF/NAV 更新・zip
├── metadata/           # _normalize_legacy_metadata, YAML 読み込み
└── utils/              # read_text_file / write_text_file
yaml2epub.py            # 薄いラッパ(実装は yaml2epub パッケージ本体)
```

| 対象(現行) | 現行行 | 移動先 |
|---|---|---|
| 定数群(TEMPLATE_DIR … DEFAULT_TITLE) | L29, L64-92 | `epub/constants.py` |
| `read_text_file` / `write_text_file` | L116-124 | `utils/` |
| `_normalize_legacy_metadata` | L95 | `metadata/` |
| `_compute_style_value` / `_compute_html_class` | L32 / L48 | `epub/xhtml.py` |
| `replace_title_in_xhtml` | L127 | `epub/xhtml.py` |
| `add_stylesheets_to_xhtml` | L140 | `epub/xhtml.py` |
| `_build_xhtml_document` | L176 | `epub/xhtml.py` |
| `_apply_body_template` | L216 | `epub/xhtml.py` |
| `_render_document` | L279 | `epub/xhtml.py` |
| `_insert_document_section` | L320 | `epub/pages.py` |
| `insert_frontmatter` / `insert_backmatter` | L440 / L454 | `epub/pages.py` |
| `insert_caution` | L471 | `epub/pages.py` |
| `insert_colophon` | L479 | `epub/pages.py` |
| `insert_advertisement` | L570 | `epub/pages.py` |
| `insert_titlepage` | L618 | `epub/pages.py` |
| `_replace_title_in_string` | L645 | `epub/xhtml.py` |
| `generate_chapter_xhtmls` | L659 | `epub/pages.py` |
| `update_opf_dynamic` / `update_opf_basic` | L725 / L942 | `epub/opf.py` |
| `update_navigation` | L973 | `epub/navigation.py` |
| `make_epub_from_template` | L1051 | `epub/package.py` |
| `_setup_temporary_directory` | L1104 | `epub/package.py` |
| `_process_images` | L1132 | `epub/package.py` |
| `_generate_document_content` | L1239 | `epub/package.py` |
| `_update_manifest_and_spine` | L1345 | `epub/package.py` |
| `main` | L1371 | `yaml2epub/pipeline.py` |
| YAML 読み込み(L1390-1392: `yaml.safe_load` + 正規化) | L1390 | `metadata/`(または `pipeline.py` 側保持) |

モジュール名・ファイル分割は提案であり、上記マッピングの範囲内で新規セッションが調整してよい。
行番号は WIP コミット前のもの。Step 0 完了後、grep で再確認すること。

## 4. 不変条件(制約)

- **`TEMPLATE/book-template` の内容は一切変更しない**。
  補足: 同ディレクトリは **git 管理外**(`.gitignore` の `book-template` パターンで無視、`git ls-files TEMPLATE` は空)。
  ローカル資産であり、リポジトリに含める必要もない。
- **CLI 契約**: `python yaml2epub.py metadata.yaml [out.epub]` 不変(ルートラッパ)。
- **各段階でテスト全件グリーン**: `.venv/bin/python -m pytest`(ベースライン 29)。
- **挙動不変**(Step 4 の例外スワロウ明示化を除く): e2e がパッケージ構造・内容を検証する。
- 規約(`.github/copilot-instructions.md`):
  - ソース内コメントは**英語+日本語両方**。
  - 公開クラス/関数は引数・戻り値・例外を明記した Docstring。
  - 命名: snake_case / CamelCase / UPPER_SNAKE_CASE。
- 依存管理は pip-tools。`pyproject.toml` を変更した場合は `pip-compile` を再実行。
- レビュー・コメントは日本語。

## 5. ステップ計画

### Step 0 — WIP コミット
- テスト全件グリーンを確認: `.venv/bin/python -m pytest -q`
- WIP をコミット。メッセージ例: `Refactoring Step2: extract _render_document; add unit tests`
- コミット後、§3 対応表の行番号(L番号)がズレていないか grep で確認。

### Step 1 — dev ツール導入(初回のみ)
- `.venv/bin/pip install -r requirements-dev.txt`
  (black / ruff / isort / mypy / pytest-cov / pre-commit / pip-tools / coverage)
- `requirements-dev.txt` は pip-compile 生成物。手編集しない。

### Step 2 — 純粋な移動のみ(ロジック変更禁止)
- **切り貼りだけ**。関数・変数のリネームなし、挙動変更なし。
- §3 準拠でパッケージ作成。ルート `yaml2epub.py` は薄いラッパに縮小:
  ```python
  import sys

  from yaml2epub.pipeline import main

  if __name__ == "__main__":
      raise SystemExit(main(sys.argv))
  ```
- **`__file__` 依存の修正(必須)**:
  現行 `TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "TEMPLATE", "book-template")`(L29)は
  移動後、`yaml2epub/epub/constants.py` 基準では**パッケージディレクトリ**を指して壊れる。
   **リポジトリ基準**に直す。例: `yaml2epub/epub/constants.py` からリポジトリルートは **3階上**
   (`constants.py` → `epub/` → `yaml2epub/` → root):
   `REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
   として `TEMPLATE_DIR = os.path.join(REPO_ROOT, "TEMPLATE", "book-template")`。
- **ラッパは内部関数を再エクスポートしない**(Step 3 のユニットテスト再指向が、ラッパに内部が見えない前提で成立するため)。
- ゲート: `.venv/bin/python -m pytest` 全グリーン +
  `python yaml2epub.py sample_yaml/metadata.yaml out.epub` のスモーク実行。
- **出力比較のベースライン取得**: 移動前に `out.epub` を生成し、展開コピー(XHTML/OPF テキスト)を退避しておく
  (zip はタイムスタンプ等が入るためバイト列比較しない。Step 7 参照)。

### Step 3 — テストの修正
- **「再指向」の意味**: **redirection(参照先の差し替え)**。retry(再試行)の意味では**ない**。
  - **e2e**: `module` フィクスチャ(`tests/conftest.py` L27-29)は `yaml2epub.py` を
    **ファイルパスから `importlib.util.spec_from_file_location` で明示ロード**して返す。
    ルートファイルはラッパとして残存し `main` を公開するため、e2e は `module.main` の呼び出しが
    ラッパを参照し続ける**同一パスを維持**する(実質不変)。
  - **ユニットテスト**: **こちらが再指向の本体。** WIP で追加した5件が `module._apply_body_template` /
    `module._insert_document_section` 等の内部関数を直接触るが、それらはパッケージ本体へ移り、
    ラッパには載らない。従って**新モジュールからの直接 import に差し替える**(例:
    `from yaml2epub.epub.xhtml import _apply_body_template`)。
- conftest にリポジトリルートを `sys.path` に追加し、`yaml2epub` パッケージを import できるようにする
  (現行はファイルパス読み込みのみのため、パッケージ import の経路がまだ無い)。
- ゲート: 29 件全グリーン。

### Step 4 — 中身クリーンアップ(小コミット分割。各項目でテスト全グリーンを確認)
- **例外スワロウの明示化**:
  - 用語確認: 「スワロウ」= 例外を**飲み込む(suppress)** の意。`except Exception` を「throw(送出)する」
    誤記では**ない**。対象は「送出された例外を `pass` で黙って握り潰している」現状コードの整理。
  - 現行の `except Exception` は全22箇所。代表的なサイレントスワロウ:
    - `_generate_document_content`: L1259-1262(titlepage 生成)、L1267-1271(backcover コピー)、
      L1284-1289(stylesheet コピー)、L1335-1340(不要 p-XXX 削除)
    - `insert_advertisement`: L577-581(広告ファイル削除)、L591-594(YAML 読み込み失敗フォールバック)
    - `add_stylesheets_to_xhtml`: L156-159(読み取り失敗 → スキップ)
  - 方針: まず `grep -n "except Exception" yaml2epub.py` で全列挙し、**箇所ごとに判定**する。
    - (a) 冪等・後始末の手順(テンプレート残骸ファイルの削除等): 黙ってもよいが、**理由をコメントに明記**。
    - (b) 内容生成・コピーの手順: **明示化**(最低限 stderr へ警告)。
  - **挙動が変わる変更は、まず回帰テストを追加してから変更にすること**
    (例: titlepage 生成失敗でも処理は継続される、という挙動を固定するテスト)。
- **direction 判定の重複統一**: `direction.lower().startswith("v")` は L43(`_compute_style_value`)と
  L61(`_compute_html_class`)の2箇所。**単一の `_is_vertical(direction) -> bool`** を新設し、両方から置換。
- **`br_flag` の重複除去**: `_generate_document_content` 内で L1297 / L1317 の
  `bool(meta.get("br_convert"))` が2回取得されている。1回に統一。
- **`NONE` 判定の重複統一**: L575(`insert_advertisement` の削除分岐)と L1308
  (`_generate_document_content` の `include_advertisement` 算出)。**単一の情報源**へ統一し、
  `"NONE"` は定数化。
- **マジック文字列の定数化**: `"p-text"`(L191 / L226)、`"NONE"`、`"目次"`、
  デフォルトタイトル等。
- **title 置換系の整理**: `_replace_title_in_string`(L645、文字列1件置換)、
  `replace_title_in_xhtml`(L127、ディレクトリ全走査)、`_render_document` の
  `replace_title` パラメータの3系統の役割境界を整理し、Docstring を揃える。

### Step 5 — lint / 型チェック
- `black` / `isort` / `ruff check` / `mypy` を**ルートファイル+パッケージ配下**に展開して実行。
  (現 AGENTS.md のコマンドは `yaml2epub.py` 単体。分割後は `yaml2epub/` を含める。)
- 既存の型指摘も是正対象。

### Step 6 — ドキュメント更新・コミット
- `AGENTS.md`: 「実質1ファイル(`yaml2epub.py`)が全部のロジックを持つ」等の記述を新構造へ更新。
  テスト件数(24 → 29 等)も現行に合わせて更新。
- `yaml2epub.py_instruction.md`: 「プログラムについて」節を新構造に合わせる。
- 最終コミット。

## 6. 既知の罠

1. **パッケージ/ファイル同名衝突**: `yaml2epub/`(パッケージ)と `yaml2epub.py`(ファイル)が同ディレクトリに併存する。
   import 機構では**通常パッケージが同名モジュールに優先**するため `import yaml2epub` はパッケージに解決される。
   - conftest のパス指定ロード(`spec_from_file_location`)は優先順位の影響を**受けない**。
   - ラッパ(ルートファイル)は `python yaml2epub.py` でスクリプト実行され、自身は `__main__` になるため、
     `from yaml2epub.pipeline import main` は自己 import をせず動作する。
   - `import yaml2epub` が**ルートファイル**を返すことを前提にしたコードを書いてはいけない。
2. **`__file__` 依存パスの壊れ**: `TEMPLATE_DIR`(L29)は移動後、パッケージディレクトリを指して壊れ、
   EPUB が組めない。必ずリポジトリ基準に修正(Step 2 参照)。
3. **例外スワロウの挙動変更**: Step 4 で swallow → 明示化すると、失敗時の終了コード・出力が変わりうる。
   各変更はテスト全グリーンを確認し、必要なら変更前に回帰テストを追加する(Step 4 参照)。

## 7. 検証方法と Definition of Done

- **各ステップ共通**: `.venv/bin/python -m pytest` — 29 passed。
- **出力比較**: サンプル実行後、展開した XHTML/OPF の**テキスト内容**を Step 2 前のベースラインと比較する。
  - 比較対象: `item/xhtml/*.xhtml`、`item/standard.opf`、`item/navigation-documents.xhtml`。
  - zip 本体のバイト列比較はしない(圧縮メタデータ・タイムスタンプが入る)。
- **DoD(完了条件)**:
  1. 29 テスト全グリーン。
  2. lint(black/isort/ruff)+ 型チェック(mypy)クリーン(パッケージ含む)。
  3. `AGENTS.md` と `yaml2epub.py_instruction.md` が新構造と整合。
  4. `Refactoring_try1` 上に WIP + 各ステップのコミットが存在。

## 8. 実行コマンド(参考)

- 実行: `python yaml2epub.py metadata.yaml [out.epub]`
- テスト: `.venv/bin/python -m pytest`
- 整形/lint/型: `black yaml2epub.py && isort yaml2epub.py && ruff check yaml2epub.py && mypy yaml2epub.py`
  (分割後は `yaml2epub/` を対象に含める)
