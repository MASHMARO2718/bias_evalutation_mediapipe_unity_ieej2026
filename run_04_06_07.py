#!/usr/bin/env python3
"""04 → 06 → 07 を v2 データで実行（03/05/09 は済）"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
Y_LAYERS = ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]


def run(cmd, cwd):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    return r.returncode == 0


def main() -> int:
    mp_base = ROOT / "20_pose_correction" / "mediapipe_processed_csv"
    gt_glob = str(ROOT / "10_input_videos" / "CapturedFrames_*" / "gt_joints.csv")
    calc_script = ROOT / "31_max_angle_error" / "calculate_max_angle_error.py"

    print("=" * 60)
    print("=== 04: 最大角度誤差 ===")
    print("=" * 60)
    for y in Y_LAYERS:
        mp_dir = mp_base / y
        out_dir = ROOT / "31_max_angle_error" / "calculation" / y
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / "coordinate_max_angle_error.csv"
        ok = run([
            sys.executable, str(calc_script),
            "--mp_csv", str(mp_dir / "CapturedFrames_*.csv"),
            "--gt_csv", gt_glob,
            "--output_csv", str(out_csv),
        ], ROOT / "31_max_angle_error")
        if not ok:
            return 1
        print(f"OK {y}: {out_csv}", flush=True)

    print("=" * 60)
    print("=== 06: theta verification ===")
    print("=" * 60)
    if not run([sys.executable, "run_all.py"], ROOT / "33_theta_verification"):
        print("警告: 06 が失敗（継続）", flush=True)

    print("=" * 60)
    print("=== 04/06 完了。07 は別プロセスで起動してください ===")
    print("  python 50_dashboard/app.py")
    print("  → http://127.0.0.1:8050/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
