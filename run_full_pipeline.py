#!/usr/bin/env python3
"""
全パイプライン一括実行（後方互換）

推奨: python run.py を使用してください。
"""
import sys

if __name__ == "__main__":
    import run
    sys.exit(run.main())
