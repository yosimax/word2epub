# md2epub.py 仕様、概要

* TEMPLATE配下にあるEPUB3のサンプルbook-templateをベースに中身を書き換えることで日本語、縦書き、リフロー、右開き対応のEPUB3（zip）ファイルを作成する。
* 以下の内容を、metadata.yamlに記載して、このファイルを読み込む
  * metadata.yamlには以下を記載する。

```yaml
title: 作品名
  # 指定されていないときは、作品名未設定と置き換える
seriestitle: 作品シリーズ名
creator01: Author01
  # 指定されていないときは、著者名未設定と置き換える
creator02: Author02
  # 指定されていないときは、要素/タグごと削除
publisher: 出版社
  # 指定されていないときは、要素/タグごと削除
version: 版数を記載
created_at: NOW_YMD
# NOW_YMDと記載していたら現在の年月日（西暦4桁年月日で置き換える）
copyright: |
  © 2026 本来は著者名を記載します。が、これはサンプルです。    
special_thanks: |
  謝辞
  　一般社団法人デジタル出版者連盟様のガイドラインを参考にさせていただきました。
image:
  cover: coverの画像ファイル
    # 指定されていないときは、タグごと削除
    # 指定されていないときは、p-cover.xhtmlごと削除
  backcover: backcoverの画像ファイル
    # 指定されていないときは、要素/タグごと削除
caution: 著作権の注意事項など
  # 指定されていないときは、p-caution.xhtmlごと削除(作成しない)
colophon:
  text: colophonの内容を記載したファイル
advatizement:
  text: NONE
  # NONEと記載していたらp-ad-001.xhtmlごと削除(作成しない)
documents:
  frontmatter:
    # 指定されていないときは、p-fmatter-<index>.xhtmlごと削除(作成しない)
    text: frontmatterの文章ファイル
    image: frontmatterの画像ファイル
    # 画像ファイルと文章ファイルを指定している場合は、記載順に配置する。
  contents:
    # 章ごとの文章ファイル <繰り返し>
    - chapter: 1章のファイル
    - chapter: 2章のファイル
```

* TEMPLATE配下は以下
```
+---TEMPLATE
|   |
|   \---book-template
|       |   mimetype
|       |
|       +---item
|       |   |   navigation-documents.xhtml  : 目次toc
|       |   |   standard.opf
|       |   |
|       |   +---image
|       |   |       ad-001.jpg
|       |   |       cover.jpg
|       |   |       img-001.jpg
|       |   |       kuchie-001.jpg
|       |   |       logo-bunko.png
|       |   |
|       |   +---style
|       |   |       book-style.css
|       |   |       style-advance.css
|       |   |       style-check.css
|       |   |       style-reset.css
|       |   |       style-standard.css
|       |   |
|       |   \---xhtml
|       |           p-cover.xhtml         : 1.表紙
|       |           p-fmatter-001.xhtml   : 2.frontmatter
|       |           p-titlepage.xhtml     : 3.本扉
|       |           p-caution.xhtml       : 4.注意書き
|       |           p-toc.xhtml           : 5.目次見出し
|       |           p-001.xhtml           : 6.本文
|       |           p-002.xhtml           : 6.本文
|       |           p-003.xhtml           : 6.本文
|       |           p-004.xhtml           : 6.本文
|       |           p-005.xhtml           : 6.本文
|       |           p-colophon.xhtml      : 7.奥付
|       |           p-ad-001.xhtml        : 8.広告
|       |
|       \---META-INF
|               container.xml
```

* 出力するページの順序は、standard.opf に従って以下のように生成する。
```
p-cover.xhtml         : 1.表紙
p-fmatter-001.xhtml   : 2.frontmatter
p-titlepage.xhtml     : 3.本扉
p-caution.xhtml       : 4.注意書き
p-toc.xhtml           : 5.目次見出し
p-001.xhtml           : 6.本文
p-002.xhtml           : 6.本文
本文はchapterの数だけ繰り返し
p-colophon.xhtml      : 7.奥付
p-ad-001.xhtml        : 8.広告
p-backcover.xhtml     : 9.表紙
```

* プログラムについて
  * pythonスクリプトは適宜lib化して保守性が良くなるようなプログラム構造としてください。
