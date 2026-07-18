#!/usr/bin/env python3
"""
UV 擬似ワールド座標系による進行方向直交成分フィルタ補正（GT フリー）

「補正アルゴリズムプロンプト」(prompt_taira.pdf) に基づく実装。

座標系
------
  S_wod  : Unity ワールド座標系（評価にのみ使用）
  S_med  : MediaPipe 相対座標系（腰中心）
  UV_wod : UV 由来の擬似ワールド座標系（本補正の作業空間）

擬似ワールド座標系の構成
------------------------
  MediaPipe pose_landmarks (u, v, z) から
      P = s * ( u*W,  -v*H,  z*W )        [m]
  とする。u,v は画像正規化座標（大域位置を含む）、z は MP の相対深度。
  Y は画像下向き → 上向きに反転。s は「体幹長は既知」という事前情報から
      s = TORSO_M / median_t(体幹長_px(t))
  で決める（GT は補正経路では使わない。体幹長定数は実運用では
  被写体の体格既知に相当。GT が無い場合は --torso-m 既定値で動作）。

アルゴリズム（PDF 手順）
------------------------
  1. 各関節の (最終フレーム位置 − 初期フレーム位置) を平均 → 進行方向 D
  2. ΔP(t) = P(t) − P(t0)                     ※ t0 = 初期フレーム基準と解釈
  3. ε(t) = ΔP(t) − (ΔP(t)·D̂)D̂               （直交成分）
     r(t) = ΔP(t)·D̂                           （平行成分）
  4. ε'(t) = ε(t) の窓幅 W=7 中心移動平均
  5. ‖ε(t) − ε'(t)‖ > K·σ(t) （σ は窓内移動標準偏差、K=3）の点を除外し、
     その位置の ε(t) を ε'(t) で置換 → ε~(t)
  6. P_corr(t) = P(t0) + r(t)·D̂ + ε~(t)       ※「p(t) + ε~(t)」を
     平行成分＋フィルタ済み直交成分の再合成と解釈

前提条件（PDF）
---------------
  1. MediaPipe の誤差はカメラ視線（奥行き）方向に乗りやすい。真横撮影では
     奥行き軸は進行方向と直交するため、直交成分 ε のフィルタで除去できる。
  2. 擬似ワールド位置ベクトルが利用可能（上記の構成で満たす）。

評価（GT 使用、補正そのものは GT フリー）
-----------------------------------------
  擬似ワールド軌跡を GT ワールドへ「ヨー回転（進行方向合わせ）＋平行移動
  （腰中心軌跡の平均合わせ）＋鏡映候補」で位置合わせし、補正前後の
  3D 誤差を比較する。位置合わせは補正前軌跡から推定し前後で共通。
  腰ランドマークは補正対象だが、GT が Hips 単一点のため誤差評価からは除外
  （run_error_mc_analysis.py と同じ扱い）。

出力
----
  02_mediapipe_v2/uv_pseudo_world_correction/results/

使用例:
  python run_uv_pseudo_world_correction.py --max_cameras 3
  python run_uv_pseudo_world_correction.py --window 7 --k-sigma 3
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_error_mc_analysis import (  # noqa: E402
    AZ_LABELS,
    INPUT_DIR,
    JOINTS,
    MP_BASE,
    azimuth_bin,
    extract_gt_coords,
    extract_mp_coords,
    hip_center,
    parse_camera,
    y_folder,
)
from run_ma_noise_rejection import (  # noqa: E402
    moving_mean_center,
    moving_std_scalar,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent / "uv_pseudo_world_correction"
OUT_DIR = BASE_DIR / "results"   # main() で --outdir により差し替え
PLOT_DIR = OUT_DIR / "plots"

MAD_TO_SIGMA = 1.4826  # 正規分布での MAD → σ 換算係数

IMG_W, IMG_H = 1280, 720

# 補正対象ランドマーク（腰も擬似ワールドでは大域運動を持つため含める）
TARGET_LM = JOINTS + ["LEFT_HIP", "RIGHT_HIP"]
# GT 誤差評価の対象（腰は GT が単一 Hips のため除外）
EVAL_JOINTS = JOINTS

# 体幹長の既定値 [m]（GT が無い場合のフォールバック。Y-Bot 実測相当）
DEFAULT_TORSO_M = 0.55
# 2D（uv のみ）体幹長に対する実効定数 [m]。真横カメラ4台で
# 「真スケール×2D体幹px」を実測した平均（0.549–0.611, ±5%）。
# MP ランドマーク定義（肩峰・大転子相当）に固有の値で、GT のどの体節長とも
# 一致しないため、被写体ごとに 1 回キャリブレーションする定数として扱う。
EFFECTIVE_TORSO_2D_M = 0.582


# ──────────────────────────────────────────────────────────────────────────────
# 擬似ワールド構成
# ──────────────────────────────────────────────────────────────────────────────
def px_coords(mp_abs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """
    正規化 (u, v, z) → 主点中心の画素系 ((u-0.5)*W, -(v-0.5)*H, z*W)。
    Y は上向きに反転。主点中心化はピンホール逆投影 X=(u-c_x)·Z/f と整合させる
    ため（定数スケールでは並進に吸収されるが、フレーム毎スケールでは必須）。
    """
    return {
        k: np.array([(v[0] - 0.5) * IMG_W, -((v[1] - 0.5) * IMG_H),
                     v[2] * IMG_W], dtype=np.float64)
        for k, v in mp_abs.items()
    }


def torso_px(coords: Dict[str, np.ndarray], use_2d: bool = False) -> Optional[float]:
    """
    肩–腰中心距離の平均 [px]。
    use_2d=True では uv 成分のみで測る。MP の z は体幹長を大きく水増しする
    （実測で長さの5割超が z 由来）ため、スケール決定には 2D が正確。
    """
    hc = hip_center(coords)
    if hc is None:
        return None
    dim = 2 if use_2d else 3
    lens = [
        float(np.linalg.norm((coords[s] - hc)[:dim]))
        for s in ("LEFT_SHOULDER", "RIGHT_SHOULDER")
        if s in coords
    ]
    if not lens:
        return None
    m = float(np.mean(lens))
    return m if m > 1e-8 else None


def torso_m_from_gt(gt_df: pd.DataFrame, max_frames: int = 30) -> Optional[float]:
    """GT から体幹長 [m] を推定（被写体体格の事前情報に相当。全カメラ共通値）。"""
    lens = []
    for fid in sorted(gt_df["Frame"].dropna().astype(int).unique())[:max_frames]:
        gt_abs = extract_gt_coords(gt_df, fid)
        t = torso_px(gt_abs)  # ワールド座標でもロジックは同じ
        if t is not None:
            lens.append(t)
    return float(np.median(lens)) if lens else None


def build_pseudo_world(
    mp_df: pd.DataFrame, torso_m: float, per_frame_scale: bool = False,
    smooth_window: int = 9, torso_2d: bool = False,
) -> Tuple[List[int], Dict[int, Dict[str, np.ndarray]], float, float]:
    """
    フレームごとの擬似ワールド位置 P[fid][lm] [m] を構成。

    per_frame_scale=False: カメラ毎の定数スケール s = torso_m / median(体幹長px)。
    per_frame_scale=True : フレーム毎スケール s(t) = torso_m / 体幹長px(t)
                           （移動中央値で平滑化）。u = f·X/Z の Z(t) 変動を
                           吸収する弱透視の逐次補正に相当し、近距離カメラの
                           透視ドリフト（V字誤差）を除去する。
    """
    fids = sorted(mp_df["frame_id"].dropna().astype(int).unique())
    raw: Dict[int, Dict[str, np.ndarray]] = {}
    torso_by_fid: Dict[int, float] = {}
    for fid in fids:
        mp_abs = extract_mp_coords(mp_df, fid)
        if not mp_abs:
            continue
        px = px_coords(mp_abs)
        t = torso_px(px, use_2d=torso_2d)
        if t is not None:
            torso_by_fid[fid] = t
        raw[fid] = px
    if not torso_by_fid:
        return [], {}, np.nan, np.nan
    t_med = float(np.median(list(torso_by_fid.values())))

    if not per_frame_scale:
        s_const = torso_m / t_med
        P = {fid: {lm: v * s_const for lm, v in c.items()} for fid, c in raw.items()}
        return sorted(P.keys()), P, s_const, t_med

    # フレーム毎: 体幹長px(t) を移動中央値で平滑化してからスケール化
    ok_fids = sorted(raw.keys())
    t_series = np.array([torso_by_fid.get(f, np.nan) for f in ok_fids])
    # 欠損は全体中央値で埋める
    t_series = np.where(np.isfinite(t_series), t_series, t_med)
    w = max(1, int(smooth_window))
    if w % 2 == 0:
        w += 1
    half = w // 2
    t_smooth = np.array([
        np.median(t_series[max(0, i - half): min(len(t_series), i + half + 1)])
        for i in range(len(t_series))
    ])
    P = {}
    for i, fid in enumerate(ok_fids):
        s_t = torso_m / t_smooth[i]
        P[fid] = {lm: v * s_t for lm, v in raw[fid].items()}
    s_mean = float(np.mean(torso_m / t_smooth))
    return ok_fids, P, s_mean, t_med


# ──────────────────────────────────────────────────────────────────────────────
# PDF 手順 1–6
# ──────────────────────────────────────────────────────────────────────────────
def travel_direction(
    fids: List[int], P: Dict[int, Dict[str, np.ndarray]]
) -> Optional[np.ndarray]:
    """手順 1: 各関節の (最終 − 初期) 変位の平均 → 進行方向単位ベクトル D̂。"""
    moves = []
    for lm in TARGET_LM:
        lm_fids = [f for f in fids if lm in P[f]]
        if len(lm_fids) < 2:
            continue
        moves.append(P[lm_fids[-1]][lm] - P[lm_fids[0]][lm])
    if not moves:
        return None
    D = np.mean(np.stack(moves, axis=0), axis=0)
    n = float(np.linalg.norm(D))
    return D / n if n > 1e-6 else None


def moving_mad_scalar(arr: np.ndarray, window: int) -> np.ndarray:
    """中心窓の MAD × 1.4826（頑健な σ 推定）。スパイクに引っ張られない。"""
    n = len(arr)
    w = max(1, int(window))
    if w % 2 == 0:
        w += 1
    half = w // 2
    out = np.zeros(n, dtype=np.float64)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = arr[lo:hi]
        if len(seg) > 1:
            med = np.median(seg)
            out[i] = MAD_TO_SIGMA * float(np.median(np.abs(seg - med)))
    return out


def filter_joint(
    pos: np.ndarray, d_hat: np.ndarray, window: int, k_sigma: float,
    robust: bool = False,
) -> dict:
    """手順 2–6 を単一関節の位置時系列 pos (n, 3) に適用。"""
    p0 = pos[0]
    dP = pos - p0                                   # 手順2
    r = dP @ d_hat                                  # 手順4（平行成分）
    eps = dP - r[:, None] * d_hat[None, :]          # 手順3（直交成分）
    eps_bar = moving_mean_center(eps, window)       # 手順5（ε'）
    resid = np.linalg.norm(eps - eps_bar, axis=1)
    if robust:
        sigma = moving_mad_scalar(resid, window)    # MAD: 自己マスキング回避
    else:
        sigma = moving_std_scalar(resid, window)
    sigma_floor = max(float(np.median(sigma)) * 0.1, 1e-4)
    sigma_use = np.maximum(sigma, sigma_floor)
    thresh = k_sigma * sigma_use
    replaced = resid > thresh                       # 手順6 前段（除外判定）
    eps_t = np.where(replaced[:, None], eps_bar, eps)  # ε~
    pos_corr = p0 + r[:, None] * d_hat[None, :] + eps_t  # 手順6
    return {
        "r": r,
        "eps": eps,
        "eps_bar": eps_bar,
        "resid": resid,
        "sigma": sigma_use,
        "thresh": thresh,
        "replaced": replaced,
        "pos_corr": pos_corr,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GT 位置合わせ（評価専用）
# ──────────────────────────────────────────────────────────────────────────────
def rot_y(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def fit_alignment(
    ps_hipc: np.ndarray, gt_hipc: np.ndarray
) -> Optional[Tuple[np.ndarray, np.ndarray, bool, float]]:
    """
    擬似ワールド → GT ワールドの位置合わせ (R, t, mirrored, rmse)。
    ヨー回転（水平進行方向合わせ）＋平行移動。z 軸（MP 深度）の掌性が
    合わない場合に備え、進行方向を含む鉛直面での鏡映も候補にする。
    """
    if len(ps_hipc) < 2 or len(gt_hipc) < 2:
        return None
    d_ps = ps_hipc[-1] - ps_hipc[0]
    d_gt = gt_hipc[-1] - gt_hipc[0]
    h_ps = np.array([d_ps[0], d_ps[2]])
    h_gt = np.array([d_gt[0], d_gt[2]])
    if np.linalg.norm(h_ps) < 1e-6 or np.linalg.norm(h_gt) < 1e-6:
        return None
    a_ps = np.arctan2(h_ps[1], h_ps[0])
    a_gt = np.arctan2(h_gt[1], h_gt[0])
    R = rot_y(a_gt - a_ps)

    # 鏡映: 進行方向（水平）と鉛直軸が張る面に対する反転
    n_h = np.array([-h_ps[1], 0.0, h_ps[0]])
    n_h /= np.linalg.norm(n_h)
    M = np.eye(3) - 2.0 * np.outer(n_h, n_h)

    best = None
    for mirrored, A in ((False, R), (True, R @ M)):
        mapped = ps_hipc @ A.T
        t = gt_hipc.mean(axis=0) - mapped.mean(axis=0)
        rmse = float(np.sqrt(np.mean(np.sum((mapped + t - gt_hipc) ** 2, axis=1))))
        if best is None or rmse < best[3]:
            best = (A, t, mirrored, rmse)
    return best


# ──────────────────────────────────────────────────────────────────────────────
def process_camera(
    folder: str,
    mp_path: Path,
    gt_path: Optional[Path],
    *,
    window: int,
    k_sigma: float,
    torso_m_default: float,
    robust: bool = False,
    per_frame_scale: bool = False,
    torso_2d: bool = False,
) -> Tuple[List[dict], Optional[dict]]:
    cam = parse_camera(folder)
    if cam is None:
        return [], None
    cx, cy, cz = cam
    az = azimuth_bin(cx, cz)

    mp_df = pd.read_csv(mp_path)
    gt_df = load_gt_csv(gt_path) if gt_path is not None else None

    # 体幹長（事前情報）
    #   3D モード: GT があれば推定、無ければ既定値
    #   2D モード: MP 定義固有の実効定数を使う（GT の体節長とは別物のため）
    if torso_2d:
        torso_m = torso_m_default
    else:
        torso_m = None
        if gt_df is not None:
            torso_m = torso_m_from_gt(gt_df)
        if torso_m is None:
            torso_m = torso_m_default

    fids, P, scale, t_px = build_pseudo_world(
        mp_df, torso_m, per_frame_scale, torso_2d=torso_2d)
    if len(fids) < 3:
        return [], None

    d_hat = travel_direction(fids, P)
    if d_hat is None:
        return [], None

    # ─── 手順 2–6（関節ごと） ───────────────────────────────────────────────
    per_joint: Dict[str, dict] = {}
    joint_fids: Dict[str, List[int]] = {}
    for lm in TARGET_LM:
        lm_fids = [f for f in fids if lm in P[f]]
        if len(lm_fids) < 3:
            continue
        pos = np.stack([P[f][lm] for f in lm_fids], axis=0)
        per_joint[lm] = filter_joint(pos, d_hat, window, k_sigma, robust) | {"pos": pos}
        joint_fids[lm] = lm_fids
    if not per_joint:
        return [], None

    # ─── 評価用位置合わせ（GT がある場合のみ） ─────────────────────────────
    A = t_vec = None
    mirrored = False
    align_rmse = np.nan
    gt_world: Dict[int, Dict[str, np.ndarray]] = {}
    if gt_df is not None:
        gt_frames = set(gt_df["Frame"].dropna().astype(int).unique())
        common = [f for f in fids if f in gt_frames]
        ps_hipc, gt_hipc, hipc_fids = [], [], []
        for f in common:
            gt_abs = extract_gt_coords(gt_df, f)
            gh = hip_center(gt_abs)
            if gh is None:
                continue
            lh, rh = P[f].get("LEFT_HIP"), P[f].get("RIGHT_HIP")
            if lh is None or rh is None:
                continue
            gt_world[f] = gt_abs
            ps_hipc.append(0.5 * (lh + rh))
            gt_hipc.append(gh)
            hipc_fids.append(f)
        if len(ps_hipc) >= 2:
            fit = fit_alignment(np.stack(ps_hipc), np.stack(gt_hipc))
            if fit is not None:
                A, t_vec, mirrored, align_rmse = fit

    def to_world(v: np.ndarray) -> Optional[np.ndarray]:
        if A is None:
            return None
        return A @ v + t_vec

    # ─── 行生成 ─────────────────────────────────────────────────────────────
    C_vec = np.array([cx, cy, cz], dtype=np.float64)
    rows: List[dict] = []
    for lm, res in per_joint.items():
        lm_fids = joint_fids[lm]

        # 評価ベクトル（GT ワールド系での誤差ベクトル）を先に計算
        #   err_dyn_*: カメラ×関節ごとの平均誤差（静的成分）を除いた変動成分。
        #   時系列フィルタが原理的に触れるのはこの成分のみ。
        eval_vecs: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        mean_eb = mean_ea = None
        if A is not None and lm in EVAL_JOINTS:
            for i, fid in enumerate(lm_fids):
                if fid not in gt_world:
                    continue
                gt_p = gt_world[fid].get(lm)
                if gt_p is None:
                    continue
                wb = to_world(res["pos"][i])
                wa = to_world(res["pos_corr"][i])
                eval_vecs[i] = (wb - gt_p, wa - gt_p, gt_p)
            if eval_vecs:
                mean_eb = np.mean([v[0] for v in eval_vecs.values()], axis=0)
                mean_ea = np.mean([v[1] for v in eval_vecs.values()], axis=0)

        for i, fid in enumerate(lm_fids):
            err_before = err_after = np.nan
            eb_los = eb_perp = ea_los = ea_perp = np.nan
            dyn_before = dyn_after = np.nan
            if i in eval_vecs:
                e_b, e_a, gt_p = eval_vecs[i]
                err_before = float(np.linalg.norm(e_b))
                err_after = float(np.linalg.norm(e_a))
                # カメラ視線 (LoS) 分解: 前提条件1の検証用
                u_los = gt_p - C_vec
                n_los = float(np.linalg.norm(u_los))
                if n_los > 1e-8:
                    u_los = u_los / n_los
                    eb_los = float(abs(e_b @ u_los))
                    eb_perp = float(np.linalg.norm(e_b - (e_b @ u_los) * u_los))
                    ea_los = float(abs(e_a @ u_los))
                    ea_perp = float(np.linalg.norm(e_a - (e_a @ u_los) * u_los))
                # 静的バイアス除去後の変動誤差
                dyn_before = float(np.linalg.norm(e_b - mean_eb))
                dyn_after = float(np.linalg.norm(e_a - mean_ea))
            rows.append({
                "folder_name": folder,
                "camera_x": cx, "camera_y": cy, "camera_z": cz,
                "height_label": y_folder(cy),
                "azimuth_bin": az, "azimuth_label": AZ_LABELS[az],
                "frame_id": fid,
                "joint": lm,
                "P_x": float(res["pos"][i][0]),
                "P_y": float(res["pos"][i][1]),
                "P_z": float(res["pos"][i][2]),
                "Pcorr_x": float(res["pos_corr"][i][0]),
                "Pcorr_y": float(res["pos_corr"][i][1]),
                "Pcorr_z": float(res["pos_corr"][i][2]),
                "r_parallel": float(res["r"][i]),
                "eps_norm": float(np.linalg.norm(res["eps"][i])),
                "eps_bar_norm": float(np.linalg.norm(res["eps_bar"][i])),
                "resid_norm": float(res["resid"][i]),
                "sigma": float(res["sigma"][i]),
                "threshold": float(res["thresh"][i]),
                "replaced": bool(res["replaced"][i]),
                "err_before_m": err_before,
                "err_after_m": err_after,
                "err_before_los": eb_los,
                "err_before_perp": eb_perp,
                "err_after_los": ea_los,
                "err_after_perp": ea_perp,
                "err_dyn_before": dyn_before,
                "err_dyn_after": dyn_after,
            })

    n_replaced = int(sum(res["replaced"].sum() for res in per_joint.values()))
    n_total = int(sum(len(v) for v in joint_fids.values()))
    meta = {
        "folder_name": folder,
        "camera_x": cx, "camera_y": cy, "camera_z": cz,
        "height_label": y_folder(cy),
        "azimuth_bin": az, "azimuth_label": AZ_LABELS[az],
        "n_frames": len(fids),
        "scale_m_per_px": scale,
        "scale_mode": "per_frame" if per_frame_scale else "const",
        "torso_px_median": t_px,
        "torso_m_prior": torso_m,
        "D_x": float(d_hat[0]), "D_y": float(d_hat[1]), "D_z": float(d_hat[2]),
        "replace_rate": n_replaced / n_total if n_total else np.nan,
        "align_mirrored": mirrored,
        "align_hip_rmse_m": align_rmse,
        "window": window,
        "k_sigma": k_sigma,
    }
    return rows, meta


# ──────────────────────────────────────────────────────────────────────────────
def make_plots(df: pd.DataFrame, out_dir: Path):
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)

    # 置換率（関節別）
    rep = df.groupby("joint")["replaced"].mean().reindex(TARGET_LM)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(len(rep)), rep.values, color="#e67e22", alpha=0.85)
    ax.set_xticks(range(len(rep)))
    ax.set_xticklabels(rep.index, rotation=35, ha="right")
    ax.set_ylabel("Replace rate")
    ax.set_title("UV pseudo-world correction: replace rate by joint")
    ax.set_ylim(0, max(0.05, float(rep.max()) * 1.2))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "replace_rate_by_joint.png", dpi=140)
    plt.close(fig)

    # 置換率（関節×方位）
    piv = (
        df.groupby(["joint", "azimuth_bin"])["replaced"].mean()
        .unstack("azimuth_bin").reindex(TARGET_LM)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd", vmin=0,
                   vmax=max(0.01, float(np.nanmax(piv.values))))
    ax.set_xticks(range(8))
    ax.set_xticklabels([f"{i}:{AZ_LABELS[i]}" for i in range(8)])
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index)
    ax.set_title("Replace rate · joint × azimuth")
    fig.colorbar(im, ax=ax, label="replace rate")
    fig.tight_layout()
    fig.savefig(out_dir / "replace_rate_heatmap.png", dpi=140)
    plt.close(fig)

    # GT 誤差 前後比較（関節別）
    ev = df.dropna(subset=["err_before_m", "err_after_m"])
    if not ev.empty:
        agg = ev.groupby("joint")[["err_before_m", "err_after_m"]].mean().reindex(EVAL_JOINTS)
        x = np.arange(len(agg))
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(x - 0.2, agg["err_before_m"], width=0.4, label="before", color="#7f8c8d")
        ax.bar(x + 0.2, agg["err_after_m"], width=0.4, label="after", color="#2980b9")
        ax.set_xticks(x)
        ax.set_xticklabels(agg.index, rotation=35, ha="right")
        ax.set_ylabel("mean 3D error [m]")
        ax.set_title("GT error before/after correction (all frames)")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "gt_error_before_after_by_joint.png", dpi=140)
        plt.close(fig)

        # 置換フレームのみ
        rep_ev = ev[ev["replaced"]]
        if not rep_ev.empty:
            agg2 = rep_ev.groupby("joint")[["err_before_m", "err_after_m"]].mean().reindex(EVAL_JOINTS)
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(x - 0.2, agg2["err_before_m"], width=0.4, label="before", color="#c0392b")
            ax.bar(x + 0.2, agg2["err_after_m"], width=0.4, label="after", color="#27ae60")
            ax.set_xticks(x)
            ax.set_xticklabels(agg2.index, rotation=35, ha="right")
            ax.set_ylabel("mean 3D error [m]")
            ax.set_title("GT error before/after (replaced frames only)")
            ax.legend()
            ax.grid(axis="y", alpha=0.3)
            fig.tight_layout()
            fig.savefig(out_dir / "gt_error_replaced_frames.png", dpi=140)
            plt.close(fig)

    # 例: タイムシリーズ
    example = "CapturedFrames_3.0_1.0_0.0"
    sub = df[(df["folder_name"] == example) & (df["joint"] == "LEFT_KNEE")].sort_values("frame_id")
    if sub.empty:
        example = df["folder_name"].iloc[0]
        sub = df[(df["folder_name"] == example) & (df["joint"] == "LEFT_KNEE")].sort_values("frame_id")
    if not sub.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sub["frame_id"], sub["resid_norm"], "o-", color="#2980b9", ms=4,
                label=r"$||\varepsilon - \varepsilon'||$")
        ax.plot(sub["frame_id"], sub["threshold"], ":", color="#95a5a6",
                label=r"threshold $K\sigma$")
        bad = sub[sub["replaced"]]
        if not bad.empty:
            ax.scatter(bad["frame_id"], bad["resid_norm"], c="#e74c3c", s=40,
                       zorder=5, label="replaced")
        ax.set_xlabel("Frame")
        ax.set_ylabel("residual [m]")
        ax.set_title(f"{example} · LEFT_KNEE · orthogonal residual filtering")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "example_timeseries_LEFT_KNEE.png", dpi=140)
        plt.close(fig)


# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UV pseudo-world correction (GT-free)")
    parser.add_argument("--max_cameras", type=int, default=None)
    parser.add_argument("--window", type=int, default=7)
    parser.add_argument("--k-sigma", type=float, default=3.0)
    parser.add_argument("--torso-m", type=float, default=None,
                        help="体幹長事前値 [m]（省略時: 3D=0.55, 2D=0.582）")
    parser.add_argument("--torso-2d", action="store_true",
                        help="スケール決定に uv のみの体幹長を使う（MP z の水増しを除去）")
    parser.add_argument("--skip_frame_csv", action="store_true")
    parser.add_argument("--robust-sigma", action="store_true",
                        help="σ を移動標準偏差でなく移動 MAD で推定（自己マスキング回避）")
    parser.add_argument("--per-frame-scale", action="store_true",
                        help="画素→m をフレーム毎の体幹長で決める（透視ドリフト除去）")
    parser.add_argument("--camera", type=str, default=None,
                        help="部分一致でカメラを絞る（例: 3.0_1.0_0.0）")
    parser.add_argument("--outdir", type=str, default="results",
                        help="出力サブディレクトリ名（既定: results）")
    args = parser.parse_args()

    global OUT_DIR, PLOT_DIR
    OUT_DIR = BASE_DIR / args.outdir
    PLOT_DIR = OUT_DIR / "plots"

    if args.torso_m is None:
        args.torso_m = EFFECTIVE_TORSO_2D_M if args.torso_2d else DEFAULT_TORSO_M

    mp_csvs = sorted(MP_BASE.glob("Y=*/CapturedFrames_*.csv"))
    if args.camera:
        mp_csvs = [p for p in mp_csvs if args.camera in p.stem]
    if args.max_cameras:
        mp_csvs = mp_csvs[: args.max_cameras]
    if not mp_csvs:
        print(f"No MediaPipe CSV under: {MP_BASE}")
        sys.exit(1)

    print("UV pseudo-world correction (GT-free, PDF spec)")
    print(f"  window={args.window}  K={args.k_sigma}  sigma={'MAD' if args.robust_sigma else 'std'}")
    print(f"  cameras: {len(mp_csvs)}")
    print(f"  out: {OUT_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: List[dict] = []
    metas: List[dict] = []
    empty = 0
    t0 = time.time()

    for i, mp_path in enumerate(mp_csvs, 1):
        folder = mp_path.stem
        if i == 1 or i % 50 == 0 or i == len(mp_csvs):
            print(f"  [{i}/{len(mp_csvs)}] {folder}", flush=True)
        gt_path = find_gt_csv_for_camera(folder, INPUT_DIR)
        rows, meta = process_camera(
            folder, mp_path, gt_path,
            window=args.window, k_sigma=args.k_sigma,
            torso_m_default=args.torso_m,
            robust=args.robust_sigma,
            per_frame_scale=args.per_frame_scale,
            torso_2d=args.torso_2d,
        )
        if not rows:
            empty += 1
            continue
        all_rows.extend(rows)
        if meta:
            metas.append(meta)

    if not all_rows:
        print("No valid rows")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    if not args.skip_frame_csv:
        df.to_csv(OUT_DIR / "uvpw_frame_joint.csv", index=False)

    gcols = ["folder_name", "camera_x", "camera_y", "camera_z",
             "height_label", "azimuth_bin", "azimuth_label", "joint"]
    by_cam = df.groupby(gcols, as_index=False).agg(
        n_frames=("frame_id", "nunique"),
        replace_rate=("replaced", "mean"),
        mean_err_before=("err_before_m", "mean"),
        mean_err_after=("err_after_m", "mean"),
    )
    by_cam.to_csv(OUT_DIR / "uvpw_by_camera_joint.csv", index=False)

    by_joint = df.groupby("joint", as_index=False).agg(
        n=("replaced", "count"),
        replace_rate=("replaced", "mean"),
        mean_err_before=("err_before_m", "mean"),
        mean_err_after=("err_after_m", "mean"),
        mean_los_before=("err_before_los", "mean"),
        mean_perp_before=("err_before_perp", "mean"),
        mean_dyn_before=("err_dyn_before", "mean"),
        mean_dyn_after=("err_dyn_after", "mean"),
    )
    by_joint["dyn_improvement_pct"] = (
        (by_joint["mean_dyn_before"] - by_joint["mean_dyn_after"])
        / by_joint["mean_dyn_before"] * 100
    )
    by_joint["improvement_pct"] = (
        (by_joint["mean_err_before"] - by_joint["mean_err_after"])
        / by_joint["mean_err_before"] * 100
    )
    by_joint.to_csv(OUT_DIR / "uvpw_by_joint.csv", index=False)

    if metas:
        pd.DataFrame(metas).to_csv(OUT_DIR / "uvpw_camera_meta.csv", index=False)

    make_plots(df, PLOT_DIR)

    ev = df.dropna(subset=["err_before_m", "err_after_m"])
    rep_ev = ev[ev["replaced"]]
    rep_rate = float(df["replaced"].mean())
    summary = [
        "# UV pseudo-world correction summary (GT-free, PDF spec)",
        "",
        f"- cameras: {df['folder_name'].nunique()}",
        f"- rows: {len(df)}",
        f"- window: {args.window}",
        f"- K_sigma: {args.k_sigma}",
        f"- sigma_estimator: {'MAD' if args.robust_sigma else 'std'}",
        f"- empty: {empty}",
        f"- global_replace_rate: {rep_rate:.4f}",
        "",
        "## GT error (all evaluated frames)",
        f"- mean err before: {ev['err_before_m'].mean():.4f} m" if not ev.empty else "- (no GT eval)",
        f"- mean err after:  {ev['err_after_m'].mean():.4f} m" if not ev.empty else "",
        "",
        "## GT error (replaced frames only)",
        f"- n: {len(rep_ev)}",
        f"- mean err before: {rep_ev['err_before_m'].mean():.4f} m" if not rep_ev.empty else "- (none)",
        f"- mean err after:  {rep_ev['err_after_m'].mean():.4f} m" if not rep_ev.empty else "",
        "",
        "## Error decomposition (before correction, all evaluated frames)",
        f"- LoS (camera depth) component:  {ev['err_before_los'].mean():.4f} m" if not ev.empty else "",
        f"- perpendicular component:       {ev['err_before_perp'].mean():.4f} m" if not ev.empty else "",
        f"- dynamic (bias-removed) error:  {ev['err_dyn_before'].mean():.4f} m" if not ev.empty else "",
        "",
        "## Dynamic error (static per-camera bias removed) — the filter's actual target",
        f"- all frames:      {ev['err_dyn_before'].mean():.4f} -> {ev['err_dyn_after'].mean():.4f} m" if not ev.empty else "",
        f"- replaced frames: {rep_ev['err_dyn_before'].mean():.4f} -> {rep_ev['err_dyn_after'].mean():.4f} m" if not rep_ev.empty else "",
        "",
        "## By joint",
        "",
        by_joint.to_string(index=False),
        "",
        f"- elapsed_sec: {time.time() - t0:.1f}",
        "",
        f"Plots: {PLOT_DIR}",
    ]
    (OUT_DIR / "SUMMARY.md").write_text(
        "\n".join(x for x in summary if x is not None) + "\n", encoding="utf-8"
    )

    print(f"done ({time.time() - t0:.1f}s)  replace_rate={rep_rate:.4f}")
    if not ev.empty:
        print(f"  GT err before/after (all): "
              f"{ev['err_before_m'].mean():.4f} -> {ev['err_after_m'].mean():.4f} m")
    if not rep_ev.empty:
        print(f"  GT err before/after (replaced): "
              f"{rep_ev['err_before_m'].mean():.4f} -> {rep_ev['err_after_m'].mean():.4f} m")
    print(f"  summary: {OUT_DIR / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
