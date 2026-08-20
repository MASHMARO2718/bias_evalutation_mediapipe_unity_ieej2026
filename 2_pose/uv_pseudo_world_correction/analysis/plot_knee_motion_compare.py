#!/usr/bin/env python3
"""(3,1,0) カメラ: 修正済み MP(2D体幹スケール+MAD K=5)と GT の膝軌跡比較。"""
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

# 修正済み擬似ワールド（2D体幹 + 較正定数）
fids, P, scale, _ = build_pseudo_world(
    mp_df, EFFECTIVE_TORSO_2D_M, False, torso_2d=True)
d_hat = travel_direction(fids, P)

# 位置合わせ（腰中心軌跡、補正前基準）
hip_fids = [f for f in fids if "LEFT_HIP" in P[f] and "RIGHT_HIP" in P[f]]
ps_hipc, gt_hipc, keep_f = [], [], []
for f in hip_fids:
    g = hip_center(extract_gt_coords(gt_df, f))
    if g is None:
        continue
    ps_hipc.append(0.5 * (P[f]["LEFT_HIP"] + P[f]["RIGHT_HIP"]))
    gt_hipc.append(g)
    keep_f.append(f)
A, t, mirrored, rmse = fit_alignment(np.stack(ps_hipc), np.stack(gt_hipc))

AXES = ["X", "Y", "Z"]
for joint, tag in [("LEFT_KNEE", "L_KNEE"), ("RIGHT_KNEE", "R_KNEE")]:
    lm_fids = [f for f in fids if joint in P[f]]
    pos = np.stack([P[f][joint] for f in lm_fids])
    res = filter_joint(pos, d_hat, WINDOW, K, robust=True)
    raw_w = pos @ A.T + t          # 補正前（ワールド系）
    corr_w = res["pos_corr"] @ A.T + t   # 補正後
    replaced = res["replaced"]

    gt_pts, gt_f = [], []
    for f in lm_fids:
        g = extract_gt_coords(gt_df, f).get(joint)
        if g is not None:
            gt_pts.append(g)
            gt_f.append(f)
    gt_arr = np.stack(gt_pts)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for i, ax in enumerate(axes):
        ax.plot(gt_f, gt_arr[:, i], "-", color="#2c3e50", lw=2.0, label="GT")
        ax.plot(lm_fids, raw_w[:, i], "--", color="#95a5a6", lw=1.2,
                label="MP raw (aligned)")
        ax.plot(lm_fids, corr_w[:, i], "-", color="#2980b9", lw=1.5,
                label="MP corrected (2D scale + MAD K=5)")
        rep_f = [f for f, m in zip(lm_fids, replaced) if m]
        rep_v = [v for v, m in zip(corr_w[:, i], replaced) if m]
        ax.scatter(rep_f, rep_v, s=26, color="#e74c3c", zorder=5,
                   edgecolors="white", linewidths=0.5,
                   label="replaced" if i == 0 else None)
        ax.set_ylabel(f"{AXES[i]} [m]")
        ax.grid(alpha=0.3)
        if i == 0:
            ax.legend(loc="best", fontsize=9, ncol=2)
    axes[-1].set_xlabel("Frame")
    err_r = np.linalg.norm(raw_w[[lm_fids.index(f) for f in gt_f]] - gt_arr, axis=1)
    err_c = np.linalg.norm(corr_w[[lm_fids.index(f) for f in gt_f]] - gt_arr, axis=1)
    fig.suptitle(
        f"{CAM} · {joint} · GT vs processed MediaPipe (world frame)\n"
        f"mean 3D err: raw {err_r.mean():.3f} m -> corrected {err_c.mean():.3f} m, "
        f"replaced {int(replaced.sum())}/{len(lm_fids)} frames",
        fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = (REPO / "2_pose" / "uv_pseudo_world_correction" /
           "results_mad_k5" / "plots" / f"knee_motion_{tag}.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"saved: {out}")
    print(f"  {joint}: raw {err_r.mean():.4f} -> corr {err_c.mean():.4f} m, "
          f"replaced {int(replaced.sum())}")
