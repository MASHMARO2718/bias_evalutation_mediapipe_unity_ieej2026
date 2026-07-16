"""
scripts/gen_signed_figs.py
==========================
signed_bias_eval.py の出力から論文用図を生成する。

出力:
  outputs/figures/fig_signed_vs_unsigned.png   (M4S vs M4U vs Baseline)
  outputs/figures/fig_lambda_sensitivity.png   (λ 感度分析)
  outputs/figures/fig_signed_per_joint.png     (関節別改善率)
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

# ─── 日本語フォント ─────────────────────────────────────────────────────────
_JP = ["MS Gothic", "Meiryo", "Yu Gothic", "IPAGothic", "DejaVu Sans"]
_avail = {f.name for f in fm.fontManager.ttflist}
_jp_font = next((f for f in _JP if f in _avail), "DejaVu Sans")
plt.rcParams.update({
    "font.family":      _jp_font,
    "font.size":        9,
    "axes.linewidth":   0.8,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "figure.dpi":       200,
    "savefig.dpi":      300,
    "savefig.bbox":     "tight",
    "savefig.pad_inches": 0.05,
})

JOINTS = ["L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow",
          "L_Hip", "R_Hip", "L_Knee", "R_Knee"]
COLORS = {"M4S": "#4C72B0", "M4U": "#C44E52", "M2S": "#55A868", "baseline": "#888888"}


# ─── Fig 1: Signed vs Unsigned vs Baseline ─────────────────────────────────
def fig_signed_vs_unsigned():
    df = pd.read_csv(RESULTS / "signed_bias_results.csv")
    known = df[df["split"] == "known"].set_index("model")

    baseline = float(known.loc["M4S", "mean_abs_theta_raw"])
    models   = ["M4S", "M4U", "M2S"]
    labels   = ["Model 4S\n(Signed View-Bin)", "Model 4U\n(Unsigned View-Bin)", "Model 2S\n(Signed Joint-const)"]
    values_raw  = [baseline] * 3
    values_corr = [float(known.loc[m, "mean_abs_theta_corr"]) for m in models]

    x     = np.arange(len(models))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.0 / 2.54, 6.0 / 2.54))

    b1 = ax.bar(x - width/2, values_raw,  width, label="Before correction",
                color="#BBBBBB", alpha=0.85)
    b2 = ax.bar(x + width/2, values_corr, width, label="After correction",
                color=[COLORS.get(m, "#888") for m in models], alpha=0.9)

    # improvement label
    for i, (raw, corr) in enumerate(zip(values_raw, values_corr)):
        imp = (raw - corr) / raw * 100
        ypos = max(raw, corr) + 0.8
        col  = "#1060C0" if imp > 0 else "#C00000"
        ax.text(x[i] + width/2, ypos, f"{imp:+.1f}%",
                ha="center", va="bottom", fontsize=7, color=col, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("|Δθ| [°]", fontsize=8)
    ax.set_title("Correction Effect: Signed vs Unsigned Bias\n(Known-view test, mean |Δθ|)", fontsize=8)
    ax.legend(fontsize=7, framealpha=0.85)
    ax.set_ylim(0, max(values_raw + values_corr) * 1.25)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(10))

    out = FIGURES / "fig_signed_vs_unsigned.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved: {out}")


# ─── Fig 2: λ 感度分析 ──────────────────────────────────────────────────────
def fig_lambda_sensitivity():
    df = pd.read_csv(RESULTS / "lambda_sensitivity.csv")

    fig, ax = plt.subplots(figsize=(8.6 / 2.54, 5.5 / 2.54))
    ax.plot(df["lambda"], df["mean_abs_theta_corr"], "o-",
            color="#4C72B0", lw=1.6, ms=5, label="|Δθ| after correction")
    ax.axhline(df.loc[0, "mean_abs_theta_raw"] if "mean_abs_theta_raw" in df.columns
               else df["mean_abs_theta_corr"].iloc[0],
               color="#888", ls="--", lw=1.0, label="No correction (λ=0)")

    # mark optimal
    best_idx = df["mean_abs_theta_corr"].idxmin()
    ax.scatter(df.loc[best_idx, "lambda"], df.loc[best_idx, "mean_abs_theta_corr"],
               color="#C44E52", s=60, zorder=5, label=f"Optimal λ={df.loc[best_idx,'lambda']:.2f}")

    ax.set_xlabel("Correction strength λ", fontsize=8)
    ax.set_ylabel("|Δθ| [°]", fontsize=8)
    ax.set_title("λ Sensitivity Analysis\n(Model 4S, known-view test)", fontsize=8)
    ax.legend(fontsize=7, framealpha=0.85)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.25))

    out = FIGURES / "fig_lambda_sensitivity.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved: {out}")


# ─── Fig 3: 関節別改善率 ────────────────────────────────────────────────────
def fig_signed_per_joint():
    df = pd.read_csv(RESULTS / "signed_bias_per_joint.csv")
    df = df.set_index("joint_short").reindex(JOINTS).reset_index()

    fig, ax = plt.subplots(figsize=(12.0 / 2.54, 5.5 / 2.54))
    x = np.arange(len(df))
    width = 0.55

    bars = ax.bar(x, df["improvement"], width,
                  color=["#4C72B0" if v > 0 else "#C44E52" for v in df["improvement"]],
                  alpha=0.88)

    for bar, val in zip(bars, df["improvement"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(JOINTS, fontsize=7.5)
    ax.set_ylabel("Improvement [%]", fontsize=8)
    ax.set_title("Per-joint Improvement: Model 4S (Signed View-Bin, λ=1.0, known-view)", fontsize=8)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylim(0, max(df["improvement"]) * 1.15)

    out = FIGURES / "fig_signed_per_joint.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved: {out}")


if __name__ == "__main__":
    print("Generating figures...")
    fig_signed_vs_unsigned()
    fig_lambda_sensitivity()
    fig_signed_per_joint()
    print("Done.")
