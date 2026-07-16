"""
scripts/gen_ablation_failure.py
================================
① n_az アブレーション表・図
② 低 R² ビン 失敗ケース分析
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from src.config import OUTPUT

RESULTS = OUTPUT["results"]
FIGURES = OUTPUT["figures"]
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

# ─── ① n_az Ablation ───────────────────────────────────────────────────────
def ablation_naz():
    gs = pd.read_csv(RESULTS / "grid_search_results.csv")
    # n_distance=1, min_samples=5 に絞って n_az 比較
    sub = gs[(gs["n_distance"] == 1) & (gs["min_samples"] == 5)].copy()
    sub = sub.sort_values("n_azimuth")

    print("=== n_az Ablation (n_dist=1, n_min=5) ===")
    print(sub[["n_azimuth", "e_calib", "e_val", "gen_gap", "n_bins", "score"]].to_string(index=False))

    # 改善率を計算（baseline = no correction ≈ mean raw MAE from evaluation_results）
    ev = pd.read_csv(RESULTS / "evaluation_results_az8.csv")
    raw_mae = ev[ev["model"] == "Model4_ViewBin"]["raw_mae"].mean() if "raw_mae" in ev.columns else None

    # 図: e_val と gen_gap vs n_az
    fig, ax1 = plt.subplots(figsize=(8.6 / 2.54, 5.5 / 2.54))
    ax2 = ax1.twinx()

    x = sub["n_azimuth"].values
    ax1.plot(x, sub["e_val"],  "o-", color="#4C72B0", lw=1.5, ms=5, label="Val MAE [°]")
    ax1.plot(x, sub["e_calib"],"s--",color="#55A868", lw=1.2, ms=4, label="Calib MAE [°]")
    ax2.bar(x, sub["gen_gap"], alpha=0.25, color="#C44E52", width=1.5, label="Gen Gap [°]")

    ax1.set_xlabel("Number of azimuth bins $n_{az}$", fontsize=8)
    ax1.set_ylabel("MAE [°]", fontsize=8)
    ax2.set_ylabel("Generalisation gap [°]", fontsize=8, color="#C44E52")
    ax2.tick_params(colors="#C44E52")
    ax1.set_title("Ablation: Effect of Azimuth Bin Count $n_{az}$", fontsize=8)
    ax1.set_xticks(x)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=7, framealpha=0.85)

    out = FIGURES / "fig_ablation_naz.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved: {out}")
    return sub


# ─── ② Failure Case Analysis ───────────────────────────────────────────────
def failure_analysis():
    lf = pd.read_csv(RESULTS / "local_linear_fits_az8.csv")

    # 低 R² ビンの定義
    lf["is_low_r2"] = lf["r2"] < 0.7

    # ビン別集計
    bin_stats = lf.groupby(["height_bin", "azimuth_bin"]).agg(
        mean_r2    = ("r2", "mean"),
        min_r2     = ("r2", "min"),
        mean_n     = ("n",  "mean"),
        low_r2_cnt = ("is_low_r2", "sum"),
        total_cnt  = ("r2", "count"),
    ).reset_index()
    bin_stats["low_r2_pct"] = bin_stats["low_r2_cnt"] / bin_stats["total_cnt"] * 100

    # サンプル数 vs R² 散布図
    fig, axes = plt.subplots(1, 2, figsize=(14.0 / 2.54, 5.5 / 2.54))

    # Left: n vs R²
    ax = axes[0]
    ax.scatter(lf[~lf["is_low_r2"]]["n"], lf[~lf["is_low_r2"]]["r2"],
               s=6, alpha=0.4, color="#4C72B0", label=r"$R^2 \geq 0.7$")
    ax.scatter(lf[lf["is_low_r2"]]["n"], lf[lf["is_low_r2"]]["r2"],
               s=8, alpha=0.6, color="#C44E52", label=r"$R^2 < 0.7$")
    ax.axhline(0.7, color="gray", lw=0.8, ls="--")
    ax.axvline(10, color="orange", lw=0.8, ls=":", label="n=10 threshold")
    ax.set_xlabel("Samples per bin $n$", fontsize=8)
    ax.set_ylabel("Local $R^2$", fontsize=8)
    ax.set_title("Sample Count vs $R^2$", fontsize=8)
    ax.legend(fontsize=6.5, framealpha=0.85)

    # Right: R² heatmap (mean over joints, all height bins)
    AZ_LABELS = ["N","NE","E","SE","S","SW","W","NW"]
    pivot = bin_stats.pivot_table(index="height_bin", columns="azimuth_bin",
                                  values="mean_r2", aggfunc="mean")
    pivot = pivot.sort_index(ascending=False)
    ax2 = axes[1]
    im = ax2.imshow(pivot.values, aspect="auto", vmin=0, vmax=1,
                    cmap="RdYlGn", interpolation="nearest")
    ax2.set_xticks(range(8)); ax2.set_xticklabels(AZ_LABELS, fontsize=7)
    ax2.set_yticks(range(4))
    ax2.set_yticklabels([f"Y={[2.0,1.5,1.0,0.5][i]:.1f}" for i in range(4)], fontsize=7)
    ax2.set_title("Mean $R^2$ Heatmap (all joints)", fontsize=8)
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            v = pivot.values[r, c]
            ax2.text(c, r, f"{v:.2f}", ha="center", va="center",
                     fontsize=6, color="black" if v > 0.4 else "white")
    fig.colorbar(im, ax=ax2, shrink=0.85).set_label("$R^2$", fontsize=7)

    fig.tight_layout()
    out = FIGURES / "fig_failure_analysis.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved: {out}")

    # Print failure stats
    print("\n=== Low-R2 Bin Analysis ===")
    print(f"Total bins: {len(lf)}, Low R2 (<0.7): {lf['is_low_r2'].sum()} ({lf['is_low_r2'].mean()*100:.1f}%)")
    low = lf[lf["is_low_r2"]]
    print(f"Mean n in low-R2 bins: {low['n'].mean():.1f}")
    print(f"Mean n in high-R2 bins: {lf[~lf['is_low_r2']]['n'].mean():.1f}")
    print(f"Pct of low-R2 bins with n<10: {(low['n'] < 10).mean()*100:.1f}%")

    # Save CSV
    out_csv = RESULTS / "failure_analysis.csv"
    bin_stats.to_csv(out_csv, index=False)
    print(f"  Saved: {out_csv}")
    return lf, bin_stats


if __name__ == "__main__":
    print("=== Ablation ===")
    ablation_naz()
    print("\n=== Failure Analysis ===")
    failure_analysis()
    print("\nDone.")
