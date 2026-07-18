#!/usr/bin/env python3
"""
scripts/dump_paper_stats.py
===========================
論文（IEEJ_02）用の数値を v2 データから一括算出してコンソールに出力する。
- グローバル多項式フィット R2（1/2/4 次）
- 中央分割多項式フィット R2（左右 x 2/4 次）
- 局所線形 R2 の関節別統計
- 高さ層別 MAE
- モデル別補正結果（evaluation_results_az8.csv 集計）
- 符号付き補正結果 / λ 感度 / R2 vs 補正効果
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins

RESULTS = HERE / "outputs" / "results"
JOINTS = ["L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow",
          "L_Hip", "R_Hip", "L_Knee", "R_Knee"]


def r2(y, yp):
    ss_res = np.sum((y - yp) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - ss_res / (ss_tot + 1e-12))


def main():
    df = apply_all_bins(load_angle_mae_all_layers(), n_azimuth=8)
    print(f"angle MAE rows: {len(df)}")

    x_all = df["azimuth_deg"].to_numpy()

    print("\n=== Global polynomial R2 (deg 1/2/4) ===")
    for j in JOINTS:
        y = df[j].to_numpy()
        v = np.isfinite(x_all) & np.isfinite(y)
        xs, ys = x_all[v], y[v]
        vals = []
        for d in (1, 2, 4):
            c = np.polyfit(xs, ys, d)
            vals.append(r2(ys, np.polyval(c, xs)))
        print(f"  {j:12s} {vals[0]:.3f} {vals[1]:.3f} {vals[2]:.3f}")

    print("\n=== Split polynomial R2 (left/right x deg 2/4) ===")
    for j in JOINTS:
        y = df[j].to_numpy()
        v = np.isfinite(x_all) & np.isfinite(y)
        xs, ys = x_all[v], y[v]
        mid = (xs.min() + xs.max()) / 2
        row = []
        for mask in (xs < mid, xs >= mid):
            for d in (2, 4):
                c = np.polyfit(xs[mask], ys[mask], d)
                row.append(r2(ys[mask], np.polyval(c, xs[mask])))
        print(f"  {j:12s} L2={row[0]:.3f} L4={row[1]:.3f} R2deg2={row[2]:.3f} R2deg4={row[3]:.3f}")

    print("\n=== Local linear R2 per joint (az8) ===")
    loc = pd.read_csv(RESULTS / "local_linear_fits_az8.csv")
    g = loc.groupby("joint")["r2"].agg(["mean", "min", "max", "count"])
    print(g.round(3).to_string())
    print(f"  Overall mean={loc['r2'].mean():.3f} min={loc['r2'].min():.3f} "
          f"max={loc['r2'].max():.3f} n={len(loc)}")
    low = loc[loc["r2"] < 0.7]
    print(f"  R2<0.7: {len(low)}/{len(loc)} ({len(low)/len(loc)*100:.1f}%)")
    if "n" in loc.columns:
        print(f"  n mean (R2<0.7): {low['n'].mean():.1f}  (R2>=0.7): {loc[loc['r2']>=0.7]['n'].mean():.1f}")

    print("\n=== Layer-wise raw MAE ===")
    for layer, grp in df.groupby("height_label"):
        print(f"  {layer}: {grp[JOINTS].mean(axis=1).mean():.2f}  (cameras={len(grp)})")
    print(f"  cameras total: {len(df)}")

    print("\n=== Model 2-5 improvements (mean over joints) ===")
    ev = pd.read_csv(RESULTS / "evaluation_results_az8.csv")
    piv = ev.groupby(["model", "split"])[["raw_mae", "corr_mae", "improvement_pct"]].mean()
    print(piv.round(2).to_string())

    print("\n=== Signed bias results ===")
    print(pd.read_csv(RESULTS / "signed_bias_results.csv").round(2).to_string(index=False))

    print("\n=== Signed per joint ===")
    print(pd.read_csv(RESULTS / "signed_bias_per_joint.csv").round(2).to_string(index=False))

    print("\n=== Lambda sensitivity ===")
    print(pd.read_csv(RESULTS / "lambda_sensitivity.csv").round(2).to_string(index=False))

    print("\n=== r2 vs correction ===")
    rc = pd.read_csv(RESULTS / "r2_vs_correction.csv")
    v = rc[["r2", "improvement"]].dropna()
    r = np.corrcoef(v["r2"], v["improvement"])[0, 1]
    print(f"  Pearson r = {r:.3f}  (n={len(v)})")
    hi = v[v["r2"] >= 0.7]["improvement"].mean()
    lo = v[v["r2"] < 0.7]["improvement"].mean()
    print(f"  mean improvement: R2>=0.7 {hi:.1f}%  R2<0.7 {lo:.1f}%")

    print("\n=== Model 6 ===")
    print(pd.read_csv(RESULTS / "model6_results.csv").round(3).to_string(index=False))

    print("\n=== Failure analysis csv head ===")
    fa = pd.read_csv(RESULTS / "failure_analysis.csv")
    print(fa.head(10).to_string(index=False))
    print(f"  rows={len(fa)}  cols={fa.columns.tolist()}")


if __name__ == "__main__":
    main()
