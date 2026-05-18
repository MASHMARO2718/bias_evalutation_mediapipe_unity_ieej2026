#!/usr/bin/env python3
"""
パイプライン出力のCSV・記録を削除（synced_joint_positions.csv は保持）

実行: python clean_pipeline_outputs.py
"""
from pathlib import Path

ROOT = Path(__file__).parent

# 削除対象ディレクトリ（パイプライン出力）
CLEAN_DIRS = [
    ROOT / "02_mediapipe_processed" / "Y=0.5",
    ROOT / "02_mediapipe_processed" / "Y=1.0",
    ROOT / "02_mediapipe_processed" / "Y=1.5",
    ROOT / "02_mediapipe_processed" / "Y=2.0",
    ROOT / "03_joint_angle_mae" / "Y=0.5",
    ROOT / "03_joint_angle_mae" / "Y=1.0",
    ROOT / "03_joint_angle_mae" / "Y=1.5",
    ROOT / "03_joint_angle_mae" / "Y=2.0",
    ROOT / "04_max_angle_error" / "calculation" / "Y=0.5",
    ROOT / "04_max_angle_error" / "calculation" / "Y=1.0",
    ROOT / "04_max_angle_error" / "calculation" / "Y=1.5",
    ROOT / "04_max_angle_error" / "calculation" / "Y=2.0",
    ROOT / "04_max_angle_error" / "max_angle_error_heatmap" / "Y=0.5",
    ROOT / "04_max_angle_error" / "max_angle_error_heatmap" / "Y=1.0",
    ROOT / "04_max_angle_error" / "max_angle_error_heatmap" / "Y=1.5",
    ROOT / "04_max_angle_error" / "max_angle_error_heatmap" / "Y=2.0",
    ROOT / "05_direction_detection" / "output",
    ROOT / "06_theta_verification" / "output",
    ROOT / "06_theta_verification" / "coordinate_fix_verification" / "output",
]

# 絶対に削除しないファイル名
KEEP = {"synced_joint_positions.csv"}


def main():
    deleted = []
    for d in CLEAN_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.csv"):
            if f.name in KEEP:
                print(f"保持: {f.relative_to(ROOT)}")
                continue
            f.unlink()
            deleted.append(f.relative_to(ROOT))
            print(f"削除: {f.relative_to(ROOT)}")

    # 02_mediapipe_processed 直下のCSV（Y= 以外）
    mp_root = ROOT / "02_mediapipe_processed"
    if mp_root.exists():
        for f in mp_root.glob("*.csv"):
            if f.name in KEEP:
                continue
            f.unlink()
            deleted.append(f.relative_to(ROOT))
            print(f"削除: {f.relative_to(ROOT)}")

    # 03_joint_angle_mae 直下（統合 CSV 等）
    cal_mae = ROOT / "03_joint_angle_mae"
    if cal_mae.exists():
        for f in cal_mae.glob("*.csv"):
            if f.name in KEEP:
                continue
            f.unlink()
            deleted.append(f.relative_to(ROOT))
            print(f"削除: {f.relative_to(ROOT)}")

    print(f"\n完了: {len(deleted)} ファイル削除")
    print("synced_joint_positions.csv は保持済み")


if __name__ == "__main__":
    main()
