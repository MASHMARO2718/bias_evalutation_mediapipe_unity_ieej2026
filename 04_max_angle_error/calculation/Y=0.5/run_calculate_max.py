#!/usr/bin/env python3
"""最大角度誤差計算の実行（02_mediapipe_processed を参照）"""
import os
import sys
import subprocess
from pathlib import Path

current_dir = Path(__file__).parent
y_range = current_dir.name
project_root = current_dir.parent.parent.parent
mp_dir = project_root / "02_mediapipe_processed" / y_range
gt_csv = project_root / "synced_joint_positions.csv"
output_csv = current_dir / "coordinate_max_angle_error.csv"

mp_pattern = str(mp_dir / "CapturedFrames_*.csv")
if not list(mp_dir.glob("CapturedFrames_*.csv")):
    print(f"エラー: MediaPipe CSV が見つかりません: {mp_dir}")
    sys.exit(1)

os.chdir(current_dir)
subprocess.run([
    sys.executable, "calculate_max_angle_error.py",
    "--mp_csv", mp_pattern,
    "--gt_csv", str(gt_csv),
    "--output_csv", str(output_csv)
], check=True)
