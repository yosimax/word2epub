# ~~word2epub~~ 改め yaml2epub

YAML → EPUB3 変換ツール `yaml2epub.py`。`TEMPLATE/book-template` をベースに、`metadata.yaml` と文書ファイルから日本語縦書き・リフロー対応の EPUB3（zip）を生成する。

> 履歴: このリポジトリは当初 Word HTML → EPUB3 変換ツールだった。アプローチの見直しで YAML から生成する `yaml2epub.py` が正となった（旧スクリプトは削除済み）。

**使い方**
```
python yaml2epub.py metadata.yaml [out.epub]
```
- 引数: `metadata.yaml` — メタデータファイル（必須）、`out.epub` — 出力ファイル名（省略時は `out.epub`）
- サンプル入力一式は `sample_yaml/` にある。

**詳細**
- YAML フィールド一覧・機能・制約・セットアップ: [READEME_yaml2epub.md](READEME_yaml2epub.md)
- 開発・テスト・リファクタリング履歴: [AGENTS.md](AGENTS.md) / [REFACTORING_DONE.md](REFACTORING_DONE.md)
