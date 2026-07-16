#!/usr/bin/env python3
"""関節角度 MAE を算出し、このフォルダに coordinate_angle_mae.csv を書き出す。"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
MP_DIR = REPO_ROOT / "02_mediapipe_processed" / HERE.name
GT = REPO_ROOT / "synced_joint_positions.csv"
SCRIPT = HERE.parent / "coordinate_angle_comparison.py"

if not SCRIPT.is_file():
    print(f"Missing {SCRIPT}", file=sys.stderr)
    sys.exit(1)
if not GT.is_file():
    print(f"Missing {GT}", file=sys.stderr)
    sys.exit(1)

cmd = [
    sys.executable,
    str(SCRIPT),
    "--mp_csv",
    str(MP_DIR / "CapturedFrames_*.csv"),
    "--gt_csv",
    str(GT),
    "--output_csv",
    str(HERE / "coordinate_angle_mae.csv"),
]
print(">>>", " ".join(cmd))
r = subprocess.run(cmd, cwd=str(HERE))
sys.exit(r.returncode)
