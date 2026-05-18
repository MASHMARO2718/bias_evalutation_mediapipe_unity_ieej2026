"""
config.py — 全モジュール共通の定数・パス定義

提案書との対応:
  §1   研究背景（補正対象バイアスの種類）
  §4.3 Phase A/B の入出力（入力 CSV パス）
  §6   補正モデル仕様（JOINTS, METRICS, LAYER_HEIGHTS）
  §8   データ分割（SPLIT 比率）
  §8.2 Camera Split  §8.3 Height Hold-out
"""

from pathlib import Path

# ──────────────────────────────────────────────
# リポジトリルート（このファイルの2階層上がリポジトリ root）
# ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]   # bias_evaluation_,mediapipe_unity_ieej2026/

# ──────────────────────────────────────────────
# 入力データパス  §4.3 Calibration 入力
# ──────────────────────────────────────────────
DATA = {
    # 関節角度 MAE: camera_x/y/z + 8 関節の平均絶対誤差 per camera position
    # columns: folder_name, camera_x, camera_y, camera_z, L_Elbow, R_Elbow, ...
    "angle_mae": {
        "Y=0.5": REPO_ROOT / "03_joint_angle_mae/joint_angle_mae_csv/Y=0.5/coordinate_angle_mae.csv",
        "Y=1.0": REPO_ROOT / "03_joint_angle_mae/joint_angle_mae_csv/Y=1.0/coordinate_angle_mae.csv",
        "Y=1.5": REPO_ROOT / "03_joint_angle_mae/joint_angle_mae_csv/Y=1.5/coordinate_angle_mae.csv",
        "Y=2.0": REPO_ROOT / "03_joint_angle_mae/joint_angle_mae_csv/Y=2.0/coordinate_angle_mae.csv",
    },
    # 方向角誤差集計: joint × (θ_mean, θ_std, ψ_mean, ψ_std, 3D_error) の全カメラ統合
    # columns: joint, theta_mean, theta_std, ..., psi_abs_mean, error3d_mean, ...
    "joint_summary": REPO_ROOT / "05_direction_detection/output/processed_data/joint_summary.csv",

    # フレーム×カメラ別の方向角統計
    # columns: frame_id, camera, num_joints, mean_abs_delta_theta, mean_abs_delta_psi, ...
    "frame_camera_summary": REPO_ROOT / "05_direction_detection/output/processed_data/frame_camera_summary.csv",

    # 全観測の詳細結果（サイズ大・git 除外）。存在すれば符号付き誤差を利用可能
    # columns: (詳細は 05_direction_detection/README.md 参照)
    "detailed_results": REPO_ROOT / "05_direction_detection/output/processed_data/detailed_results.csv",

    # 相関行列
    "corr_theta": REPO_ROOT / "05_direction_detection/output/correlation_analysis/correlation_matrix_theta.csv",
    "corr_psi":   REPO_ROOT / "05_direction_detection/output/correlation_analysis/correlation_matrix_psi.csv",
}

# ──────────────────────────────────────────────
# 出力パス  §4.3 Calibration 出力 / Correction 出力
# ──────────────────────────────────────────────
FRAMEWORK_DIR = Path(__file__).resolve().parent.parent   # 09_A_Local.../
OUTPUT = {
    "bias_tables": FRAMEWORK_DIR / "outputs/bias_tables",
    "results":     FRAMEWORK_DIR / "outputs/results",
    "figures":     FRAMEWORK_DIR / "outputs/figures",
}

# ──────────────────────────────────────────────
# 関節名  §6 補正モデル（8 主要関節）
# ──────────────────────────────────────────────
JOINT_COLS_ANGLE = [            # coordinate_angle_mae.csv の列名
    "L_Shoulder", "R_Shoulder",
    "L_Elbow",    "R_Elbow",
    "L_Hip",      "R_Hip",
    "L_Knee",     "R_Knee",
]

JOINT_NAMES_DIR = [             # joint_summary.csv の joint 列に出現する名称
    "LEFT_SHOULDER",  "RIGHT_SHOULDER",
    "LEFT_ELBOW",     "RIGHT_ELBOW",
    "LEFT_WRIST",     "RIGHT_WRIST",
    "LEFT_HIP",       "RIGHT_HIP",
    "LEFT_KNEE",      "RIGHT_KNEE",
    "LEFT_ANKLE",     "RIGHT_ANKLE",
]

# ──────────────────────────────────────────────
# カメラ高さ層  §8.3 Height Hold-out
# ──────────────────────────────────────────────
LAYER_HEIGHTS = [0.5, 1.0, 1.5, 2.0]
HEIGHT_HOLDOUT_TEST = [2.0]                  # テスト専用高さ（未知視点評価）
HEIGHT_HOLDOUT_TRAIN = [0.5, 1.0, 1.5]      # 学習に使う高さ

# ──────────────────────────────────────────────
# 方位角ビン  §8 View-space Binning
# ──────────────────────────────────────────────
# 8方向ビンのラベル（北=0° を基準に時計回り）
AZIMUTH_BIN_LABELS_8 = [
    "N", "NE", "E", "SE", "S", "SW", "W", "NW"
]

# ──────────────────────────────────────────────
# 評価指標名  §9 評価指標
# ──────────────────────────────────────────────
METRICS = ["angle_mae", "delta_theta_abs", "delta_psi_abs", "mpjpe"]

# ──────────────────────────────────────────────
# データ分割比率  §8.2 Camera Split (70/15/15)
# ──────────────────────────────────────────────
SPLIT_RATIO = {"calib": 0.70, "val": 0.15, "test": 0.15}
RANDOM_SEED = 42

# ──────────────────────────────────────────────
# 補正強度デフォルト  §17.7 過補正抑制 λ
# ──────────────────────────────────────────────
DEFAULT_LAMBDA = 1.0   # 0〜1: 1.0 = 推定バイアスを全量引く

# ──────────────────────────────────────────────
# 骨盤制約デフォルト  §6.7 Model 6
# ──────────────────────────────────────────────
PELVIS_TAU_PERCENTILE = 95   # GT 上の左右 hip Z 差の percentile から τ を推定

# ──────────────────────────────────────────────
# 線形補正モデルの特徴量  §6.6 Model 5 / §7.3 最小二乗
# x = [1, Y, D, sin(φ), cos(φ), ε]
# ──────────────────────────────────────────────
LINEAR_FEATURES = ["intercept", "camera_y", "distance", "sin_azimuth", "cos_azimuth", "elevation"]
