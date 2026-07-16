"""
scripts/plot_angle_timeseries.py
================================
指定したカメラ視点・関節について

  GroundTruth 角度 / MediaPipe 角度 / 補正後角度

の時系列を並列グラフ（ペアプロット）で可視化する。

出力: scripts/output/angle_timeseries_<joint>_<camera>.png
         scripts/output/angle_timeseries_<joint>_<camera>.csv

使い方
------
    # デフォルト（側面 90° ビュー, L_Elbow / L_Knee）
    python scripts/plot_angle_timeseries.py

    # カメラ・関節を指定
    python scripts/plot_angle_timeseries.py \
        --camera CapturedFrames_4.0_1.0_0.0 \
        --joints L_Elbow R_Elbow L_Knee

    # 高さ層を変える
    python scripts/plot_angle_timeseries.py --height 0.5
"""

import sys
import re
import argparse
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ── プロジェクトルートを sys.path に追加 ──────────────────────────────────
HERE = Path(__file__).resolve().parent.parent   # 09_calibration_framework/
ROOT = HERE.parent                              # project root

sys.path.insert(0, str(HERE))
from src.config import DATA, OUTPUT

# ── 出力フォルダ ──────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# ── 関節定義（3点角）──────────────────────────────────────────────────────
JOINT_DEFS = {
    "L_Elbow": {
        "gt":  ["LeftUpperArm",  "LeftLowerArm",  "LeftHand"],
        "mp":  ["LEFT_SHOULDER", "LEFT_ELBOW",    "LEFT_WRIST"],
    },
    "R_Elbow": {
        "gt":  ["RightUpperArm", "RightLowerArm", "RightHand"],
        "mp":  ["RIGHT_SHOULDER","RIGHT_ELBOW",   "RIGHT_WRIST"],
    },
    "L_Knee": {
        "gt":  ["LeftUpperLeg",  "LeftLowerLeg",  "LeftFoot"],
        "mp":  ["LEFT_HIP",      "LEFT_KNEE",     "LEFT_ANKLE"],
    },
    "R_Knee": {
        "gt":  ["RightUpperLeg", "RightLowerLeg", "RightFoot"],
        "mp":  ["RIGHT_HIP",     "RIGHT_KNEE",    "RIGHT_ANKLE"],
    },
    "L_Shoulder": {
        "gt":  ["Chest",       "LeftUpperArm",  "LeftLowerArm"],
        "mp":  ["MID_SHOULDER","LEFT_SHOULDER", "LEFT_ELBOW"],
    },
    "R_Shoulder": {
        "gt":  ["Chest",        "RightUpperArm", "RightLowerArm"],
        "mp":  ["MID_SHOULDER", "RIGHT_SHOULDER","RIGHT_ELBOW"],
    },
    "L_Hip": {
        "gt":  ["Hips",    "LeftUpperLeg",  "LeftLowerLeg"],
        "mp":  ["MID_HIP", "LEFT_HIP",      "LEFT_KNEE"],
    },
    "R_Hip": {
        "gt":  ["Hips",    "RightUpperLeg", "RightLowerLeg"],
        "mp":  ["MID_HIP", "RIGHT_HIP",     "RIGHT_KNEE"],
    },
}

# ── ヘルパー関数 ─────────────────────────────────────────────────────────
def three_point_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """p2 を頂点とした 3点角（度）を返す。"""
    v1 = p1 - p2
    v2 = p3 - p2
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return np.nan
    cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return math.degrees(math.acos(cos_a))


def parse_camera_pos(name: str):
    """CapturedFrames_X_Y_Z → (x, y, z)"""
    m = re.search(r"CapturedFrames_([-\d.]+)_([\d.]+)_([-\d.]+)", name)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    raise ValueError(f"Cannot parse camera name: {name}")


def azimuth_bin(az_deg: float, n_az: int = 8) -> int:
    return int((az_deg + 180) / (360 / n_az)) % n_az


def height_bin(y: float) -> int:
    mapping = {0.5: 0, 1.0: 1, 1.5: 2, 2.0: 3}
    return mapping.get(round(y, 1), 0)


# ── データ読み込み ────────────────────────────────────────────────────────
def load_mp(camera_name: str, height: float) -> pd.DataFrame:
    """MediaPipe CSV を読み込み、MID_SHOULDER / MID_HIP を追加して返す。"""
    layer = f"Y={height}"
    mp_dir = ROOT / "02_mediapipe_processed" / "mediapipe_processed_csv" / layer
    csv_path = mp_dir / f"{camera_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"MediaPipe CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # MID_SHOULDER / MID_HIP を付加
    rows = []
    for fid, grp in df.groupby("frame_id"):
        ls = grp[grp["landmark"] == "LEFT_SHOULDER"]
        rs = grp[grp["landmark"] == "RIGHT_SHOULDER"]
        if not ls.empty and not rs.empty:
            rows.append({
                "frame_id": fid, "landmark": "MID_SHOULDER",
                "x": (ls["x"].iloc[0] + rs["x"].iloc[0]) / 2,
                "y": (ls["y"].iloc[0] + rs["y"].iloc[0]) / 2,
                "z": (ls["z"].iloc[0] + rs["z"].iloc[0]) / 2,
                "visibility": min(ls["visibility"].iloc[0], rs["visibility"].iloc[0]),
            })
        lh = grp[grp["landmark"] == "LEFT_HIP"]
        rh = grp[grp["landmark"] == "RIGHT_HIP"]
        if not lh.empty and not rh.empty:
            rows.append({
                "frame_id": fid, "landmark": "MID_HIP",
                "x": (lh["x"].iloc[0] + rh["x"].iloc[0]) / 2,
                "y": (lh["y"].iloc[0] + rh["y"].iloc[0]) / 2,
                "z": (lh["z"].iloc[0] + rh["z"].iloc[0]) / 2,
                "visibility": min(lh["visibility"].iloc[0], rh["visibility"].iloc[0]),
            })
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    return df


def load_gt() -> pd.DataFrame:
    gt_path = ROOT / "synced_joint_positions.csv"
    if not gt_path.exists():
        raise FileNotFoundError(f"GT CSV not found: {gt_path}")
    return pd.read_csv(gt_path).rename(columns={"Frame": "frame_id"})


def get_mp_point(df: pd.DataFrame, frame_id: int, name: str,
                 vis_thr: float = 0.5) -> np.ndarray | None:
    row = df[(df["frame_id"] == frame_id) & (df["landmark"] == name)]
    if row.empty:
        return None
    if row["visibility"].iloc[0] < vis_thr:
        return None
    return np.array([row["x"].iloc[0], row["y"].iloc[0], row["z"].iloc[0]])


def get_gt_point(df: pd.DataFrame, frame_id: int, name: str) -> np.ndarray | None:
    row = df[df["frame_id"] == frame_id]
    if row.empty:
        return None
    cols = [f"{name}_X", f"{name}_Y", f"{name}_Z"]
    if any(c not in df.columns for c in cols):
        return None
    vals = [row[c].iloc[0] for c in cols]
    if any(pd.isna(v) for v in vals):
        return None
    return np.array(vals)


# ── 角度時系列の計算 ──────────────────────────────────────────────────────
def compute_angles(mp_df: pd.DataFrame, gt_df: pd.DataFrame,
                   joint: str) -> pd.DataFrame:
    """
    共通フレームについて GT・MP の 3点角を計算して DataFrame で返す。
    """
    jdef = JOINT_DEFS[joint]
    common_frames = sorted(
        set(mp_df["frame_id"].unique()) & set(gt_df["frame_id"].unique())
    )

    records = []
    for fid in common_frames:
        # GT
        gp = [get_gt_point(gt_df, fid, n) for n in jdef["gt"]]
        gt_angle = three_point_angle(*gp) if all(p is not None for p in gp) else np.nan

        # MP
        mp = [get_mp_point(mp_df, fid, n) for n in jdef["mp"]]
        mp_angle = three_point_angle(*mp) if all(p is not None for p in mp) else np.nan

        records.append({"frame": fid, "gt": gt_angle, "mp": mp_angle})

    return pd.DataFrame(records).set_index("frame").sort_index()


def apply_correction(angles_df: pd.DataFrame, joint: str,
                     h_bin: int, az_bin: int) -> pd.Series:
    """
    View-bin バイアステーブル (Model 4) で補正した角度を返す。
    テーブルがなければ mp をそのまま返す。
    """
    bias_path = HERE / "outputs" / "bias_tables" / "model4_viewbin_az8.csv"
    if not bias_path.exists():
        print(f"  [warn] bias table not found: {bias_path}")
        return angles_df["mp"].copy()

    tbl = pd.read_csv(bias_path)
    row = tbl[(tbl["joint"] == joint) &
              (tbl["height_bin"] == h_bin) &
              (tbl["azimuth_bin"] == az_bin)]

    if row.empty:
        print(f"  [warn] no bias entry for {joint} h={h_bin} az={az_bin}")
        return angles_df["mp"].copy()

    bias = float(row["bias_mean"].iloc[0])
    print(f"  bias for {joint} (h_bin={h_bin}, az_bin={az_bin}): {bias:.2f}°")
    return angles_df["mp"] - bias


# ── プロット ─────────────────────────────────────────────────────────────
COLORS = {
    "gt":   "#2ecc71",   # 緑
    "mp":   "#e74c3c",   # 赤
    "corr": "#3498db",   # 青
}

def plot_pair(angles_df: pd.DataFrame, joint: str, camera: str,
              h_bin: int, az_bin: int, az_deg: float):
    """
    上段: GT / MP / 補正後 の重ね合わせ
    下段: MP誤差（|MP-GT|）と補正誤差（|corr-GT|）の比較
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.5]})
    fig.suptitle(
        f"Joint Angle Time-series  |  Joint: {joint}  |  Camera: {camera}\n"
        f"Azimuth: {az_deg:.1f}°  |  Height-bin: {h_bin}  |  Azimuth-bin: {az_bin}",
        fontsize=11, y=0.98,
    )

    frames = angles_df.index.to_numpy()
    gt   = angles_df["gt"].to_numpy()
    mp   = angles_df["mp"].to_numpy()
    corr = angles_df["corr"].to_numpy()

    # ─ 上段：角度重ね合わせ ─────────────────────────────────────────────
    ax0 = axes[0]
    ax0.plot(frames, gt,   color=COLORS["gt"],   lw=1.8, label="Ground Truth", zorder=3)
    ax0.plot(frames, mp,   color=COLORS["mp"],   lw=1.4, alpha=0.8,
             label="MediaPipe (raw)", zorder=2)
    ax0.plot(frames, corr, color=COLORS["corr"], lw=1.6, ls="--",
             label="Corrected (Model 4)", zorder=4)

    ax0.set_ylabel("Joint Angle (deg)", fontsize=10)
    ax0.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax0.yaxis.set_minor_locator(mticker.MultipleLocator(5))
    ax0.grid(axis="y", which="major", lw=0.5, alpha=0.5)
    ax0.grid(axis="y", which="minor", lw=0.2, alpha=0.3)
    ax0.legend(fontsize=9, loc="upper right", framealpha=0.9)

    # MAE を凡例横に表示
    mae_mp   = np.nanmean(np.abs(mp   - gt))
    mae_corr = np.nanmean(np.abs(corr - gt))
    ax0.text(0.01, 0.97,
             f"MAE(raw)={mae_mp:.1f}°   MAE(corr)={mae_corr:.1f}°   "
             f"Improvement={100*(mae_mp-mae_corr)/mae_mp:.1f}%",
             transform=ax0.transAxes, va="top", ha="left",
             fontsize=9, color="#333333",
             bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", pad=2))

    # ─ 下段：誤差比較 ───────────────────────────────────────────────────
    ax1 = axes[1]
    err_mp   = np.abs(mp   - gt)
    err_corr = np.abs(corr - gt)
    ax1.fill_between(frames, 0, err_mp,   color=COLORS["mp"],   alpha=0.35, label="|MP−GT|")
    ax1.fill_between(frames, 0, err_corr, color=COLORS["corr"], alpha=0.45, label="|Corr−GT|")
    ax1.plot(frames, err_mp,   color=COLORS["mp"],   lw=0.9, alpha=0.7)
    ax1.plot(frames, err_corr, color=COLORS["corr"], lw=1.1)
    ax1.set_ylabel("Abs Error (deg)", fontsize=10)
    ax1.set_xlabel("Frame", fontsize=10)
    ax1.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax1.grid(axis="y", lw=0.4, alpha=0.4)
    ax1.legend(fontsize=9, loc="upper right", framealpha=0.9)
    ax1.set_ylim(bottom=0)

    plt.tight_layout()

    # ── 保存 ─────────────────────────────────────────────────────────────
    safe_cam = camera.replace(".", "").replace("-", "m")
    stem = f"angle_timeseries_{joint}_{safe_cam}"
    png_path = OUT_DIR / f"{stem}.png"
    csv_path = OUT_DIR / f"{stem}.csv"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    angles_df.reset_index().to_csv(csv_path, index=False)
    print(f"  Saved: {png_path.name}")
    print(f"  Saved: {csv_path.name}")
    return png_path


# ── メイン ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="CapturedFrames_4.0_1.0_0.0",
                        help="カメラ名 (例: CapturedFrames_4.0_1.0_0.0)")
    parser.add_argument("--height", type=float, default=1.0,
                        help="カメラ高さ層 (0.5/1.0/1.5/2.0)")
    parser.add_argument("--joints", nargs="+",
                        default=["L_Elbow", "R_Elbow", "L_Knee", "R_Knee"],
                        help="プロットする関節名（複数可）")
    parser.add_argument("--n_az", type=int, default=8, help="方位角ビン数")
    args = parser.parse_args()

    # カメラ情報
    cx, cy, cz = parse_camera_pos(args.camera)
    az_deg = math.degrees(math.atan2(cx, cz))
    h_bin  = height_bin(cy)
    az_bin = azimuth_bin(az_deg, args.n_az)

    print(f"\nCamera : {args.camera}")
    print(f"  X={cx}, Y={cy}, Z={cz}")
    print(f"  Azimuth={az_deg:.1f}°  height_bin={h_bin}  azimuth_bin={az_bin}")
    print(f"Joints : {args.joints}")

    # データ読み込み
    print("\nLoading MediaPipe data ...")
    mp_df = load_mp(args.camera, args.height)
    print(f"  Frames: {mp_df['frame_id'].nunique()}")

    print("Loading Ground Truth data ...")
    gt_df = load_gt()
    print(f"  Frames: {gt_df['frame_id'].nunique()}")

    # 各関節をプロット
    for joint in args.joints:
        if joint not in JOINT_DEFS:
            print(f"  [skip] unknown joint: {joint}")
            continue
        print(f"\n--- {joint} ---")
        angles_df = compute_angles(mp_df, gt_df, joint)
        if angles_df.empty:
            print("  No common frames.")
            continue
        print(f"  Common frames: {len(angles_df)}")

        angles_df["corr"] = apply_correction(angles_df, joint, h_bin, az_bin)
        plot_pair(angles_df, joint, args.camera, h_bin, az_bin, az_deg)

    print(f"\nAll outputs saved to: {OUT_DIR}/")


if __name__ == "__main__":
    main()
