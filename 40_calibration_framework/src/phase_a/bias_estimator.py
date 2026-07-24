"""
phase_a/bias_estimator.py — Phase A: バイアステーブルの推定（Model 2〜4）

提案書との対応:
  §4.1  Phase A: Calibration phase（補正パラメータを作る段階）
  §4.3  Calibration 出力: Bias parameters / correction table
  §4.5  補正テーブル CSV のイメージ (joint, height_bin, azimuth_bin, metric, bias_mean, ...)
  §6.3  Model 2: Joint-wise Constant Bias Correction  b_j = mean(e_j)
  §6.4  Model 3: Height-wise Bias Correction          b_{j,h} = mean(e_{j,h})
  §6.5  Model 4: View-bin Bias Correction             b_{j,h,a} = mean(e_{j,h,a})
  §7.1  基本原則: 補正式の構造は人間が設計, パラメータ値はデータから推定
  §7.2  平均誤差推定: b = mean(e) または median(e)
  §17.6 信頼度 (bias_std, n, reliability_weight)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Sequence

from ..config import JOINT_COLS_ANGLE, OUTPUT
from ..features import apply_all_bins, compute_bin_stats


# ──────────────────────────────────────────────────────────────────
# Model 2: Joint-wise Constant Bias  §6.3
# ──────────────────────────────────────────────────────────────────

def estimate_joint_bias(df: pd.DataFrame, joint_cols: Sequence[str] = JOINT_COLS_ANGLE) -> pd.DataFrame:
    """
    Model 2: 関節ごとの定数バイアス推定。

    入力: calib セット (angle_mae df: 行=カメラ位置, 列=関節 MAE)
    出力: joint × (bias_mean, bias_std, n) のテーブル

    §6.3 補正式: x_corr = x_mp - b_j
    b_j = mean(e_j) を全カメラ位置・全高さ層にわたって計算。
    利用可能なデータが unsigned MAE のため b_j = +mean(MAE) とする（過大推定注意）。
    """
    records = []
    for joint in joint_cols:
        if joint not in df.columns:
            continue
        vals = df[joint].dropna()
        records.append({
            "joint":       joint,
            "model":       "Model2_JointWise",
            "bias_mean":   float(vals.mean()),
            "bias_median": float(vals.median()),
            "bias_std":    float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "n":           int(len(vals)),
        })

    return pd.DataFrame(records)


# ──────────────────────────────────────────────────────────────────
# Model 3: Height-wise Bias  §6.4
# ──────────────────────────────────────────────────────────────────

def estimate_height_bias(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    height_col: str = "height_bin",
) -> pd.DataFrame:
    """
    Model 3: 関節 × カメラ高さ層ごとのバイアス推定。

    入力: calib セット (angle_mae df + height_bin 列)
    出力: (joint, height_bin) × (bias_mean, bias_std, n) のテーブル

    §6.4 補正式: x_corr = x_mp - b_{j,h}
    b_{j,h} = mean(e_{j,h}) over all cameras in height layer h
    """
    if height_col not in df.columns:
        raise ValueError(f"height_bin 列が見つかりません。apply_all_bins() を先に呼び出してください。")

    records = []
    for h_bin, grp in df.groupby(height_col):
        for joint in joint_cols:
            if joint not in grp.columns:
                continue
            vals = grp[joint].dropna()
            records.append({
                "joint":       joint,
                "height_bin":  h_bin,
                "height_label": grp["height_label"].iloc[0] if "height_label" in grp.columns else str(h_bin),
                "model":       "Model3_HeightWise",
                "bias_mean":   float(vals.mean()),
                "bias_median": float(vals.median()),
                "bias_std":    float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
                "n":           int(len(vals)),
            })

    tbl = pd.DataFrame(records)
    tbl["reliability_weight"] = _compute_reliability(tbl["n"], tbl["bias_std"])
    return tbl


# ──────────────────────────────────────────────────────────────────
# Model 4: View-bin Bias  §6.5  ← 中心モデル
# ──────────────────────────────────────────────────────────────────

def estimate_viewbin_bias(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    n_azimuth: int = 8,
    n_distance: int = 1,
    min_samples: int = 5,
) -> pd.DataFrame:
    """
    Model 4（中心モデル）: 関節 × 高さビン × 方位角ビン ごとのバイアス推定。

    入力: calib セット (angle_mae df + camera feature 列)
    出力: §4.5 のテーブル形式 (joint, height_bin, azimuth_bin[, distance_bin], metric, bias_mean, ...)

    §6.5 補正式: x_corr = x_mp - b_{j,h,a}
    b_{j,h,a} = mean(e_{j,h,a})

    §17.4 ビン粒度と「覚えただけ」問題: n_azimuth をハイパーパラメータとして
          grid search で最適化する (grid_search.py 参照)。
    §17.6 信頼度: n が小さい / bias_std が大きいビンは reliability_weight が低い。

    Parameters
    ----------
    min_samples : ビン内サンプル数の下限。これ未満のビンは bias_mean = NaN として
                  補正をスキップする（§11.4 bin 安定性）。
    """
    # ビン付与  §8
    df = apply_all_bins(df, n_azimuth=n_azimuth, n_distance=n_distance)

    group_cols = ["height_bin", "azimuth_bin"]
    if n_distance > 1:
        group_cols.append("distance_bin")

    records = []
    for keys, grp in df.groupby(group_cols):
        if isinstance(keys, (int, float)):
            keys = (keys,)

        for joint in joint_cols:
            if joint not in grp.columns:
                continue
            vals = grp[joint].dropna()
            n = len(vals)

            # §11.4 サンプル数が閾値未満のビンは信頼性が低い → bias=NaN
            bias_mean   = float(vals.mean())   if n >= min_samples else float("nan")
            bias_median = float(vals.median()) if n >= min_samples else float("nan")
            bias_std    = float(vals.std(ddof=1)) if n > 1 else 0.0

            row = {"joint": joint, "metric": "angle_mae"}
            for col, val in zip(group_cols, keys):
                row[col] = val
            if "height_label" in grp.columns:
                row["height_label"] = grp["height_label"].iloc[0]
            row.update({
                "n_azimuth":     n_azimuth,
                "n_distance":    n_distance,
                "model":         "Model4_ViewBin",
                "bias_mean":     bias_mean,
                "bias_median":   bias_median,
                "bias_std":      bias_std,
                "n":             n,
            })
            records.append(row)

    tbl = pd.DataFrame(records)
    if len(tbl) > 0:
        tbl["reliability_weight"] = _compute_reliability(tbl["n"], tbl["bias_std"])
    return tbl


# ──────────────────────────────────────────────────────────────────
# 保存・読み込み  §4.3 Calibration 出力
# ──────────────────────────────────────────────────────────────────

def save_bias_table(tbl: pd.DataFrame, name: str) -> Path:
    """
    バイアステーブルを CSV として出力ディレクトリに保存する。

    §4.5 補正テーブル CSV: calibration 後に outputs/bias_tables/ に格納し
         Phase B (phase_b/corrector.py) が読み込む。
    """
    out_dir = OUTPUT["bias_tables"]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.csv"
    tbl.to_csv(path, index=False)
    print(f"[save_bias_table] Saved: {path} ({len(tbl)} rows)")
    return path


def load_bias_table(name: str) -> pd.DataFrame:
    """
    保存済みバイアステーブルを読み込む。Phase B §4.2 で使用。
    """
    path = OUTPUT["bias_tables"] / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Bias table not found: {path}")
    return pd.read_csv(path)


# ──────────────────────────────────────────────────────────────────
# 信頼度スコア  §17.6
# ──────────────────────────────────────────────────────────────────

def _compute_reliability(n_series: pd.Series, std_series: pd.Series) -> pd.Series:
    """
    §17.6 補正値の信頼度 w ∈ [0, 1]

    w = tanh(n / 100) * exp(-std / 30)
      - n が大きいほど 1 に近づく（サンプル数十分）
      - std が小さいほど 1 に近づく（ばらつき少ない）
    既定 λ=1 の場合: corrected = raw - w * bias_mean
    """
    n   = n_series.fillna(0).to_numpy(dtype=float)
    std = std_series.fillna(30.0).to_numpy(dtype=float)
    w   = np.tanh(n / 100.0) * np.exp(-std / 30.0)
    return pd.Series(np.clip(w, 0.0, 1.0), index=n_series.index)
