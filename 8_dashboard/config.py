"""
ダッシュボード用設定
データソース（5_direction/output）を指定
"""

from pathlib import Path

# プロジェクトルート（Zeval_DataSet_organized）
PROJECT_ROOT = Path(__file__).parent.parent

# データソース（06 の出力）
DATA_SOURCE = PROJECT_ROOT / "5_direction" / "output"
