"""
compute_paper_stats.py
======================
A4  Hip delta_theta / delta_psi abs mean+-SD  -> results/hip_stats.json
A3  Y-flip before/after comparison            -> results/yflip_comparison.json
A5  Correlation p-values                      -> results/pvalue_results.json
B3  MAE by camera height layer bar chart      -> results/mae_layer_bar.png
B1  MPJPE proxy from error_3d                 -> results/mpjpe_stats.json

データルートについて
--------------------
既定の ``DATA_ROOT`` は歴史的な作業コピー ``Zeval_DataSet`` を指す。旧フォルダ番号・
綴り（``4_MAE_HEATMAP``, ``11_direction_ditection``）がパスに残っている。

本リポジトリ（フォルダ番号整理後）に寄せる場合の対応例::

    REPO = Path(__file__).resolve().parents[1]
    DETAIL_CSV = REPO / "05_direction_detection/output/processed_data/detailed_results.csv"
    JOINT_SUM_AFTER = REPO / "05_direction_detection/output/processed_data/joint_summary.csv"
    MAE_CSVS = [REPO / f"03_joint_angle_mae/Y={y}/coordinate_angle_mae.csv"
                for y in ("0.5", "1.0", "1.5", "2.0")]

task_A3（Y-flip 前後比較）だけは「反転前」の出力が ``7_direction_ditection`` にしか
無い可能性が高く、Zeval 側の二重パイプラインを前提とする。リポのみでは A3 を
スキップするか、旧出力を別途用意する必要がある。
"""

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_ROOT      = Path(r"C:\projects\MOTIONTRACK\Zeval_DataSet")
DETAIL_CSV     = DATA_ROOT / "11_direction_ditection/output/processed_data/detailed_results.csv"
JOINT_SUM_AFTER  = DATA_ROOT / "11_direction_ditection/output/processed_data/joint_summary.csv"
JOINT_SUM_BEFORE = DATA_ROOT / "7_direction_ditection/output/processed_data/joint_summary.csv"
MAE_CSV_Y05    = DATA_ROOT / "4_MAE_HEATMAP/Y=0.5,1.5/coordinate_angle_mae.csv"
MAE_CSV_Y10    = DATA_ROOT / "4_MAE_HEATMAP/Y=1.0.2.0/coordinate_angle_mae.csv"

OUT_DIR = Path(__file__).parent / "results"
OUT_DIR.mkdir(exist_ok=True)

REPO_ROOT = Path(__file__).resolve().parents[1]
MAE_LAYER_CSVS = [
    (REPO_ROOT / f"03_joint_angle_mae/Y={y}/coordinate_angle_mae.csv", [float(y)])
    for y in ("0.5", "1.0", "1.5", "2.0")
]

warnings.filterwarnings("ignore")


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {Path(path).name}")


# ===========================================================================
# A4  Hip |delta_theta| / |delta_psi| mean+-SD
# ===========================================================================
def task_A4():
    print("\n=== A4: Hip stats ===")
    df = pd.read_csv(DETAIL_CSV, usecols=["joint", "delta_theta_deg", "delta_psi_deg"])

    results = {}
    for jnt in ["LEFT_HIP", "RIGHT_HIP"]:
        sub = df[df["joint"] == jnt]
        n = len(sub)
        ta = sub["delta_theta_deg"].abs()
        pa = sub["delta_psi_deg"].abs()
        results[jnt] = {
            "n": int(n),
            "theta_abs_mean": round(float(ta.mean()), 1),
            "theta_abs_sd":   round(float(ta.std()),  1),
            "psi_abs_mean":   round(float(pa.mean()),   1),
            "psi_abs_sd":     round(float(pa.std()),    1),
        }
        print(f"  {jnt}: n={n}  |dt|={results[jnt]['theta_abs_mean']}+-{results[jnt]['theta_abs_sd']}  "
              f"|dp|={results[jnt]['psi_abs_mean']}+-{results[jnt]['psi_abs_sd']}")

    save_json(results, OUT_DIR / "hip_stats.json")
    return results


# ===========================================================================
# A3  Y-flip before / after
# ===========================================================================
def task_A3():
    print("\n=== A3: Y-flip comparison ===")
    before = pd.read_csv(JOINT_SUM_BEFORE).set_index("joint")
    after  = pd.read_csv(JOINT_SUM_AFTER).set_index("joint")

    joints = sorted(set(before.index) | set(after.index))
    rows = {}
    for jnt in joints:
        b = round(float(before.loc[jnt, "theta_abs_mean"]), 1) if jnt in before.index else None
        a = round(float(after.loc[jnt,  "theta_abs_mean"]), 1) if jnt in after.index  else None
        imp = round(b - a, 1) if (b is not None and a is not None) else None
        rows[jnt] = {"before": b, "after": a, "improvement": imp}
        print(f"  {jnt:20s}: {b} -> {a}  (delta={imp})")

    save_json(rows, OUT_DIR / "yflip_comparison.json")
    return rows


# ===========================================================================
# B3  MAE by camera height layer (wide-format CSV)
# ===========================================================================
JOINT_MAP = {
    "L_Shoulder": "LEFT_SHOULDER",
    "R_Shoulder": "RIGHT_SHOULDER",
    "L_Elbow":    "LEFT_ELBOW",
    "R_Elbow":    "RIGHT_ELBOW",
    "L_Hip":      "LEFT_HIP",
    "R_Hip":      "RIGHT_HIP",
    "L_Knee":     "LEFT_KNEE",
    "R_Knee":     "RIGHT_KNEE",
}

def task_B3():
    print("\n=== B3: MAE by layer ===")
    layer_mae = {}
    # リポ: 4 CSV（推奨）。無ければ Zeval の2バケット CSV にフォールバック
    if all(p[0].is_file() for p in MAE_LAYER_CSVS):
        todo = MAE_LAYER_CSVS
    else:
        todo = [(MAE_CSV_Y05, [0.5, 1.5]), (MAE_CSV_Y10, [1.0, 2.0])]

    for df_path, layers in todo:
        df_tmp = pd.read_csv(df_path)
        for layer in layers:
            sub = df_tmp[np.isclose(df_tmp["camera_y"].astype(float), layer, atol=0.05)]
            mae_by_joint = {}
            for short, full in JOINT_MAP.items():
                if short in sub.columns and len(sub) > 0:
                    mae_by_joint[full] = round(float(sub[short].mean()), 1)
                else:
                    mae_by_joint[full] = None
            layer_mae[str(layer)] = mae_by_joint
            print(f"    Y={layer}: n={len(sub)}")

    save_json(layer_mae, OUT_DIR / "mae_by_layer.json")
    _plot_mae_bar(layer_mae)
    return layer_mae


def _plot_mae_bar(layer_mae):
    order = ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW",
             "LEFT_HIP", "RIGHT_HIP", "LEFT_KNEE", "RIGHT_KNEE"]
    labels = ["L.Shoulder", "R.Shoulder", "L.Elbow", "R.Elbow",
              "L.Hip", "R.Hip", "L.Knee", "R.Knee"]
    layers = ["0.5", "1.0", "1.5", "2.0"]
    colors = ["#4e79a7", "#59a14f", "#f28e2b", "#e15759"]

    x = np.arange(len(order))
    width = 0.2
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (layer, color) in enumerate(zip(layers, colors)):
        vals = [layer_mae.get(layer, {}).get(j) or 0 for j in order]
        ax.bar(x + i * width, vals, width, label=f"Y={layer}", color=color)

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Joint Angle MAE (deg)")
    ax.set_title("Joint Angle MAE by Camera Height Layer")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    out = OUT_DIR / "mae_layer_bar.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Saved: {out.name}")


# ===========================================================================
# A5  Pearson r + p-value from raw data
# ===========================================================================
def task_A5():
    print("\n=== A5: p-values (this takes ~1 min) ===")
    df = pd.read_csv(DETAIL_CSV,
                     usecols=["frame_id", "camera", "joint", "delta_theta_deg", "delta_psi_deg"])

    joints = sorted(df["joint"].unique())

    def compute_pairs(col, threshold=0.7):
        pivot = (df.pivot_table(index=["frame_id", "camera"], columns="joint",
                                values=col, aggfunc="first")
                   .reindex(columns=joints))
        pairs = []
        for i, j1 in enumerate(joints):
            for j2 in joints[i+1:]:
                valid = pivot[[j1, j2]].dropna()
                if len(valid) < 30:
                    continue
                r, p = stats.pearsonr(valid[j1], valid[j2])
                if abs(r) >= threshold:
                    pairs.append({
                        "joint1": j1, "joint2": j2,
                        "r": round(float(r), 4),
                        "p_value": float(p),
                        "p_str": f"{p:.2e}",
                        "significant_001": bool(p < 0.001),
                    })
        pairs.sort(key=lambda x: -abs(x["r"]))
        return pairs

    print("  Computing theta pairs...")
    theta_pairs = compute_pairs("delta_theta_deg")
    print("  Computing psi pairs...")
    psi_pairs   = compute_pairs("delta_psi_deg")

    print("  --- theta high-corr pairs ---")
    for row in theta_pairs:
        print(f"    {row['joint1']:20s} x {row['joint2']:20s}  r={row['r']:7.4f}  p={row['p_str']}")
    print("  --- psi high-corr pairs ---")
    for row in psi_pairs:
        print(f"    {row['joint1']:20s} x {row['joint2']:20s}  r={row['r']:7.4f}  p={row['p_str']}")

    save_json({"theta": theta_pairs, "psi": psi_pairs}, OUT_DIR / "pvalue_results.json")
    return theta_pairs, psi_pairs


# ===========================================================================
# B1  MPJPE proxy
# ===========================================================================
def task_B1():
    print("\n=== B1: MPJPE proxy ===")
    df = pd.read_csv(DETAIL_CSV, usecols=["joint", "error_3d"])

    overall = float(df["error_3d"].mean())
    per_joint = (df.groupby("joint")["error_3d"]
                   .agg(mean="mean", std="std", median="median", max="max")
                   .round(4))

    print(f"  Overall mean error_3d = {overall:.4f} (MediaPipe world units)")
    print(per_joint.to_string())

    result = {
        "overall_mean_error3d": round(overall, 4),
        "unit_note": (
            "MediaPipe world coordinates: mean bone length across skeleton ~ 1.0 (dimensionless). "
            "error_3d is Euclidean distance in those units. "
            "Approximate metric scale: 1 world unit ~ 1 m for a 1.7m subject. "
            "True MPJPE requires per-subject height normalization."
        ),
        "per_joint": per_joint.reset_index().to_dict(orient="records"),
    }
    save_json(result, OUT_DIR / "mpjpe_stats.json")
    return result


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("compute_paper_stats.py")
    print("=" * 60)

    hip_stats = task_A4()
    yflip     = task_A3()
    layer_mae = task_B3()
    theta_p, psi_p = task_A5()
    mpjpe     = task_B1()

    print("\n=== All tasks complete ===")
    print(f"Results in: {OUT_DIR}")
