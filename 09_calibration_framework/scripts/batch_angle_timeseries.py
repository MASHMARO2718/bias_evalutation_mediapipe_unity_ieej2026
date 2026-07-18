#!/usr/bin/env python3
"""
scripts/batch_angle_timeseries.py
=================================
全カメラ × 全関節の角度時系列グラフを一括生成し、
カメラ座標ごとのサブフォルダに出力する。

出力構成:
    scripts/output/<v1|v2|v3>/CapturedFrames_<X>_<Y>_<Z>/
        angle_timeseries_<joint>_<camera>.png
        angle_timeseries_<joint>_<camera>.csv
    scripts/output/<v1|v2|v3>/batch_summary.csv

使い方:
    python scripts/batch_angle_timeseries.py
    python scripts/batch_angle_timeseries.py --joints L_Elbow R_Elbow
    python scripts/batch_angle_timeseries.py --overwrite
    # v3: 横軸 0–120 固定（読み込みは DATASET_VERSION=v2 のまま）
    python scripts/batch_angle_timeseries.py --output-version v3 --frame-xlim 0 120 --overwrite
"""

import sys
import math
import time
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import plot_angle_timeseries as pats  # 既存の関数・設定を再利用


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--joints", nargs="+", default=list(pats.JOINT_DEFS.keys()),
                        help="対象関節（デフォルト: 全8関節）")
    parser.add_argument("--overwrite", action="store_true",
                        help="既存フォルダも再生成（デフォルトはスキップ）")
    parser.add_argument("--n_az", type=int, default=8)
    parser.add_argument("--output-version", default=None,
                        help="出力サブフォルダ (例: v3)。未指定時は DATASET_VERSION")
    parser.add_argument("--frame-xlim", nargs=2, type=int, default=None,
                        metavar=("LO", "HI"),
                        help="横軸固定範囲 (例: --frame-xlim 0 120)")
    args = parser.parse_args()

    if args.output_version:
        pats.set_output_version(args.output_version)
    if args.frame_xlim:
        pats.set_frame_xlim((args.frame_xlim[0], args.frame_xlim[1]))

    base_out = pats.OUT_DIR
    mp_base = Path(pats.root_config.MP_DIR)

    # 全カメラを列挙（Y=* フォルダ配下の CSV）
    cameras = []
    for ydir in sorted(mp_base.glob("Y=*")):
        height = float(ydir.name.split("=")[1])
        for csv in sorted(ydir.glob("CapturedFrames_*.csv")):
            cameras.append((csv.stem, height))

    print(f"DATASET_VERSION = {pats._ds}")
    print(f"OUTPUT_VERSION  = {pats.OUTPUT_VERSION}")
    print(f"FRAME_XLIM      = {pats.FRAME_XLIM}")
    print(f"Cameras: {len(cameras)} / Joints: {args.joints}")
    print(f"Output : {base_out}")

    summary_rows = []
    n_done, n_skip, n_fail = 0, 0, 0
    t0 = time.time()
    frame_xlim = pats.FRAME_XLIM

    for idx, (camera, height) in enumerate(cameras, 1):
        cam_dir = base_out / camera
        expected = [cam_dir / f"angle_timeseries_{j}_{camera.replace('.', '').replace('-', 'm')}.png"
                    for j in args.joints]
        if not args.overwrite and cam_dir.exists() and all(p.exists() for p in expected):
            n_skip += 1
            continue

        try:
            cx, cy, cz = pats.parse_camera_pos(camera)
            az_deg = math.degrees(math.atan2(cx, cz))
            h_bin = pats.height_bin(cy)
            az_bin = pats.azimuth_bin(az_deg, args.n_az)

            mp_df = pats.load_mp(camera, height)
            gt_df = pats.load_gt(camera)

            cam_dir.mkdir(parents=True, exist_ok=True)
            pats.OUT_DIR = cam_dir  # plot_pair の保存先を切り替え

            for joint in args.joints:
                angles_df = pats.compute_angles(mp_df, gt_df, joint)
                if angles_df.empty or angles_df["mp"].notna().sum() < 5:
                    summary_rows.append({
                        "camera": camera, "joint": joint, "status": "no_data",
                        "lag": np.nan, "mae_raw": np.nan, "mae_corr": np.nan,
                    })
                    continue

                lag, _ = pats.best_lag(
                    angles_df["gt"].to_numpy(), angles_df["mp"].to_numpy()
                )
                angles_df["corr"] = pats.apply_correction(angles_df, joint, h_bin, az_bin)
                pats.plot_pair(
                    angles_df, joint, camera, h_bin, az_bin, az_deg,
                    lag=lag, frame_xlim=frame_xlim,
                )

                both = angles_df["mp"].notna() & angles_df["gt"].notna()
                gt = angles_df.loc[both, "gt"].to_numpy()
                mp = angles_df.loc[both, "mp"].to_numpy()
                corr = angles_df.loc[both, "corr"].to_numpy()
                summary_rows.append({
                    "camera": camera, "joint": joint, "status": "ok", "lag": lag,
                    "mae_raw": float(np.nanmean(np.abs(mp - gt))) if len(gt) else np.nan,
                    "mae_corr": float(np.nanmean(np.abs(corr - gt))) if len(gt) else np.nan,
                })
            n_done += 1
        except Exception as e:
            n_fail += 1
            print(f"[FAIL] {camera}: {e}", flush=True)
        finally:
            pats.OUT_DIR = base_out

        if idx % 20 == 0 or idx == len(cameras):
            elapsed = time.time() - t0
            print(f"[{idx}/{len(cameras)}] done={n_done} skip={n_skip} fail={n_fail} "
                  f"({elapsed:.0f}s)", flush=True)

    # サマリ CSV
    if summary_rows:
        summary = pd.DataFrame(summary_rows)
        summary_path = base_out / "batch_summary.csv"
        summary.to_csv(summary_path, index=False)
        print(f"\nSummary saved: {summary_path}")
        ok = summary[summary["status"] == "ok"]
        if len(ok):
            print(f"  plots: {len(ok)}")
            print(f"  lag mean={ok['lag'].mean():+.2f}  median={ok['lag'].median():+.0f}  "
                  f"|lag|<=2: {(ok['lag'].abs() <= 2).mean() * 100:.1f}%")

    print(f"\nAll done: cameras done={n_done} skip={n_skip} fail={n_fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
