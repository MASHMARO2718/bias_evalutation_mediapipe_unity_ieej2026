#!/usr/bin/env python3
"""
MotionTrack パイプライン実行

初見ユーザー向け: 画像を 01_input_photos に置いて python run.py で MediaPipe〜検証まで自動実行（既定で 07_dashboard 起動）。

使い方:
  python run.py                    # 全パイプライン（01画像→02 CSV→MAE/最大角/方向角→検証→07ダッシュボード）
  python run.py --no-mediapipe     # 02 以降のみ（02 が既にある場合）
  python run.py --dashboard        # ステップ4（方向角）のみ＋ダッシュボード起動
  python run.py --step 4           # 特定ステップのみ
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
INPUT_PHOTOS = ROOT / "01_input_photos"
MP_PROCESSED = ROOT / "02_mediapipe_processed"

STEPS = [
    ("0", None, "MediaPipe: 画像→CSV (01→02)", [None], "mediapipe"),  # 特別処理
    ("1", "03_joint_angle_mae", "3点角MAE計算", ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"], "run_cal_mae.py"),
    ("2", "03_joint_angle_mae", "MAE統計テーブル作成", [None], "create_statistics_table.py"),
    ("3", "04_max_angle_error", "最大角度誤差計算", ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"], "run_calculate_max.py"),
    ("4", "05_direction_detection", "方向角・相関分析", [None], None),  # 2スクリプト
    ("5", None, "論文データ検証", [None], "verify_paper_data.py"),
]


def run_cmd(cmd: list, cwd: Path) -> bool:
    """コマンド実行。失敗時は False"""
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        print(f"エラー: 終了コード {r.returncode}")
        return False
    return True


def _has_images(dir_path: Path) -> bool:
    """ディレクトリに画像があるか"""
    if not dir_path.exists():
        return False
    exts = {".jpg", ".jpeg", ".png"}
    for p in dir_path.rglob("*"):
        if p.suffix.lower() in exts:
            return True
    return False


def run_step(step_num: str) -> bool:
    """指定ステップを実行"""
    step = next((s for s in STEPS if s[0] == step_num), None)
    if not step:
        print(f"不明なステップ: {step_num}")
        return False

    num, folder, desc, subdirs, script = step
    print(f"\n=== ステップ {num}: {desc} ===")

    if num == "0":
        # MediaPipe: 01_input_photos → 02_mediapipe_processed
        if not _has_images(INPUT_PHOTOS):
            print(f"スキップ: {INPUT_PHOTOS} に画像がありません")
            return True
        cwd = MP_PROCESSED
        cmd = [
            sys.executable, "mediapipe_batch_processor.py",
            "--input_dir", str(INPUT_PHOTOS),
            "--output_base_dir", str(MP_PROCESSED),
        ]
        return run_cmd(cmd, cwd)

    if num == "4":
        # 05: process_all_data + compute_correlation
        cwd = ROOT / "05_direction_detection"
        if not run_cmd([sys.executable, "process_all_data.py"], cwd):
            return False
        if not run_cmd([sys.executable, "scripts/compute_correlation.py"], cwd):
            return False
        return True

    if num == "5":
        return run_cmd([sys.executable, "verify_paper_data.py"], ROOT)

    if subdirs[0] is None:
        cwd = ROOT / folder
        return run_cmd([sys.executable, script], cwd)

    for sub in subdirs:
        cwd = ROOT / folder / sub
        if num == "3":
            cwd = ROOT / folder / "calculation" / sub  # 04_max_angle_error/calculation/Y=...
        if not cwd.exists():
            print(f"スキップ（フォルダなし）: {cwd}")
            continue
        if not run_cmd([sys.executable, script], cwd):
            return False
    return True


def run_dashboard_only() -> bool:
    """ダッシュボード用データのみ（06の処理のみ）"""
    print("\n=== ダッシュボード用データ生成（05_direction_detection）===")
    return run_step("4")


def run_full(skip_mediapipe: bool = False, launch_dashboard: bool = False) -> bool:
    """全パイプライン実行"""
    print("\n=== MotionTrack 全パイプライン ===\n")
    start = 1 if skip_mediapipe else 0
    for step in STEPS:
        if int(step[0]) < start:
            continue
        if not run_step(step[0]):
            return False
    print("\n=== 全パイプライン完了 ===")
    if launch_dashboard:
        print("\n>>> ダッシュボードを起動します...")
        return run_cmd([sys.executable, "07_dashboard/app.py"], ROOT)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="MotionTrack パイプライン実行（MediaPipe〜検証、既定で07ダッシュボード）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python run.py                   画像から全処理＋ダッシュボード起動
  python run.py --no-dashboard    ダッシュボードは起動しない
  python run.py --no-mediapipe   02 以降のみ（02 が既にある場合）
  python run.py --dashboard      ステップ4＋ダッシュボード
  python run.py --step 0         MediaPipe のみ
        """,
    )
    parser.add_argument("--dashboard", action="store_true", help="ステップ4（方向角）のみ実行しダッシュボード起動")
    parser.add_argument("--no-mediapipe", action="store_true", help="ステップ0（MediaPipe）をスキップ")
    parser.add_argument("--no-dashboard", action="store_true", help="完了後にダッシュボードを起動しない")
    parser.add_argument("--step", metavar="N", help="ステップ番号のみ実行 (0-5)")
    args = parser.parse_args()

    if args.dashboard:
        ok = run_dashboard_only()
        if ok:
            run_cmd([sys.executable, "07_dashboard/app.py"], ROOT)
    elif args.step:
        ok = run_step(args.step)
    else:
        ok = run_full(skip_mediapipe=args.no_mediapipe, launch_dashboard=not args.no_dashboard)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
