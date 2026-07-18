#!/usr/bin/env python3
"""
scripts/rebuild_batch_summary.py
================================
output/<v1|v2>/CapturedFrames_*/ に保存済みの角度時系列 CSV から
batch_summary.csv（camera × joint のラグ・MAE 一覧）を再構築する。

batch_angle_timeseries.py を分割実行した際にサマリが部分上書き
された場合の復旧用。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import plot_angle_timeseries as pats

JOINTS = list(pats.JOINT_DEFS.keys())


def main() -> int:
    base_out = pats.OUT_DIR
    rows = []
    cam_dirs = sorted(d for d in base_out.glob("CapturedFrames_*") if d.is_dir())
    print(f"Camera folders: {len(cam_dirs)}  ({base_out})")

    for cam_dir in cam_dirs:
        camera = cam_dir.name
        for joint in JOINTS:
            matches = list(cam_dir.glob(f"angle_timeseries_{joint}_*.csv"))
            if not matches:
                rows.append({"camera": camera, "joint": joint, "status": "no_data",
                             "lag": np.nan, "mae_raw": np.nan, "mae_corr": np.nan})
                continue
            df = pd.read_csv(matches[0])
            gt = df["gt"].to_numpy()
            mp = df["mp"].to_numpy()
            corr = df["corr"].to_numpy() if "corr" in df.columns else mp
            lag, _ = pats.best_lag(gt, mp)
            rows.append({
                "camera": camera, "joint": joint, "status": "ok", "lag": lag,
                "mae_raw": np.nanmean(np.abs(mp - gt)),
                "mae_corr": np.nanmean(np.abs(corr - gt)),
            })

    summary = pd.DataFrame(rows)
    out_path = base_out / "batch_summary.csv"
    summary.to_csv(out_path, index=False)

    ok = summary[summary["status"] == "ok"]
    print(f"Saved: {out_path}")
    print(f"  rows total={len(summary)}  ok={len(ok)}  no_data={len(summary) - len(ok)}")
    if len(ok):
        print(f"  lag mean={ok['lag'].mean():+.2f}  median={ok['lag'].median():+.0f}  "
              f"|lag|<=2: {(ok['lag'].abs() <= 2).mean() * 100:.1f}%")
        print(f"  MAE raw={ok['mae_raw'].mean():.2f}  corr={ok['mae_corr'].mean():.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
