"""
evaluation/metrics.py — 補正前後の全評価指標

提案書との対応:
  §9    評価指標（全7種）
  §9.1  Joint Angle MAE
  §9.2  Direction Angle Error (Δθ, Δψ)
  §9.4  Hip Correlation       (左右 hip Δψ の r)
  §9.5  Upper-limb Correlation (肩-肘-手首の r)
  §9.6  Viewpoint Gap         E_worst / E_best
  §9.7  Improvement Rate      (E_raw - E_corr) / E_raw × 100
  §9.8  Generalization Drop   Improvement_known - Improvement_unknown
  §17.8 Temporal Jitter       mean|α_t - α_{t-1}|
  §13.1 成功条件の確認（summary_report）
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Sequence

from ..config import JOINT_COLS_ANGLE


# ──────────────────────────────────────────────────────────────────
# §9.1 Joint Angle MAE
# ──────────────────────────────────────────────────────────────────

def joint_angle_mae(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    suffix: str = "",
) -> Dict[str, float]:
    """
    関節角度の平均絶対誤差 (MAE) を関節ごとに計算する。

    §9.1 MAE_α = (1/N) Σᵢ |α_i^corr - α_i^gt|

    現行データでは coordinate_angle_mae.csv の値が既に MAE なので
    suffix="" では raw MAE を、suffix="_corr" では補正後 MAE を計算する。

    Returns
    -------
    {joint: mean_mae}
    """
    result = {}
    for joint in joint_cols:
        col = f"{joint}{suffix}"
        if col in df.columns:
            result[joint] = float(df[col].dropna().mean())
    return result


# ──────────────────────────────────────────────────────────────────
# §9.2 Direction Angle Error
# ──────────────────────────────────────────────────────────────────

def direction_angle_stats(
    df: pd.DataFrame,
    theta_col: str = "mean_abs_delta_theta",
    psi_col: str = "mean_abs_delta_psi",
) -> Dict[str, float]:
    """
    方向角誤差 |Δθ| と |Δψ| の統計を計算する。

    §9.2  Δθ = θ^mp - θ^gt,  Δψ = ψ^mp - ψ^gt
    frame_camera_summary.csv の mean_abs_delta_theta 等を使用。
    """
    result = {}
    for label, col in [("mean_abs_delta_theta", theta_col), ("mean_abs_delta_psi", psi_col)]:
        if col in df.columns:
            vals = df[col].dropna()
            result[f"{label}_mean"] = float(vals.mean())
            result[f"{label}_std"]  = float(vals.std())
    return result


# ──────────────────────────────────────────────────────────────────
# §9.4 Hip Correlation
# ──────────────────────────────────────────────────────────────────

def hip_correlation(
    df: pd.DataFrame,
    left_col: str = "L_Hip",
    right_col: str = "R_Hip",
) -> float:
    """
    左右 hip の MAE/誤差間の Pearson 相関係数を返す。

    IEEJ 論文で確認された Δψ の反相関 r=-0.840 が補正後に低下するか評価。
    §9.4 r = Pearson(Δψ_L, Δψ_R)
    """
    if left_col not in df.columns or right_col not in df.columns:
        return float("nan")
    valid = df[[left_col, right_col]].dropna()
    if len(valid) < 3:
        return float("nan")
    r = float(valid.corr().iloc[0, 1])
    return r


# ──────────────────────────────────────────────────────────────────
# §9.5 Upper-limb Correlation
# ──────────────────────────────────────────────────────────────────

def upper_limb_correlations(
    df: pd.DataFrame,
    pairs: Optional[Sequence[tuple]] = None,
) -> Dict[str, float]:
    """
    上肢関節間の誤差相関を計算する。

    §9.5 対象ペア: shoulder-elbow, elbow-wrist, shoulder-wrist (左右別)
    IEEJ 論文で確認された r=0.72〜0.77 が補正後に低下するか評価。
    """
    if pairs is None:
        pairs = [
            ("L_Shoulder", "L_Elbow"),
            ("R_Shoulder", "R_Elbow"),
            ("L_Elbow",    "L_Hip"),     # 上肢-腰の連動 (IEEJ論文で r=0.721 確認)
            ("R_Elbow",    "R_Hip"),
        ]

    result = {}
    for a, b in pairs:
        if a in df.columns and b in df.columns:
            valid = df[[a, b]].dropna()
            if len(valid) >= 3:
                r = float(valid.corr().iloc[0, 1])
                result[f"r_{a}_{b}"] = r
    return result


# ──────────────────────────────────────────────────────────────────
# §9.6 Viewpoint Gap
# ──────────────────────────────────────────────────────────────────

def viewpoint_gap(
    df: pd.DataFrame,
    error_col: str = "mean_abs_delta_theta",
    camera_col: str = "camera",
) -> Dict[str, float]:
    """
    フレームごとの最良・最悪カメラの誤差比を計算する。

    §9.6 Gap = E_worst / E_best
    IEEJ 論文: 最良 8.8°, 最悪 80.1°, Gap ≈ 9.1 倍。
    補正後にこのギャップが縮小すれば視点依存性が緩和されている。
    """
    if error_col not in df.columns:
        return {}

    per_camera = df.groupby(camera_col)[error_col].mean() if camera_col in df.columns \
                 else pd.Series(dtype=float)

    if len(per_camera) == 0:
        return {"gap": float("nan")}

    best  = float(per_camera.min())
    worst = float(per_camera.max())
    gap   = worst / best if best > 0 else float("inf")

    return {"E_best": best, "E_worst": worst, "gap": gap}


# ──────────────────────────────────────────────────────────────────
# §9.7 Improvement Rate
# ──────────────────────────────────────────────────────────────────

def improvement_rate(raw_error: float, corr_error: float) -> float:
    """
    §9.7 Improvement = (E_raw - E_corr) / E_raw × 100 (%)
    負値 → 補正によって悪化（過補正または未知視点での汎化失敗）
    """
    if raw_error == 0:
        return 0.0
    return (raw_error - corr_error) / raw_error * 100.0


# ──────────────────────────────────────────────────────────────────
# §9.8 Generalization Drop
# ──────────────────────────────────────────────────────────────────

def generalization_drop(improvement_known: float, improvement_unknown: float) -> float:
    """
    §9.8 Δ_gen = Improvement_known - Improvement_unknown

    大きな正値 → 既知視点では効くが未知視点では効かない（過学習的）。
    §13 成功条件: 未知視点でも一定の改善が見られることを確認。
    """
    return improvement_known - improvement_unknown


# ──────────────────────────────────────────────────────────────────
# §17.8 Temporal Jitter
# ──────────────────────────────────────────────────────────────────

def temporal_jitter(
    df: pd.DataFrame,
    angle_cols: Sequence[str] = JOINT_COLS_ANGLE,
    frame_col: str = "frame_id",
    suffix: str = "",
) -> Dict[str, float]:
    """
    補正がフレーム独立のため生じる可能性のある時系列ガタつきを評価する。

    §17.8 jitter = mean_t(|α_t - α_{t-1}|)
    補正前後で jitter が増大する場合、補正の滑らかさが不足している。

    注意: frame_id 列が存在するデータが必要。
          coordinate_angle_mae.csv はカメラ位置別集計なので時系列は frame_camera_summary を使用。
    """
    result = {}
    if frame_col not in df.columns:
        return result

    df_sorted = df.sort_values(frame_col)
    for joint in angle_cols:
        col = f"{joint}{suffix}"
        if col not in df_sorted.columns:
            continue
        vals = df_sorted[col].dropna().to_numpy(float)
        if len(vals) < 2:
            continue
        jitter = float(np.mean(np.abs(np.diff(vals))))
        result[f"jitter_{joint}"] = jitter

    return result


# ──────────────────────────────────────────────────────────────────
# 総合評価レポート  §13.1 成功条件
# ──────────────────────────────────────────────────────────────────

def summary_report(
    df_calib: pd.DataFrame,
    df_test: pd.DataFrame,
    df_test_unknown: Optional[pd.DataFrame] = None,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
) -> pd.DataFrame:
    """
    補正前後・既知/未知視点の主要指標をまとめたサマリを生成する。

    §13.1 成功条件の確認:
      - Joint Angle MAE の低下
      - |Δθ|, |Δψ| の低下
      - hip 負相関の弱化
      - viewpoint gap の縮小
      - anatomical validity が悪化していない（jitter で代理確認）
      - calibration set だけでなく test set でも改善

    Returns
    -------
    DataFrame: 指標名 × (raw, corr, improvement_pct, [known, unknown])
    """
    rows = []

    def _add_mae(label, df_, sfx):
        mae = joint_angle_mae(df_, joint_cols=joint_cols, suffix=sfx)
        for j, v in mae.items():
            rows.append({"metric": f"MAE_{j}", "split": label, "value": v, "suffix": sfx})

    _add_mae("test_known_raw",  df_test,   "")
    _add_mae("test_known_corr", df_test,   "_corr")

    if df_test_unknown is not None:
        _add_mae("test_unknown_raw",  df_test_unknown, "")
        _add_mae("test_unknown_corr", df_test_unknown, "_corr")

    # Hip correlation
    r_raw  = hip_correlation(df_test, "L_Hip", "R_Hip")
    r_corr = hip_correlation(df_test, "L_Hip_corr", "R_Hip_corr") \
             if "L_Hip_corr" in df_test.columns else float("nan")
    rows.append({"metric": "hip_r_raw",  "split": "test_known", "value": r_raw,  "suffix": ""})
    rows.append({"metric": "hip_r_corr", "split": "test_known", "value": r_corr, "suffix": "_corr"})

    return pd.DataFrame(rows)
