#!/usr/bin/env python3
"""
(3,1,0) 膝 X 成分誤差の改正版プロット:
  Stage 0: 補正済みMP(2Dスケール+MAD K=5)の X 誤差
  Stage 1: 視点ビン(方位E×Y=1.0)の他カメラから求めた符号付き平均バイアスを減算
           (Model 4S 流・アウトオブサンプル)
  Stage 2: 残差に ARIMA を適用し、その残差を最終誤差とする
L/R 膝を上下2段、右側に縦軸共有ヒストグラム。
"""
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(r"C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026")
sys.path.insert(0, str(REPO / "20_pose_correction"))
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


def knee_x_errors(cam: str):
    """補正済みMP(ワールド整合後)の X 誤差系列 {joint: (fids, ex)} を返す。"""
    try:
        mp_path = next(MP_BASE.glob(f"Y=*/{cam}.csv"))
    except StopIteration:
        return None
    gt_path = find_gt_csv_for_camera(cam, INPUT_DIR)
    if gt_path is None:
        return None
    mp_df = pd.read_csv(mp_path)
    gt_df = load_gt_csv(gt_path)
    fids, P, _, _ = build_pseudo_world(mp_df, EFFECTIVE_TORSO_2D_M, False, torso_2d=True)
    if len(fids) < 10:
        return None
    d_hat = travel_direction(fids, P)
    if d_hat is None:
        return None
    hip_fids = [f for f in fids if "LEFT_HIP" in P[f] and "RIGHT_HIP" in P[f]]
    ps, gt = [], []
    for f in hip_fids:
        g = hip_center(extract_gt_coords(gt_df, f))
        if g is None:
            continue
        ps.append(0.5 * (P[f]["LEFT_HIP"] + P[f]["RIGHT_HIP"]))
        gt.append(g)
    if len(ps) < 2:
        return None
    fit = fit_alignment(np.stack(ps), np.stack(gt))
    if fit is None:
        return None
    A, t, mirrored, _ = fit

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
    return out, mirrored


# ── Stage1: ビン内他カメラから符号付き平均バイアス(アウトオブサンプル) ──
meta = pd.read_csv(REPO / "20_pose_correction/uv_pseudo_world_correction/results_mad_k5/uvpw_camera_meta.csv")
bin_mates = meta[(meta.azimuth_label == "E") & (meta.camera_y == 1.0) &
                 (meta.folder_name != TARGET)].folder_name.tolist()
print(f"bin mates (E x Y=1.0, excl. target): {len(bin_mates)}")

# 対象カメラを先に処理し、鏡映フラグを取得
target, target_mirrored = knee_x_errors(TARGET)
print(f"target mirrored: {target_mirrored}")

# 鏡映フラグが同じビン内カメラのみでバイアスを構築
# (鏡映が異なると MP 奥行き誤差が世界 ±X のどちらに写るかが反転するため)
bias = {j: [] for j in JOINTS}
used = 0
for cam in bin_mates:
    r = knee_x_errors(cam)
    if r is None:
        continue
    errs, mir = r
    if mir != target_mirrored:
        continue
    used += 1
    for j in JOINTS:
        bias[j].append(float(errs[j][1].mean()))
b_out = {j: float(np.mean(v)) for j, v in bias.items()}
print(f"bin mates used (same mirror flag): {used}")
print("out-of-sample bin bias:", {j: round(v, 3) for j, v in b_out.items()})

fig, axes = plt.subplots(
    2, 2, figsize=(11.5, 7.5), sharex="col",
    gridspec_kw={"width_ratios": [4, 1], "wspace": 0.04, "hspace": 0.15},
)

COLORS = {"LEFT_KNEE": "#2980b9", "RIGHT_KNEE": "#27ae60"}
for row, joint in enumerate(JOINTS):
    fr, e_raw = target[joint]
    e_bin = e_raw - b_out[joint]                     # Stage1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(e_bin, order=ARIMA_ORDER, trend="c").fit()
    fit_vals = model.fittedvalues
    e_arima = e_bin - fit_vals                       # Stage2(最終残差)

    c = COLORS[joint]
    ax, axh = axes[row]
    ax.axhline(0, color="#2c3e50", lw=1.0)
    ax.plot(fr, e_raw, "-", color="#b0b6ba", lw=1.2,
            label=f"raw error (mean {e_raw.mean():+.2f})")
    ax.plot(fr, e_bin, "-", color=c, lw=1.6,
            label=f"− bin bias {b_out[joint]:+.2f} (out-of-sample)")
    ax.plot(fr, fit_vals, "--", color="#2c3e50", lw=1.2,
            label=f"ARIMA{ARIMA_ORDER} fit")
    ax.plot(fr, e_arima, "-", color="#e67e22", lw=1.0, alpha=0.9,
            label=f"ARIMA residual (std {e_arima.std():.3f})")
    ax.set_ylabel(f"{joint}\nX error [m]")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=7.5, ncol=2)

    bins = np.linspace(
        min(e_raw.min(), e_bin.min(), e_arima.min()),
        max(e_raw.max(), e_bin.max(), e_arima.max()), 30)
    axh.hist(e_raw, bins=bins, orientation="horizontal", color="#b0b6ba", alpha=0.55)
    axh.hist(e_bin, bins=bins, orientation="horizontal", color=c, alpha=0.55)
    axh.hist(e_arima, bins=bins, orientation="horizontal", color="#e67e22", alpha=0.6)
    axh.axhline(0, color="#2c3e50", lw=1.0)
    axh.sharey(ax)
    axh.tick_params(labelleft=False)
    axh.set_xlabel("count", fontsize=8)
    axh.grid(alpha=0.3)

    print(f"{joint}: raw mean {e_raw.mean():+.3f} std {e_raw.std():.3f} | "
          f"bin-corrected mean {e_bin.mean():+.3f} std {e_bin.std():.3f} | "
          f"ARIMA resid mean {e_arima.mean():+.3f} std {e_arima.std():.3f}")

axes[1, 0].set_xlabel("Frame")
fig.suptitle(
    f"{TARGET} · knee X error, revised: bin-bias (Model 4S style) + ARIMA{ARIMA_ORDER}\n"
    "gray: raw → color: − viewpoint-bin signed bias → orange: ARIMA residual",
    fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.92])
out = (REPO / "20_pose_correction" / "uv_pseudo_world_correction" /
       "results_mad_k5" / "plots" / "knee_X_error_with_hist_v2.png")
fig.savefig(out, dpi=150)
print(f"saved: {out}")
