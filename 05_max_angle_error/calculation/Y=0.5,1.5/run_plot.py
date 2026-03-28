#!/usr/bin/env python3
"""
時系列グラフ作成の実行スクリプト（ラッパー）
02_mediapipe_processed の CSV を参照（重複コピー不要）
"""
import os
import glob
import sys
from pathlib import Path

# プロジェクトルートと MediaPipe ディレクトリ
current_dir = Path(__file__).parent  # calculation/Y=0.5,1.5/
y_range = current_dir.name  # Y=0.5,1.5
project_root = current_dir.parent.parent.parent
mp_dir = project_root / "02_mediapipe_processed" / y_range

print(f"作業ディレクトリ: {current_dir}")
os.chdir(current_dir)

# 02_mediapipe_processed から CSV を参照
csv_pattern = str(mp_dir / "CapturedFrames_*.csv")
csv_files = glob.glob(csv_pattern)
print(f"発見されたCSVファイル: {len(csv_files)}個 (from {mp_dir})")

if not csv_files:
    print("エラー: CSVファイルが見つかりません")
    print(f"検索パターン: {csv_pattern}")
    sys.exit(1)

# GT CSVパス
gt_csv = str(project_root / "synced_joint_positions.csv")
print(f"Ground Truth CSV: {gt_csv}")

if not os.path.exists(gt_csv):
    print(f"エラー: Ground Truth CSVが見つかりません: {gt_csv}")
    sys.exit(1)

# 出力ディレクトリ
output_dir = "graphs"

# 関節リスト
joints = ['L_Elbow', 'R_Elbow', 'L_Knee', 'R_Knee', 'L_Shoulder', 'R_Shoulder', 'L_Hip', 'R_Hip']

# スクリプトをインポートして実行
from plot_time_series_error import TimeSeriesErrorPlotter

print("時系列グラフ作成を開始...")
plotter = TimeSeriesErrorPlotter(output_dir=output_dir)

# 各CSVファイルを個別に処理（フルパスのCSVパターンを使用）
plotter.process_all_coordinates(csv_pattern, gt_csv, joints)

print("完了！")


