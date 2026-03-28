# 論文（LaTeX・データ）

## コンパイルの正

| 用途 | パス | コンパイラ |
|------|------|-------------|
| 査読稿・IEEE Access 想定（英語・twocolumn article） | `source/main.tex` | pdfLaTeX |
| 日本語ドラフト | `source/main_ja.tex` | XeLaTeX |
| 電気学会 英文 | `source/IEEJ_en/` | pdfLaTeX（`README_OVERLEAF.md`） |
| 電気学会 和文 | `source/IEEJ_ja/` | LuaLaTeX（`README_OVERLEAF.md`） |

図の**単一の原本**は `source/figs/`。本文はすべて `figs/...` を参照する。

## IEEJ フォルダを Overleaf に出す前に

`source/` で:

```bash
python prepare_ieej_overleaf.py
python build_ieej_mains.py   # main.tex をルート原稿から再生成するとき
```

## その他

- `notes/` … エージェント向け指示・検証メモ（旧 `07_paper` 相当の文脈はここに集約）
- `assets/` … 生成図のアーカイブ（`source/figs` と重複しうるが参照用に保持）
- `submitted/` … 提出済み PDF
- `original_paper.md`, `paper.md`, `paper_en.md` … 元の4ページ稿・日本語・英語ソース
