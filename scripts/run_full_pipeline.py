#!/usr/bin/env python3
"""
全パイプライン一括実行（後方互換）

推奨: python run.py を使用してください。
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 根の run.py を import
    import run
    sys.exit(run.main())
