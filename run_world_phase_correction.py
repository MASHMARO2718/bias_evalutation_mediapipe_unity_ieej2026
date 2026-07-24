#!/usr/bin/env python3
"""
world landmarks + 歩行位相索引による系統誤差補正（論文 IEEJ_02 / CANDAR の本線）

このリポジトリには系統の違う 2 本のラインがある:

  * 本スクリプト        … 補正モデルのライン（docs/07〜11）。
                          少数カメラで「較正 → 減算」を検証する。
                          最終形は world landmarks + 位相索引（W-phase）。
  * run_v2_pipeline.py … 576 カメラのバイアス調査ライン（03〜07, 09）。
                          Model 4S 符号付きビン補正まで。

やること（既定 = 論文の最終結果だけを再現）:

  0. world landmarks 抽出   → 02_mediapipe_v2/mediapipe_world_csv/
  1. world + 位相索引の補正 → 02_mediapipe_v2/world_landmark_model/   ★最終形

過程の実験（docs/07, 08, 10）は既定では走らない。--history で再現できる。

  2. UV 擬似ワールド補正     (docs/07)  → uv_pseudo_world_correction/
  3. UV 系カンニングペーパー (docs/08)  → gt_free_model/
  4. 位相明示型 4 方式比較   (docs/10)  → phase_explicit_model/

使い方:
  python run_world_phase_correction.py              # 0（不足時のみ）→ 1
  python run_world_phase_correction.py --force-extract  # 0 を必ず再実行
  python run_world_phase_correction.py --step 1     # 最終形のみ
  python run_world_phase_correction.py --history    # 2→3→4（過程の再現）
  python run_world_phase_correction.py --check      # 入力の有無だけ確認
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MP = ROOT / "02_mediapipe_v2"

# 補正モデルが読む入力（較正 1 本 + 検証 1 本）
CALIB_CAM = "CapturedFrames_3.0_1.0_0.0"
VAL_CAM = "CapturedFrames_3.2_1.1_0.4"

WORLD_DIR = MP / "mediapipe_world_csv"
REQUIRED_INPUTS = [
    (ROOT / "01_input_videos" / CALIB_CAM / "video.mp4", "較正動画"),
    (ROOT / "01_input_videos" / CALIB_CAM / "gt_joints.csv", "較正 GT"),
    (ROOT / "01_input_videos" / "aditional__test_data" / VAL_CAM / "video.mp4",
     "検証動画"),
    (ROOT / "01_input_videos" / "aditional__test_data" / VAL_CAM / "gt_joints.csv",
     "検証 GT"),
    (MP / "mediapipe_processed_csv" / "Y=1.0" / f"{CALIB_CAM}.csv",
     "較正 MediaPipe UV CSV"),
    (MP / "mediapipe_processed_csv_additional" / "Y=0.5" / f"{VAL_CAM}.csv",
     "検証 MediaPipe UV CSV"),
]

WORLD_CSVS = [WORLD_DIR / f"{CALIB_CAM}.csv", WORLD_DIR / f"{VAL_CAM}.csv"]


def run_script(script: str, args: list[str] | None = None) -> bool:
    cmd = [sys.executable, script] + (args or [])
    print(f"\n>>> {' '.join(cmd)}\n    cwd={MP}")
    return subprocess.run(cmd, cwd=MP).returncode == 0


def check_inputs() -> bool:
    """補正モデルが必要とする入力の有無を表示する。"""
    print("=== 入力チェック ===")
    ok = True
    for path, label in REQUIRED_INPUTS:
        mark = "OK " if path.exists() else "欠落"
        if not path.exists():
            ok = False
        print(f"  [{mark}] {label:24s} {path.relative_to(ROOT)}")

    print("--- world landmarks（ステップ 0 の出力）---")
    for path in WORLD_CSVS:
        mark = "OK " if path.exists() else "未生成"
        print(f"  [{mark}] {path.relative_to(ROOT)}")

    if not ok:
        print("\n入力が足りません。")
        print("  MediaPipe UV CSV が無い場合: python run_v2_pipeline.py --step 0")
        print("  動画・GT が無い場合: 01_input_videos/ の配置を確認してください。")
    return ok


def step_extract_world() -> bool:
    """0. pose_world_landmarks を 2 動画から抽出"""
    return run_script("extract_world_landmarks.py")


def step_world_phase() -> bool:
    """1. world landmarks + 位相索引の補正（最終形）"""
    return run_script("run_world_landmark_model.py")


def step_uv_correction() -> bool:
    """2. UV 擬似ワールド補正（docs/07・推奨構成）"""
    return run_script("run_uv_pseudo_world_correction.py",
                      ["--torso-2d", "--robust-sigma", "--k-sigma", "5",
                       "--outdir", "results_mad_k5"])


def step_gt_free_uv() -> bool:
    """3. UV 系カンニングペーパー（docs/08）"""
    return run_script("run_gt_free_model.py")


def step_phase_explicit() -> bool:
    """4. 位相明示型 4 方式比較（docs/10）"""
    return run_script("run_phase_explicit_model.py")


STEPS = {
    0: ("world landmarks 抽出", step_extract_world),
    1: ("world + 位相索引 補正（最終形）", step_world_phase),
    2: ("UV 擬似ワールド補正 (docs/07)", step_uv_correction),
    3: ("UV 系カンニングペーパー (docs/08)", step_gt_free_uv),
    4: ("位相明示型 4 方式比較 (docs/10)", step_phase_explicit),
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="world landmarks + 位相索引による系統誤差補正（論文本線）")
    ap.add_argument("--step", type=int, choices=sorted(STEPS),
                    help="単一ステップのみ実行")
    ap.add_argument("--history", action="store_true",
                    help="過程の実験 2→3→4 を再現（docs/07, 08, 10）")
    ap.add_argument("--force-extract", action="store_true",
                    help="world landmarks が既にあっても再抽出する")
    ap.add_argument("--check", action="store_true",
                    help="入力の有無を確認して終了")
    args = ap.parse_args()

    inputs_ok = check_inputs()
    if args.check:
        return 0 if inputs_ok else 1
    if not inputs_ok:
        return 1

    if args.step is not None:
        steps = [args.step]
    elif args.history:
        steps = [2, 3, 4]
    else:
        steps = []
        if args.force_extract or not all(p.exists() for p in WORLD_CSVS):
            steps.append(0)
        else:
            print("\nworld landmarks は生成済みのためステップ 0 を省略"
                  "（--force-extract で再実行）")
        steps.append(1)

    for s in steps:
        name, fn = STEPS[s]
        print(f"\n{'=' * 60}\n=== ステップ {s}: {name} ===\n{'=' * 60}")
        if not fn():
            print(f"\n失敗: ステップ {s}（{name}）")
            return 1

    print("\n=== 完了 ===")
    if 1 in steps:
        print(f"最終結果: {(MP / 'world_landmark_model').relative_to(ROOT)}")
        print("解説: docs/11_WORLD_LANDMARK_MODEL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
