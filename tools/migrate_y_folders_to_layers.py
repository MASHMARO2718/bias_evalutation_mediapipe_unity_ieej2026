#!/usr/bin/env python3
"""
旧レイアウト（02: Y=0.5,1.5 / Y=1.0.2.0、03 MAE: 同様）から
カメラ高さごとの Y=0.5, Y=1.0, Y=1.5, Y=2.0 フォルダへ移行する。

使用例（リポジトリルートで）:
  python tools/migrate_y_folders_to_layers.py --dry-run
  python tools/migrate_y_folders_to_layers.py

02: CapturedFrames_X_Y_Z.csv をファイル名の Y に応じて Y=<y>/ へ移動。
03: coordinate_angle_mae.csv が旧フォルダにあれば camera_y 列で行を分割して書き出し。
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
LAYERS = [0.5, 1.0, 1.5, 2.0]
OLD_MP_BUCKETS = ["Y=0.5,1.5", "Y=1.0.2.0"]
OLD_MAE_BUCKETS = ["Y=0.5,1.5", "Y=1.0.2.0"]


def layer_dir_name(y: float) -> str:
    return f"Y={y}"


def parse_captured_y(stem: str) -> float | None:
    m = re.match(r"CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)", stem)
    if not m:
        return None
    y = float(m.group(2))
    for allowed in LAYERS:
        if abs(y - allowed) < 1e-6:
            return allowed
    return None


def migrate_02_mp(dry: bool) -> int:
    mp_root = REPO / "02_mediapipe_processed"
    moved = 0
    for bucket in OLD_MP_BUCKETS:
        src = mp_root / bucket
        if not src.is_dir():
            continue
        for f in list(src.glob("CapturedFrames_*.csv")):
            y = parse_captured_y(f.stem)
            if y is None:
                print(f"  skip (unknown y): {f.name}")
                continue
            dst_dir = mp_root / layer_dir_name(y)
            dst = dst_dir / f.name
            if dst.exists():
                print(f"  exists, skip: {dst}")
                continue
            print(f"  {f.relative_to(REPO)} -> {dst.relative_to(REPO)}")
            if not dry:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dst))
            moved += 1
    return moved


def migrate_03_mae(dry: bool) -> int:
    mae_root = REPO / "03_joint_angle_mae"
    written = 0
    for bucket in OLD_MAE_BUCKETS:
        src_csv = mae_root / bucket / "coordinate_angle_mae.csv"
        if not src_csv.is_file():
            continue
        df = pd.read_csv(src_csv)
        if "camera_y" not in df.columns:
            print(f"  no camera_y column: {src_csv}")
            continue
        for y in LAYERS:
            sub = df[df["camera_y"].astype(float).sub(y).abs() < 0.05]
            if sub.empty:
                continue
            dst_dir = mae_root / layer_dir_name(y)
            dst = dst_dir / "coordinate_angle_mae.csv"
            print(f"  {src_csv.name} Y={y} ({len(sub)} rows) -> {dst.relative_to(REPO)}")
            if not dry:
                dst_dir.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    existing = pd.read_csv(dst)
                    sub = pd.concat([existing, sub], ignore_index=True)
                sub.to_csv(dst, index=False)
            written += 1
    return written


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("=== 02_mediapipe_processed ===")
    n = migrate_02_mp(args.dry_run)
    print(f"moved files: {n}")

    print("=== 03_joint_angle_mae (coordinate_angle_mae.csv) ===")
    n2 = migrate_03_mae(args.dry_run)
    print(f"layer writes: {n2}")

    if args.dry_run:
        print("\n(dry-run: no changes written)")
    else:
        mp_root = REPO / "02_mediapipe_processed"
        for bucket in OLD_MP_BUCKETS:
            p = mp_root / bucket
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
                print(f"removed empty bucket: {p.relative_to(REPO)}")
            elif p.is_dir():
                print(f"note: {p.relative_to(REPO)} still has files — remove or re-run after clearing")


if __name__ == "__main__":
    main()
