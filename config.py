"""
プロジェクト設定（ルート）
全パイプラインで共通利用
"""
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent

# データパス
GT_CSV = PROJECT_ROOT / "synced_joint_positions.csv"
MP_DIR = PROJECT_ROOT / "02_mediapipe_processed"  # MediaPipe CSV

# Y範囲
Y_RANGES = ["Y=0.5,1.5", "Y=1.0.2.0"]

# 03_cal_mae 出力
CAL_MAE_DIR = PROJECT_ROOT / "03_cal_mae"

# 04_mae_heatmap
MAE_HEATMAP_DIR = PROJECT_ROOT / "04_mae_heatmap"

# 05_max_angle_error
MAX_ANGLE_ERROR_DIR = PROJECT_ROOT / "05_max_angle_error"
