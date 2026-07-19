#!/usr/bin/env python3
"""
GT フリー補正モデルの再構築（カンニングペーパー方式）

推論パイプライン（GT 不使用）
------------------------------
  1. MediaPipe pose_landmarks → UV 擬似ワールド 3 次元座標 (x,y,z)(t)
     スケールは UV 平面内の体幹長（2D）＋実効定数 0.582 m から取得
  2. 方向分離しないスパイク除去:
     各関節・各軸で窓幅 7 の移動中央値をとり、|x − median| > 4×MAD の点を
     中央値で置換
  3. カルマンスムーザー（等速モデル + RTS）でノイズ除去
     ノイズパラメータ (Q, R) はカンニングペーパーから読む
  4. 3 次元角度（3 点角: 膝=腰-膝-足首, 肘=肩-肘-手首）を計算
     ※ 3 点角は回転・並進・スケール・鏡映に不変 → 位置合わせ不要で
       GT 角度と直接比較できる
  5. 系統誤差の除去:
     撮影対象に対するカメラ方向 φ(t) を「カメラ既知位置 + UV 復元の
     進行距離 r(t)」から推定し、カンニングペーパーの角度バイアス表を
     線形補間して減算

カンニングペーパー（較正、GT 使用は較正時のみ）
------------------------------------------------
  較正カメラ (3.0, 1.0, 0.0) の GT を使って学習・保存する内容:
    - カルマン Q（GT 加速度分散）/ R（MP 残差の白色成分分散）: 関節×軸ごと
    - 進行距離 r(t) → ワールド Z の線形写像 (a, b) と基準フレーム
    - 被写体の横位置 x_s（シーン定数）
    - 角度バイアス表 b(φ): 相対カメラ方位 φ のビン平均（線形補間で使用）

検証
----
  検証カメラ (3.2, 1.1, 0.4) の別動画に、較正カメラで作った
  カンニングペーパーをそのまま適用し、GT は精度評価のみに使用。

使用例:
  python run_gt_free_model.py            # 較正 → 検証を通しで実行
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_error_mc_analysis import (  # noqa: E402
    INPUT_DIR,
    extract_gt_coords,
    hip_center,
    parse_camera,
)
from run_uv_pseudo_world_correction import (  # noqa: E402
    EFFECTIVE_TORSO_2D_M,
    build_pseudo_world,
    fit_alignment,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.gt_adapter import load_gt_csv  # noqa: E402

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "gt_free_model"

DT = 1.0 / 30.0
MAD_TO_SIGMA = 1.4826

# スパイク除去（方向分離なし）
MEDIAN_WINDOW = 7
K_MAD = 4.0

# 角度定義: MP は (端点1, 頂点, 端点2)
ANGLE_DEFS_MP = {
    "L_KNEE": ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"),
    "R_KNEE": ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"),
    "L_ELBOW": ("LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"),
    "R_ELBOW": ("RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST"),
}
# GT は Unity ボーン位置（肩は肩峰相当の UpperArm を使用 — マッピング監査の結論）
ANGLE_DEFS_GT = {
    "L_KNEE": ("LeftUpperLeg", "LeftLowerLeg", "LeftFoot"),
    "R_KNEE": ("RightUpperLeg", "RightLowerLeg", "RightFoot"),
    "L_ELBOW": ("LeftUpperArm", "LeftLowerArm", "LeftHand"),
    "R_ELBOW": ("RightUpperArm", "RightLowerArm", "RightHand"),
}
KF_JOINTS = sorted({j for tri in ANGLE_DEFS_MP.values() for j in tri}
                   | {"LEFT_HIP", "RIGHT_HIP"})

REF_FID = 60          # r(t) のアンカー基準フレーム（両動画で検出済みであること）
IDX_BINS = 30         # バイアス表のビン数（進行位置 z 索引）

# バイアス表の索引:
#   'z'   = 被写体進行位置 ẑ(t)（歩行位相と 1 対 1。位相ロックした誤差に追従）
#   'phi' = 相対カメラ方位 φ(t)（視方位ロックの誤差向け）
# ラグ解析の結果、膝の系統誤差は歩行位相ロック（カメラを 0.4 m ずらすと
# φ 索引は約 8 フレームずれて波形が合わない）ため既定は 'z'。
INDEX_MODE = "z"


# ──────────────────────────────────────────────────────────────────────────────
# 基本演算
# ──────────────────────────────────────────────────────────────────────────────
def moving_median_1d(x: np.ndarray, window: int) -> np.ndarray:
    half = window // 2
    return np.array([np.median(x[max(0, i - half): i + half + 1])
                     for i in range(len(x))])


def median_mad_filter(pos: np.ndarray, window: int = MEDIAN_WINDOW,
                      k: float = K_MAD) -> Tuple[np.ndarray, np.ndarray]:
    """
    (n,3) 位置系列に対し、軸ごとに移動中央値 + k×MAD でスパイク置換。
    方向分離はしない。返り値: (filtered, replaced_mask (n,))
    """
    out = pos.copy()
    replaced = np.zeros(len(pos), dtype=bool)
    half = window // 2
    for ax in range(pos.shape[1]):
        x = pos[:, ax]
        med = moving_median_1d(x, window)
        mad = np.array([
            np.median(np.abs(x[max(0, i - half): i + half + 1]
                             - med[i]))
            for i in range(len(x))
        ])
        floor = max(float(np.median(mad)) * 0.1, 1e-4)
        bad = np.abs(x - med) > k * np.maximum(mad, floor)
        out[bad, ax] = med[bad]
        replaced |= bad
    return out, replaced


def kalman_rts_1d(y: np.ndarray, dt: float, qa2: float, r_var: float) -> np.ndarray:
    """等速モデルのカルマンフィルタ + RTS スムーザー（1 軸）。"""
    n = len(y)
    F = np.array([[1.0, dt], [0.0, 1.0]])
    Q = qa2 * np.array([[dt ** 4 / 4, dt ** 3 / 2], [dt ** 3 / 2, dt ** 2]])
    H = np.array([[1.0, 0.0]])
    R = max(r_var, 1e-8)

    x = np.array([y[0], (y[1] - y[0]) / dt if n > 1 else 0.0])
    P = np.diag([1.0, 10.0])
    xs_f, Ps_f, xs_p, Ps_p = [], [], [], []
    for t in range(n):
        if t > 0:
            x = F @ x
            P = F @ P @ F.T + Q
        xs_p.append(x.copy()); Ps_p.append(P.copy())
        S = float(H @ P @ H.T) + R
        K = (P @ H.T / S).ravel()
        x = x + K * (y[t] - float(H @ x))
        P = P - np.outer(K, H @ P)
        xs_f.append(x.copy()); Ps_f.append(P.copy())

    xs = [None] * n
    xs[-1] = xs_f[-1]
    Pk = Ps_f[-1]
    for t in range(n - 2, -1, -1):
        C = Ps_f[t] @ F.T @ np.linalg.inv(Ps_p[t + 1])
        xs[t] = xs_f[t] + C @ (xs[t + 1] - xs_p[t + 1])
        Pk = Ps_f[t] + C @ (Pk - Ps_p[t + 1]) @ C.T
    return np.array([s[0] for s in xs])


def smooth_positions(pos: np.ndarray, qa2: np.ndarray, r_var: np.ndarray) -> np.ndarray:
    return np.stack([kalman_rts_1d(pos[:, ax], DT, float(qa2[ax]), float(r_var[ax]))
                     for ax in range(pos.shape[1])], axis=1)


def angle3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """(n,3) 3 点の頂点 b における角度 [deg]。"""
    v1, v2 = a - b, c - b
    n1 = np.linalg.norm(v1, axis=1)
    n2 = np.linalg.norm(v2, axis=1)
    cosang = np.einsum("ij,ij->i", v1, v2) / np.maximum(n1 * n2, 1e-9)
    return np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))


# ──────────────────────────────────────────────────────────────────────────────
# 系列構築
# ──────────────────────────────────────────────────────────────────────────────
def joint_series(fids: List[int], P: Dict[int, Dict[str, np.ndarray]],
                 joints: List[str]) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    検出フレーム範囲の連続グリッド上に各関節の (n,3) 系列を構築。
    欠損フレームは軸ごとに線形補間（較正カメラで 2 フレームのみ）。
    """
    grid = np.arange(fids[0], fids[-1] + 1)
    series = {}
    for j in joints:
        f_ok = np.array([f for f in fids if j in P[f]])
        if len(f_ok) < 5:
            continue
        vals = np.stack([P[f][j] for f in f_ok], axis=0)
        series[j] = np.stack(
            [np.interp(grid, f_ok, vals[:, ax]) for ax in range(3)], axis=1)
    return grid, series


def hip_center_series(series: Dict[str, np.ndarray]) -> np.ndarray:
    return 0.5 * (series["LEFT_HIP"] + series["RIGHT_HIP"])


def travel_r(hipc: np.ndarray, grid: np.ndarray, ref_fid: int) -> np.ndarray:
    """腰中心軌跡の主進行方向への射影距離 r(t)。ref_fid でゼロにアンカー。"""
    d = hipc[-1] - hipc[0]
    n = np.linalg.norm(d)
    d_hat = d / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])
    r = (hipc - hipc[0]) @ d_hat
    r0 = float(np.interp(ref_fid, grid, r))
    return r - r0


def rel_azimuth(cam_x: float, cam_z: float, x_s: float,
                z_s: np.ndarray) -> np.ndarray:
    """被写体 (x_s, z_s(t)) から見たカメラの水平方位 [deg]。"""
    return np.degrees(np.arctan2(cam_z - z_s, cam_x - x_s))


# ──────────────────────────────────────────────────────────────────────────────
# パイプライン共通部（GT フリー）
# ──────────────────────────────────────────────────────────────────────────────
def run_inference_stage(mp_csv: Path) -> Optional[dict]:
    """手順 1–2: 擬似ワールド構成 + 方向分離なしスパイク除去。"""
    mp_df = pd.read_csv(mp_csv)
    fids, P, scale, t_px = build_pseudo_world(
        mp_df, EFFECTIVE_TORSO_2D_M, per_frame_scale=False, torso_2d=True)
    if len(fids) < 10:
        return None
    grid, series = joint_series(fids, P, KF_JOINTS)
    if not all(j in series for j in KF_JOINTS):
        return None
    filtered, replaced = {}, {}
    for j, pos in series.items():
        filtered[j], replaced[j] = median_mad_filter(pos)
    return {
        "grid": grid, "raw": series, "filt": filtered, "replaced": replaced,
        "scale": scale, "torso_px": t_px,
    }


def angles_from_positions(series: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    return {name: angle3(series[a], series[b], series[c])
            for name, (a, b, c) in ANGLE_DEFS_MP.items()}


def gt_angle_series(gt_df: pd.DataFrame, grid: np.ndarray) -> Dict[str, np.ndarray]:
    """GT ボーン位置から 3 点角 [deg]（grid 上、GT 欠損フレームは NaN）。"""
    gt_fids = sorted(gt_df["Frame"].dropna().astype(int).unique())
    pos = {f: extract_raw_gt(gt_df, f) for f in gt_fids}
    out = {}
    for name, (a, b, c) in ANGLE_DEFS_GT.items():
        vals = np.full(len(grid), np.nan)
        for i, f in enumerate(grid):
            p = pos.get(int(f))
            if p and all(k in p for k in (a, b, c)):
                vals[i] = angle3(p[a][None], p[b][None], p[c][None])[0]
        out[name] = vals
    return out


def extract_raw_gt(gt_df: pd.DataFrame, fid: int) -> Dict[str, np.ndarray]:
    row = gt_df[gt_df["Frame"] == fid]
    if row.empty:
        return {}
    row = row.iloc[0]
    out = {}
    for bone in {b for tri in ANGLE_DEFS_GT.values() for b in tri} | {"Hips"}:
        cols = [f"{bone}_X", f"{bone}_Y", f"{bone}_Z"]
        if all(c in row.index for c in cols):
            v = row[cols].to_numpy(dtype=float)
            if np.all(np.isfinite(v)):
                out[bone] = v
    return out


# ──────────────────────────────────────────────────────────────────────────────
# 較正（カンニングペーパー作成、GT 使用）
# ──────────────────────────────────────────────────────────────────────────────
def calibrate(mp_csv: Path, gt_csv: Path, cam: Tuple[float, float, float]) -> dict:
    stage = run_inference_stage(mp_csv)
    if stage is None:
        raise RuntimeError("calibration camera: not enough MP frames")
    grid, filt = stage["grid"], stage["filt"]
    gt_df = load_gt_csv(gt_csv)

    # GT を擬似ワールド系へ（Q/R 学習のための座標合わせ。較正時のみ許可）
    gt_world = {int(f): extract_gt_coords(gt_df, int(f))
                for f in gt_df["Frame"].dropna().astype(int).unique()}
    hipc_filt = hip_center_series(filt)
    hipc_ps, hipc_gt, common = [], [], []
    for i, f in enumerate(grid):
        g = gt_world.get(int(f))
        if not g:
            continue
        gh = hip_center(g)
        if gh is None:
            continue
        hipc_ps.append(hipc_filt[i])
        hipc_gt.append(gh)
        common.append(i)
    fit = fit_alignment(np.stack(hipc_ps), np.stack(hipc_gt))
    if fit is None:
        raise RuntimeError("alignment failed")
    A, t_vec, mirrored, rmse = fit
    A_inv = np.linalg.inv(A)

    def gt_to_pseudo(v: np.ndarray) -> np.ndarray:
        return A_inv @ (v - t_vec)

    # カルマン Q / R の学習（関節×軸）。extract_gt_coords は MP 名キーで返す
    kf_params = {}
    for j in KF_JOINTS:
        pairs = []
        for i in common:
            g = gt_world.get(int(grid[i]), {})
            if j in g:
                pairs.append((i, g[j]))
        if len(pairs) < 20:
            # GT 対応が無い関節（腰など）は全関節平均を後で使う
            kf_params[j] = None
            continue
        idx = [p[0] for p in pairs]
        gt_ps = np.stack([gt_to_pseudo(p[1]) for p in pairs])
        mp_ps = filt[j][idx]
        resid = mp_ps - gt_ps
        r_var = np.zeros(3)
        qa2 = np.zeros(3)
        for ax in range(3):
            e = resid[:, ax]
            e_smooth = moving_median_1d(e, 15)
            r_var[ax] = float(np.var(e - e_smooth))
            acc = np.diff(gt_ps[:, ax], 2) / DT ** 2
            qa2[ax] = float(np.var(acc))
        kf_params[j] = {"qa2": qa2.tolist(), "R": r_var.tolist()}
    # 欠測関節は学習済み関節の平均で補完
    learned = [v for v in kf_params.values() if v]
    mean_qa2 = np.mean([v["qa2"] for v in learned], axis=0).tolist()
    mean_r = np.mean([v["R"] for v in learned], axis=0).tolist()
    for j, v in kf_params.items():
        if v is None:
            kf_params[j] = {"qa2": mean_qa2, "R": mean_r}

    # カルマン平滑（学習済みパラメータで適用）
    smooth = {j: smooth_positions(filt[j], np.array(kf_params[j]["qa2"]),
                                  np.array(kf_params[j]["R"]))
              for j in KF_JOINTS}

    # r(t) → ワールド Z の線形写像（GT で学習）
    hipc = hip_center_series(smooth)
    r = travel_r(hipc, grid, REF_FID)
    z_gt = np.array([hip_center(gt_world[int(grid[i])])[2] for i in common])
    r_c = r[common]
    b_slope, a_inter = np.polyfit(r_c, z_gt, 1)
    x_s = float(np.mean([hip_center(gt_world[int(grid[i])])[0] for i in common]))

    # 角度バイアス表 b(idx)。索引は INDEX_MODE（既定: 進行位置 ẑ）
    ang_mp = angles_from_positions(smooth)
    ang_gt = gt_angle_series(gt_df, grid)
    z_hat = a_inter + b_slope * r
    phi = rel_azimuth(cam[0], cam[2], x_s, z_hat)
    idx = z_hat if INDEX_MODE == "z" else phi
    bias_tables = {}
    for name in ANGLE_DEFS_MP:
        e = ang_mp[name] - ang_gt[name]
        ok = np.isfinite(e)
        edges = np.linspace(idx[ok].min(), idx[ok].max(), IDX_BINS + 1)
        centers, biases = [], []
        for k in range(IDX_BINS):
            m = ok & (idx >= edges[k]) & (idx <= edges[k + 1])
            if m.sum() >= 1:
                centers.append(float(0.5 * (edges[k] + edges[k + 1])))
                biases.append(float(np.mean(e[m])))
        # 隣接 3 ビンの移動平均で表を平滑化（ビン内サンプル数が少ないため）
        b_arr = np.array(biases)
        if len(b_arr) >= 3:
            b_arr = np.convolve(np.pad(b_arr, 1, mode="edge"),
                                np.ones(3) / 3, mode="valid")
        bias_tables[name] = {"idx": centers, "bias": b_arr.tolist()}

    cheat = {
        "calib_camera": list(cam),
        "torso_2d_m": EFFECTIVE_TORSO_2D_M,
        "median_window": MEDIAN_WINDOW,
        "k_mad": K_MAD,
        "ref_fid": REF_FID,
        "index_mode": INDEX_MODE,
        "r_to_z": {"a": float(a_inter), "b": float(b_slope)},
        "x_s": x_s,
        "kalman": kf_params,
        "bias_tables": bias_tables,
        "calib_align": {"mirrored": bool(mirrored), "hip_rmse_m": float(rmse)},
    }

    diag = {
        "grid": grid, "smooth": smooth, "ang_mp": ang_mp, "ang_gt": ang_gt,
        "phi": phi, "z_hat": z_hat, "idx": idx, "stage": stage,
        "z_fit_resid_m": float(np.sqrt(np.mean((a_inter + b_slope * r_c - z_gt) ** 2))),
    }
    return cheat, diag


# ──────────────────────────────────────────────────────────────────────────────
# 検証（GT は評価のみ）
# ──────────────────────────────────────────────────────────────────────────────
def validate(mp_csv: Path, gt_csv: Path, cam: Tuple[float, float, float],
             cheat: dict) -> dict:
    stage = run_inference_stage(mp_csv)
    if stage is None:
        raise RuntimeError("validation camera: not enough MP frames")
    grid, filt, raw = stage["grid"], stage["filt"], stage["raw"]

    # カルマン平滑（カンニングペーパーのパラメータ）
    smooth = {j: smooth_positions(filt[j], np.array(cheat["kalman"][j]["qa2"]),
                                  np.array(cheat["kalman"][j]["R"]))
              for j in KF_JOINTS}

    # 角度（3 段階）
    ang_raw = angles_from_positions(raw)
    ang_smooth = angles_from_positions(smooth)

    # 進行位置 ẑ(t)・方位 φ(t) の GT フリー推定 → バイアス線形補間 → 減算
    hipc = hip_center_series(smooth)
    r = travel_r(hipc, grid, cheat["ref_fid"])
    z_hat = cheat["r_to_z"]["a"] + cheat["r_to_z"]["b"] * r
    phi = rel_azimuth(cam[0], cam[2], cheat["x_s"], z_hat)
    idx = z_hat if cheat.get("index_mode", "z") == "z" else phi
    ang_corr = {}
    for name, tab in cheat["bias_tables"].items():
        bias = np.interp(idx, tab["idx"], tab["bias"])
        ang_corr[name] = ang_smooth[name] - bias

    # 評価（ここだけ GT）
    gt_df = load_gt_csv(gt_csv)
    ang_gt = gt_angle_series(gt_df, grid)
    z_gt = np.full(len(grid), np.nan)
    for i, f in enumerate(grid):
        g = extract_raw_gt(gt_df, int(f))
        if "Hips" in g:
            z_gt[i] = g["Hips"][2]

    return {
        "grid": grid, "phi": phi, "z_hat": z_hat, "z_gt": z_gt,
        "ang_raw": ang_raw, "ang_smooth": ang_smooth, "ang_corr": ang_corr,
        "ang_gt": ang_gt, "stage": stage,
    }


# ──────────────────────────────────────────────────────────────────────────────
def mae(e: np.ndarray) -> float:
    return float(np.nanmean(np.abs(e)))


def make_report(val: dict, cheat: dict, diag: dict, out: Path,
                cam_val: Tuple[float, float, float]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.mkdir(parents=True, exist_ok=True)
    grid, gt = val["grid"], val["ang_gt"]

    rows = []
    for name in ANGLE_DEFS_MP:
        g = gt[name]
        rows.append({
            "angle": name,
            "mae_raw_deg": mae(val["ang_raw"][name] - g),
            "mae_kalman_deg": mae(val["ang_smooth"][name] - g),
            "mae_corrected_deg": mae(val["ang_corr"][name] - g),
        })
    res = pd.DataFrame(rows)
    res["improve_vs_raw_pct"] = (1 - res["mae_corrected_deg"] / res["mae_raw_deg"]) * 100
    res.to_csv(out / "validation_angle_mae.csv", index=False)

    # 角度時系列 2×2
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    for ax, name in zip(axes.ravel(), ANGLE_DEFS_MP):
        ax.plot(grid, gt[name], "k-", lw=2, label="GT")
        ax.plot(grid, val["ang_raw"][name], color="#bbbbbb", lw=1, label="MP raw")
        ax.plot(grid, val["ang_smooth"][name], color="#2980b9", lw=1.2,
                label="+median/MAD+Kalman")
        ax.plot(grid, val["ang_corr"][name], color="#c0392b", lw=1.5,
                label="+cheat-sheet bias")
        ax.set_title(name)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("frame")
    for ax in axes[:, 0]:
        ax.set_ylabel("angle [deg]")
    fig.suptitle(f"Validation camera {cam_val} — GT-free pipeline "
                 f"(cheat sheet from {tuple(cheat['calib_camera'])})")
    fig.tight_layout()
    fig.savefig(out / "val_angle_timeseries.png", dpi=140)
    plt.close(fig)

    # MAE 棒グラフ
    x = np.arange(len(res))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for k, (col, lab, c) in enumerate([
            ("mae_raw_deg", "MP raw", "#7f8c8d"),
            ("mae_kalman_deg", "+median/MAD+Kalman", "#2980b9"),
            ("mae_corrected_deg", "+cheat-sheet bias", "#c0392b")]):
        ax.bar(x + (k - 1) * 0.27, res[col], width=0.27, label=lab, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels(res["angle"])
    ax.set_ylabel("MAE [deg]")
    ax.set_title("Validation angle MAE by pipeline stage")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "val_angle_mae_stages.png", dpi=140)
    plt.close(fig)

    # 診断: z 推定と φ
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(grid, val["z_gt"], "k-", label="GT Hips Z")
    axes[0].plot(grid, val["z_hat"], "r--", label="GT-free estimate")
    axes[0].set_xlabel("frame"); axes[0].set_ylabel("world Z [m]")
    axes[0].set_title("Subject travel position (GT-free vs GT)")
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[1].plot(grid, val["phi"], "b-")
    axes[1].set_xlabel("frame"); axes[1].set_ylabel("relative azimuth [deg]")
    axes[1].set_title("Cheat-sheet index φ(t)")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "val_travel_and_phi.png", dpi=140)
    plt.close(fig)

    # 較正: バイアス表
    idx_label = ("subject travel position z [m]"
                 if cheat.get("index_mode", "z") == "z"
                 else "relative azimuth [deg]")
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, name in zip(axes.ravel(), ANGLE_DEFS_MP):
        e = diag["ang_mp"][name] - diag["ang_gt"][name]
        ax.scatter(diag["idx"], e, s=8, alpha=0.4, label="calib samples")
        tab = cheat["bias_tables"][name]
        ax.plot(tab["idx"], tab["bias"], "ro-", ms=4, label="bias table")
        ax.set_title(name)
        ax.set_xlabel(idx_label)
        ax.set_ylabel("angle error [deg]")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Cheat sheet: systematic angle bias vs gait/viewpoint index (calibration)")
    fig.tight_layout()
    fig.savefig(out / "cheatsheet_bias_tables.png", dpi=140)
    plt.close(fig)

    z_err = val["z_hat"] - val["z_gt"]
    n_rep = int(sum(m.sum() for m in val["stage"]["replaced"].values()))
    n_tot = int(sum(len(m) for m in val["stage"]["replaced"].values()))
    lines = [
        "# GT-free model validation summary",
        "",
        f"- calibration camera: {tuple(cheat['calib_camera'])}",
        f"- validation camera:  {cam_val}",
        f"- pipeline: UV pseudo-world (2D torso scale {cheat['torso_2d_m']} m)",
        f"  -> moving median w={cheat['median_window']} + {cheat['k_mad']}xMAD spike replace"
        f" (direction-agnostic, replace rate {n_rep / n_tot:.3f})",
        "  -> Kalman RTS smoother (Q/R learned on calibration GT)",
        "  -> 3-point 3D angles (rigid-transform invariant)",
        "  -> cheat-sheet bias, linearly interpolated over "
        + ("subject travel position z(t) (gait-phase locked index)"
           if cheat.get("index_mode", "z") == "z" else "relative azimuth phi(t)"),
        "",
        "## GT-free travel estimate at validation",
        f"- z error: mean {np.nanmean(np.abs(z_err)):.3f} m / max {np.nanmax(np.abs(z_err)):.3f} m",
        f"- (calibration z-fit residual: {diag['z_fit_resid_m']:.3f} m)",
        "",
        "## Validation angle MAE [deg]",
        "",
        res.to_string(index=False),
        "",
        "## Notes",
        "- GT used at inference: none (only for this evaluation).",
        "- Validation GT is the world-space trajectory copied from camera 4.0_1.0_0.0",
        "  (GT is camera-independent within 3 mm; the additional capture has no own GT).",
        "- Cheat sheet learned entirely at the calibration camera.",
    ]
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return res


# ──────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="GT-free model with cheat sheet")
    ap.add_argument("--calib-mp", default=str(
        BASE / "mediapipe_processed_csv/Y=1.0/CapturedFrames_3.0_1.0_0.0.csv"))
    ap.add_argument("--calib-gt", default=str(
        INPUT_DIR / "CapturedFrames_3.0_1.0_0.0/gt_joints.csv"))
    ap.add_argument("--val-mp", default=str(
        BASE / "mediapipe_processed_csv_additional/Y=0.5/CapturedFrames_3.2_1.1_0.4.csv"))
    ap.add_argument("--val-gt", default=str(
        INPUT_DIR / "aditional__test_data/CapturedFrames_3.2_1.1_0.4/gt_joints.csv"))
    ap.add_argument("--outdir", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    cam_cal = parse_camera(Path(args.calib_mp).stem)
    cam_val = parse_camera(Path(args.val_mp).stem)
    print(f"calibrate on {cam_cal} ...")
    cheat, diag = calibrate(Path(args.calib_mp), Path(args.calib_gt), cam_cal)
    (out / "cheatsheet.json").write_text(
        json.dumps(cheat, indent=2), encoding="utf-8")
    print(f"  cheat sheet -> {out / 'cheatsheet.json'}")
    print(f"  align mirrored={cheat['calib_align']['mirrored']} "
          f"hip_rmse={cheat['calib_align']['hip_rmse_m']:.3f} m, "
          f"z-fit resid {diag['z_fit_resid_m']:.3f} m")

    print(f"validate on {cam_val} ...")
    val = validate(Path(args.val_mp), Path(args.val_gt), cam_val, cheat)
    res = make_report(val, cheat, diag, out, cam_val)
    print(res.to_string(index=False))
    print(f"summary: {out / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
