"""
phase_b/pelvis.py — Model 6: 骨盤剛体制約補正

提案書との対応:
  §6.7  Model 6: Pelvis Rigidity Correction
        単眼3D推定では左右 hip の深度誤差に強い反相関が現れる
        （IEEJ 論文 Tab. correlation_psi: LEFT_HIP--RIGHT_HIP r=-0.840）。
        左右 hip の深度差を物理的に妥当な範囲 τ に制限する。

  §7.4  制約閾値推定: τ = P₉₅(|z_L - z_R|) on GT data
        手動チューニングなし。GT 分布の 95th percentile から自動推定。

  §4.2  Phase B: GT なしで clip を適用（τ は Phase A で推定済み）

対応するバイアス:
  IEEJ 論文の骨盤回転アーティファクト: 実際には剛体の骨盤なのに
  left/right hip の Δψ が r=-0.840 の強い負相関を示す現象。
"""

import numpy as np
import pandas as pd
from typing import Optional

from ..config import PELVIS_TAU_PERCENTILE


# ──────────────────────────────────────────────────────────────────
# Phase A: τ の推定  §7.4
# ──────────────────────────────────────────────────────────────────

def estimate_pelvis_tau(
    gt_z_left: np.ndarray,
    gt_z_right: np.ndarray,
    percentile: int = PELVIS_TAU_PERCENTILE,
) -> float:
    """
    GT データから左右 hip の Z 深度差の許容幅 τ を推定する。

    §7.4 τ = P₉₅(|z_L^gt - z_R^gt|)
    これにより「実際の人体で起こりうる最大深度差」を τ として採用する。

    Parameters
    ----------
    gt_z_left  : GT の左 hip Z 座標配列
    gt_z_right : GT の右 hip Z 座標配列
    percentile : 使用するパーセンタイル (既定 95)

    Returns
    -------
    tau : 骨盤深度差の許容上限値（メートル単位、world landmark スケール）
    """
    depth_diff = np.abs(gt_z_left - gt_z_right)
    tau = float(np.percentile(depth_diff, percentile))
    print(f"[estimate_pelvis_tau] P{percentile} = {tau:.4f}  "
          f"(mean={depth_diff.mean():.4f}, max={depth_diff.max():.4f})")
    return tau


# ──────────────────────────────────────────────────────────────────
# Phase B: 骨盤制約の適用  §6.7
# ──────────────────────────────────────────────────────────────────

def apply_pelvis_rigidity(
    df: pd.DataFrame,
    tau: float,
    z_left_col: str = "z_left_hip",
    z_right_col: str = "z_right_hip",
    out_left_col: str = "z_left_hip_corr",
    out_right_col: str = "z_right_hip_corr",
) -> pd.DataFrame:
    """
    左右 hip の深度差を τ でクリップし、中点を保持したまま再配分する。

    §6.7 制約: |z_L - z_R| < τ
    中点計算:   z_mid = (z_L + z_R) / 2
    深度差:     Δz    = z_L - z_R
    クリップ:   Δz'   = clip(Δz, -τ, τ)
    補正後:     z_L'  = z_mid + Δz'/2
                z_R'  = z_mid - Δz'/2

    この操作により:
    - 中点（骨盤中心深度）は保持される
    - 左右の差のみが τ 内に収まる
    - 単眼推定でよく現れる疑似骨盤回転アーティファクトを抑制する
      (IEEJ 論文で確認された r=-0.840 の反相関パターンへの対処)

    Parameters
    ----------
    df          : phase_b に入力される DataFrame
    tau         : Phase A で推定した許容深度差（estimate_pelvis_tau() の出力）
    z_*_col     : 入力 hip Z 列名
    out_*_col   : 出力（補正後）hip Z 列名
    """
    if z_left_col not in df.columns or z_right_col not in df.columns:
        print(f"[WARNING] pelvis correction: 列 {z_left_col} or {z_right_col} が存在しません。スキップ。")
        return df

    df = df.copy()

    z_L = df[z_left_col].to_numpy(float)
    z_R = df[z_right_col].to_numpy(float)

    z_mid = (z_L + z_R) / 2.0          # 中点（骨盤中心）
    delta_z = z_L - z_R                  # 左右差

    # §6.7 Δz' = clip(Δz, -τ, τ)
    delta_z_clipped = np.clip(delta_z, -tau, tau)

    # 補正後の座標
    df[out_left_col]  = z_mid + delta_z_clipped / 2.0
    df[out_right_col] = z_mid - delta_z_clipped / 2.0

    n_clipped = int(np.sum(np.abs(delta_z) > tau))
    print(f"[apply_pelvis_rigidity] tau={tau:.4f}, "
          f"clipped {n_clipped}/{len(df)} frames ({100*n_clipped/len(df):.1f}%)")
    return df


# ──────────────────────────────────────────────────────────────────
# 評価用: 補正前後の左右 hip 相関の変化  §9.4
# ──────────────────────────────────────────────────────────────────

def evaluate_hip_correlation(
    df: pd.DataFrame,
    raw_psi_left:  str = "psi_left_hip",
    raw_psi_right: str = "psi_right_hip",
    corr_psi_left:  Optional[str] = None,
    corr_psi_right: Optional[str] = None,
) -> dict:
    """
    左右 hip Δψ の Pearson 相関係数を補正前後で計算する。

    §9.4 Hip Correlation:
      骨盤剛体制約後に |r| が 0.840 から低下すれば補正が機能している証拠。
      r が依然として高い場合は単眼深度曖昧性が構造的限界として残っている (§12.2)。

    Returns
    -------
    {"r_raw": float, "r_corr": float (if available)}
    """
    result = {}

    if raw_psi_left in df.columns and raw_psi_right in df.columns:
        r_raw = float(df[[raw_psi_left, raw_psi_right]].dropna().corr().iloc[0, 1])
        result["r_raw"] = r_raw
        print(f"[hip_corr] raw  r(Δψ_L, Δψ_R) = {r_raw:.3f}")

    if corr_psi_left and corr_psi_right:
        if corr_psi_left in df.columns and corr_psi_right in df.columns:
            r_corr = float(df[[corr_psi_left, corr_psi_right]].dropna().corr().iloc[0, 1])
            result["r_corr"] = r_corr
            print(f"[hip_corr] corr r(Δψ_L, Δψ_R) = {r_corr:.3f}")

    return result
