#!/usr/bin/env python3
"""(3,1,0): 膝の X 成分誤差の時系列 + 右側周辺ヒストグラム(L/R 上下2段・1枚)。"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "2_pose"))
sys.path.insert(0, str(REPO))

from run_uv_pseudo_world_correction import (
    build_pseudo_world, travel_direction, filter_joint, fit_alignment,
    hip_center, EFFECTIVE_TORSO_2D_M,
)
from run_error_mc_analysis import extract_gt_coords, MP_BASE, INPUT_DIR
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv

CAM = "CapturedFrames_3.0_1.0_0.0"
WINDOW, K = 7, 5.0

mp_df = pd.read_csv(next(MP_BASE.glob(f"Y=*/{CAM}.csv")))
gt_df = load_gt_csv(find_gt_csv_for_camera(CAM, INPUT_DIR))

fids, P, scale, _ = build_pseudo_world(mp_df, EFFECTIVE_TORSO_2D_M, False, torso_2d=True)
d_hat = travel_direction(fids, P)

# 位置合わせ(腰中心軌跡)
hip_fids = [f for f in fids if "LEFT_HIP" in P[f] and "RIGHT_HIP" in P[f]]
ps_hipc, gt_hipc = [], []
for f in hip_fids:
    g = hip_center(extract_gt_coords(gt_df, f))
    if g is None:
        continue
    ps_hipc.append(0.5 * (P[f]["LEFT_HIP"] + P[f]["RIGHT_HIP"]))
    gt_hipc.append(g)
A, t, _, _ = fit_alignment(np.stack(ps_hipc), np.stack(gt_hipc))

fig, axes = plt.subplots(
    2, 2, figsize=(11, 7), sharex="col",
    gridspec_kw={"width_ratios": [4, 1], "wspace": 0.04, "hspace": 0.15},
)

for row, (joint, color) in enumerate([("LEFT_KNEE", "#2980b9"),
                                      ("RIGHT_KNEE", "#27ae60")]):
    lm_fids = [f for f in fids if joint in P[f]]
    pos = np.stack([P[f][joint] for f in lm_fids])
    res = filter_joint(pos, d_hat, WINDOW, K, robust=True)
    corr_w = res["pos_corr"] @ A.T + t

    ex, fr, rep = [], [], []
    for i, f in enumerate(lm_fids):
        g = extract_gt_coords(gt_df, f).get(joint)
        if g is None:
            continue
        ex.append(corr_w[i, 0] - g[0])   # X 成分の符号付き誤差
        fr.append(f)
        rep.append(bool(res["replaced"][i]))
    ex = np.array(ex); fr = np.array(fr); rep = np.array(rep)

    ax, axh = axes[row]
    ax.axhline(0, color="#2c3e50", lw=1.0)
    ax.plot(fr, ex, "-", color=color, lw=1.5)
    ax.scatter(fr[rep], ex[rep], s=26, color="#e74c3c", zorder=5,
               edgecolors="white", linewidths=0.5, label="replaced")
    ax.axhline(ex.mean(), color=color, lw=1.0, ls="--", alpha=0.7)
    ax.set_ylabel(f"{joint}\nX error [m]  (MP corr − GT)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    ax.text(0.02, 0.95, f"mean {ex.mean():+.3f} m,  std {ex.std():.3f} m",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(fc="white", ec="none", alpha=0.7))

    # 右側: 縦軸共有の周辺ヒストグラム
    axh.hist(ex, bins=25, orientation="horizontal", color=color, alpha=0.65)
    axh.axhline(0, color="#2c3e50", lw=1.0)
    axh.axhline(ex.mean(), color=color, lw=1.0, ls="--", alpha=0.7)
    axh.sharey(ax)
    axh.tick_params(labelleft=False)
    axh.set_xlabel("count", fontsize=8)
    axh.grid(alpha=0.3)

axes[1, 0].set_xlabel("Frame")
fig.suptitle(f"{CAM} · knee X-component (camera depth axis) error\n"
             "processed MediaPipe (2D scale + MAD K=5) vs GT", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = (REPO / "2_pose" / "uv_pseudo_world_correction" /
       "results_mad_k5" / "plots" / "knee_X_error_with_hist.png")
fig.savefig(out, dpi=150)
print(f"saved: {out}")
