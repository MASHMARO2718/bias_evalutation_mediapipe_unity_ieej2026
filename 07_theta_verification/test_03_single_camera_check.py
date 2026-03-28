"""
テスト03: 単一カメラに絞ったときの joint_summary 相当

仮説: 全カメラ平均で 121° でも、単一カメラなら異なる値になる可能性
      1 台のカメラだけで見たときの肘 Δθ 平均を計算
"""

import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DETAILED_CSV = BASE / "06_direction_detection" / "output" / "processed_data" / "detailed_results.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    if not DETAILED_CSV.exists():
        print(f"[ERROR] 見つかりません: {DETAILED_CSV}")
        return 1

    df = pd.read_csv(DETAILED_CSV)
    elbows = df[df["joint"].isin(["LEFT_ELBOW", "RIGHT_ELBOW"])]

    # 全カメラ統合（joint_summary 相当）
    global_stats = elbows.groupby("joint").agg(
        theta_mean=("delta_theta_deg", "mean"),
        theta_std=("delta_theta_deg", "std"),
        theta_abs_mean=("delta_theta_deg", lambda x: x.abs().mean()),
    ).round(2)
    print("=== All cameras (joint_summary equiv) ===")
    print(global_stats)
    print()

    # 単一カメラごと
    single_cam = elbows.groupby(["camera", "joint"]).agg(
        theta_mean=("delta_theta_deg", "mean"),
        theta_std=("delta_theta_deg", "std"),
        count=("frame_id", "count"),
    ).reset_index()

    # 代表カメラ数台を表示
    cameras = single_cam["camera"].unique()[:5]
    print("=== Sample 5 cameras: elbow delta_theta mean ===")
    for cam in cameras:
        sub = single_cam[single_cam["camera"] == cam]
        left = sub[sub["joint"] == "LEFT_ELBOW"]
        right = sub[sub["joint"] == "RIGHT_ELBOW"]
        lv = left["theta_mean"].values[0] if len(left) else 0
        rv = right["theta_mean"].values[0] if len(right) else 0
        print(f"  {cam}: LEFT={lv:+.1f}, RIGHT={rv:+.1f} deg")

    # 全単一カメラの theta_mean 分布
    left_means = single_cam[single_cam["joint"] == "LEFT_ELBOW"]["theta_mean"]
    right_means = single_cam[single_cam["joint"] == "RIGHT_ELBOW"]["theta_mean"]
    print(f"\nSingle-cam LEFT_ELBOW theta_mean:  min={left_means.min():.1f}, max={left_means.max():.1f}, std={left_means.std():.1f} deg")
    print(f"Single-cam RIGHT_ELBOW theta_mean: min={right_means.min():.1f}, max={right_means.max():.1f}, std={right_means.std():.1f} deg")

    out_csv = OUTPUT_DIR / "elbow_theta_by_single_camera.csv"
    single_cam.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n[SAVE] {out_csv}")


if __name__ == "__main__":
    sys.exit(main() or 0)
