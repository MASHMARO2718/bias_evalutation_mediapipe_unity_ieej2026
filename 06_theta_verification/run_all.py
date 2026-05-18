"""
全検証テストを順に実行
"""

import subprocess
import sys
from pathlib import Path

TESTS = [
    "test_01_elbow_by_camera.py",
    "test_02_error_vs_angle.py",
    "test_03_single_camera_check.py",
    "test_04_coordinate_system.py",
]

def main():
    root = Path(__file__).resolve().parent
    for name in TESTS:
        path = root / name
        print("\n" + "=" * 60)
        print(f"実行: {name}")
        print("=" * 60)
        r = subprocess.run([sys.executable, str(path)], cwd=str(root))
        if r.returncode != 0:
            print(f"[FAIL] {name}")
            return 1
    print("\n[OK] 全テスト完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
