"""Sync canonical source/figs into IEEJ_en/figs and IEEJ_ja/figs; rebuild a1–a3.pdf.

Run from paper/source/ before zipping IEEJ_* folders for Overleaf:
  python prepare_ieej_overleaf.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
FIGS = ROOT / "figs"
BIO = [
    ("bio_taira.jpg", 1),
    ("bio_kato.jpg", 2),
    ("bio_afuso.jpg", 3),
]


def copy_figs() -> None:
    for sub in ("IEEJ_en", "IEEJ_ja"):
        dest = ROOT / sub / "figs"
        dest.mkdir(parents=True, exist_ok=True)
        for f in FIGS.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
        print(f"copied figs/ -> {sub}/figs/ ({len(list(dest.iterdir()))} files)")


def write_portrait_pdfs() -> None:
    for sub in ("IEEJ_en", "IEEJ_ja"):
        out_dir = ROOT / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        for jpg_name, n in BIO:
            src = FIGS / jpg_name
            dst = out_dir / f"a{n}.pdf"
            im = Image.open(src).convert("RGB")
            im.save(dst, "PDF", resolution=150.0)
            print(f"wrote {dst.relative_to(ROOT)}")


def main() -> None:
    if not FIGS.is_dir():
        raise SystemExit(f"missing {FIGS}")
    copy_figs()
    write_portrait_pdfs()


if __name__ == "__main__":
    main()
