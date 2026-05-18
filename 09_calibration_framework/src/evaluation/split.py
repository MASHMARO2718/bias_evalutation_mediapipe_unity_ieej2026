"""
evaluation/split.py — データ分割（Camera Split / Height Hold-out）

提案書との対応:
  §8    データ分割と評価戦略
  §8.1  基本方針: 補正パラメータ推定用と評価用を必ず分離
  §8.2  分割案 A: Camera Split (70/15/15)
  §8.3  分割案 B: Height Hold-out (Y=0.5/1.0/1.5 → train, Y=2.0 → test)
  §17.4 View-bin 感度分析: 分割後の各セットで n を確認
  §17.5 Known-view / Unknown-view の二系統評価
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple

from ..config import SPLIT_RATIO, RANDOM_SEED, HEIGHT_HOLDOUT_TEST, HEIGHT_HOLDOUT_TRAIN


# ──────────────────────────────────────────────────────────────────
# §8.2 Camera Split
# ──────────────────────────────────────────────────────────────────

def camera_split(
    df: pd.DataFrame,
    camera_col: str = "folder_name",
    ratio: Dict[str, float] = SPLIT_RATIO,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    カメラ位置を calib / val / test に分割する。

    §8.2 Camera Split: 70% cameras → calibration, 15% → validation, 15% → test
    分割はカメラ単位（同一カメラの全フレームが同一 split に入る）。

    「同じデータで推定して同じデータだけ評価した」批判を避けるために必須。
    §4.7 推奨研究デザインの手順 1 に対応。

    Returns
    -------
    (df_calib, df_val, df_test)
    """
    cameras = df[camera_col].unique()
    rng = np.random.default_rng(seed)
    rng.shuffle(cameras)

    n = len(cameras)
    n_calib = int(np.floor(n * ratio["calib"]))
    n_val   = int(np.floor(n * ratio["val"]))

    calib_cams = cameras[:n_calib]
    val_cams   = cameras[n_calib:n_calib + n_val]
    test_cams  = cameras[n_calib + n_val:]

    df_calib = df[df[camera_col].isin(calib_cams)].copy()
    df_val   = df[df[camera_col].isin(val_cams)].copy()
    df_test  = df[df[camera_col].isin(test_cams)].copy()

    print(f"[camera_split] total cameras={n}  "
          f"calib={len(calib_cams)}({len(df_calib)} rows)  "
          f"val={len(val_cams)}({len(df_val)} rows)  "
          f"test={len(test_cams)}({len(df_test)} rows)")
    return df_calib, df_val, df_test


# ──────────────────────────────────────────────────────────────────
# §8.3 Height Hold-out
# ──────────────────────────────────────────────────────────────────

def height_holdout_split(
    df: pd.DataFrame,
    train_heights: list = HEIGHT_HOLDOUT_TRAIN,
    test_heights:  list = HEIGHT_HOLDOUT_TEST,
    y_col: str = "camera_y",
    tol: float = 0.05,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    カメラ高さ Y を基準に train / test を分割する。

    §8.3 Height Hold-out:
      Training: Y ∈ {0.5, 1.0, 1.5}
      Testing:  Y ∈ {2.0}  （未知視点 = 俯瞰）

    これにより「既知視点では有効・未知視点（俯瞰）では限定的」という
    §13.2 研究成功条件の主張を検証できる。
    §17.5 Known-view / Unknown-view の二系統評価

    Parameters
    ----------
    tol : 高さの一致判定の許容誤差（浮動小数点誤差対策）
    """
    def in_heights(y: float, heights: list) -> bool:
        return any(abs(y - h) < tol for h in heights)

    mask_train = df[y_col].apply(lambda y: in_heights(y, train_heights))
    mask_test  = df[y_col].apply(lambda y: in_heights(y, test_heights))

    df_train = df[mask_train].copy()
    df_test  = df[mask_test].copy()

    print(f"[height_holdout] train heights={train_heights} ({len(df_train)} rows)  "
          f"test heights={test_heights} ({len(df_test)} rows)")
    return df_train, df_test


# ──────────────────────────────────────────────────────────────────
# 分割後の bin 分布確認（§17.4 感度分析補助）
# ──────────────────────────────────────────────────────────────────

def check_bin_coverage(
    df_calib: pd.DataFrame,
    df_test: pd.DataFrame,
    group_cols: list = ["height_bin", "azimuth_bin"],
    min_samples: int = 5,
) -> pd.DataFrame:
    """
    calib セットと test セットで bin ごとのサンプル数を比較する。

    §17.4 View-bin の細かさと「覚えただけ」問題:
      calib に存在するが test に存在しない bin（または n < min_samples の bin）が多いと
      「覚えた」だけになりやすい。この表でビン粒度の妥当性を判断する。

    Returns
    -------
    DataFrame: bin_key × (n_calib, n_test, covered_by_test)
    """
    available_cols = [c for c in group_cols if c in df_calib.columns and c in df_test.columns]
    if not available_cols:
        print("[check_bin_coverage] ビン列が見つかりません。apply_all_bins() を先に呼び出してください。")
        return pd.DataFrame()

    calib_counts = df_calib.groupby(available_cols).size().rename("n_calib")
    test_counts  = df_test.groupby(available_cols).size().rename("n_test")

    coverage = calib_counts.to_frame().join(test_counts, how="outer").fillna(0).astype(int)
    coverage["covered_by_test"] = coverage["n_test"] >= min_samples

    total_bins   = len(coverage)
    covered_bins = coverage["covered_by_test"].sum()
    print(f"[check_bin_coverage] {covered_bins}/{total_bins} bins covered by test (n>={min_samples})")
    return coverage.reset_index()
