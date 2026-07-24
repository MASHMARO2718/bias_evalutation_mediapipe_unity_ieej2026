#!/usr/bin/env python3
"""
位相明示型 GT フリー補正モデル（docs/10 の実装）

docs/08 の GT フリーモデル（進行位置 ẑ 索引）を拡張し、4 方式を比較する。

  A) z-travel : docs/08 の現行方式。進行距離 r(t) を基準フレームでアンカー
                → frame_id が振り直されると壊れる
  B) z-bearing: 腰の画像内水平位置 u(t) とカメラ位置から絶対 z を幾何推定
                （焦点距離 f のみ較正時に学習）→ アンカー不要
  C) phase    : ヒルベルト瞬時位相 φ_g のみで索引 → アンカー不要だが
                誤差の非周期（ゆっくり）成分を表現できない
  D) two-level: ゆっくり成分 g(z_bearing)（粗ビン）+ 位相波 h(φ_g)（残差）
                の 2 階建て → アンカー不要で両成分を表現

位相推定（GT フリー）:
  s(t) = 左右足首の進行方向相対位置 → 自己相関で主周期 → 周期幅で
  デトレンド → ヒルベルト変換 → φ_g(t)。較正テンプレートとの照合で
  位相オフセット δ と左右スワップを同時確定（π 曖昧性の解消）。

検証（docs/10 §4）:
  テスト1 同等性:      フル検証動画 (3.2,1.1,0.4) で 4 方式を比較
  テスト2 アンカー破壊: 冒頭 N フレーム切り落とし + frame_id 振り直し
                        （録画開始が遅いカメラの模擬）で 4 方式を比較

使用例:
  python run_phase_explicit_model.py
  python run_phase_explicit_model.py --trunc 25
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.signal import hilbert

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_gt_free_model as M  # noqa: E402

BASE = Path(__file__).resolve().parent
OUT = BASE / "phase_explicit_model"

CALIB_MP = BASE / "mediapipe_processed_csv/Y=1.0/CapturedFrames_3.0_1.0_0.0.csv"
CALIB_GT = BASE.parent / "10_input_videos/CapturedFrames_3.0_1.0_0.0/gt_joints.csv"
VAL_MP = BASE / "mediapipe_processed_csv_additional/Y=0.5/CapturedFrames_3.2_1.1_0.4.csv"
VAL_GT = (BASE.parent
          / "10_input_videos/aditional__test_data/CapturedFrames_3.2_1.1_0.4/gt_joints.csv")

PHASE_BINS = 24
ZB_BINS = 30      # z-bearing 単独索引のビン数
G_BINS = 8        # 2 階建てのゆっくり成分 g(z) の粗ビン数
SWAP = {"L_KNEE": "R_KNEE", "R_KNEE": "L_KNEE",
        "L_ELBOW": "R_ELBOW", "R_ELBOW": "L_ELBOW"}
TWO_PI = 2.0 * np.pi

VARIANTS = ["z_travel", "z_bearing", "phase_only", "two_level"]


# ──────────────────────────────────────────────────────────────────────────────
# 基本ヘルパ
# ──────────────────────────────────────────────────────────────────────────────
def bin_table_linear(x: np.ndarray, y: np.ndarray,
                     n_bins: int) -> Tuple[np.ndarray, np.ndarray]:
    """非周期のビン平均表（3 ビン移動平均で平滑化、欠損は線形補間）。"""
    ok = np.isfinite(x) & np.isfinite(y)
    edges = np.linspace(x[ok].min(), x[ok].max(), n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    means = np.full(n_bins, np.nan)
    for k in range(n_bins):
        m = ok & (x >= edges[k]) & (x <= edges[k + 1])
        if m.sum() >= 1:
            means[k] = y[m].mean()
    good = np.isfinite(means)
    means = np.interp(centers, centers[good], means[good])
    padded = np.pad(means, 1, mode="edge")
    means = np.convolve(padded, np.ones(3) / 3, mode="valid")
    return centers, means


def bin_table_periodic(phi: np.ndarray, y: np.ndarray,
                       n_bins: int = PHASE_BINS) -> Tuple[np.ndarray, np.ndarray]:
    """[0, 2π) 周期のビン平均表（周期 3 ビン移動平均）。"""
    edges = np.linspace(0, TWO_PI, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    ok = np.isfinite(y)
    means = np.full(n_bins, np.nan)
    for k in range(n_bins):
        m = ok & (phi >= edges[k]) & (phi < edges[k + 1])
        if m.sum() >= 1:
            means[k] = y[m].mean()
    if np.isnan(means).any():
        good = np.isfinite(means)
        means = interp_periodic(centers, centers[good], means[good])
    padded = np.concatenate([means[-1:], means, means[:1]])
    means = np.convolve(padded, np.ones(3) / 3, mode="valid")
    return centers, means


def interp_periodic(phi: np.ndarray, tab_phi: np.ndarray,
                    tab_val: np.ndarray) -> np.ndarray:
    order = np.argsort(tab_phi)
    tp, tv = np.asarray(tab_phi)[order], np.asarray(tab_val)[order]
    xp = np.concatenate([tp - TWO_PI, tp, tp + TWO_PI])
    fp = np.tile(tv, 3)
    return np.interp(np.asarray(phi) % TWO_PI, xp, fp)


# ──────────────────────────────────────────────────────────────────────────────
# 方位ベース絶対 z 推定（B, D 用。アンカー不要）
# ──────────────────────────────────────────────────────────────────────────────
def cam_axes(cx: float, cz: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """水平面のカメラ位置・光軸（原点向き）・右方向ベクトル。"""
    C = np.array([cx, cz], dtype=float)
    a = -C / np.linalg.norm(C)
    r = np.array([a[1], -a[0]])
    return C, a, r


def hip_u_series(mp_csv: Path, grid: np.ndarray) -> np.ndarray:
    """腰中心の画像内水平位置 u−0.5（grid 上、移動中央値 7 で平滑化）。"""
    df = pd.read_csv(mp_csv)
    rows = df[df["landmark"].isin(["LEFT_HIP", "RIGHT_HIP"])]
    g = rows.groupby("frame_id")["x"].mean()
    u = np.interp(grid, g.index.to_numpy(), g.to_numpy()) - 0.5
    return M.moving_median_1d(u, 7)


def fit_focal(u: np.ndarray, z_gt: np.ndarray, cam, x_s: float) -> float:
    """較正: u = f · (v·r)/(v·a) から f を推定（GT 使用は較正時のみ）。"""
    C, a, r = cam_axes(cam[0], cam[2])
    v = np.stack([np.full_like(z_gt, x_s - C[0]), z_gt - C[1]], axis=1)
    ratio = (v @ r) / (v @ a)
    ok = np.isfinite(u) & np.isfinite(ratio) & (np.abs(ratio) > 1e-6)
    return float(np.median(u[ok] / ratio[ok]))


def bearing_z(u: np.ndarray, cam, f: float, x_s: float) -> np.ndarray:
    """u−0.5 とカメラ位置から被写体の絶対 z を幾何的に解く。"""
    C, a, r = cam_axes(cam[0], cam[2])
    k = u / f
    num = (x_s - C[0]) * (r[0] - k * a[0])
    den = k * a[1] - r[1]
    return C[1] + num / np.where(np.abs(den) > 1e-9, den, np.nan)


# ──────────────────────────────────────────────────────────────────────────────
# 位相推定（GT フリー）
# ──────────────────────────────────────────────────────────────────────────────
def estimate_gait_phase(smooth: Dict[str, np.ndarray]) -> dict:
    hipc = M.hip_center_series(smooth)
    d = hipc[-1] - hipc[0]
    d_hat = d / max(np.linalg.norm(d), 1e-9)
    s = (smooth["LEFT_ANKLE"] - smooth["RIGHT_ANKLE"]) @ d_hat

    s0 = s - s.mean()
    ac = np.correlate(s0, s0, "full")[len(s0) - 1:]
    ac = ac / max(ac[0], 1e-12)
    lo, hi = 15, min(60, len(ac) - 1)
    period = int(lo + np.argmax(ac[lo:hi]))

    w = period if period % 2 == 1 else period + 1
    trend = M.moving_median_1d(s, w)
    sd = s - trend
    phi = np.angle(hilbert(sd)) % TWO_PI
    return {"phi": phi, "s": s, "sd": sd, "period": period}


def match_offset_and_swap(ang_obs: Dict[str, np.ndarray], phi: np.ndarray,
                          templates: dict) -> Tuple[float, bool, float]:
    """テンプレート照合で (位相オフセット δ, 左右スワップ) を同時確定。"""
    deltas = np.linspace(0, TWO_PI, 72, endpoint=False)
    best = (0.0, False, -np.inf)
    for swapped in (False, True):
        for d in deltas:
            score = 0.0
            for name in templates:
                src = SWAP[name] if swapped else name
                pred = interp_periodic(phi + d, templates[src]["phi"],
                                       templates[src]["val"])
                obs = ang_obs[name]
                ok = np.isfinite(obs) & np.isfinite(pred)
                if ok.sum() > 10:
                    score += float(np.corrcoef(obs[ok], pred[ok])[0, 1])
            if score > best[2]:
                best = (float(d), swapped, score)
    return best


# ──────────────────────────────────────────────────────────────────────────────
# 較正
# ──────────────────────────────────────────────────────────────────────────────
def calibrate_all(mp_csv: Path, gt_csv: Path, cam) -> Tuple[dict, dict, dict]:
    cheat, diag = M.calibrate(mp_csv, gt_csv, cam)
    grid, smooth = diag["grid"], diag["smooth"]

    # GT の z 系列（f の較正用）
    gt_df = M.load_gt_csv(gt_csv)
    z_gt = np.full(len(grid), np.nan)
    for i, fid in enumerate(grid):
        g = M.extract_raw_gt(gt_df, int(fid))
        if "Hips" in g:
            z_gt[i] = g["Hips"][2]

    # B/D 用: 方位ベース z
    u = hip_u_series(mp_csv, grid)
    f = fit_focal(u, z_gt, cam, cheat["x_s"])
    zb = bearing_z(u, cam, f, cheat["x_s"])
    cheat["focal_norm"] = f

    # C/D 用: 歩行位相
    ph = estimate_gait_phase(smooth)
    phi = ph["phi"]

    # 各角度の表（zb 索引 / 位相のみ / 2 階建て）
    tabs_zb, tabs_phase, tabs_g, tabs_h, templates = {}, {}, {}, {}, {}
    for name in M.ANGLE_DEFS_MP:
        e = diag["ang_mp"][name] - diag["ang_gt"][name]
        c, b = bin_table_linear(zb, e, ZB_BINS)
        tabs_zb[name] = {"idx": c.tolist(), "bias": b.tolist()}
        c, b = bin_table_periodic(phi, e)
        tabs_phase[name] = {"phi": c.tolist(), "bias": b.tolist()}
        # 2 階建て: 粗い g(zb) → 残差を位相表 h(φ) に
        cg, bg = bin_table_linear(zb, e, G_BINS)
        tabs_g[name] = {"idx": cg.tolist(), "bias": bg.tolist()}
        resid = e - np.interp(zb, cg, bg)
        ch, bh = bin_table_periodic(phi, resid)
        tabs_h[name] = {"phi": ch.tolist(), "bias": bh.tolist()}
        # テンプレート（照合用: 平滑 MP 角度 vs 位相）
        ct, tt = bin_table_periodic(phi, diag["ang_mp"][name])
        templates[name] = {"phi": ct, "val": tt}

    cheat["bias_tables_zb"] = tabs_zb
    cheat["bias_tables_phase"] = tabs_phase
    cheat["bias_tables_g"] = tabs_g
    cheat["bias_tables_h"] = tabs_h
    return cheat, templates, {"diag": diag, "phase": ph, "zb": zb, "z_gt": z_gt}


# ──────────────────────────────────────────────────────────────────────────────
# 検証（B/C/D。A は M.validate を使用）
# ──────────────────────────────────────────────────────────────────────────────
def validate_variants(mp_csv: Path, gt_csv: Path, cam, cheat: dict,
                      templates: dict) -> dict:
    stage = M.run_inference_stage(mp_csv)
    grid = stage["grid"]
    smooth = {j: M.smooth_positions(
        stage["filt"][j], np.array(cheat["kalman"][j]["qa2"]),
        np.array(cheat["kalman"][j]["R"])) for j in M.KF_JOINTS}

    ang_raw = M.angles_from_positions(stage["raw"])
    ang_smooth = M.angles_from_positions(smooth)

    u = hip_u_series(mp_csv, grid)
    zb = bearing_z(u, cam, cheat["focal_norm"], cheat["x_s"])
    ph = estimate_gait_phase(smooth)
    delta, swapped, score = match_offset_and_swap(ang_smooth, ph["phi"], templates)

    corr = {v: {} for v in ("z_bearing", "phase_only", "two_level")}
    for name in M.ANGLE_DEFS_MP:
        src = SWAP[name] if swapped else name
        t = cheat["bias_tables_zb"][src]
        corr["z_bearing"][name] = ang_smooth[name] - np.interp(
            zb, np.array(t["idx"]), np.array(t["bias"]))
        t = cheat["bias_tables_phase"][src]
        corr["phase_only"][name] = ang_smooth[name] - interp_periodic(
            ph["phi"] + delta, np.array(t["phi"]), np.array(t["bias"]))
        tg = cheat["bias_tables_g"][src]
        th = cheat["bias_tables_h"][src]
        bias2 = (np.interp(zb, np.array(tg["idx"]), np.array(tg["bias"]))
                 + interp_periodic(ph["phi"] + delta,
                                   np.array(th["phi"]), np.array(th["bias"])))
        corr["two_level"][name] = ang_smooth[name] - bias2

    gt_df = M.load_gt_csv(gt_csv)
    ang_gt = M.gt_angle_series(gt_df, grid)
    z_gt = np.full(len(grid), np.nan)
    for i, fid in enumerate(grid):
        g = M.extract_raw_gt(gt_df, int(fid))
        if "Hips" in g:
            z_gt[i] = g["Hips"][2]

    return {
        "grid": grid, "phase": ph, "zb": zb, "z_gt": z_gt,
        "delta": delta, "swapped": swapped, "match_score": score,
        "ang_raw": ang_raw, "ang_smooth": ang_smooth,
        "corr": corr, "ang_gt": ang_gt,
    }


def make_truncated_inputs(n_trunc: int, tmp_dir: Path) -> Tuple[Path, Path]:
    """冒頭 n_trunc フレーム切り落とし + frame_id 振り直し（開始遅れの模擬）。"""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    mp_df = pd.read_csv(VAL_MP)
    mp_df = mp_df[mp_df["frame_id"] >= n_trunc].copy()
    mp_df["frame_id"] -= n_trunc
    mp_path = tmp_dir / f"val_mp_trunc{n_trunc}.csv"
    mp_df.to_csv(mp_path, index=False)

    gt_df = pd.read_csv(VAL_GT)
    fcol = "frame_id" if "frame_id" in gt_df.columns else "Frame"
    gt_df = gt_df[gt_df[fcol] >= n_trunc].copy()
    gt_df[fcol] -= n_trunc
    gt_path = tmp_dir / f"val_gt_trunc{n_trunc}.csv"
    gt_df.to_csv(gt_path, index=False)
    return mp_path, gt_path


# ──────────────────────────────────────────────────────────────────────────────
def make_plots(cal_pack, val_full, comp, cheat, n_trunc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    diag, ph_cal = cal_pack["diag"], cal_pack["phase"]

    # 1) 位相信号と瞬時位相
    fig, axes = plt.subplots(2, 2, figsize=(13, 6))
    for col, (label, ph, grid) in enumerate([
            ("calibration (3.0,1.0,0.0)", ph_cal, diag["grid"]),
            ("validation (3.2,1.1,0.4)", val_full["phase"], val_full["grid"])]):
        axes[0, col].plot(grid, ph["s"], color="#7f8c8d", label="s(t) = ankle L−R")
        axes[0, col].plot(grid, ph["sd"], color="#2980b9", label="detrended")
        axes[0, col].set_title(f"{label} · period {ph['period']} fr")
        axes[0, col].legend(fontsize=8)
        axes[0, col].grid(alpha=0.3)
        axes[1, col].plot(grid, ph["phi"], ".", ms=3, color="#c0392b")
        axes[1, col].set_ylabel(r"$\varphi_g$ [rad]")
        axes[1, col].set_xlabel("frame")
        axes[1, col].grid(alpha=0.3)
    fig.suptitle("GT-free gait phase estimation (Hilbert transform)")
    fig.tight_layout()
    fig.savefig(OUT / "phase_signal_and_phi.png", dpi=140)
    plt.close(fig)

    # 2) 2 階建て表: g(z) と h(φ)
    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    for col, name in enumerate(M.ANGLE_DEFS_MP):
        e = diag["ang_mp"][name] - diag["ang_gt"][name]
        ax = axes[0, col]
        ax.scatter(cal_pack["zb"], e, s=7, alpha=0.35)
        tg = cheat["bias_tables_g"][name]
        ax.plot(tg["idx"], tg["bias"], "ro-", ms=4)
        ax.set_title(f"{name}\nslow g(z_bearing)")
        ax.set_xlabel("z [m]")
        ax.grid(alpha=0.3)
        resid = e - np.interp(cal_pack["zb"], np.array(tg["idx"]),
                              np.array(tg["bias"]))
        ax = axes[1, col]
        ax.scatter(ph_cal["phi"], resid, s=7, alpha=0.35)
        th = cheat["bias_tables_h"][name]
        ax.plot(th["phi"], th["bias"], "ro-", ms=4)
        ax.set_title(r"phase wave h($\varphi_g$)")
        ax.set_xlabel(r"$\varphi_g$ [rad]")
        ax.grid(alpha=0.3)
    axes[0, 0].set_ylabel("angle error [deg]")
    axes[1, 0].set_ylabel("residual [deg]")
    fig.suptitle("Two-level cheat sheet: slow viewpoint component + gait-phase wave")
    fig.tight_layout()
    fig.savefig(OUT / "two_level_bias_tables.png", dpi=140)
    plt.close(fig)

    # 3) 検証: 角度時系列（2 階建て）
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    grid = val_full["grid"]
    for ax, name in zip(axes.ravel(), M.ANGLE_DEFS_MP):
        ax.plot(grid, val_full["ang_gt"][name], "k-", lw=2, label="GT")
        ax.plot(grid, val_full["ang_raw"][name], color="#bbbbbb", lw=1,
                label="MP raw")
        ax.plot(grid, val_full["corr"]["two_level"][name], color="#c0392b",
                lw=1.6, label="two-level corrected")
        ax.set_title(name)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("frame")
    for ax in axes[:, 0]:
        ax.set_ylabel("angle [deg]")
    fig.suptitle("Validation — two-level (anchor-free) GT-free correction "
                 f"(delta={val_full['delta']:.2f} rad, swap={val_full['swapped']})")
    fig.tight_layout()
    fig.savefig(OUT / "val_two_level_timeseries.png", dpi=140)
    plt.close(fig)

    # 4) アンカー破壊テスト: 4 方式 × full/trunc
    labels = {"z_travel": "A z-travel (docs/08)", "z_bearing": "B z-bearing",
              "phase_only": "C phase-only", "two_level": "D two-level"}
    colors = {"z_travel": "#95a5a6", "z_bearing": "#27ae60",
              "phase_only": "#2980b9", "two_level": "#c0392b"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    x = np.arange(len(comp))
    for ax, suffix, title in [
            (axes[0], "full", "Full video"),
            (axes[1], "trunc", f"Anchor break (first {n_trunc} fr dropped)")]:
        for k, v in enumerate(VARIANTS):
            ax.bar(x + (k - 1.5) * 0.2, comp[f"{v}_{suffix}"], width=0.2,
                   color=colors[v], label=labels[v])
        ax.plot(x, comp[f"raw_{suffix}"], "kv", ms=8, label="MP raw")
        ax.set_xticks(x)
        ax.set_xticklabels(comp["angle"])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("MAE [deg]")
    axes[1].legend(fontsize=8)
    fig.suptitle("Anchor-break test: which index survives a shifted frame origin?")
    fig.tight_layout()
    fig.savefig(OUT / "anchor_break_comparison.png", dpi=140)
    plt.close(fig)

    # 5) 診断: bearing-z vs GT
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(grid, val_full["z_gt"], "k-", label="GT Hips Z")
    ax.plot(grid, val_full["zb"], "g--", label="bearing-z (GT-free, anchor-free)")
    ax.set_xlabel("frame")
    ax.set_ylabel("world Z [m]")
    err = val_full["zb"] - val_full["z_gt"]
    ax.set_title(f"Bearing-based absolute z at validation "
                 f"(mean |err| {np.nanmean(np.abs(err)):.3f} m)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "val_bearing_z.png", dpi=140)
    plt.close(fig)


# ──────────────────────────────────────────────────────────────────────────────
def collect_mae(val_A: dict, val_BCD: dict, suffix: str, comp: dict):
    for name in M.ANGLE_DEFS_MP:
        row = comp.setdefault(name, {"angle": name})
        gA = val_A["ang_gt"][name]
        gB = val_BCD["ang_gt"][name]
        row[f"raw_{suffix}"] = M.mae(val_BCD["ang_raw"][name] - gB)
        row[f"z_travel_{suffix}"] = M.mae(val_A["ang_corr"][name] - gA)
        for v in ("z_bearing", "phase_only", "two_level"):
            row[f"{v}_{suffix}"] = M.mae(val_BCD["corr"][v][name] - gB)


def main():
    ap = argparse.ArgumentParser(description="Phase-explicit GT-free model")
    ap.add_argument("--trunc", type=int, default=25)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    print("calibrate (z-travel + z-bearing + phase + two-level tables) ...")
    cheat, templates, cal_pack = calibrate_all(CALIB_MP, CALIB_GT, (3.0, 1.0, 0.0))
    print(f"  gait period {cal_pack['phase']['period']} fr, "
          f"focal_norm {cheat['focal_norm']:.4f}")

    comp: dict = {}

    print("test 1: full validation video ...")
    val_A = M.validate(VAL_MP, VAL_GT, (3.2, 1.1, 0.4), cheat)
    val_BCD = validate_variants(VAL_MP, VAL_GT, (3.2, 1.1, 0.4), cheat, templates)
    collect_mae(val_A, val_BCD, "full", comp)
    print(f"  match: delta={val_BCD['delta']:.2f} rad, swap={val_BCD['swapped']}")

    n = args.trunc
    print(f"test 2: anchor break (drop first {n} frames + renumber) ...")
    mp_t, gt_t = make_truncated_inputs(n, OUT / "tmp_inputs")
    val_A_t = M.validate(mp_t, gt_t, (3.2, 1.1, 0.4), cheat)
    val_BCD_t = validate_variants(mp_t, gt_t, (3.2, 1.1, 0.4), cheat, templates)
    collect_mae(val_A_t, val_BCD_t, "trunc", comp)
    print(f"  match(trunc): delta={val_BCD_t['delta']:.2f} rad, "
          f"swap={val_BCD_t['swapped']}")

    comp_df = pd.DataFrame([comp[name] for name in M.ANGLE_DEFS_MP])
    comp_df.to_csv(OUT / "phase_model_comparison.csv", index=False)

    make_plots(cal_pack, val_BCD, comp_df, cheat, n)

    cols_full = ["angle", "raw_full"] + [f"{v}_full" for v in VARIANTS]
    cols_tr = ["angle", "raw_trunc"] + [f"{v}_trunc" for v in VARIANTS]
    zb_err = val_BCD["zb"] - val_BCD["z_gt"]
    lines = [
        "# Phase-explicit / anchor-free GT-free model — results",
        "",
        "- A z-travel: docs/08 (ref-frame anchored travel distance)",
        "- B z-bearing: absolute z from image bearing + camera position (anchor-free)",
        "- C phase-only: Hilbert gait phase index (anchor-free)",
        "- D two-level: slow g(z_bearing) + phase wave h(phi_g) (anchor-free)",
        "",
        f"- gait period: calib {cal_pack['phase']['period']} fr / "
        f"val {val_BCD['phase']['period']} fr",
        f"- template match (full): delta={val_BCD['delta']:.2f} rad, "
        f"swap={val_BCD['swapped']}",
        f"- bearing-z error at validation: mean {np.nanmean(np.abs(zb_err)):.3f} m",
        "",
        "## MAE [deg] — full video",
        "",
        comp_df[cols_full].round(2).to_string(index=False),
        "",
        f"## MAE [deg] — anchor break (first {args.trunc} frames dropped, renumbered)",
        "",
        comp_df[cols_tr].round(2).to_string(index=False),
        "",
        "- GT used at inference: none (evaluation only).",
    ]
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print(comp_df[cols_full].round(2).to_string(index=False))
    print()
    print(comp_df[cols_tr].round(2).to_string(index=False))
    print(f"\nsummary: {OUT / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
