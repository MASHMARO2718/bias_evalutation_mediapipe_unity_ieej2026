"""
ダッシュボード起動用ランチャー（後方互換）

ダッシュボードは 07_dashboard/ に配置。
このファイルは 07_dashboard/app.py を起動するランチャーです。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 07_dashboard.app を実行
import runpy
runpy.run_path(str(project_root / "07_dashboard" / "app.py"), run_name="__main__")
