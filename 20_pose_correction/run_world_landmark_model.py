#!/usr/bin/env python3
"""
pose_world_landmarks 単独の GT フリー補正モデル（UV 擬似ワールド不使用）

問い: 「UV 擬似ワールドを使わず world landmarks だけで補正できるか?」

world landmarks は腰中心・メートル・等方 3D なので座標構成が不要。
ただし大域位置を含まないため、較正表の「ゆっくり成分」の索引を
world 内部の信号から作れるかが焦点になる。索引 4 方式を比較:

  W-yaw     : 腰ライン（LEFT_HIP−RIGHT_HIP）のカメラ相対ヨー角。
              純 world（画像情報もカメラ位置も不要）だが、深度成分に
              依存するため側面視で鏡映フリップの懸念
  W-bearing : 腰の画像内水平位置 u(t) + カメラ幾何（ハイブリッド。
              画像から使うのは u のみ）
  W-phase   : ヒルベルト歩行位相のみ(対照。非周期成分を表現できない)
  W-2level  : g(z_bearing) 粗ビン + 位相波 h(φ_g) 残差

その他の段は docs/08,10 と同じ（中央値+4×MAD → カルマン RTS → 3 点角 →
バイアス表線形補間減算）。カルマン Q/R は本モデルでは GT を使わず
自己推定（高周波残差と加速度分散）とした。

出力: 20_pose_correction/world_landmark_model/
使用例: python run_world_landmark_model.py
"""

from __future__ import annotations

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
import run_phase_explicit_model as PH  # noqa: E402

BASE = Path(__file__).resolve().parent
OUT = BASE / "world_landmark_model"
WORLD_DIR = BASE / "mediapipe_world_csv"

CALIB_W = WORLD_DIR / "CapturedFrames_3.0_1.0_0.0.csv"
VAL_W = WORLD_DIR / "CapturedFrames_3.2_1.1_0.4.csv"
CALIB_UV = BASE / "mediapipe_processed_csv/Y=1.0/CapturedFrames_3.0_1.0_0.0.csv"
VAL_UV = BASE / "mediapipe_processed_csv_additional/Y=0.5/CapturedFrames_3.2_1.1_0.4.csv"
CALIB_GT = BASE.parent / "10_input_videos/CapturedFrames_3.0_1.0_0.0/gt_joints.csv"
VAL_GT = (BASE.parent
          / "10_input_videos/aditional__test_data/CapturedFrames_3.2_1.1_0.4/gt_joints.csv")
CAM_CAL = (3.0, 1.0, 0.0)
CAM_VAL = (3.2, 1.1, 0.4)

YAW_BINS = 30
TWO_PI = 2.0 * np.pi
VARIANTS = ["yaw", "bearing", "phase", "two_level"]

# 参照値: UV 擬似ワールド系（docs/08, 10。フル検証動画）
UV_REF = {
    "raw":      {"L_KNEE": 15.33, "R_KNEE": 13.34, "L_ELBOW": 40.93, "R_ELBOW": 16.08},
    "UV-A":     {"L_KNEE": 8.27,  "R_KNEE": 7.71,  "L_ELBOW": 8.92,  "R_ELBOW": 4.60},
    "UV-B":     {"L_KNEE": 11.37, "R_KNEE": 9.25,  "L_ELBOW": 8.86,  "R_ELBOW": 4.99},
}


# ──────────────────────────────────────────────────────────────────────────────
# world 系列の構築（座標構成なし: CSV の x,y,z をそのまま使う）
# ──────────────────────────────────────────────────────────────────────────────
def load_world_series(csv_path: Path) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    df = pd.read_csv(csv_path)
    fids = sorted(df["frame_id"].unique())
    P = {}
    for fid in fids:
        sub = df[df["frame_id"] == fid]
        P[fid] = {r["landmark"]: np.array([r["x"], r["y"], r["z"]])
                  for _, r in sub.iterrows()
                  if r["landmark"] in M.KF_JOINTS}
    return M.joint_series(fids, P, M.KF_JOINTS)


def self_kf_params(pos: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """GT を使わない Q/R 自己推定（軸ごと）。"""
    qa2 = np.zeros(3)
    r_var = np.zeros(3)
    for ax in range(3):
        x = pos[:, ax]
        hf = x - M.moving_median_1d(x, 7)
        r_var[ax] = max(float(np.var(hf)), 1e-8)
        acc = np.diff(M.moving_median_1d(x, 5), 2) / M.DT ** 2
        qa2[ax] = max(float(np.var(acc)), 1e-6)
    return qa2, r_var


def world_stage(csv_path: Path) -> dict:
    grid, series = load_world_series(csv_path)
    filt, smooth = {}, {}
    for j, pos in series.items():
        f, _ = M.median_mad_filter(pos)
        filt[j] = f
        qa2, r_var = self_kf_params(f)
        smooth[j] = M.smooth_positions(f, qa2, r_var)
    return {"grid": grid, "raw": series, "filt": filt, "smooth": smooth}


# ──────────────────────────────────────────────────────────────────────────────
# 索引信号（すべて推論時 GT フリー）
# ──────────────────────────────────────────────────────────────────────────────
def hip_yaw_deg(smooth: Dict[str, np.ndarray]) -> np.ndarray:
    """腰ラインのカメラ相対ヨー角 [deg]（純 world 索引）。"""
    h = smooth["LEFT_HIP"] - smooth["RIGHT_HIP"]
    return np.degrees(np.arctan2(h[:, 2], h[:, 0]))


def gait_phase_world(smooth: Dict[str, np.ndarray]) -> dict:
    """足首 L−R の主変動軸への射影から瞬時位相（world には進行方向が
    無いため、進行方向の代わりに第 1 主成分軸を使う）。"""
    d = smooth["LEFT_ANKLE"] - smooth["RIGHT_ANKLE"]
    dc = d - d.mean(axis=0)
    _, _, vt = np.linalg.svd(dc, full_matrices=False)
    pc1 = vt[0]
    if pc1[0] < 0:          # 符号を決定論的に固定（動画間の一貫性のため）
        pc1 = -pc1
    s = dc @ pc1
    s0 = s - s.mean()
    ac = np.correlate(s0, s0, "full")[len(s0) - 1:]
    ac = ac / max(ac[0], 1e-12)
    lo, hi = 15, min(60, len(ac) - 1)
    period = int(lo + np.argmax(ac[lo:hi]))
    w = period if period % 2 == 1 else period + 1
    sd = s - M.moving_median_1d(s, w)
    phi = np.angle(hilbert(sd)) % TWO_PI
    return {"phi": phi, "s": s, "sd": sd, "period": period}


# ──────────────────────────────────────────────────────────────────────────────
# 較正・検証
# ──────────────────────────────────────────────────────────────────────────────
def calibrate() -> Tuple[dict, dict, dict]:
    st = world_stage(CALIB_W)
    grid, smooth = st["grid"], st["smooth"]
    gt_df = M.load_gt_csv(CALIB_GT)
    ang_mp = M.angles_from_positions(smooth)
    ang_gt = M.gt_angle_series(gt_df, grid)

    # GT z 系列と x_s（focal 較正用。較正時のみ GT）
    z_gt = np.full(len(grid), np.nan)
    x_list = []
    for i, fid in enumerate(grid):
        g = M.extract_raw_gt(gt_df, int(fid))
        if "Hips" in g:
            z_gt[i] = g["Hips"][2]
            x_list.append(g["Hips"][0])
    x_s = float(np.mean(x_list))

    # bearing 索引（u は UV CSV から。使うのは腰の u のみ）
    u = PH.hip_u_series(CALIB_UV, grid)
    focal = PH.fit_focal(u, z_gt, CAM_CAL, x_s)
    zb = PH.bearing_z(u, CAM_CAL, focal, x_s)

    yaw = hip_yaw_deg(smooth)
    ph = gait_phase_world(smooth)

    tabs = {v: {} for v in VARIANTS}
    templates = {}
    for name in M.ANGLE_DEFS_MP:
        e = ang_mp[name] - ang_gt[name]
        c, b = PH.bin_table_linear(yaw, e, YAW_BINS)
        tabs["yaw"][name] = {"idx": c.tolist(), "bias": b.tolist()}
        c, b = PH.bin_table_linear(zb, e, PH.ZB_BINS)
        tabs["bearing"][name] = {"idx": c.tolist(), "bias": b.tolist()}
        c, b = PH.bin_table_periodic(ph["phi"], e)
        tabs["phase"][name] = {"phi": c.tolist(), "bias": b.tolist()}
        cg, bg = PH.bin_table_linear(zb, e, PH.G_BINS)
        resid = e - np.interp(zb, cg, bg)
        ch, bh = PH.bin_table_periodic(ph["phi"], resid)
        tabs["two_level"][name] = {
            "g_idx": cg.tolist(), "g_bias": bg.tolist(),
            "h_phi": ch.tolist(), "h_bias": bh.tolist(),
        }
        ct, tt = PH.bin_table_periodic(ph["phi"], ang_mp[name])
        templates[name] = {"phi": ct, "val": tt}

    cheat = {"x_s": x_s, "focal": focal, "tables": tabs}
    diag = {"grid": grid, "ang_mp": ang_mp, "ang_gt": ang_gt,
            "yaw": yaw, "zb": zb, "z_gt": z_gt, "phase": ph, "stage": st}
    return cheat, templates, diag


def validate(cheat: dict, templates: dict) -> dict:
    st = world_stage(VAL_W)
    grid, smooth = st["grid"], st["smooth"]
    ang_raw = M.angles_from_positions(st["raw"])
    ang_smooth = M.angles_from_positions(smooth)

    u = PH.hip_u_series(VAL_UV, grid)
    zb = PH.bearing_z(u, CAM_VAL, cheat["focal"], cheat["x_s"])
    yaw = hip_yaw_deg(smooth)
    ph = gait_phase_world(smooth)
    delta, swapped, score = PH.match_offset_and_swap(
        ang_smooth, ph["phi"], templates)

    corr = {v: {} for v in VARIANTS}
    for name in M.ANGLE_DEFS_MP:
        src = PH.SWAP[name] if swapped else name
        t = cheat["tables"]["yaw"][src]
        corr["yaw"][name] = ang_smooth[name] - np.interp(
            yaw, np.array(t["idx"]), np.array(t["bias"]))
        t = cheat["tables"]["bearing"][src]
        corr["bearing"][name] = ang_smooth[name] - np.interp(
            zb, np.array(t["idx"]), np.array(t["bias"]))
        t = cheat["tables"]["phase"][src]
        corr["phase"][name] = ang_smooth[name] - PH.interp_periodic(
            ph["phi"] + delta, np.array(t["phi"]), np.array(t["bias"]))
        t = cheat["tables"]["two_level"][src]
        bias2 = (np.interp(zb, np.array(t["g_idx"]), np.array(t["g_bias"]))
                 + PH.interp_periodic(ph["phi"] + delta,
                                      np.array(t["h_phi"]),
                                      np.array(t["h_bias"])))
        corr["two_level"][name] = ang_smooth[name] - bias2

    gt_df = M.load_gt_csv(VAL_GT)
    ang_gt = M.gt_angle_series(gt_df, grid)
    z_gt = np.full(len(grid), np.nan)
    for i, fid in enumerate(grid):
        g = M.extract_raw_gt(gt_df, int(fid))
        if "Hips" in g:
            z_gt[i] = g["Hips"][2]

    return {"grid": grid, "yaw": yaw, "zb": zb, "z_gt": z_gt, "phase": ph,
            "delta": delta, "swapped": swapped, "score": score,
            "ang_raw": ang_raw, "ang_smooth": ang_smooth,
            "corr": corr, "ang_gt": ang_gt}


# ──────────────────────────────────────────────────────────────────────────────
def make_plots(diag: dict, val: dict, res: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUT.mkdir(parents=True, exist_ok=True)
    grid = val["grid"]

    # 1) 検証: 角度時系列（world raw / 最良方式）
    best = res.set_index("angle")[[f"{v}_mae" for v in VARIANTS]].mean().idxmin()
    best_v = best.replace("_mae", "")
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    for ax, name in zip(axes.ravel(), M.ANGLE_DEFS_MP):
        ax.plot(grid, val["ang_gt"][name], "k-", lw=2, label="GT")
        ax.plot(grid, val["ang_raw"][name], color="#bbbbbb", lw=1,
                label="world raw")
        ax.plot(grid, val["corr"][best_v][name], color="#c0392b", lw=1.6,
                label=f"corrected ({best_v})")
        ax.set_title(name)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("frame")
    for ax in axes[:, 0]:
        ax.set_ylabel("angle [deg]")
    fig.suptitle("World-landmark-only pipeline — validation camera "
                 f"(best index: {best_v}, swap={val['swapped']})")
    fig.tight_layout()
    fig.savefig(OUT / "val_world_timeseries.png", dpi=140)
    plt.close(fig)

    # 2) 索引の診断: ヨーと bearing-z の素性
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    axes[0].plot(diag["z_gt"], diag["yaw"], ".", ms=4, label="calibration")
    axes[0].plot(val["z_gt"], val["yaw"], ".", ms=4, label="validation")
    axes[0].set_xlabel("GT subject z [m]")
    axes[0].set_ylabel("hip-line yaw [deg]")
    axes[0].set_title("W-yaw index vs true position\n(monotone? mirror flips?)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].plot(grid, val["z_gt"], "k-", label="GT z")
    axes[1].plot(grid, val["zb"], "g--", label="bearing z (GT-free)")
    axes[1].set_xlabel("frame")
    axes[1].set_ylabel("z [m]")
    axes[1].set_title("W-bearing index at validation")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    axes[2].plot(grid, val["yaw"], "b-")
    axes[2].set_xlabel("frame")
    axes[2].set_ylabel("hip-line yaw [deg]")
    axes[2].set_title(f"W-yaw at validation (period-free?)")
    axes[2].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "world_index_diagnostics.png", dpi=140)
    plt.close(fig)

    # 3) 較正: ヨー索引バイアス表
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, name in zip(axes.ravel(), M.ANGLE_DEFS_MP):
        e = diag["ang_mp"][name] - diag["ang_gt"][name]
        ax.scatter(diag["yaw"], e, s=8, alpha=0.4, label="calib samples")
        # tabs構造から
        ax.set_title(name)
        ax.set_xlabel("hip-line yaw [deg]")
        ax.set_ylabel("angle error [deg]")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("W-yaw index: angle error vs hip-line yaw (calibration)")
    fig.tight_layout()
    fig.savefig(OUT / "world_yaw_bias_scatter.png", dpi=140)
    plt.close(fig)

    # 4) UV 系との比較バー
    labels = [("UV raw", UV_REF["raw"], "#dddddd"),
              ("world raw", None, "#999999"),
              ("UV-B (z-bearing)", UV_REF["UV-B"], "#a8d5ba"),
              ("W-yaw", "yaw", "#f39c12"),
              ("W-bearing", "bearing", "#27ae60"),
              ("W-phase", "phase", "#2980b9"),
              ("W-2level", "two_level", "#c0392b")]
    x = np.arange(len(M.ANGLE_DEFS_MP))
    width = 0.12
    fig, ax = plt.subplots(figsize=(12, 5))
    for k, (lab, src, color) in enumerate(labels):
        if src is None:
            vals = [res.loc[res["angle"] == n, "raw_mae"].iloc[0]
                    for n in M.ANGLE_DEFS_MP]
        elif isinstance(src, dict):
            vals = [src[n] for n in M.ANGLE_DEFS_MP]
        else:
            vals = [res.loc[res["angle"] == n, f"{src}_mae"].iloc[0]
                    for n in M.ANGLE_DEFS_MP]
        ax.bar(x + (k - 3) * width, vals, width=width, label=lab, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(list(M.ANGLE_DEFS_MP))
    ax.set_ylabel("MAE [deg]")
    ax.set_title("World-landmark-only vs UV pseudo-world (validation camera, full video)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "world_vs_uv_comparison.png", dpi=140)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("calibrate (world-only) ...")
    cheat, templates, diag = calibrate()
    print(f"  focal {cheat['focal']:.4f}, gait period {diag['phase']['period']} fr")

    print("validate ...")
    val = validate(cheat, templates)
    print(f"  match: delta={val['delta']:.2f} rad, swap={val['swapped']}")

    rows = []
    for name in M.ANGLE_DEFS_MP:
        g = val["ang_gt"][name]
        row = {"angle": name,
               "raw_mae": M.mae(val["ang_raw"][name] - g)}
        for v in VARIANTS:
            row[f"{v}_mae"] = M.mae(val["corr"][v][name] - g)
        rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "world_model_mae.csv", index=False)

    make_plots(diag, val, res)

    lines = [
        "# World-landmark-only GT-free model — results",
        "",
        "- coordinates: pose_world_landmarks only (no UV pseudo-world construction)",
        "- Kalman Q/R: self-estimated (no GT)",
        "- indexes: yaw (pure world) / bearing (hip u + camera geometry) /",
        "  phase (Hilbert) / two-level (g(z_bearing)+h(phi))",
        f"- template match: delta={val['delta']:.2f} rad, swap={val['swapped']}",
        "",
        "## Validation MAE [deg] (full video)",
        "",
        res.round(2).to_string(index=False),
        "",
        "## UV pseudo-world reference (same video; docs/08,10)",
        "",
        pd.DataFrame(UV_REF).T.round(2).to_string(),
        "",
        "- GT used at inference: none (evaluation only).",
    ]
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print(res.round(2).to_string(index=False))
    print(f"\nsummary: {OUT / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
