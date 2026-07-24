#!/usr/bin/env python3
"""(3,1,0): ARIMA バイアス補正後の膝 X 成分・絶対誤差の時間変動(L/R 上下2段)。"""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(r"C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026")
sys.path.insert(0, str(REPO / "2_pose"))
sys.path.insert(0, str(REPO))

from run_uv_pseudo_world_correction import (
    build_pseudo_world, travel_direction, filter_joint, fit_alignment,
    hip_center, EFFECTIVE_TORSO_2D_M,
)
from run_error_mc_analysis import extract_gt_coords, MP_BASE, INPUT_DIR
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv
from statsmodels.tsa.arima.model import ARIMA

TARGET = "CapturedFrames_3.0_1.0_0.0"
JOINTS = ["LEFT_KNEE", "RIGHT_KNEE"]
WINDOW, K = 7, 5.0
ARIMA_ORDER = (2, 0, 2)
# 前段(v2 プロット)で確定した鏡映整合済みのビン別バイアス(アウトオブサンプル)
BIN_BIAS = {"LEFT_KNEE": 0.859, "RIGHT_KNEE": -0.475}


def knee_x_errors(cam: str):
    mp_df = pd.read_csv(next(MP_BASE.glob(f"Y=*/{cam}.csv")))
    gt_df = load_gt_csv(find_gt_csv_for_camera(cam, INPUT_DIR))
    fids, P, _, _ = build_pseudo_world(mp_df, EFFECTIVE_TORSO_2D_M, False, torso_2d=True)
    d_hat = travel_direction(fids, P)
    hip_fids = [f for f in fids if "LEFT_HIP" in P[f] and "RIGHT_HIP" in P[f]]
    ps, gt = [], []
    for f in hip_fids:
        g = hip_center(extract_gt_coords(gt_df, f))
        if g is None:
            continue
        ps.append(0.5 * (P[f]["LEFT_HIP"] + P[f]["RIGHT_HIP"]))
        gt.append(g)
    A, t, _, _ = fit_alignment(np.stack(ps), np.stack(gt))
    out = {}
    for joint in JOINTS:
        lm_fids = [f for f in fids if joint in P[f]]
        pos = np.stack([P[f][joint] for f in lm_fids])
        res = filter_joint(pos, d_hat, WINDOW, K, robust=True)
        corr_w = res["pos_corr"] @ A.T + t
        fr, ex = [], []
        for i, f in enumerate(lm_fids):
            g = extract_gt_coords(gt_df, f).get(joint)
            if g is None:
                continue
            fr.append(f)
            ex.append(corr_w[i, 0] - g[0])
        out[joint] = (np.array(fr), np.array(ex))
    return out


target = knee_x_errors(TARGET)

fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
COLORS = {"LEFT_KNEE": "#2980b9", "RIGHT_KNEE": "#27ae60"}

for ax, joint in zip(axes, JOINTS):
    fr, e_raw = target[joint]
    e_bin = e_raw - BIN_BIAS[joint]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(e_bin, order=ARIMA_ORDER, trend="c").fit()
    e_final = e_bin - model.fittedvalues       # ARIMA バイアス補正後

    abs_raw, abs_fin = np.abs(e_raw), np.abs(e_final)
    c = COLORS[joint]
    ax.plot(fr, abs_raw, "-", color="#b0b6ba", lw=1.6,
            label=f"|X error| before  (mean {abs_raw.mean():.3f} m)")
    ax.plot(fr, abs_fin, "-", color=c, lw=1.8,
            label=f"|X error| after bin+ARIMA  (mean {abs_fin.mean():.3f} m)")
    ax.axhline(abs_raw.mean(), color="#b0b6ba", ls="--", lw=1.0, alpha=0.8)
    ax.axhline(abs_fin.mean(), color=c, ls="--", lw=1.0, alpha=0.8)
    ax.set_ylabel(f"{joint}\n|X error| [m]")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    impr = (abs_raw.mean() - abs_fin.mean()) / abs_raw.mean() * 100
    ax.text(0.02, 0.95, f"improvement {impr:.1f}%", transform=ax.transAxes,
            va="top", fontsize=10, fontweight="bold", color=c,
            bbox=dict(fc="white", ec="none", alpha=0.7))
    print(f"{joint}: |e| {abs_raw.mean():.4f} -> {abs_fin.mean():.4f} m ({impr:.1f}%), "
          f"max {abs_raw.max():.3f} -> {abs_fin.max():.3f}")

axes[1].set_xlabel("Frame")
fig.suptitle(f"{TARGET} · knee |X error| vs frame\n"
             f"bias correction: viewpoint-bin signed bias + ARIMA{ARIMA_ORDER}",
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = (REPO / "2_pose" / "uv_pseudo_world_correction" /
       "results_mad_k5" / "plots" / "knee_X_abs_error_arima_corrected.png")
fig.savefig(out, dpi=150)
print(f"saved: {out}")
