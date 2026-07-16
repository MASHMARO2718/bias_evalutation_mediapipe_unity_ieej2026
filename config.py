"""
プロジェクト設定（ルート）
全パイプラインで共通利用

データセットバージョン切り替え:
  DATASET_VERSION = "v1"  : 旧データ（JPG 個別キャプチャ）  2025-12 収集
  DATASET_VERSION = "v2"  : 新データ（動画キャプチャ・GT同期済み）  2026-07 収集
"""
from pathlib import Path

# ─── データセットバージョン切り替え ───────────────────────────────────────
# "v1" → 旧 JPG キャプチャデータ（同期ずれあり）
# "v2" → 新 動画キャプチャデータ（フレーム同期済み）
DATASET_VERSION = "v2"

# ─── プロジェクトルート ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent

# ─── v1 パス（旧データ・変更禁止） ────────────────────────────────────────
_V1_INPUT_DIR = PROJECT_ROOT / "01_input_photos"          # JPG + synced_joint_positions_*.csv
_V1_MP_DIR    = PROJECT_ROOT / "02_mediapipe_processed" / "mediapipe_processed_csv"

# ─── v2 パス（新データ） ──────────────────────────────────────────────────
_V2_INPUT_DIR = PROJECT_ROOT / "01_input_videos"          # video.mp4 + gt_joints.csv
_V2_MP_DIR    = PROJECT_ROOT / "02_mediapipe_v2" / "mediapipe_processed_csv"

# ─── アクティブパス（DATASET_VERSION で自動切り替え） ─────────────────────
if DATASET_VERSION == "v1":
    INPUT_DIR = _V1_INPUT_DIR
    MP_DIR    = _V1_MP_DIR
    GT_MODE   = "per_folder_synced"   # 各フォルダに synced_joint_positions_*.csv
elif DATASET_VERSION == "v2":
    INPUT_DIR = _V2_INPUT_DIR
    MP_DIR    = _V2_MP_DIR
    GT_MODE   = "per_folder_gt"       # 各フォルダに gt_joints.csv（frame_id/time_sec 形式）
else:
    raise ValueError(f"Unknown DATASET_VERSION: {DATASET_VERSION!r}. Use 'v1' or 'v2'.")

# ─── 後方互換（旧コードが GT_CSV / MP_DIR を直接参照している場合） ─────────
# v1 の旧スクリプトはこのパスを参照していた（v2 では per-folder gt_joints.csv を使う）
GT_CSV = PROJECT_ROOT / "synced_joint_positions.csv"

# ─── Y 層範囲（v1/v2 共通） ───────────────────────────────────────────────
Y_RANGES = ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]

# ─── 処理結果フォルダ（スクリプト番号順） ────────────────────────────────
JOINT_ANGLE_MAE_DIR = PROJECT_ROOT / "03_joint_angle_mae"
MAX_ANGLE_ERROR_DIR = PROJECT_ROOT / "04_max_angle_error"
