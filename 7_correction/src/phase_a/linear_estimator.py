"""
phase_a/linear_estimator.py — Phase A: 線形パラメトリック補正の推定（Model 5）

提案書との対応:
  §6.6  Model 5: Linear Parametric Correction
        誤差 e をカメラ視点パラメータの連続関数で近似
        ê = β₀ + β₁Y + β₂D + β₃sin(φ) + β₄cos(φ) + β₅ε
        x_corr = x_mp - ê
  §7.3  最小二乗推定: min_β Σᵢ(eᵢ - êᵢ)² → β = (XᵀX)⁻¹Xᵀe
  §9    Grid Search との組み合わせで bin 内の局所線形モデルとして使用可能（02提案書）

利点:
  - 離散ビンではなく連続視点変数に対応
  - View-bin Bias (Model 4) との比較対象として有効  §6.6
  - 係数 β が解釈可能（正負で「この方向のカメラほど誤差が大きい」等）
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..config import JOINT_COLS_ANGLE, LINEAR_FEATURES, OUTPUT


# ──────────────────────────────────────────────────────────────────
# 特徴量行列の構築
# ──────────────────────────────────────────────────────────────────

def build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    §6.5 Model 5 の特徴量ベクトルを作成する。

    x = [1, Y, D, sin(φ), cos(φ), ε]
      1         : 切片 (intercept)
      Y         : camera_y   カメラ高さ
      D         : distance   水平距離
      sin(φ)    : sin_azimuth
      cos(φ)    : cos_azimuth
      ε         : elevation_deg  仰角

    Returns
    -------
    X : shape (n_samples, 6) の float64 配列
    """
    required = ["camera_y", "distance", "sin_azimuth", "cos_azimuth", "elevation_deg"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"特徴量列が不足しています: {missing}\n"
            "data_loader._add_camera_features() を呼び出してください。"
        )

    n = len(df)
    X = np.column_stack([
        np.ones(n),                          # 切片
        df["camera_y"].to_numpy(float),      # Y
        df["distance"].to_numpy(float),      # D
        df["sin_azimuth"].to_numpy(float),   # sin(φ)
        df["cos_azimuth"].to_numpy(float),   # cos(φ)
        df["elevation_deg"].to_numpy(float), # ε
    ])
    return X


# ──────────────────────────────────────────────────────────────────
# OLS 係数推定
# ──────────────────────────────────────────────────────────────────

def fit_linear_model(
    X: np.ndarray,
    e: np.ndarray,
    regularize: float = 0.0,
) -> np.ndarray:
    """
    最小二乗法で β = argmin Σᵢ(eᵢ - Xᵢβ)² を解く。

    §7.3 最小二乗推定:
      β = (XᵀX)⁻¹Xᵀe
    実装では scipy.linalg.lstsq を使用（逆行列の直接計算よりも数値的安定）。

    Parameters
    ----------
    X          : (n, p) 特徴量行列（build_feature_matrix() の出力）
    e          : (n,) 誤差ベクトル e = MP_value - GT_value
    regularize : L2 正則化強度 λ₂ ≥ 0。0 = 正則化なし（通常の OLS）。
                 §10 目的関数のハイパーパラメータ regularization_strength に対応。

    Returns
    -------
    beta : (p,) 係数ベクトル
    """
    from scipy.linalg import lstsq

    if regularize > 0.0:
        # リッジ回帰: 解は (XᵀX + λI)⁻¹Xᵀe
        # 切片には正則化をかけない（慣例）
        n, p = X.shape
        reg_matrix = regularize * np.eye(p)
        reg_matrix[0, 0] = 0.0   # 切片を正則化対象外に
        XtX = X.T @ X + reg_matrix
        Xte = X.T @ e
        beta, _, _, _ = lstsq(XtX, Xte)
    else:
        beta, _, _, _ = lstsq(X, e)

    return beta


def predict_error(X: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """
    学習済み β から誤差予測 ê = Xβ を計算する。

    §6.6 x_corr = x_mp - ê
    """
    return X @ beta


# ──────────────────────────────────────────────────────────────────
# 関節ごとに全モデルを学習
# ──────────────────────────────────────────────────────────────────

def fit_all_joints(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    regularize: float = 0.0,
    bin_mask: Optional[pd.Series] = None,
) -> Dict[str, np.ndarray]:
    """
    全関節に対して線形補正モデルを学習し、β の辞書を返す。

    §6.6 誤差を関節ごとに独立に最小二乗で推定。
    利用可能なデータが unsigned MAE の場合、e = +MAE とする（上限の近似）。

    Parameters
    ----------
    df       : calib セット (angle_mae + camera features)
    bin_mask : 特定 bin のみを使う場合の bool マスク（局所線形モデル用）
    regularize: L2 正則化強度（§9 Grid Search の regularization_strength）

    Returns
    -------
    beta_dict : {joint_name: beta_array(6,)}
    """
    X = build_feature_matrix(df)

    if bin_mask is not None:
        X_fit = X[bin_mask]
        df_fit = df[bin_mask]
    else:
        X_fit = X
        df_fit = df

    beta_dict = {}
    for joint in joint_cols:
        if joint not in df_fit.columns:
            continue
        e = df_fit[joint].to_numpy(float)
        valid = ~np.isnan(e)
        if valid.sum() < len(LINEAR_FEATURES):
            print(f"[WARNING] {joint}: サンプル数不足({valid.sum()}), スキップ")
            continue
        beta_dict[joint] = fit_linear_model(X_fit[valid], e[valid], regularize=regularize)

    return beta_dict


# ──────────────────────────────────────────────────────────────────
# 評価（R²・RMSE）  §11 局所線形性の評価
# ──────────────────────────────────────────────────────────────────

def evaluate_linear_fit(
    X: np.ndarray,
    e: np.ndarray,
    beta: np.ndarray,
) -> Dict[str, float]:
    """
    線形モデルの当てはまり指標を計算する。

    §11.1 決定係数 R² = 1 - Σ(eᵢ - êᵢ)² / Σ(eᵢ - ē)²
    §11.2 Local RMSE = sqrt(mean((eᵢ - êᵢ)²))
    §11.3 Local MAE  = mean(|eᵢ - êᵢ|)
    """
    e_hat = X @ beta
    residual = e - e_hat
    ss_res = np.sum(residual**2)
    ss_tot = np.sum((e - e.mean())**2)

    r2   = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    rmse = float(np.sqrt(np.mean(residual**2)))
    mae  = float(np.mean(np.abs(residual)))

    return {"r2": float(r2), "rmse": rmse, "local_mae": mae, "n": len(e)}


# ──────────────────────────────────────────────────────────────────
# 局所線形モデル（各 bin 内で個別に fit）  §7 局所線形補正モデル（02提案書）
# ──────────────────────────────────────────────────────────────────

def fit_local_linear_models(
    df: pd.DataFrame,
    joint_cols: Sequence[str] = JOINT_COLS_ANGLE,
    group_cols: Sequence[str] = ("height_bin", "azimuth_bin"),
    regularize: float = 0.0,
    min_samples: int = 6,
) -> pd.DataFrame:
    """
    各 bin 内で局所線形モデルを学習し、R²・係数を記録する。

    02提案書 §7 局所線形補正モデル:
      各 bin B_k 内で ê_{j,k} = xᵀβ_{j,k}
      β_{j,k} = argmin Σᵢ∈Bₖ (eᵢ - xᵢᵀβ)²

    02提案書 §11 局所線形性の評価:
      bin ごとに R², RMSE, Local MAE を記録する。

    Returns
    -------
    DataFrame with columns:
      *group_cols, joint, metric, r2, rmse, local_mae, n,
      beta_0..beta_5 (係数), reliability_weight
    """
    records = []
    for bin_keys, grp in df.groupby(list(group_cols)):
        if isinstance(bin_keys, (int, float)):
            bin_keys = (bin_keys,)

        if len(grp) < min_samples:
            continue   # §11.4 bin 安定性: サンプル不足はスキップ

        try:
            X_bin = build_feature_matrix(grp)
        except ValueError:
            continue

        for joint in joint_cols:
            if joint not in grp.columns:
                continue
            e = grp[joint].to_numpy(float)
            valid = ~np.isnan(e)
            if valid.sum() < min_samples:
                continue

            beta = fit_linear_model(X_bin[valid], e[valid], regularize=regularize)
            stats = evaluate_linear_fit(X_bin[valid], e[valid], beta)

            rec = dict(zip(group_cols, bin_keys))
            rec["joint"] = joint
            rec["metric"] = "angle_mae"
            rec.update(stats)
            for i, feat_name in enumerate(LINEAR_FEATURES):
                rec[f"beta_{i}_{feat_name}"] = float(beta[i])

            # 信頼度: R² が高く n が大きいほど 1 に近づく
            rec["reliability_weight"] = float(
                np.clip(np.tanh(stats["n"] / 50.0) * max(0, stats["r2"]), 0, 1)
            )
            records.append(rec)

    return pd.DataFrame(records)


# ──────────────────────────────────────────────────────────────────
# 保存・読み込み
# ──────────────────────────────────────────────────────────────────

def save_beta_dict(beta_dict: Dict[str, np.ndarray], name: str) -> Path:
    """β の辞書を JSON として保存する。Phase B で読み込む。"""
    out_dir = OUTPUT["bias_tables"]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    serializable = {k: v.tolist() for k, v in beta_dict.items()}
    path.write_text(json.dumps(serializable, indent=2))
    print(f"[save_beta_dict] Saved: {path}")
    return path


def load_beta_dict(name: str) -> Dict[str, np.ndarray]:
    """保存済み β の辞書を読み込む。"""
    path = OUTPUT["bias_tables"] / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Beta dict not found: {path}")
    raw = json.loads(path.read_text())
    return {k: np.array(v) for k, v in raw.items()}
