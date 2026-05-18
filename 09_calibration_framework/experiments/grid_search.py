"""
experiments/grid_search.py — ビン分割ハイパーパラメータの Grid Search

提案書との対応:
  §9    bin 分割のハイパーパラメータ最適化
  §9.1  Grid Search: azimuth_bin_count, height_bin_count, distance_bin_count 等を探索
  §10   最適化の目的関数:
          Score = E_val + λ₁·G + λ₂·K + λ₃·N_small
          E_val  : validation set の補正後誤差
          G      : generalization gap = E_val - E_calib
          K      : bin 数
          N_small: サンプル数不足の bin 数
  §17.4 ビン粒度感度分析: 4/8/16 bin で calibration vs test 乖離を確認
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import itertools
import pandas as pd
import numpy as np
from typing import Dict, List

from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins
from src.evaluation.split import camera_split
from src.phase_a.bias_estimator import estimate_viewbin_bias
from src.phase_b.corrector import apply_viewbin_bias, compute_improvement
from src.config import JOINT_COLS_ANGLE, OUTPUT


# §8.3 探索候補  (02提案書 §8.3)
SEARCH_SPACE = {
    "n_azimuth":    [4, 8, 12, 16],
    "n_distance":   [1, 2],
    "min_samples":  [5, 10, 20],
    "regularize":   [0.0],   # 線形モデルとは別。バイアステーブルは正則化なし
}

# §10 目的関数の重み係数
LAMBDA_GAP   = 0.5   # λ₁: generalization gap への重み
LAMBDA_BINS  = 0.01  # λ₂: bin 数への重み（過細分割ペナルティ）
LAMBDA_SMALL = 0.1   # λ₃: サンプル不足 bin 数への重み


def objective_score(
    e_val: float,
    e_calib: float,
    n_bins: int,
    n_small_bins: int,
) -> float:
    """
    §10 目的関数:
    Score = E_val + λ₁·(E_val - E_calib) + λ₂·K + λ₃·N_small

    Score が小さいほど良い（補正誤差が小さく、過学習が少なく、bin が適度）。
    """
    g = e_val - e_calib   # generalization gap: 正値 = val > calib（過学習傾向）
    return e_val + LAMBDA_GAP * g + LAMBDA_BINS * n_bins + LAMBDA_SMALL * n_small_bins


def run_grid_search(max_configs: int = 50) -> pd.DataFrame:
    """
    Grid Search の実行。

    §17.4 感度分析:
      azimuth_bin 数を変化させたとき、
      calib 誤差と val 誤差の乖離がどう変わるかを記録する。

    Parameters
    ----------
    max_configs : 評価する設定数の上限（計算コスト削減のため）

    Returns
    -------
    DataFrame of all results, sorted by Score (ascending = better)
    """
    print("=" * 60)
    print("Grid Search: bin ハイパーパラメータ最適化")
    print("=" * 60)

    # データ準備
    df = load_angle_mae_all_layers()
    df_calib, df_val, _ = camera_split(df, camera_col="folder_name")

    # 全候補の組み合わせ
    keys = list(SEARCH_SPACE.keys())
    candidates = list(itertools.product(*[SEARCH_SPACE[k] for k in keys]))
    if len(candidates) > max_configs:
        rng = np.random.default_rng(42)
        candidates = [candidates[i] for i in rng.choice(len(candidates), max_configs, replace=False)]

    results = []
    for i, combo in enumerate(candidates):
        params = dict(zip(keys, combo))
        n_az   = params["n_azimuth"]
        n_dist = params["n_distance"]
        n_min  = params["min_samples"]

        # Phase A: calib セットでバイアス推定
        tbl = estimate_viewbin_bias(
            df_calib,
            joint_cols=JOINT_COLS_ANGLE,
            n_azimuth=n_az,
            n_distance=n_dist,
            min_samples=n_min,
        )
        n_total_bins = len(tbl)
        n_small_bins = int(tbl["n"].lt(n_min).sum())

        # Phase B: calib セットで自己評価（過学習確認用）
        df_calib_b = apply_viewbin_bias(
            df_calib.copy(), tbl, JOINT_COLS_ANGLE, n_az, n_dist
        )
        impr_calib = compute_improvement(df_calib_b, JOINT_COLS_ANGLE)
        e_calib    = float(impr_calib["corr_mean"].mean()) if len(impr_calib) > 0 else float("nan")

        # Phase B: val セットで評価（汎化性能）
        df_val_b = apply_viewbin_bias(
            df_val.copy(), tbl, JOINT_COLS_ANGLE, n_az, n_dist
        )
        impr_val = compute_improvement(df_val_b, JOINT_COLS_ANGLE)
        e_val    = float(impr_val["corr_mean"].mean()) if len(impr_val) > 0 else float("nan")

        score = objective_score(e_val, e_calib, n_total_bins, n_small_bins)

        row = {**params, "e_calib": e_calib, "e_val": e_val,
               "gen_gap": e_val - e_calib, "n_bins": n_total_bins,
               "n_small_bins": n_small_bins, "score": score}
        results.append(row)
        print(f"  [{i+1}/{len(candidates)}] n_az={n_az} n_dist={n_dist} "
              f"→ e_val={e_val:.2f} gap={e_val-e_calib:.2f} score={score:.3f}")

    df_results = pd.DataFrame(results).sort_values("score")

    out_path = OUTPUT["results"] / "grid_search_results.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(out_path, index=False)
    print(f"\n[Grid Search 完了] 結果保存: {out_path}")
    print("\nTop 5 設定:")
    print(df_results.head(5).to_string(index=False))

    return df_results


if __name__ == "__main__":
    run_grid_search()
