"""
Y軸反転の検証: MediaPipe の Y を反転した場合の delta_theta/psi の変化を確認

既存の detailed_results.csv を読み、mp_y を -mp_y に変えて再計算し、
joint_summary を比較する。
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent.parent.parent
DETAILED_CSV = BASE / "06_direction_detection" / "output" / "processed_data" / "detailed_results.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 同フォルダの coordinate_transform_copy を import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from coordinate_transform_copy import compute_delta_theta_psi


def main():
    if not DETAILED_CSV.exists():
        print(f"[ERROR] Not found: {DETAILED_CSV}")
        return 1

    df = pd.read_csv(DETAILED_CSV)

    # HIP を除外
    df_no_hip = df[~df["joint"].str.contains("HIP")].copy()

    # オリジナル（既存の delta_theta_deg, delta_psi_deg）と Y-flip 版を比較
    results = []
    for _, row in df_no_hip.iterrows():
        delta_orig_theta = row["delta_theta_deg"]
        delta_orig_psi = row["delta_psi_deg"]

        delta_new_theta, delta_new_psi = compute_delta_theta_psi(
            row["gt_x"], row["gt_y"], row["gt_z"],
            row["mp_x"], row["mp_y"], row["mp_z"],
            mp_y_flip=True,
        )
        results.append({
            "frame_id": row["frame_id"],
            "camera": row["camera"],
            "joint": row["joint"],
            "delta_theta_orig": delta_orig_theta,
            "delta_theta_yflip": delta_new_theta,
            "delta_psi_orig": delta_orig_psi,
            "delta_psi_yflip": delta_new_psi,
        })

    df_result = pd.DataFrame(results)

    # 関節ごとのサマリ（joint_summary 相当）
    joint_summary_orig = df_result.groupby("joint").agg(
        theta_mean_orig=("delta_theta_orig", "mean"),
        theta_std_orig=("delta_theta_orig", "std"),
        theta_abs_mean_orig=("delta_theta_orig", lambda x: x.abs().mean()),
        psi_mean_orig=("delta_psi_orig", "mean"),
        psi_abs_mean_orig=("delta_psi_orig", lambda x: x.abs().mean()),
    ).reset_index()

    joint_summary_yflip = df_result.groupby("joint").agg(
        theta_mean_yflip=("delta_theta_yflip", "mean"),
        theta_std_yflip=("delta_theta_yflip", "std"),
        theta_abs_mean_yflip=("delta_theta_yflip", lambda x: x.abs().mean()),
        psi_mean_yflip=("delta_psi_yflip", "mean"),
        psi_abs_mean_yflip=("delta_psi_yflip", lambda x: x.abs().mean()),
    ).reset_index()

    joint_compare = joint_summary_orig.merge(
        joint_summary_yflip, on="joint"
    )

    out_csv = OUTPUT_DIR / "y_flip_joint_comparison.csv"
    joint_compare.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {out_csv}")

    # 肘の比較
    print("\n=== Elbow: Original vs Y-flip ===")
    for joint in ["LEFT_ELBOW", "RIGHT_ELBOW"]:
        row = joint_compare[joint_compare["joint"] == joint].iloc[0]
        print(f"\n{joint}:")
        print(f"  Original: theta_mean={row['theta_mean_orig']:.2f}, |theta|_mean={row['theta_abs_mean_orig']:.2f} deg")
        print(f"  Y-flip:   theta_mean={row['theta_mean_yflip']:.2f}, |theta|_mean={row['theta_abs_mean_yflip']:.2f} deg")
        print(f"  Change:   theta_mean {row['theta_mean_orig']:.1f} -> {row['theta_mean_yflip']:.1f}")

    print("\n=== Full joint comparison ===")
    print(joint_compare.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
