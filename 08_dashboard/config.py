"""
ダッシュボード用設定
データソース（06_direction_detection/output）を指定
"""

from pathlib import Path

# プロジェクトルート（Zeval_DataSet_organized）
PROJECT_ROOT = Path(__file__).parent.parent

# データソース（06 の出力）
DATA_SOURCE = PROJECT_ROOT / "06_direction_detection" / "output"
