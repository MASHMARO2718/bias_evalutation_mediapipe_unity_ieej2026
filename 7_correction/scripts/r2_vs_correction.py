"""
scripts/r2_vs_correction.py
============================
ビン内局所線形 R² と符号付き補正効果の相関を分析する。

仮説: R² が高いビンほど、signed bias 推定の精度が高く、補正効果が大きい。

手順
----
1. detailed_results.csv からビン別・関節別 signed correction を計算
2. local_linear_fits_az8.csv の R² と結合
3. Pearson 相関・散布図を出力

出力
----
  outputs/results/r2_vs_correction.csv
  outputs/figures/fig_r2_vs_correction.png
"""

import sys
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from src.config import DATA, OUTPUT, RANDOM_SEED

DETAILED = DATA["detailed_results"]
RESULTS  = OUTPUT["results"]
FIGURES  = OUTPUT["figures"]
FIGURES.mkdir(parents=True, exist_ok=True)

_JP = ["MS Gothic", "Meiryo", "Yu Gothic", "DejaVu Sans"]
_avail = {f.name for f in fm.fontManager.ttflist}
plt.rcParams.update({
    "font.family": next((f for f in _JP if f in _avail), "DejaVu Sans"),
    "font.size": 9, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
})

JOINT_MAP = {
    "LEFT_SHOULDER": "L_Shoulder", "RIGHT_SHOULDER": "R_Shoulder",
    "LEFT_ELBOW": "L_Elbow",       "RIGHT_ELBOW":    "R_Elbow",
    "LEFT_HIP":   "L_Hip",         "RIGHT_HIP":      "R_Hip",
    "LEFT_KNEE":  "L_Knee",        "RIGHT_KNEE":     "R_Knee",
}
N_AZIMUTH = 8


def parse_coords(camera_name):
    m = re.search(r"CapturedFrames_([-\d.]+)_([-\d.]+)_([-\d.]+)", camera_name)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else (None, None, None)


def compute_viewbin(az_deg, y, n_az=8):
    az_bin = int((az_deg + 180) / (360 / n_az)) % n_az
    y_map = {0.5: 0, 1.0: 1, 1.5: 2, 2.0: 3}
    return y_map.get(round(y, 1), 0), az_bin


def main():
    print("Loading detailed_results.csv ...")
    df = pd.read_csv(DETAILED)
    df = df[df["joint"].isin(JOINT_MAP.keys())].copy()

    coords = df["camera"].apply(parse_coords)
    df["cam_x"] = [c[0] for c in coords]
    df["cam_y"] = [c[1] for c in coords]
    df["cam_z"] = [c[2] for c in coords]
    df = df.dropna(subset=["cam_x"])

    df["distance"]    = np.sqrt(df["cam_x"]**2 + df["cam_z"]**2)
    df["azimuth_deg"] = np.degrees(np.arctan2(df["cam_x"], df["cam_z"]))

    bins = df.apply(lambda r: compute_viewbin(r["azimuth_deg"], r["cam_y"]), axis=1)
    df["height_bin"]  = [b[0] for b in bins]
    df["azimuth_bin"] = [b[1] for b in bins]
    df["joint_short"] = df["joint"].map(JOINT_MAP)

    # Camera split (same seed as signed_bias_eval.py)
    rng = np.random.default_rng(RANDOM_SEED)
    cameras = df["camera"].unique()
    perm = rng.permutation(len(cameras))
    n_calib = int(len(cameras) * 0.70)
    calib_cams = set(cameras[perm[:n_calib]])
    test_cams  = set(cameras[perm[n_calib + int(len(cameras)*0.15):]])

    calib_df = df[df["camera"].isin(calib_cams)]
    test_df  = df[df["camera"].isin(test_cams)]

    # ── 1. Bin-level signed bias (from calib) ──────────────────────────────
    calib_bias = calib_df.groupby(["joint_short", "height_bin", "azimuth_bin"]).agg(
        bias_signed_theta = ("delta_theta_deg", "mean"),
        abs_bias          = ("delta_theta_deg", lambda x: x.abs().mean()),
        n_calib           = ("delta_theta_deg", "count"),
    ).reset_index()

    # ── 2. Bin-level correction effect (on test) ───────────────────────────
    test_agg = test_df.groupby(["joint_short", "height_bin", "azimuth_bin"]).agg(
        raw_abs_theta  = ("delta_theta_deg", lambda x: x.abs().mean()),
        signed_mean    = ("delta_theta_deg", "mean"),
        n_test         = ("delta_theta_deg", "count"),
    ).reset_index()

    merged = test_agg.merge(calib_bias, on=["joint_short", "height_bin", "azimuth_bin"], how="inner")
    # Apply correction per sample using bin signed bias
    merged["corr_abs_theta"] = (merged["raw_abs_theta"] - merged["bias_signed_theta"]).abs()
    merged["improvement"] = (merged["raw_abs_theta"] - merged["corr_abs_theta"]) / merged["raw_abs_theta"] * 100
    merged["improvement"] = merged["improvement"].clip(-200, 200)   # cap outliers

    # ── 3. Join with local linear R² ───────────────────────────────────────
    lf = pd.read_csv(RESULTS / "local_linear_fits_az8.csv")
    lf = lf.rename(columns={"joint": "joint_short"})

    # Map lf joint names to short names
    lf_map = {
        "L_Shoulder": "L_Shoulder", "R_Shoulder": "R_Shoulder",
        "L_Elbow": "L_Elbow",       "R_Elbow": "R_Elbow",
        "L_Hip": "L_Hip",           "R_Hip": "R_Hip",
        "L_Knee": "L_Knee",         "R_Knee": "R_Knee",
    }
    lf = lf[lf["joint_short"].isin(lf_map)]

    combined = merged.merge(
        lf[["joint_short", "height_bin", "azimuth_bin", "r2", "n"]],
        on=["joint_short", "height_bin", "azimuth_bin"], how="inner"
    )

    # Filter bins with sufficient test samples
    combined = combined[combined["n_test"] >= 3]
    print(f"Combined bins for analysis: {len(combined)}")

    # ── 4. Correlation analysis ─────────────────────────────────────────────
    r_val = float(np.corrcoef(combined["r2"], combined["improvement"])[0, 1])
    print(f"\nPearson r(R2, improvement): {r_val:.3f}")
    print(f"Mean improvement when R2>=0.7: {combined[combined['r2']>=0.7]['improvement'].mean():.1f}%")
    print(f"Mean improvement when R2<0.7:  {combined[combined['r2']< 0.7]['improvement'].mean():.1f}%")

    # ── 5. Save & Plot ─────────────────────────────────────────────────────
    out_csv = RESULTS / "r2_vs_correction.csv"
    combined.to_csv(out_csv, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(14.0 / 2.54, 6.0 / 2.54))

    # Scatter: R2 vs improvement
    ax = axes[0]
    low  = combined[combined["r2"] <  0.7]
    high = combined[combined["r2"] >= 0.7]
    ax.scatter(low["r2"],  low["improvement"],  s=8, alpha=0.5, color="#C44E52", label=r"$R^2 < 0.7$")
    ax.scatter(high["r2"], high["improvement"], s=8, alpha=0.5, color="#4C72B0", label=r"$R^2 \geq 0.7$")
    # regression line
    z = np.polyfit(combined["r2"], combined["improvement"], 1)
    xl = np.linspace(0, 1, 100)
    ax.plot(xl, np.polyval(z, xl), "k--", lw=1.0, label=f"fit (r={r_val:.2f})")
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0.7, color="orange", lw=0.8, ls=":", alpha=0.7)
    ax.set_xlabel("Local $R^2$ (bin)", fontsize=8)
    ax.set_ylabel("Signed correction improvement [%]", fontsize=8)
    ax.set_title(f"$R^2$ vs Correction Effectiveness\n(Pearson r={r_val:.2f})", fontsize=8)
    ax.legend(fontsize=6.5, framealpha=0.85)
    ax.set_xlim(-0.05, 1.05)

    # Box plot by R2 quartile
    ax2 = axes[1]
    combined["r2_group"] = pd.cut(combined["r2"],
                                  bins=[0, 0.4, 0.7, 0.85, 1.01],
                                  labels=["0–0.4", "0.4–0.7", "0.7–0.85", "0.85–1.0"])
    groups = [combined[combined["r2_group"] == g]["improvement"].dropna().values
              for g in ["0–0.4", "0.4–0.7", "0.7–0.85", "0.85–1.0"]]
    bp = ax2.boxplot(groups, labels=["0–0.4", "0.4–0.7", "0.7–0.85", "0.85–1.0"],
                     patch_artist=True, medianprops={"color": "red", "lw": 1.5})
    colors = ["#C44E52", "#DD8452", "#55A868", "#4C72B0"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c); patch.set_alpha(0.7)
    ax2.axhline(0, color="gray", lw=0.5)
    ax2.set_xlabel("Local $R^2$ group", fontsize=8)
    ax2.set_ylabel("Improvement [%]", fontsize=8)
    ax2.set_title("Improvement by $R^2$ Quartile", fontsize=8)

    fig.tight_layout()
    out_fig = FIGURES / "fig_r2_vs_correction.png"
    fig.savefig(out_fig)
    plt.close(fig)
    print(f"\nSaved: {out_csv}")
    print(f"Saved: {out_fig}")


if __name__ == "__main__":
    main()
