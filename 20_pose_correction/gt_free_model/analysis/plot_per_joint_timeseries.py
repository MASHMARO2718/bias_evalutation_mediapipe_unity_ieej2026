#!/usr/bin/env python3
"""
関節ごとの角度時系列プロット（検証カメラ）

各関節 1 枚: 横軸フレーム、縦軸に
  - GT 角度
  - MediaPipe 処理直後（擬似ワールド構成のみ、フィルタ・補正なし）
  - GT フリー補正後（中央値/MAD + カルマン + カンニングペーパー）

出力: 20_pose_correction/gt_free_model/per_joint/val_<JOINT>.png
"""

import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import run_gt_free_model as M

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "gt_free_model" / "per_joint"

CALIB_MP = BASE / "mediapipe_processed_csv/Y=1.0/CapturedFrames_3.0_1.0_0.0.csv"
CALIB_GT = BASE.parent / "10_input_videos/CapturedFrames_3.0_1.0_0.0/gt_joints.csv"
VAL_MP = BASE / "mediapipe_processed_csv_additional/Y=0.5/CapturedFrames_3.2_1.1_0.4.csv"
VAL_GT = (BASE.parent
          / "10_input_videos/aditional__test_data/CapturedFrames_3.2_1.1_0.4/gt_joints.csv")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cheat, _ = M.calibrate(CALIB_MP, CALIB_GT, (3.0, 1.0, 0.0))
    val = M.validate(VAL_MP, VAL_GT, (3.2, 1.1, 0.4), cheat)

    grid = val["grid"]
    for name in M.ANGLE_DEFS_MP:
        gt = val["ang_gt"][name]
        raw = val["ang_raw"][name]
        corr = val["ang_corr"][name]
        mae_raw = float(np.nanmean(np.abs(raw - gt)))
        mae_corr = float(np.nanmean(np.abs(corr - gt)))

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(grid, gt, "k-", lw=2.2, label="GT")
        ax.plot(grid, raw, color="#7f8c8d", lw=1.3, alpha=0.9,
                label=f"MediaPipe raw (MAE {mae_raw:.1f}°)")
        ax.plot(grid, corr, color="#c0392b", lw=1.8,
                label=f"corrected (MAE {mae_corr:.1f}°)")
        ax.set_xlabel("frame")
        ax.set_ylabel("angle [deg]")
        ax.set_title(f"{name} — validation camera (3.2, 1.1, 0.4), "
                     f"cheat sheet from (3.0, 1.0, 0.0)")
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        path = OUT / f"val_{name}.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        print(f"saved: {path}  (raw {mae_raw:.1f} -> corrected {mae_corr:.1f} deg)")


if __name__ == "__main__":
    main()
