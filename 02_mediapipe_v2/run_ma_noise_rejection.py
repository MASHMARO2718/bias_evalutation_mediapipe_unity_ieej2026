#!/usr/bin/env python3
"""
移動平均によるノイズ除去（進行方向直交成分）

docs/06_MOVING_AVERAGE_NOISE_REJECTION.md に基づく実装（案 B 座標揃え）。

  D = m_final − m_0（GT 腰の歩行方向）
  E_n = m_n^MP − m_n^world（腰相対・Y反転・スケール後）
  ε_n = E_n − proj_D(E_n)
  窓 W の移動平均から K·σ を超えるフレームをマスク排除

出力:
  02_mediapipe_v2/ma_noise_rejection/results/

使用例:
  python run_ma_noise_rejection.py --max_cameras 3
  python run_ma_noise_rejection.py --window 7 --k-sigma 3
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
    extract_gt_coords,
    extract_mp_coords,
    flip_mp_y,
    hip_center,
    parse_camera,
    to_relative,
    torso_scale,
    y_folder,
    azimuth_bin,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "ma_noise_rejection" / "results"
PLOT_DIR = OUT_DIR / "plots"


def moving_mean_center(arr: np.ndarray, window: int) -> np.ndarray:
    n = len(arr)
    if n == 0:
        return arr
    w = max(1, int(window))
    if w % 2 == 0:
        w += 1
    half = w // 2
    out = np.empty_like(arr, dtype=np.float64)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        out[i] = arr[lo:hi].mean(axis=0)
    return out


def moving_std_scalar(arr: np.ndarray, window: int) -> np.ndarray:
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
        out[i] = float(seg.std(ddof=0)) if len(seg) > 1 else 0.0
    return out


def process_camera(
    folder: str,
    mp_path: Path,
    gt_path: Path,
    *,
    window: int,
    k_sigma: float,
) -> Tuple[List[dict], Optional[dict]]:
    cam = parse_camera(folder)
    if cam is None:
        return [], None
    cx, cy, cz = cam
    az = azimuth_bin(cx, cz)

    mp_df = pd.read_csv(mp_path)
    gt_df = load_gt_csv(gt_path)
    mp_frames = set(mp_df["frame_id"].dropna().astype(int).unique())
    gt_frames = set(gt_df["Frame"].dropna().astype(int).unique())
    frames = sorted(mp_frames & gt_frames)
    if len(frames) < 3:
        return [], None

    hips = []
    for fid in frames:
        gt_abs = extract_gt_coords(gt_df, fid)
        M = hip_center(gt_abs)
        if M is not None:
            hips.append((fid, M))
    if len(hips) < 2:
        return [], None
    m0 = hips[0][1]
    m_final = hips[-1][1]
    D = m_final - m0
    d_norm = float(np.linalg.norm(D))
    if d_norm < 1e-6:
        return [], None
    D_hat = D / d_norm

    per_frame: Dict[int, Dict[str, np.ndarray]] = {}
    for fid in frames:
        gt_abs = extract_gt_coords(gt_df, fid)
        mp_abs = extract_mp_coords(mp_df, fid)
        M = hip_center(gt_abs)
        Hmp = hip_center(mp_abs)
        if M is None or Hmp is None:
            continue
        gt_rel = to_relative(gt_abs, M)
        mp_rel = flip_mp_y(to_relative(mp_abs, Hmp))
        s_gt = torso_scale(gt_rel)
        s_mp = torso_scale(mp_rel)
        if s_gt is None or s_mp is None:
            continue
        scale = s_gt / s_mp
        mp_scaled = {k: v * scale for k, v in mp_rel.items()}
        per_frame[fid] = {}
        for joint in JOINTS:
            if joint not in gt_rel or joint not in mp_scaled:
                continue
            per_frame[fid][joint] = mp_scaled[joint] - gt_rel[joint]

    valid_frames = sorted(per_frame.keys())
    if len(valid_frames) < 3:
        return [], None

    meta = {
        "folder_name": folder,
        "camera_x": cx,
        "camera_y": cy,
        "camera_z": cz,
        "height_label": y_folder(cy),
        "azimuth_bin": az,
        "azimuth_label": AZ_LABELS[az],
        "D_norm": d_norm,
        "n_frames": len(valid_frames),
        "window": window,
        "k_sigma": k_sigma,
    }

    rows: List[dict] = []
    for joint in JOINTS:
        fids = [f for f in valid_frames if joint in per_frame[f]]
        if len(fids) < 3:
            continue
        E = np.stack([per_frame[f][joint] for f in fids], axis=0)
        proj = (E @ D_hat)[:, None] * D_hat[None, :]
        eps = E - proj
        eps_norm = np.linalg.norm(eps, axis=1)
        eps_bar = moving_mean_center(eps, window)
        resid = np.linalg.norm(eps - eps_bar, axis=1)
        sigma = moving_std_scalar(resid, window)
        sigma_floor = max(float(np.median(sigma)) * 0.1, 1e-4)
        sigma_use = np.maximum(sigma, sigma_floor)
        thresh = k_sigma * sigma_use
        keep = resid <= thresh

        for i, fid in enumerate(fids):
            rows.append({
                "folder_name": folder,
                "camera_x": cx,
                "camera_y": cy,
                "camera_z": cz,
                "height_label": y_folder(cy),
                "azimuth_bin": az,
                "azimuth_label": AZ_LABELS[az],
                "frame_id": fid,
                "joint": joint,
                "E_norm": float(np.linalg.norm(E[i])),
                "eps_norm": float(eps_norm[i]),
                "eps_bar_norm": float(np.linalg.norm(eps_bar[i])),
                "resid_norm": float(resid[i]),
                "sigma": float(sigma_use[i]),
                "threshold": float(thresh[i]),
                "keep": bool(keep[i]),
                "window": window,
                "k_sigma": k_sigma,
                "D_norm": d_norm,
            })
    return rows, meta


def make_plots(df: pd.DataFrame, out_dir: Path):
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)

    rej = (
        df.groupby("joint")["keep"]
        .apply(lambda s: 1.0 - float(s.mean()))
        .reindex(JOINTS)
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(len(rej)), rej.values, color="#e74c3c", alpha=0.85)
    ax.set_xticks(range(len(rej)))
    ax.set_xticklabels(rej.index, rotation=35, ha="right")
    ax.set_ylabel("Rejection rate")
    ax.set_title("MA noise rejection rate by joint (all cameras)")
    ax.set_ylim(0, max(0.05, float(rej.max()) * 1.2))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "reject_rate_by_joint.png", dpi=140)
    plt.close(fig)

    piv = (
        df.groupby(["joint", "azimuth_bin"])["keep"]
        .apply(lambda s: 1.0 - float(s.mean()))
        .unstack("azimuth_bin")
        .reindex(JOINTS)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(
        piv.values, aspect="auto", cmap="YlOrRd", vmin=0,
        vmax=max(0.01, float(np.nanmax(piv.values))),
    )
    ax.set_xticks(range(8))
    ax.set_xticklabels([f"{i}:{AZ_LABELS[i]}" for i in range(8)])
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index)
    ax.set_title("Rejection rate · joint × azimuth")
    fig.colorbar(im, ax=ax, label="reject rate")
    fig.tight_layout()
    fig.savefig(out_dir / "reject_rate_heatmap.png", dpi=140)
    plt.close(fig)

    example = "CapturedFrames_3.0_1.0_0.0"
    sub = df[(df["folder_name"] == example) & (df["joint"] == "LEFT_KNEE")].sort_values(
        "frame_id"
    )
    if sub.empty:
        example = df["folder_name"].iloc[0]
        sub = df[(df["folder_name"] == example) & (df["joint"] == "LEFT_KNEE")].sort_values(
            "frame_id"
        )
    if not sub.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sub["frame_id"], sub["eps_norm"], "o-", color="#2980b9", ms=4,
                label=r"$||\varepsilon||$")
        ax.plot(sub["frame_id"], sub["eps_bar_norm"], "--", color="#27ae60",
                label=r"MA $||\bar{\varepsilon}||$")
        ax.plot(sub["frame_id"], sub["threshold"], ":", color="#95a5a6",
                label=r"threshold $K\sigma$")
        bad = sub[~sub["keep"]]
        if not bad.empty:
            ax.scatter(bad["frame_id"], bad["eps_norm"], c="#e74c3c", s=40, zorder=5,
                       label="rejected")
        ax.set_xlabel("Frame")
        ax.set_ylabel(r"$||\varepsilon||$ (walk-orthogonal)")
        ax.set_title(f"{example} · LEFT_KNEE · MA noise rejection")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "example_timeseries_LEFT_KNEE.png", dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df.loc[df["keep"], "eps_norm"], bins=50, alpha=0.7, label="keep",
            color="#2980b9", density=True)
    ax.hist(df.loc[~df["keep"], "eps_norm"], bins=50, alpha=0.7, label="rejected",
            color="#e74c3c", density=True)
    ax.set_xlabel(r"$||\varepsilon||$")
    ax.set_ylabel("density")
    ax.set_title(r"$||\varepsilon||$ distribution: keep vs rejected")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "eps_norm_hist.png", dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="MA noise rejection")
    parser.add_argument("--max_cameras", type=int, default=None)
    parser.add_argument("--window", type=int, default=7)
    parser.add_argument("--k-sigma", type=float, default=3.0)
    args = parser.parse_args()

    mp_csvs = sorted(MP_BASE.glob("Y=*/CapturedFrames_*.csv"))
    if args.max_cameras:
        mp_csvs = mp_csvs[: args.max_cameras]
    if not mp_csvs:
        print(f"No MediaPipe CSV under: {MP_BASE}")
        sys.exit(1)

    print("MA noise rejection (Plan B coords)")
    print(f"  window={args.window}  K={args.k_sigma}")
    print(f"  cameras: {len(mp_csvs)}")
    print(f"  out: {OUT_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: List[dict] = []
    metas: List[dict] = []
    missing = empty = 0
    t0 = time.time()

    for i, mp_path in enumerate(mp_csvs, 1):
        folder = mp_path.stem
        if i == 1 or i % 50 == 0 or i == len(mp_csvs):
            print(f"  [{i}/{len(mp_csvs)}] {folder}", flush=True)
        gt_path = find_gt_csv_for_camera(folder, INPUT_DIR)
        if gt_path is None:
            missing += 1
            continue
        rows, meta = process_camera(
            folder, mp_path, gt_path,
            window=args.window, k_sigma=args.k_sigma,
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
    # lean CSV
    df.to_csv(OUT_DIR / "ma_noise_frame_joint.csv", index=False)

    gcols = [
        "folder_name", "camera_x", "camera_y", "camera_z",
        "height_label", "azimuth_bin", "azimuth_label", "joint",
    ]
    by_cam = df.groupby(gcols, as_index=False).agg(
        n_frames=("frame_id", "nunique"),
        n_keep=("keep", "sum"),
        reject_rate=("keep", lambda s: 1.0 - float(s.mean())),
        mean_eps_norm=("eps_norm", "mean"),
    )
    keep_mean = (
        df[df["keep"]]
        .groupby(gcols, as_index=False)["eps_norm"]
        .mean()
        .rename(columns={"eps_norm": "mean_eps_norm_keep"})
    )
    by_cam = by_cam.merge(keep_mean, on=gcols, how="left")
    by_cam.to_csv(OUT_DIR / "ma_noise_by_camera_joint.csv", index=False)

    by_joint = (
        df.groupby("joint", as_index=False)
        .agg(
            n=("keep", "count"),
            reject_rate=("keep", lambda s: 1.0 - float(s.mean())),
            mean_eps_norm=("eps_norm", "mean"),
        )
    )
    by_joint.to_csv(OUT_DIR / "ma_noise_by_joint.csv", index=False)

    if metas:
        pd.DataFrame(metas).to_csv(OUT_DIR / "ma_noise_camera_meta.csv", index=False)

    make_plots(df, PLOT_DIR)

    rej = 1.0 - float(df["keep"].mean())
    summary = [
        "# MA noise rejection summary",
        "",
        f"- cameras: {df['folder_name'].nunique()}",
        f"- rows: {len(df)}",
        f"- window: {args.window}",
        f"- K_sigma: {args.k_sigma}",
        f"- missing_gt: {missing}",
        f"- empty: {empty}",
        f"- global_reject_rate: {rej:.4f}",
        f"- mean_|eps|: {df['eps_norm'].mean():.4f}",
        f"- mean_|eps|_keep: {df.loc[df['keep'], 'eps_norm'].mean():.4f}",
        f"- elapsed_sec: {time.time() - t0:.1f}",
        "",
        "## Reject rate by joint",
        "",
        by_joint.sort_values("reject_rate", ascending=False).to_string(index=False),
        "",
        f"Plots: {PLOT_DIR}",
        "See docs/06_MOVING_AVERAGE_NOISE_REJECTION.md",
    ]
    (OUT_DIR / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(f"done ({time.time() - t0:.1f}s)  reject_rate={rej:.3f}")
    print(f"  cameras={df['folder_name'].nunique()} rows={len(df)}")
    print(f"  summary: {OUT_DIR / 'SUMMARY.md'}")
    print(f"  plots: {PLOT_DIR}")


if __name__ == "__main__":
    main()
