#!/usr/bin/env python3
"""
カメラ位置と関節位置誤差の関連分析（Error · MC）— 案 B（近似）

docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md に基づき、既存の
  20_pose_correction/mediapipe_processed_csv  と
  10_input_videos/*/gt_joints.csv
を用いて Error·MC / cosφ を計算する。

案 B:
  1. 腰原点の相対座標（Error 用）
  2. MediaPipe の Y 反転（画像下向き → 上向き）
  3. 肩–腰距離でスケール合わせ
  4. MC_n = C - GT_world(n)（関節 n → カメラ。|MC| は関節ごとに異なる）
  5. cos φ = (Error · MC_n) / (|Error| |MC_n|)

注意: MP は pose_landmarks（画像正規化）のため軸は厳密には Unity と一致しない。
      結果は近似指標として解釈すること。

使用例:
  python run_error_mc_analysis.py --max_cameras 5
  python run_error_mc_analysis.py
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv  # noqa: E402

MP_BASE = Path(__file__).resolve().parent / "mediapipe_processed_csv"
INPUT_DIR = ROOT / "10_input_videos"
OUT_DIR = Path(__file__).resolve().parent / "error_mc_analysis" / "results"

FOLDER_RE = re.compile(
    r"CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)"
)
ALLOWED_Y = (0.5, 1.0, 1.5, 2.0)

# GT bone → MP landmark 名（32_direction_detection と同系）
GT_TO_MP = {
    "Hips": ["LEFT_HIP", "RIGHT_HIP"],
    "LeftShoulder": "LEFT_SHOULDER",
    "RightShoulder": "RIGHT_SHOULDER",
    "LeftLowerArm": "LEFT_ELBOW",
    "RightLowerArm": "RIGHT_ELBOW",
    "LeftLowerLeg": "LEFT_KNEE",
    "RightLowerLeg": "RIGHT_KNEE",
    "LeftFoot": "LEFT_ANKLE",
    "RightFoot": "RIGHT_ANKLE",
    "LeftHand": "LEFT_WRIST",
    "RightHand": "RIGHT_WRIST",
}

# Error を計算する関節（腰は相対化後ほぼ 0 なので除外）
JOINTS = [
    "LEFT_SHOULDER", "RIGHT_SHOULDER",
    "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST",
    "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE",
]

AZ_LABELS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def parse_camera(folder: str) -> Optional[Tuple[float, float, float]]:
    m = FOLDER_RE.fullmatch(folder)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def y_folder(y: float) -> str:
    for a in ALLOWED_Y:
        if abs(y - a) < 1e-6:
            return f"Y={a}"
    return f"Y={y}"


def azimuth_bin(x: float, z: float) -> int:
    """atan2(x, z) を 8 方位ビン（キャリブレーションと同系）。"""
    deg = math.degrees(math.atan2(x, z))
    if deg < 0:
        deg += 360.0
    return int((deg + 22.5) // 45.0) % 8


def extract_gt_coords(gt_df: pd.DataFrame, frame_id: int) -> Dict[str, np.ndarray]:
    row = gt_df[gt_df["Frame"] == frame_id]
    if row.empty:
        return {}
    r = row.iloc[0]
    coords: Dict[str, np.ndarray] = {}
    for gt_name, mp_name in GT_TO_MP.items():
        cols = (f"{gt_name}_X", f"{gt_name}_Y", f"{gt_name}_Z")
        if any(c not in r.index for c in cols):
            continue
        try:
            v = np.array([float(r[cols[0]]), float(r[cols[1]]), float(r[cols[2]])],
                         dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if isinstance(mp_name, list):
            for n in mp_name:
                coords[n] = v.copy()
        else:
            coords[mp_name] = v
    return coords


def extract_mp_coords(mp_df: pd.DataFrame, frame_id: int) -> Dict[str, np.ndarray]:
    sub = mp_df[mp_df["frame_id"] == frame_id]
    if sub.empty:
        return {}
    coords: Dict[str, np.ndarray] = {}
    for name in set(JOINTS + ["LEFT_HIP", "RIGHT_HIP"]):
        hit = sub[sub["landmark"] == name]
        if hit.empty:
            continue
        h = hit.iloc[0]
        try:
            coords[name] = np.array(
                [float(h["x"]), float(h["y"]), float(h["z"])], dtype=np.float64
            )
        except (TypeError, ValueError):
            continue
    return coords


def hip_center(coords: Dict[str, np.ndarray]) -> Optional[np.ndarray]:
    lh, rh = coords.get("LEFT_HIP"), coords.get("RIGHT_HIP")
    if lh is None or rh is None:
        return None
    return 0.5 * (lh + rh)


def to_relative(coords: Dict[str, np.ndarray], origin: np.ndarray) -> Dict[str, np.ndarray]:
    return {k: v - origin for k, v in coords.items()}


def flip_mp_y(coords: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    return {k: np.array([v[0], -v[1], v[2]], dtype=np.float64) for k, v in coords.items()}


def torso_scale(coords: Dict[str, np.ndarray]) -> Optional[float]:
    """肩–腰距離の平均（スケール合わせ用）。"""
    lens = []
    hc = hip_center(coords)
    if hc is None:
        # すでに相対化済みなら腰はほぼ 0
        hc = np.zeros(3)
    for sh in ("LEFT_SHOULDER", "RIGHT_SHOULDER"):
        if sh in coords:
            lens.append(float(np.linalg.norm(coords[sh] - hc)))
    if not lens:
        return None
    m = float(np.mean(lens))
    return m if m > 1e-8 else None


def process_camera(folder: str, mp_path: Path, gt_path: Path) -> List[dict]:
    cam = parse_camera(folder)
    if cam is None:
        return []
    cx, cy, cz = cam
    C = np.array([cx, cy, cz], dtype=np.float64)
    az = azimuth_bin(cx, cz)

    mp_df = pd.read_csv(mp_path)
    gt_df = load_gt_csv(gt_path)

    mp_frames = set(mp_df["frame_id"].dropna().astype(int).unique())
    gt_frames = set(gt_df["Frame"].dropna().astype(int).unique())
    frames = sorted(mp_frames & gt_frames)
    if not frames:
        return []

    rows: List[dict] = []
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

        for joint in JOINTS:
            if joint not in gt_rel or joint not in mp_scaled or joint not in gt_abs:
                continue
            # MC_n = C - GT_world(n): 関節 n からカメラへ（関節ごとに異なる）
            MC = C - gt_abs[joint]
            mc_norm = float(np.linalg.norm(MC))
            if mc_norm < 1e-8:
                continue

            gt_u = gt_rel[joint]
            md_u = mp_scaled[joint]
            err = md_u - gt_u
            err_norm = float(np.linalg.norm(err))
            dot = float(np.dot(err, MC))
            cos_phi = float(dot / (err_norm * mc_norm)) if err_norm > 1e-10 else np.nan

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
                "scale": scale,
                "M_x": float(M[0]),
                "M_y": float(M[1]),
                "M_z": float(M[2]),
                "GT_world_x": float(gt_abs[joint][0]),
                "GT_world_y": float(gt_abs[joint][1]),
                "GT_world_z": float(gt_abs[joint][2]),
                "MC_x": float(MC[0]),
                "MC_y": float(MC[1]),
                "MC_z": float(MC[2]),
                "MC_norm": mc_norm,
                "Error_x": float(err[0]),
                "Error_y": float(err[1]),
                "Error_z": float(err[2]),
                "Error_norm": err_norm,
                "error_dot_mc": dot,
                "cos_phi": cos_phi,
                "abs_cos_phi": abs(cos_phi) if np.isfinite(cos_phi) else np.nan,
            })
    return rows


def aggregate(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    by_cam_joint = (
        df.groupby(["folder_name", "camera_x", "camera_y", "camera_z",
                    "height_label", "azimuth_bin", "azimuth_label", "joint"],
                   as_index=False)
        .agg(
            n_frames=("frame_id", "nunique"),
            mean_cos_phi=("cos_phi", "mean"),
            mean_abs_cos_phi=("abs_cos_phi", "mean"),
            mean_error_dot_mc=("error_dot_mc", "mean"),
            mean_error_norm=("Error_norm", "mean"),
            median_abs_cos_phi=("abs_cos_phi", "median"),
        )
    )
    by_az_joint = (
        df.groupby(["height_label", "azimuth_bin", "azimuth_label", "joint"],
                   as_index=False)
        .agg(
            n=("cos_phi", "count"),
            mean_cos_phi=("cos_phi", "mean"),
            mean_abs_cos_phi=("abs_cos_phi", "mean"),
            mean_error_norm=("Error_norm", "mean"),
        )
    )
    overall = (
        df.groupby(["joint"], as_index=False)
        .agg(
            n=("cos_phi", "count"),
            mean_cos_phi=("cos_phi", "mean"),
            mean_abs_cos_phi=("abs_cos_phi", "mean"),
            mean_error_norm=("Error_norm", "mean"),
            frac_abs_cos_lt_0_3=("abs_cos_phi", lambda s: float((s < 0.3).mean())),
        )
    )
    return by_cam_joint, by_az_joint, overall


def plot_heatmap(by_az_joint: pd.DataFrame, out_path: Path):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    # 関節×方位の mean |cos φ|（全高さ平均）
    pivot = (
        by_az_joint.groupby(["joint", "azimuth_bin"])["mean_abs_cos_phi"]
        .mean()
        .unstack("azimuth_bin")
        .reindex(JOINTS)
    )
    if pivot.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(8))
    ax.set_xticklabels([f"{i}:{AZ_LABELS[i]}" for i in range(8)])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("mean |cos φ| = |Error·MC| / (|Error||MC|)  (Plan B approx)")
    ax.set_xlabel("Azimuth bin")
    fig.colorbar(im, ax=ax, label="mean |cos φ|")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Error·MC analysis (Plan B)")
    parser.add_argument("--max_cameras", type=int, default=None)
    parser.add_argument("--skip_frame_csv", action="store_true",
                        help="フレーム単位 CSV を書かない（集計のみ）")
    args = parser.parse_args()

    mp_csvs = sorted(MP_BASE.glob("Y=*/CapturedFrames_*.csv"))
    if args.max_cameras:
        mp_csvs = mp_csvs[: args.max_cameras]
    if not mp_csvs:
        print(f"No MediaPipe CSV under: {MP_BASE}")
        sys.exit(1)

    print("Plan B (approx): computing Error dot MC")
    print(f"  MP:  {MP_BASE}")
    print(f"  GT:  {INPUT_DIR}/*/gt_joints.csv")
    print(f"  cameras: {len(mp_csvs)}")
    print(f"  out: {OUT_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: List[dict] = []
    missing_gt = 0
    empty = 0
    t0 = time.time()

    for mp_path in tqdm(mp_csvs, desc="Error.MC"):
        folder = mp_path.stem
        gt_path = find_gt_csv_for_camera(folder, INPUT_DIR)
        if gt_path is None:
            missing_gt += 1
            continue
        rows = process_camera(folder, mp_path, gt_path)
        if not rows:
            empty += 1
            continue
        all_rows.extend(rows)

    if not all_rows:
        print("No valid rows (missing GT or no common frames)")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    by_cam, by_az, overall = aggregate(df)

    if not args.skip_frame_csv:
        frame_path = OUT_DIR / "error_mc_frame_joint.csv"
        df.to_csv(frame_path, index=False)
        print(f"  wrote {frame_path}  ({len(df)} rows)")

    by_cam.to_csv(OUT_DIR / "error_mc_by_camera_joint.csv", index=False)
    by_az.to_csv(OUT_DIR / "error_mc_by_azimuth_joint.csv", index=False)
    overall.to_csv(OUT_DIR / "error_mc_by_joint_overall.csv", index=False)

    plot_heatmap(by_az, OUT_DIR / "error_mc_abs_cos_heatmap.png")

    # 短い要約
    summary_lines = [
        "# Error · MC analysis summary (Plan B approx)",
        "",
        f"- cameras_processed: {df['folder_name'].nunique()}",
        f"- rows: {len(df)}",
        f"- missing_gt: {missing_gt}",
        f"- empty_result: {empty}",
        f"- elapsed_sec: {time.time() - t0:.1f}",
        "",
        "## Overall by joint (mean |cos φ|; closer to 0 ⇒ more orthogonal to camera ray)",
        "",
        overall.sort_values("mean_abs_cos_phi")[
            ["joint", "n", "mean_cos_phi", "mean_abs_cos_phi",
             "mean_error_norm", "frac_abs_cos_lt_0_3"]
        ].to_string(index=False),
        "",
        "## Global",
        f"- mean |cos φ|: {df['abs_cos_phi'].mean():.4f}",
        f"- median |cos φ|: {df['abs_cos_phi'].median():.4f}",
        f"- fraction |cos φ| < 0.3: {(df['abs_cos_phi'] < 0.3).mean():.3f}",
        "",
        "See docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md for interpretation and caveats.",
    ]
    summary_path = OUT_DIR / "SUMMARY.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"done ({time.time() - t0:.1f}s)")
    print(f"  mean |cos phi| = {df['abs_cos_phi'].mean():.4f}  "
          f"median = {df['abs_cos_phi'].median():.4f}")
    print(f"  summary: {summary_path}")


if __name__ == "__main__":
    main()
