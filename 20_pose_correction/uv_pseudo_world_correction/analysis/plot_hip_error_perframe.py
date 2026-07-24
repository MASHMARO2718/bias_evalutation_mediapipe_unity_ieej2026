#!/usr/bin/env python3
"""腰中心誤差のフレーム推移: 定数スケール vs フレーム毎スケール(B2)の検証。"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(r"C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026")
sys.path.insert(0, str(REPO / "20_pose_correction"))
sys.path.insert(0, str(REPO))

from run_uv_pseudo_world_correction import (
    build_pseudo_world, travel_direction, filter_joint, fit_alignment,
    torso_m_from_gt, hip_center,
)
from run_error_mc_analysis import extract_gt_coords, MP_BASE, INPUT_DIR
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv

CAM = "CapturedFrames_3.0_1.0_0.0"
WINDOW = 7

mp_path = next(MP_BASE.glob(f"Y=*/{CAM}.csv"))
gt_path = find_gt_csv_for_camera(CAM, INPUT_DIR)
mp_df = pd.read_csv(mp_path)
gt_df = load_gt_csv(gt_path)
torso_m = torso_m_from_gt(gt_df)


def hip_error_series(torso_2d: bool, correct: bool):
    """(fids, |GT−hip| 系列, 置換マスク, align_rmse) を返す。"""
    tm = 0.582 if torso_2d else torso_m
    fids, P, scale, _ = build_pseudo_world(mp_df, tm, False, torso_2d=torso_2d)
    d_hat = travel_direction(fids, P)
    hip_fids = [f for f in fids if "LEFT_HIP" in P[f] and "RIGHT_HIP" in P[f]]
    posL = np.stack([P[f]["LEFT_HIP"] for f in hip_fids])
    posR = np.stack([P[f]["RIGHT_HIP"] for f in hip_fids])
    if correct:
        rL = filter_joint(posL, d_hat, WINDOW, 5.0, robust=True)
        rR = filter_joint(posR, d_hat, WINDOW, 5.0, robust=True)
        hipc = 0.5 * (rL["pos_corr"] + rR["pos_corr"])
        replaced = rL["replaced"] | rR["replaced"]
    else:
        hipc = 0.5 * (posL + posR)
        replaced = np.zeros(len(hip_fids), dtype=bool)

    gt_list, keep = [], []
    for i, f in enumerate(hip_fids):
        g = hip_center(extract_gt_coords(gt_df, f))
        if g is not None:
            gt_list.append(g)
            keep.append(i)
    gt_arr = np.stack(gt_list)
    keep = np.array(keep)

    # 位置合わせは「補正前」軌跡で推定（correct でも同じ基準にするため再計算）
    hipc_raw = 0.5 * (posL + posR)
    fit = fit_alignment(hipc_raw[keep], gt_arr)
    A, t, mirrored, rmse = fit
    err = np.linalg.norm(hipc[keep] @ A.T + t - gt_arr, axis=1)
    kfids = [hip_fids[i] for i in keep]
    rep_mask = replaced[keep]
    return kfids, err, rep_mask, rmse


f_c, e_const, _, rmse_c = hip_error_series(torso_2d=False, correct=False)
f_p, e_pf, _, rmse_p = hip_error_series(torso_2d=True, correct=False)
f_pc, e_pf_corr, rep, _ = hip_error_series(torso_2d=True, correct=True)

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(f_c, e_const, "-", color="#7f8c8d", lw=1.8,
        label=f"old: 3D torso scale  (mean {e_const.mean():.3f} m)")
ax.plot(f_p, e_pf, "-", color="#2980b9", lw=1.8,
        label=f"fixed: 2D torso + calibrated 0.582 m  (mean {e_pf.mean():.3f} m)")
ax.plot(f_pc, e_pf_corr, "-", color="#27ae60", lw=1.4, alpha=0.9,
        label=f"fixed + MAD K=5 correction  (mean {e_pf_corr.mean():.3f} m)")
rep_f = [f for f, m in zip(f_pc, rep) if m]
rep_e = [e for e, m in zip(e_pf_corr, rep) if m]
ax.scatter(rep_f, rep_e, s=26, color="#27ae60", zorder=5, edgecolors="white",
           linewidths=0.5, label=f"replaced ({len(rep_f)})")
ax.set_xlabel("Frame")
ax.set_ylabel("|GT hip center - pseudo-world hip center|  [m]")
ax.set_title(f"{CAM} · scale fix verification: 3D-torso vs 2D-torso(calibrated)")
ax.grid(alpha=0.3)
ax.legend(loc="upper center", fontsize=9)
fig.tight_layout()
out = (REPO / "20_pose_correction" / "uv_pseudo_world_correction" /
       "results_mad_k5" / "plots" / "hip_center_error_scale_fix.png")
fig.savefig(out, dpi=150)
print(f"saved: {out}")
print(f"old 3D torso    : mean {e_const.mean():.4f} m, max {e_const.max():.4f}, align_rmse {rmse_c:.4f}")
print(f"2D torso 0.582  : mean {e_pf.mean():.4f} m, max {e_pf.max():.4f}, align_rmse {rmse_p:.4f}")
print(f"2D + MAD K=5    : mean {e_pf_corr.mean():.4f} m, max {e_pf_corr.max():.4f}")
