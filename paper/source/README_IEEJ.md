# 電気学会 IEEJ LaTeX（Overleaf 用フォルダ）

| フォルダ | クラス | コンパイラ | 用途 |
|----------|--------|------------|------|
| [IEEJ_en/](IEEJ_en/) | `ieej-e.cls` | **pdfLaTeX** | 英文稿 |
| [IEEJ_ja/](IEEJ_ja/) | `ieej.cls` | **LuaLaTeX** | 和文稿 |

各フォルダを **ZIP ごと Overleaf にアップロード**すれば、`main.tex` をコンパイルできる構成です。

- **アップロード前**（`figs/` と著者 `a*.pdf` を親の `figs/` と同期）:  
  `python prepare_ieej_overleaf.py`（このディレクトリで実行）
- 詳細手順: 各フォルダ内 `README_OVERLEAF.md`
- `main.tex` の再生成: `python build_ieej_mains.py`
- 従来の `article` 版は各フォルダの `main_legacy_article.tex` に保存
