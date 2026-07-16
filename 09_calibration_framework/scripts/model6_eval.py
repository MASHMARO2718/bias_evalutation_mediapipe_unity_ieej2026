"""
scripts/model6_eval.py
======================
Model 6: 骨盤剛体制約の評価。

detailed_results.csv から LEFT_HIP / RIGHT_HIP の 3D 座標を取得し、
- GT 上の Z 差分布から τ を推定
- MediaPipe 出力の Z 差を τ でクリップ
- 補正前後の左右 Hip Δψ 相関 (r) を比較
- 補正前後の |Δψ| (Hip) を比較

出力
----
  outputs/results/model6_results.csv
  outputs/figures/fig_model6_hip_corr.png
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from src.config import DATA, OUTPUT, PELVIS_TAU_PERCENTILE

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


def main():
    print("Loading detailed_results.csv ...")
    df = pd.read_csv(DETAILED)

    # Left/Right Hip だけ取得
    hips = df[df["joint"].isin(["LEFT_HIP", "RIGHT_HIP"])].copy()
    print(f"  Hip rows: {len(hips):,}")

    # per-frame × camera にピボット
    piv = hips.pivot_table(
        index=["frame_id", "camera"],
        columns="joint",
        values=["gt_z", "mp_z", "delta_psi_deg"],
        aggfunc="first",
    )
    piv.columns = ["_".join(c) for c in piv.columns]
    piv = piv.reset_index().dropna()
    print(f"  Paired frames: {len(piv):,}")

    # ── τ 推定 ─────────────────────────────────────────────────────────────
    gt_z_L = piv["gt_z_LEFT_HIP"].values
    gt_z_R = piv["gt_z_RIGHT_HIP"].values
    depth_diff_gt = np.abs(gt_z_L - gt_z_R)
    tau = float(np.percentile(depth_diff_gt, PELVIS_TAU_PERCENTILE))
    print(f"\nτ = P{PELVIS_TAU_PERCENTILE}(|z_L^gt - z_R^gt|) = {tau:.4f}")
    print(f"  GT depth diff: mean={depth_diff_gt.mean():.4f}, max={depth_diff_gt.max():.4f}")

    # ── MediaPipe hip Z に制約適用 ─────────────────────────────────────────
    mp_z_L = piv["mp_z_LEFT_HIP"].values
    mp_z_R = piv["mp_z_RIGHT_HIP"].values

    z_mid    = (mp_z_L + mp_z_R) / 2.0
    delta_z  = mp_z_L - mp_z_R
    delta_z_c = np.clip(delta_z, -tau, tau)

    piv["mp_z_L_corr"] = z_mid + delta_z_c / 2.0
    piv["mp_z_R_corr"] = z_mid - delta_z_c / 2.0

    n_clipped = int(np.sum(np.abs(delta_z) > tau))
    print(f"  Clipped: {n_clipped}/{len(piv)} ({100*n_clipped/len(piv):.1f}%)")

    # ── 評価: Δψ 相関 ─────────────────────────────────────────────────────
    psi_L = piv["delta_psi_deg_LEFT_HIP"].values
    psi_R = piv["delta_psi_deg_RIGHT_HIP"].values
    r_raw = float(np.corrcoef(psi_L, psi_R)[0, 1])

    # 補正後の Δψ はZ補正から再計算する必要がある（近似: z_diff 変化量でΔψ を比例補正）
    # ここでは z_diff 変化比で Δψ を線形スケールする近似を使う
    scale_L = np.where(np.abs(delta_z) > 1e-6, delta_z_c / delta_z, 1.0)
    psi_L_c = psi_L * scale_L
    psi_R_c = psi_R * scale_L   # 同じフレームなので対称的に
    r_corr = float(np.corrcoef(psi_L_c, psi_R_c)[0, 1])

    print(f"\nHip Δψ correlation (Pearson r):")
    print(f"  Before Model 6: r = {r_raw:.3f}")
    print(f"  After  Model 6: r = {r_corr:.3f}  (Δ = {r_corr - r_raw:+.3f})")

    # ── 評価: |Δψ| 改善 ────────────────────────────────────────────────────
    abs_psi_raw_L  = np.abs(psi_L).mean()
    abs_psi_raw_R  = np.abs(psi_R).mean()
    abs_psi_corr_L = np.abs(psi_L_c).mean()
    abs_psi_corr_R = np.abs(psi_R_c).mean()
    imp_L = (abs_psi_raw_L - abs_psi_corr_L) / abs_psi_raw_L * 100
    imp_R = (abs_psi_raw_R - abs_psi_corr_R) / abs_psi_raw_R * 100

    print(f"\n|Δψ| improvement (Model 6):")
    print(f"  L_Hip: {abs_psi_raw_L:.2f}° → {abs_psi_corr_L:.2f}°  ({imp_L:+.1f}%)")
    print(f"  R_Hip: {abs_psi_raw_R:.2f}° → {abs_psi_corr_R:.2f}°  ({imp_R:+.1f}%)")

    # ── 結果 CSV 保存 ──────────────────────────────────────────────────────
    res = pd.DataFrame([{
        "tau": tau, "n_clipped": n_clipped, "clip_pct": 100*n_clipped/len(piv),
        "r_raw": r_raw, "r_corr": r_corr, "delta_r": r_corr - r_raw,
        "abs_psi_L_raw": abs_psi_raw_L, "abs_psi_L_corr": abs_psi_corr_L, "imp_L_pct": imp_L,
        "abs_psi_R_raw": abs_psi_raw_R, "abs_psi_R_corr": abs_psi_corr_R, "imp_R_pct": imp_R,
    }])
    out_csv = RESULTS / "model6_results.csv"
    res.to_csv(out_csv, index=False)
    print(f"\n  Saved: {out_csv}")

    # ── 図: Δψ 散布図（補正前後） ─────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14.0 / 2.54, 6.0 / 2.54))
    lim = 180

    ax = axes[0]
    ax.scatter(psi_L[::3], psi_R[::3], s=2, alpha=0.15, color="#4C72B0", rasterized=True)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_xlabel("L\_Hip $\\Delta\\psi$ [°]", fontsize=8)
    ax.set_ylabel("R\_Hip $\\Delta\\psi$ [°]", fontsize=8)
    ax.set_title(f"Before Model 6  (r={r_raw:.3f})", fontsize=8)
    ax.axhline(0, color="gray", lw=0.5); ax.axvline(0, color="gray", lw=0.5)

    ax2 = axes[1]
    ax2.scatter(psi_L_c[::3], psi_R_c[::3], s=2, alpha=0.15, color="#55A868", rasterized=True)
    ax2.set_xlim(-lim, lim); ax2.set_ylim(-lim, lim)
    ax2.set_xlabel("L\_Hip $\\Delta\\psi$ [°] (corrected)", fontsize=8)
    ax2.set_ylabel("R\_Hip $\\Delta\\psi$ [°] (corrected)", fontsize=8)
    ax2.set_title(f"After Model 6  (r={r_corr:.3f})", fontsize=8)
    ax2.axhline(0, color="gray", lw=0.5); ax2.axvline(0, color="gray", lw=0.5)

    fig.suptitle("Hip $\\Delta\\psi$ Anti-correlation Before/After Pelvis Rigidity Constraint",
                 fontsize=8, y=1.02)
    fig.tight_layout()
    out_fig = FIGURES / "fig_model6_hip_corr.png"
    fig.savefig(out_fig)
    plt.close(fig)
    print(f"  Saved: {out_fig}")


if __name__ == "__main__":
    main()
