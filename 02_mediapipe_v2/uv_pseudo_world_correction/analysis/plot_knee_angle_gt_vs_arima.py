#!/usr/bin/env python3
"""
(3,1,0): 膝角度(hip–knee–ankle 3点角)の時間変化。
GT vs ARIMA 補正後 MP(脚3関節の X 成分を ARIMA(2,0,2) でバイアス補正)。
"""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(r"C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026")
sys.path.insert(0, str(REPO / "02_mediapipe_v2"))
sys.path.insert(0, str(REPO))

from run_uv_pseudo_world_correction import (
    build_pseudo_world, travel_direction, filter_joint, fit_alignment,
    hip_center, EFFECTIVE_TORSO_2D_M,
)
from run_error_mc_analysis import extract_gt_coords, MP_BASE, INPUT_DIR
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv
from statsmodels.tsa.arima.model import ARIMA

TARGET = "CapturedFrames_3.0_1.0_0.0"
WINDOW, K = 7, 5.0
ARIMA_ORDER = (2, 0, 2)

# 3点角の構成(MP ランドマーク)と GT ボーン対応(マッピング監査の最良候補)
LEGS = {
    "LEFT":  {"mp": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
              "gt": ("LeftUpperLeg", "LeftLowerLeg", "LeftFoot")},
    "RIGHT": {"mp": ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"),
              "gt": ("RightUpperLeg", "RightLowerLeg", "RightFoot")},
}
MP_JOINTS = [j for leg in LEGS.values() for j in leg["mp"]]


def gt_point(row, bone):
    cols = (f"{bone}_X", f"{bone}_Y", f"{bone}_Z")
    try:
        v = np.array([float(row[c]) for c in cols])
    except (TypeError, ValueError, KeyError):
        return None
    return v if np.all(np.isfinite(v)) else None


def angle_deg(p_hip, p_knee, p_ankle):
    a = p_hip - p_knee
    b = p_ankle - p_knee
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return np.nan
    c = np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0)
    return float(np.degrees(np.arccos(c)))


# ── パイプライン(修正済み構成) ──
mp_df = pd.read_csv(next(MP_BASE.glob(f"Y=*/{TARGET}.csv")))
gt_df = load_gt_csv(find_gt_csv_for_camera(TARGET, INPUT_DIR))
gt_rows = {int(r["Frame"]): r for _, r in gt_df.iterrows()}

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

# 各関節: MAD 補正 → ワールド整合 → X 成分を ARIMA でバイアス補正
mp_world = {}   # joint -> {fid: pos(3,)}
gt_map = {"LEFT_HIP": "LeftUpperLeg", "LEFT_KNEE": "LeftLowerLeg",
          "LEFT_ANKLE": "LeftFoot", "RIGHT_HIP": "RightUpperLeg",
          "RIGHT_KNEE": "RightLowerLeg", "RIGHT_ANKLE": "RightFoot"}
for joint in MP_JOINTS:
    lm_fids = [f for f in fids if joint in P[f]]
    pos = np.stack([P[f][joint] for f in lm_fids])
    res = filter_joint(pos, d_hat, WINDOW, K, robust=True)
    w = res["pos_corr"] @ A.T + t
    # X 誤差系列 → ARIMA(定数項込み)フィット → 減算
    ex, idx = [], []
    for i, f in enumerate(lm_fids):
        row = gt_rows.get(f)
        g = gt_point(row, gt_map[joint]) if row is not None else None
        if g is None:
            continue
        ex.append(w[i, 0] - g[0])
        idx.append(i)
    ex = np.array(ex)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit_vals = ARIMA(ex, order=ARIMA_ORDER, trend="c").fit().fittedvalues
    w_corr = w.copy()
    for k_, i in enumerate(idx):
        w_corr[i, 0] -= fit_vals[k_]        # X のみ補正(Y, Z はそのまま)
    mp_world[joint] = {"raw": {f: w[i] for i, f in enumerate(lm_fids)},
                       "corr": {f: w_corr[i] for i, f in enumerate(lm_fids)}}

# ── 角度計算 ──
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
COLORS = {"LEFT": "#2980b9", "RIGHT": "#27ae60"}

for ax, (side, cfg) in zip(axes, LEGS.items()):
    hip_lm, knee_lm, ankle_lm = cfg["mp"]
    gt_h, gt_k, gt_a = cfg["gt"]
    frames, th_gt, th_raw, th_corr = [], [], [], []
    for f in fids:
        row = gt_rows.get(f)
        if row is None:
            continue
        gh, gk, ga = gt_point(row, gt_h), gt_point(row, gt_k), gt_point(row, gt_a)
        ok_mp = all(f in mp_world[j]["raw"] for j in cfg["mp"])
        if gh is None or gk is None or ga is None or not ok_mp:
            continue
        frames.append(f)
        th_gt.append(angle_deg(gh, gk, ga))
        th_raw.append(angle_deg(mp_world[hip_lm]["raw"][f],
                                mp_world[knee_lm]["raw"][f],
                                mp_world[ankle_lm]["raw"][f]))
        th_corr.append(angle_deg(mp_world[hip_lm]["corr"][f],
                                 mp_world[knee_lm]["corr"][f],
                                 mp_world[ankle_lm]["corr"][f]))
    th_gt, th_raw, th_corr = map(np.array, (th_gt, th_raw, th_corr))
    mae_raw = np.nanmean(np.abs(th_raw - th_gt))
    mae_corr = np.nanmean(np.abs(th_corr - th_gt))
    c = COLORS[side]
    ax.plot(frames, th_gt, "-", color="#2c3e50", lw=2.0, label="GT")
    ax.plot(frames, th_raw, "--", color="#b0b6ba", lw=1.2,
            label=f"MP before X-corr (MAE {mae_raw:.1f}°)")
    ax.plot(frames, th_corr, "-", color=c, lw=1.7,
            label=f"MP after bin+ARIMA X-corr (MAE {mae_corr:.1f}°)")
    ax.set_ylabel(f"{side}_KNEE angle [deg]")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=8.5)
    print(f"{side}_KNEE: MAE raw {mae_raw:.2f} deg -> corrected {mae_corr:.2f} deg "
          f"({(mae_raw-mae_corr)/mae_raw*100:.1f}% improvement)")

axes[1].set_xlabel("Frame")
fig.suptitle(f"{TARGET} · knee angle (hip–knee–ankle) vs frame\n"
             "GT vs processed MediaPipe (leg-joint X components ARIMA-corrected)",
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = (REPO / "02_mediapipe_v2" / "uv_pseudo_world_correction" /
       "results_mad_k5" / "plots" / "knee_angle_gt_vs_arima.png")
fig.savefig(out, dpi=150)
print(f"saved: {out}")
