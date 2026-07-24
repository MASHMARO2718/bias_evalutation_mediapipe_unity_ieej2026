"""
experiments/run_evaluation.py — 全モデルの補正適用と評価

§4.7 推奨研究デザイン 手順 3〜5:
  3. Test セットの MediaPipe に補正適用
  4. GT と比較し raw_error / corrected_error / improvement を計算
  5. Known-view / Unknown-view の二系統で汎化を確認

§10.1 比較するモデル一覧:
  Model 0: Raw MediaPipe（ベースライン）
  Model 2: Joint-wise Constant Bias
  Model 3: Height-wise Bias
  Model 4: View-bin Bias  ← 中心モデル
  Model 5: Linear Parametric

§13.1 成功条件:
  - calib set だけでなく test set でも改善
  - known-view と unknown-view (Y=2.0) の両方で報告
  - anatomical validity (hip r, upper-limb r, jitter) が悪化していない
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins
from src.evaluation.split import camera_split, height_holdout_split, check_bin_coverage
from src.evaluation.metrics import (
    joint_angle_mae, hip_correlation, upper_limb_correlations,
    viewpoint_gap, improvement_rate, generalization_drop,
)
from src.phase_a.bias_estimator import (
    estimate_joint_bias, estimate_height_bias,
    estimate_viewbin_bias, load_bias_table,
)
from src.phase_a.linear_estimator import load_beta_dict
from src.phase_b.corrector import (
    apply_joint_bias, apply_height_bias,
    apply_viewbin_bias, apply_linear_correction,
    compute_improvement,
)
from src.config import JOINT_COLS_ANGLE, OUTPUT


def evaluate_model(name: str, df_raw: pd.DataFrame, df_corrected: pd.DataFrame) -> pd.DataFrame:
    """各モデルの補正前後の MAE・改善率をまとめる。"""
    raw_mae  = joint_angle_mae(df_raw,       JOINT_COLS_ANGLE, suffix="")
    corr_mae = joint_angle_mae(df_corrected, JOINT_COLS_ANGLE, suffix="_corr")

    rows = []
    for j in JOINT_COLS_ANGLE:
        if j in raw_mae and j in corr_mae:
            imp = improvement_rate(raw_mae[j], corr_mae[j])
            rows.append({
                "model":           name,
                "joint":           j,
                "raw_mae":         raw_mae[j],
                "corr_mae":        corr_mae[j],
                "improvement_pct": imp,
            })
    return pd.DataFrame(rows)


def run(n_azimuth: int = 8):
    """
    全モデルを Test セット（Camera Split + Height Hold-out）で評価する。
    """
    print("=" * 60)
    print("Phase A + B: 全モデル評価")
    print("=" * 60)

    # ─── データ準備 ───────────────────────────────────────
    df = load_angle_mae_all_layers()
    df_calib, df_val, df_test = camera_split(df, camera_col="folder_name")
    _, df_test_unknown = height_holdout_split(df_test, y_col="camera_y")

    # カメラ特徴量 + ビンは df 全体に適用済み（load_angle_mae_all_layers が付加）

    # ─── Phase A: キャリブレーション（calib セット） ─────────
    tbl_m2 = estimate_joint_bias(df_calib)
    tbl_m3 = estimate_height_bias(apply_all_bins(df_calib, n_azimuth=1))
    tbl_m4 = estimate_viewbin_bias(df_calib, n_azimuth=n_azimuth)
    beta_m5 = {}
    try:
        beta_m5 = load_beta_dict("model5_linear_global")
    except FileNotFoundError:
        from src.phase_a.linear_estimator import fit_all_joints
        beta_m5 = fit_all_joints(df_calib)

    # ─── Phase B: 補正適用 + 評価 ────────────────────────
    all_results = []

    def _eval(name, df_in, df_out, split_label):
        impr = evaluate_model(name, df_in, df_out)
        impr["split"] = split_label
        all_results.append(impr)
        print(f"  [{split_label}] {name}: mean improvement = {impr['improvement_pct'].mean():.1f}%")

    for split_label, df_t in [("known_view", df_test), ("unknown_view", df_test_unknown)]:
        print(f"\n── Split: {split_label} ({len(df_t)} rows) ──")

        # Model 2
        df_m2 = apply_joint_bias(df_t, tbl_m2)
        _eval("Model2_JointWise", df_t, df_m2, split_label)

        # Model 3
        df_t_h = apply_all_bins(df_t, n_azimuth=1)
        df_m3  = apply_height_bias(df_t_h, tbl_m3)
        _eval("Model3_HeightWise", df_t, df_m3, split_label)

        # Model 4  §6.5 中心モデル
        df_m4 = apply_viewbin_bias(df_t, tbl_m4, n_azimuth=n_azimuth)
        _eval("Model4_ViewBin", df_t, df_m4, split_label)

        # Model 5
        if beta_m5:
            df_m5 = apply_linear_correction(df_t, beta_m5)
            _eval("Model5_Linear", df_t, df_m5, split_label)

        # hip 相関  §9.4
        r_hip = hip_correlation(df_t, "L_Hip", "R_Hip")
        print(f"  hip r (raw): {r_hip:.3f}")

    # ─── 汎化ドロップ計算  §9.8 ─────────────────────────────
    df_all = pd.concat(all_results, ignore_index=True)
    for model in df_all["model"].unique():
        known   = df_all[(df_all["model"] == model) & (df_all["split"] == "known_view")]["improvement_pct"].mean()
        unknown = df_all[(df_all["model"] == model) & (df_all["split"] == "unknown_view")]["improvement_pct"].mean()
        gdrop   = generalization_drop(known, unknown)
        print(f"  {model}: gen_drop = {gdrop:.1f}pp  (known={known:.1f}%, unknown={unknown:.1f}%)")

    # 保存
    out_path = OUTPUT["results"] / f"evaluation_results_az{n_azimuth}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(out_path, index=False)
    print(f"\n[評価完了] 結果保存: {out_path}")

    return df_all


if __name__ == "__main__":
    run(n_azimuth=8)
