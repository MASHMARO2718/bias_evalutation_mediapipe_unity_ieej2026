# 電気学会 和文論文（Overleaf）

1. **新規プロジェクト** → **プロジェクトをアップロード** で、このフォルダ全体（`IEEJ_ja`）を ZIP 化してアップロードするか、同じ構成でファイルを置く：
   - `main.tex`（これをコンパイル）
   - `ieej.cls`
   - `figs/`（図一式）
   - `a1.pdf`, `a2.pdf`, `a3.pdf`（著者顔写真。**`main.tex` と同じ階層**。**PDF** — `ieej.cls` は pdfLaTeX/LuaLaTeX では `.png` ではなく `.pdf` を参照する）

2. **メニュー → コンパイラ → LuaLaTeX**

3. **`main.tex`** を開いて **Recompile**。

4. 投稿前に `\FIELD{}`、`\YEAR{}`、`\NO{}` を記入し、必要なら `\received` / `\revised` のコメントを外す。

5. **従来稿**（`article` + XeLaTeX 用）: `main_legacy_article.tex` — IEEJ 提出用のコンパイル対象ではない。

6. 図と著者 PDF: `paper/source/` で **`python prepare_ieej_overleaf.py`** を実行 — 親の `figs/` をこのフォルダにコピーし、`a1.pdf`～`a3.pdf` を再生成する（`\profile` の並び順）。

7. リポジトリから `main.tex` を再生成する場合:  
   `python paper/source/build_ieej_mains.py`（`IEEJ_en` / `IEEJ_ja` の両方を更新）
