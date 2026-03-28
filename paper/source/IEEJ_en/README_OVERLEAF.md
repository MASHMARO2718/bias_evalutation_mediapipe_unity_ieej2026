# IEEJ English paper (Overleaf)

1. Create a **New Project** → **Upload Project** and zip **this entire folder** (`IEEJ_en`), or upload files keeping this structure:
   - `main.tex` (compile this)
   - `ieej-e.cls`
   - `figs/` (all figures)
   - `a1.pdf`, `a2.pdf`, `a3.pdf` (author portraits; **same folder as `main.tex`**, **PDF** — the IEEJ class does **not** use `.png` here under pdfLaTeX)

2. **Menu → Compiler → pdfLaTeX**

3. Open **`main.tex`** and click **Recompile**.

4. Before submission, fill in `\FIELD{}`, `\YEAR{}`, `\NO{}` and uncomment `\received` / `\revised` if required.

5. **Legacy draft** (previous `article` class): `main_legacy_article.tex` — not used for IEEJ output.

6. Author photos + figures: from `paper/source/`, run **`python prepare_ieej_overleaf.py`** — copies canonical `figs/` into this folder and rebuilds **`a1.pdf`–`a3.pdf`** (same order as `\profile` in `\begin{biography}`).

7. Regenerating `main.tex` from the repo root:  
   `python paper/source/build_ieej_mains.py` (updates both `IEEJ_en` and `IEEJ_ja`).
