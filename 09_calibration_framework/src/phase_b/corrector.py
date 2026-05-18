"""
phase_b/corrector.py — Phase B: 補正パラメータの適用（Model 2〜5）

提案書との対応:
  §4.2  Phase B: Correction / inference phase
        GT なしで新規 MediaPipe 出力に補正を適用する
  §4.3  Correction 入力: 新規 MP 出力 + カメラ情報 + precomputed bias table
  §4.4  補正式: x_corr = x_mp - bias  (または - λ·w·bias)
  §17.7 過補正抑制: corrected = raw - λ·bias  (λ ∈ [0,1])
  §17.6 信頼度重み: corrected = raw - w·bias   (w = reliability_weight)

注意:
  Phase B では GT は使わない。
  MPJPE 等の GT ベース指標は評価セットでのみ計算する（§4.2, §9.3）。
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Sequence

from ..config import JOINT_COLS_ANGLE, DEFAULT_LAMBDA
from ..features import apply_all_bins


# ──────────────────────────────────────────────────────────────────
# Model 2: Joint-wise Constant Bias  §6.3
# ──────────────────────────────────────────────────────────────────

def apply_joint_bias(
    df: pd.DataFrame,
    bias_table: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    lam: float = DEFAULT_LAMBDA,
    use_reliability: bool = True,
) -> pd.DataFrame:
    """
    Model 2: 関節ごとの定数バイアスを引く。

    §6.3 x_corr = x_mp - b_j
    §17.7 λ: x_corr = x_mp - λ·b_j  (λ=1.0 が既定)
    §17.6 信頼度重み w: x_corr = x_mp - λ·w·b_j

    Parameters
    ----------
    bias_table : estimate_joint_bias() の出力 (joint, bias_mean, reliability_weight)
    lam        : 補正強度 §17.7
    use_reliability : True なら reliability_weight を掛ける §17.6
    """
    df = df.copy()
    bias_map = bias_table.set_index("joint")

    for joint in joint_cols:
        if joint not in df.columns or joint not in bias_map.index:
            continue
        row = bias_map.loc[joint]
        b = float(row["bias_mean"])
        w = float(row.get("reliability_weight", 1.0)) if use_reliability else 1.0
        df[f"{joint}_corr"] = df[joint] - lam * w * b

    return df


# ──────────────────────────────────────────────────────────────────
# Model 3: Height-wise Bias  §6.4
# ──────────────────────────────────────────────────────────────────

def apply_height_bias(
    df: pd.DataFrame,
    bias_table: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    lam: float = DEFAULT_LAMBDA,
    use_reliability: bool = True,
) -> pd.DataFrame:
    """
    Model 3: 関節 × 高さ層ごとのバイアスを引く。

    §6.4 x_corr = x_mp - b_{j,h}
    df には height_bin 列が必要 (apply_all_bins() 済み)。
    """
    df = df.copy()
    bias_map = bias_table.set_index(["joint", "height_bin"])

    for joint in joint_cols:
        if joint not in df.columns:
            continue
        corrected = df[joint].copy()
        for idx in df.index:
            h_bin = df.at[idx, "height_bin"] if "height_bin" in df.columns else None
            key = (joint, h_bin)
            if key not in bias_map.index:
                continue
            row = bias_map.loc[key]
            b = float(row["bias_mean"])
            w = float(row.get("reliability_weight", 1.0)) if use_reliability else 1.0
            if not np.isnan(b):
                corrected.at[idx] = df.at[idx, joint] - lam * w * b
        df[f"{joint}_corr"] = corrected

    return df


# ──────────────────────────────────────────────────────────────────
# Model 4: View-bin Bias  §6.5  ← 中心モデル
# ──────────────────────────────────────────────────────────────────

def apply_viewbin_bias(
    df: pd.DataFrame,
    bias_table: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    n_azimuth: int = 8,
    n_distance: int = 1,
    lam: float = DEFAULT_LAMBDA,
    use_reliability: bool = True,
) -> pd.DataFrame:
    """
    Model 4（中心モデル）: 関節 × 高さ × 方位角ビンごとのバイアスを引く。

    §6.5 x_corr = x_mp - b_{j,h,a}
    §17.7 λ, §17.6 信頼度重み w を考慮:
      x_corr = x_mp - λ · w · b_{j,h,a}

    bias_table の bias_mean が NaN のビン（§11.4 サンプル不足）は補正をスキップ。
    """
    # ビン付与（Phase B でも同一のビン割り当てを適用）
    df = apply_all_bins(df, n_azimuth=n_azimuth, n_distance=n_distance)

    # グループキー構築
    key_cols = ["joint", "height_bin", "azimuth_bin"]
    if n_distance > 1:
        key_cols.append("distance_bin")

    bias_map = bias_table.set_index(key_cols) if all(c in bias_table.columns for c in key_cols) else None
    if bias_map is None:
        print("[WARNING] bias_table に必要な列が不足しています。補正をスキップします。")
        return df

    df = df.copy()
    for joint in joint_cols:
        if joint not in df.columns:
            continue
        corrected = df[joint].copy().astype(float)

        for idx in df.index:
            key_vals = [joint, df.at[idx, "height_bin"], df.at[idx, "azimuth_bin"]]
            if n_distance > 1:
                key_vals.append(df.at[idx, "distance_bin"])
            key = tuple(key_vals)

            if key not in bias_map.index:
                continue
            row = bias_map.loc[key]

            # 複数行ヒットする場合（距離ビンが一意でない等）は最初の行を使用
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            b = float(row["bias_mean"])
            if np.isnan(b):
                continue   # §11.4 サンプル不足ビンはスキップ

            w = float(row.get("reliability_weight", 1.0)) if use_reliability else 1.0
            corrected.at[idx] = df.at[idx, joint] - lam * w * b

        df[f"{joint}_corr"] = corrected

    return df


# ──────────────────────────────────────────────────────────────────
# Model 5: Linear Parametric  §6.6
# ──────────────────────────────────────────────────────────────────

def apply_linear_correction(
    df: pd.DataFrame,
    beta_dict: Dict[str, np.ndarray],
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    lam: float = DEFAULT_LAMBDA,
) -> pd.DataFrame:
    """
    Model 5: 線形モデル β で予測した誤差 ê = Xβ を引く。

    §6.6 x_corr = x_mp - ê
    df には camera_y, distance, sin_azimuth, cos_azimuth, elevation_deg 列が必要。
    """
    from ..phase_a.linear_estimator import build_feature_matrix, predict_error

    df = df.copy()
    X = build_feature_matrix(df)

    for joint in joint_cols:
        if joint not in df.columns or joint not in beta_dict:
            continue
        e_hat = predict_error(X, beta_dict[joint])   # ê = Xβ
        df[f"{joint}_corr"] = df[joint].to_numpy(float) - lam * e_hat

    return df


# ──────────────────────────────────────────────────────────────────
# 改善率の計算  §9.7 Improvement Rate
# ──────────────────────────────────────────────────────────────────

def compute_improvement(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    suffix_raw: str = "",
    suffix_corr: str = "_corr",
) -> pd.DataFrame:
    """
    補正前後の改善率を計算する。

    §9.7 Improvement = (E_raw - E_corr) / E_raw × 100 (%)
    負値は「補正によって悪化した」ことを示す（過補正や未知視点での汎化失敗）。

    Returns
    -------
    DataFrame with columns: joint, raw_mean, corr_mean, improvement_pct
    """
    records = []
    for joint in joint_cols:
        raw_col  = f"{joint}{suffix_raw}"
        corr_col = f"{joint}{suffix_corr}"
        if raw_col not in df.columns or corr_col not in df.columns:
            continue

        raw_mean  = df[raw_col].dropna().mean()
        corr_mean = df[corr_col].dropna().mean()
        improvement = (raw_mean - corr_mean) / raw_mean * 100 if raw_mean != 0 else 0.0

        records.append({
            "joint":           joint,
            "raw_mean":        float(raw_mean),
            "corr_mean":       float(corr_mean),
            "improvement_pct": float(improvement),
        })

    return pd.DataFrame(records)
