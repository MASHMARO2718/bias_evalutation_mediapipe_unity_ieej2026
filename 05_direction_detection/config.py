"""
設定ファイル（11: Y軸反転修正版）
座標変換で MediaPipe の Y 反転を適用（正しい実装）
ルート config を参照し、11 独自の設定のみ定義
"""

import importlib.util
from pathlib import Path

# ルート config を読み込み
_root_config_path = Path(__file__).parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("_root_config", _root_config_path)
_root = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root)

# ルートから共通設定を参照
BASE_DIR = _root.PROJECT_ROOT
GT_CSV = _root.GT_CSV
MP_DIR = _root.MP_DIR
Y_RANGES = _root.Y_RANGES

# プロジェクトルート（05_direction_detection）
PROJECT_ROOT = Path(__file__).parent

# 出力ディレクトリ（11 専用）
OUTPUT_DIR = PROJECT_ROOT / "output"
HTML_DIR = OUTPUT_DIR / "html_reports"
LOG_DIR = OUTPUT_DIR / "logs"
DEBUG_DATA_DIR = OUTPUT_DIR / "debug_data"
VALIDATION_DIR = OUTPUT_DIR / "validation_results"

# デバッグ設定
DEBUG_MODE = False
LOG_LEVEL = "INFO"
SAVE_INTERMEDIATE_DATA = False

# MediaPipe関節マッピング
JOINT_MAPPING = {
    'NOSE': 0, 'LEFT_EYE_INNER': 1, 'LEFT_EYE': 2, 'LEFT_EYE_OUTER': 3,
    'RIGHT_EYE_INNER': 4, 'RIGHT_EYE': 5, 'RIGHT_EYE_OUTER': 6,
    'LEFT_EAR': 7, 'RIGHT_EAR': 8, 'MOUTH_LEFT': 9, 'MOUTH_RIGHT': 10,
    'LEFT_SHOULDER': 11, 'RIGHT_SHOULDER': 12, 'LEFT_ELBOW': 13, 'RIGHT_ELBOW': 14,
    'LEFT_WRIST': 15, 'RIGHT_WRIST': 16, 'LEFT_PINKY': 17, 'RIGHT_PINKY': 18,
    'LEFT_INDEX': 19, 'RIGHT_INDEX': 20, 'LEFT_THUMB': 21, 'RIGHT_THUMB': 22,
    'LEFT_HIP': 23, 'RIGHT_HIP': 24, 'LEFT_KNEE': 25, 'RIGHT_KNEE': 26,
    'LEFT_ANKLE': 27, 'RIGHT_ANKLE': 28, 'LEFT_HEEL': 29, 'RIGHT_HEEL': 30,
    'LEFT_FOOT_INDEX': 31, 'RIGHT_FOOT_INDEX': 32,
}

DEFAULT_Y_RANGE = "Y=0.5"


def create_output_dirs():
    """出力ディレクトリを作成"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "processed_data").mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    DEBUG_DATA_DIR.mkdir(exist_ok=True)
    VALIDATION_DIR.mkdir(exist_ok=True)
    print(f"[OK] Output directories created: {OUTPUT_DIR}")
