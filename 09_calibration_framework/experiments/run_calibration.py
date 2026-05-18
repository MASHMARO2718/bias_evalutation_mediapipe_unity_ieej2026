"""
experiments/run_calibration.py — Phase A の実行スクリプト

Phase A の手順  §4.7 推奨研究デザイン:
  1. データ読み込み（全4層統合）
  2. カメラ分割 70/15/15  §8.2
  3. 高さホールドアウト分割  §8.3
  4. Model 2: 関節別定数バイアス推定  §6.3
  5. Model 3: 高さ別バイアス推定      §6.4
  6. Model 4: View-bin バイアス推定   §6.5  ← 中心モデル
  7. Model 5: 線形パラメトリック推定  §6.6
  8. バイアステーブルの保存  §4.5
"""

import sys
from pathlib import Path

# src を import パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins
from src.evaluation.split import camera_split, height_holdout_split, check_bin_coverage
from src.phase_a.bias_estimator import (
    estimate_joint_bias,
    estimate_height_bias,
    estimate_viewbin_bias,
    save_bias_table,
)
from src.phase_a.linear_estimator import (
    fit_all_joints,
    fit_local_linear_models,
    save_beta_dict,
)
from src.config import JOINT_COLS_ANGLE


def run(n_azimuth: int = 8, n_distance: int = 1, regularize: float = 0.0):
    """
    Phase A のメイン実行関数。

    Parameters
    ----------
    n_azimuth  : 方位角ビン数（§8.3 Grid Search のハイパーパラメータ）
    n_distance : 距離ビン数（1 = 分割なし）
    regularize : 線形モデルの L2 正則化強度
    """
    print("=" * 60)
    print(f"Phase A: Calibration  [n_azimuth={n_azimuth}, n_distance={n_distance}]")
    print("=" * 60)

    # ─────────────────────────────────────────────────
    # Step 1: データ読み込み
    # ─────────────────────────────────────────────────
    print("\n[Step 1] データ読み込み（全4層）")
    df = load_angle_mae_all_layers()   # §4.6 前論文の Unity データを使用
    print(f"  Total: {len(df)} rows, columns: {df.columns.tolist()}")

    # ─────────────────────────────────────────────────
    # Step 2a: Camera Split  §8.2
    # ─────────────────────────────────────────────────
    print("\n[Step 2a] Camera Split (70/15/15)")
    df_calib, df_val, df_test_cam = camera_split(df, camera_col="folder_name")

    # ─────────────────────────────────────────────────
    # Step 2b: Height Hold-out  §8.3
    # ─────────────────────────────────────────────────
    print("\n[Step 2b] Height Hold-out (train: Y<=1.5, test: Y=2.0)")
    df_train_h, df_test_h = height_holdout_split(df, y_col="camera_y")

    # ─────────────────────────────────────────────────
    # Step 3: ビン付与と coverage 確認  §17.4
    # ─────────────────────────────────────────────────
    print("\n[Step 3] ビン付与 & coverage 確認")
    df_calib_binned = apply_all_bins(df_calib, n_azimuth=n_azimuth, n_distance=n_distance)
    df_test_binned  = apply_all_bins(df_test_cam, n_azimuth=n_azimuth, n_distance=n_distance)
    coverage = check_bin_coverage(df_calib_binned, df_test_binned)
    coverage.to_csv(
        Path(__file__).parent / f"../outputs/results/bin_coverage_az{n_azimuth}.csv",
        index=False
    )

    # ─────────────────────────────────────────────────
    # Step 4: Model 2 — Joint-wise Constant Bias  §6.3
    # ─────────────────────────────────────────────────
    print("\n[Step 4] Model 2: Joint-wise Constant Bias")
    tbl_m2 = estimate_joint_bias(df_calib, joint_cols=JOINT_COLS_ANGLE)
    print(tbl_m2[["joint", "bias_mean", "bias_std", "n"]].to_string(index=False))
    save_bias_table(tbl_m2, "model2_joint_bias")

    # ─────────────────────────────────────────────────
    # Step 5: Model 3 — Height-wise Bias  §6.4
    # ─────────────────────────────────────────────────
    print("\n[Step 5] Model 3: Height-wise Bias")
    df_calib_h = apply_all_bins(df_calib, n_azimuth=1, n_distance=1)  # 高さビンのみ
    tbl_m3 = estimate_height_bias(df_calib_h, joint_cols=JOINT_COLS_ANGLE)
    save_bias_table(tbl_m3, "model3_height_bias")

    # ─────────────────────────────────────────────────
    # Step 6: Model 4 — View-bin Bias  §6.5  ← 中心モデル
    # ─────────────────────────────────────────────────
    print(f"\n[Step 6] Model 4: View-bin Bias (n_azimuth={n_azimuth})")
    tbl_m4 = estimate_viewbin_bias(
        df_calib,
        joint_cols=JOINT_COLS_ANGLE,
        n_azimuth=n_azimuth,
        n_distance=n_distance,
        min_samples=5,
    )
    save_bias_table(tbl_m4, f"model4_viewbin_az{n_azimuth}")
    print(f"  {len(tbl_m4)} bias table rows")

    # ─────────────────────────────────────────────────
    # Step 7: Model 5 — Linear Parametric  §6.6
    # ─────────────────────────────────────────────────
    print(f"\n[Step 7] Model 5: Linear Parametric (regularize={regularize})")
    beta_global = fit_all_joints(df_calib, joint_cols=JOINT_COLS_ANGLE, regularize=regularize)
    save_beta_dict(beta_global, "model5_linear_global")

    # 局所線形モデル（各ビン内で個別 fit）  §7 (02提案書)
    df_calib_binned2 = apply_all_bins(df_calib, n_azimuth=n_azimuth, n_distance=n_distance)
    local_fits = fit_local_linear_models(
        df_calib_binned2,
        joint_cols=JOINT_COLS_ANGLE,
        group_cols=["height_bin", "azimuth_bin"],
        regularize=regularize,
        min_samples=6,
    )
    if len(local_fits) > 0:
        local_fits.to_csv(
            Path(__file__).parent / f"../outputs/results/local_linear_fits_az{n_azimuth}.csv",
            index=False
        )
        mean_r2 = local_fits["r2"].mean()
        print(f"  局所線形モデル: {len(local_fits)} bin×joint, mean R²={mean_r2:.3f}")

    print("\n[Phase A 完了]")
    return {
        "df_calib": df_calib,
        "df_val":   df_val,
        "df_test":  df_test_cam,
        "df_train_height": df_train_h,
        "df_test_height":  df_test_h,
        "tables": {
            "m2": tbl_m2,
            "m3": tbl_m3,
            "m4": tbl_m4,
        },
        "beta": beta_global,
    }


if __name__ == "__main__":
    run(n_azimuth=8, n_distance=1)
