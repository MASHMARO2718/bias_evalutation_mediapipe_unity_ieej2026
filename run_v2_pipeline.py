#!/usr/bin/env python3
"""
v2 データセット向けパイプライン実行スクリプト

前提:
  - config.py の DATASET_VERSION = "v2"
  - 01_input_videos/ に video.mp4 + gt_joints.csv
  - 02_mediapipe_v2/ に MediaPipe CSV（未完了なら --step 0 で処理）

流れ（v1 と同様に 03〜07 も含む）:
  0. MediaPipe 動画処理          → 02_mediapipe_v2/
  1. 3点角 MAE（層別）           → 03_joint_angle_mae/joint_angle_mae_csv/Y=*/
  2. MAE 統計テーブル統合
  3. 最大角度誤差（04）          → 04_max_angle_error/calculation/Y=*/
  4. 方向角・相関（05）          → 05_direction_detection/output/
  5. θ検証（06）                 → 06_theta_verification/
  6. ダッシュボード（07）        → http://127.0.0.1:8050/
  7. キャリブレーション（09）    → 09_calibration_framework/outputs/

使い方:
  python run_v2_pipeline.py                  # MediaPipe 完了済み前提で 1→7
  python run_v2_pipeline.py --with-mediapipe # 0 から全部
  python run_v2_pipeline.py --step 1         # 03 のみ
  python run_v2_pipeline.py --step 3         # 04 のみ
  python run_v2_pipeline.py --step 4         # 05 のみ
  python run_v2_pipeline.py --step 7         # 09 のみ
  python run_v2_pipeline.py --backup-v1      # 実行前に v1 出力を退避
  python run_v2_pipeline.py --no-dashboard   # 07 を起動しない
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
Y_LAYERS = ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]


def run_cmd(cmd: list[str], cwd: Path) -> bool:
    print(f"\n>>> {' '.join(cmd)}")
    print(f"    cwd={cwd}")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        print(f"エラー: 終了コード {r.returncode}")
        return False
    return True


def backup_v1_outputs() -> None:
    """v1 の処理結果を timestamp 付きフォルダへコピー（上書き前の退避）"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / f"_backup_v1_outputs_{stamp}"
    targets = [
        ROOT / "03_joint_angle_mae" / "joint_angle_mae_csv",
        ROOT / "03_joint_angle_mae" / "coordinate_angle_mae_combined.csv",
        ROOT / "05_direction_detection" / "output",
        ROOT / "09_calibration_framework" / "outputs",
    ]
    backup_root.mkdir(parents=True, exist_ok=True)
    for t in targets:
        if not t.exists():
            print(f"  skip (なし): {t.relative_to(ROOT)}")
            continue
        dest = backup_root / t.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if t.is_dir():
            shutil.copytree(t, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(t, dest)
        print(f"  backed up: {t.relative_to(ROOT)} -> {dest.relative_to(ROOT)}")
    print(f"バックアップ完了: {backup_root}")


def step_mediapipe() -> bool:
    cwd = ROOT / "02_mediapipe_v2"
    return run_cmd([sys.executable, "mediapipe_video_processor.py"], cwd)


def step_angle_mae() -> bool:
    """層別に coordinate_angle_comparison.py を実行"""
    mp_base = ROOT / "02_mediapipe_v2" / "mediapipe_processed_csv"
    gt_glob = str(ROOT / "01_input_videos" / "CapturedFrames_*" / "gt_joints.csv")
    out_base = ROOT / "03_joint_angle_mae" / "joint_angle_mae_csv"
    script = ROOT / "03_joint_angle_mae" / "coordinate_angle_comparison.py"

    for y in Y_LAYERS:
        mp_dir = mp_base / y
        n = len(list(mp_dir.glob("CapturedFrames_*.csv"))) if mp_dir.exists() else 0
        if n == 0:
            print(f"スキップ（CSVなし）: {mp_dir}")
            continue
        out_dir = out_base / y
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / "coordinate_angle_mae.csv"
        mp_pattern = str(mp_dir / "CapturedFrames_*.csv")
        ok = run_cmd([
            sys.executable, str(script),
            "--mp_csv", mp_pattern,
            "--gt_csv", gt_glob,
            "--output_csv", str(out_csv),
        ], ROOT / "03_joint_angle_mae")
        if not ok:
            return False
    return True


def step_mae_stats() -> bool:
    return run_cmd(
        [sys.executable, "create_statistics_table.py"],
        ROOT / "03_joint_angle_mae",
    )


def step_max_angle() -> bool:
    """層別に calculate_max_angle_error.py を実行（04）"""
    mp_base = ROOT / "02_mediapipe_v2" / "mediapipe_processed_csv"
    gt_glob = str(ROOT / "01_input_videos" / "CapturedFrames_*" / "gt_joints.csv")
    script = ROOT / "04_max_angle_error" / "calculate_max_angle_error.py"

    for y in Y_LAYERS:
        mp_dir = mp_base / y
        n = len(list(mp_dir.glob("CapturedFrames_*.csv"))) if mp_dir.exists() else 0
        if n == 0:
            print(f"スキップ（CSVなし）: {mp_dir}")
            continue
        out_dir = ROOT / "04_max_angle_error" / "calculation" / y
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / "coordinate_max_angle_error.csv"
        ok = run_cmd([
            sys.executable, str(script),
            "--mp_csv", str(mp_dir / "CapturedFrames_*.csv"),
            "--gt_csv", gt_glob,
            "--output_csv", str(out_csv),
        ], ROOT / "04_max_angle_error")
        if not ok:
            return False
    return True


def step_direction() -> bool:
    cwd = ROOT / "05_direction_detection"
    if not run_cmd([sys.executable, "process_all_data.py"], cwd):
        return False
    return run_cmd([sys.executable, "scripts/compute_correlation.py"], cwd)


def step_theta_verify() -> bool:
    """06 θ・座標系検証（失敗しても警告のみで継続可）"""
    ok = run_cmd([sys.executable, "run_all.py"], ROOT / "06_theta_verification")
    if not ok:
        print("警告: 06_theta_verification が失敗（継続）")
    return True  # 検証失敗でパイプライン全体を止めない


def step_dashboard() -> bool:
    """07 ダッシュボード起動（ブロッキング）"""
    print("ダッシュボード: http://127.0.0.1:8050/")
    return run_cmd([sys.executable, "07_dashboard/app.py"], ROOT)


def step_calibration() -> bool:
    cwd = ROOT / "09_calibration_framework"
    if not run_cmd([sys.executable, "experiments/run_calibration.py"], cwd):
        return False
    if not run_cmd([sys.executable, "experiments/run_evaluation.py"], cwd):
        return False
    # 論文用の追加解析（存在すれば実行）
    scripts_dir = cwd / "scripts"
    extras = [
        "signed_bias_eval.py",
        "gen_signed_figs.py",
        "gen_ablation_failure.py",
        "model6_eval.py",
        "r2_vs_correction.py",
    ]
    for name in extras:
        script = scripts_dir / name
        if script.exists():
            if not run_cmd([sys.executable, str(script)], cwd):
                print(f"警告: {name} が失敗（継続）")
    return True


def count_mp_csv() -> int:
    base = ROOT / "02_mediapipe_v2" / "mediapipe_processed_csv"
    return len(list(base.rglob("CapturedFrames_*.csv"))) if base.exists() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="v2 パイプライン実行")
    parser.add_argument("--with-mediapipe", action="store_true", help="MediaPipe から実行")
    parser.add_argument("--backup-v1", action="store_true", help="実行前に v1 出力を退避")
    parser.add_argument("--no-dashboard", action="store_true", help="07 ダッシュボードを起動しない")
    parser.add_argument("--step", type=int, choices=[0, 1, 2, 3, 4, 5, 6, 7],
                        help="単一ステップ (0=MP,1=MAE,2=統計,3=04,4=05,5=06,6=07,7=09)")
    args = parser.parse_args()

    # DATASET_VERSION 確認
    sys.path.insert(0, str(ROOT))
    import config as root_config
    if root_config.DATASET_VERSION != "v2":
        print(f"警告: DATASET_VERSION={root_config.DATASET_VERSION!r}（v2 推奨）")

    if args.backup_v1:
        print("\n=== v1 出力バックアップ ===")
        backup_v1_outputs()
        if args.step is None and not args.with_mediapipe:
            print("バックアップのみ完了（パイプラインは未実行）。")
            print("通し実行: python run_v2_pipeline.py")
            return 0

    steps = []
    if args.step is not None:
        steps = [args.step]
    else:
        if args.with_mediapipe:
            steps.append(0)
        steps.extend([1, 2, 3, 4, 5])
        if not args.no_dashboard:
            steps.append(6)
        steps.append(7)

    need_mp = any(s in steps for s in (1, 2, 3, 4, 5, 7))
    if 0 not in steps and need_mp:
        n = count_mp_csv()
        print(f"\nMediaPipe CSV 数: {n} / 576")
        if n < 576:
            print(f"未完了です（{n}/576）。MediaPipe 完了を待ってから再実行してください。")
            return 1
        if n == 0:
            print("MediaPipe CSV がありません。--with-mediapipe / --step 0 を実行してください。")
            return 1

    dispatch = {
        0: ("MediaPipe 動画処理", step_mediapipe),
        1: ("3点角 MAE (03)", step_angle_mae),
        2: ("MAE 統計統合", step_mae_stats),
        3: ("最大角度誤差 (04)", step_max_angle),
        4: ("方向角・相関 (05)", step_direction),
        5: ("θ検証 (06)", step_theta_verify),
        6: ("ダッシュボード (07)", step_dashboard),
        7: ("キャリブレーション (09)", step_calibration),
    }

    for s in steps:
        name, fn = dispatch[s]
        print(f"\n{'='*60}\n=== ステップ {s}: {name} ===\n{'='*60}")
        if not fn():
            print(f"\n失敗: ステップ {s}")
            return 1

    print("\n=== v2 パイプライン完了 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
