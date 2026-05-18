"""
全主要関節について、Δθ・Δψ 誤差をカメラ位置（X, Z）ごとに可視化するヒートマップを生成する。
入力: 05_direction_detection/output/processed_data/detailed_results.csv
出力: output/heatmap/heatmap_{JOINT}_theta_Y{y}.jpg, heatmap_{JOINT}_psi_Y{y}.jpg
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# プロジェクトルート（05_direction_detection）を path に追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import config

# 主要関節（論文用は肘・腰のみで十分な場合 PAPER_JOINTS を使用）
MAJOR_JOINTS = [
    'LEFT_SHOULDER', 'RIGHT_SHOULDER',
    'LEFT_ELBOW', 'RIGHT_ELBOW',
    'LEFT_WRIST', 'RIGHT_WRIST',
    'LEFT_HIP', 'RIGHT_HIP',
    'LEFT_KNEE', 'RIGHT_KNEE',
    'LEFT_ANKLE', 'RIGHT_ANKLE',
]
PAPER_JOINTS = ['LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_HIP', 'RIGHT_HIP']  # 論文図で使用
# 論文用ヒートマップの共通カラースケール（肘Δθ・腰Δψで統一、比較しやすくする）
PAPER_HEATMAP_VMIN = 0
PAPER_HEATMAP_VMAX = 180


def parse_camera_xyz(camera_name: str):
    """CapturedFrames_X_Y_Z から (camera_x, camera_y, camera_z) を返す。"""
    try:
        parts = camera_name.replace('CapturedFrames_', '').split('_')
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (IndexError, ValueError):
        return None, None, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper-only', action='store_true', help='Generate only paper figures (elbow, hip, Y=0.5)')
    args = parser.parse_args()

    detailed_csv = config.OUTPUT_DIR / 'processed_data' / 'detailed_results.csv'
    if not detailed_csv.exists():
        print(f"[ERROR] Not found: {detailed_csv}")
        return

    out_dir = config.OUTPUT_DIR / 'heatmap'
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output directory: {out_dir} (11: Y-flip corrected)")

    joints_to_use = PAPER_JOINTS if args.paper_only else MAJOR_JOINTS
    if args.paper_only:
        print("[INFO] Paper-only mode: LEFT_ELBOW, RIGHT_ELBOW, LEFT_HIP, RIGHT_HIP, Y=0.5")

    df = pd.read_csv(detailed_csv, usecols=['frame_id', 'camera', 'joint', 'delta_theta_deg', 'delta_psi_deg'])
    df = df[df['joint'].isin(joints_to_use)]  # 対象関節のみに絞って高速化
    xyz = df['camera'].apply(parse_camera_xyz)
    df['camera_x'] = [t[0] for t in xyz]
    df['camera_y'] = [t[1] for t in xyz]
    df['camera_z'] = [t[2] for t in xyz]
    df = df.dropna(subset=['camera_x', 'camera_y', 'camera_z'])

    joints_in_data = [j for j in joints_to_use if j in df['joint'].values]
    print(f"[INFO] Joints to process: {len(joints_in_data)} -> {joints_in_data}")

    y_values = [0.5] if args.paper_only else sorted(df['camera_y'].unique())

    for joint in joints_in_data:
        df_j = df[df['joint'] == joint].copy()
        for y_val in y_values:
            df_y = df_j[df_j['camera_y'] == y_val]
            if df_y.empty:
                continue
            y_suffix = str(y_val).replace('.', '_')
            for metric, col, label in [
                ('theta', 'delta_theta_deg', r'Mean |$\Delta\theta$| (deg)'),
                ('psi', 'delta_psi_deg', r'Mean |$\Delta\psi$| (deg)'),
            ]:
                pivot = df_y.groupby(['camera_x', 'camera_z'])[col].apply(
                    lambda x: x.abs().mean()
                ).unstack(level=-1)
                if pivot.empty or pivot.size < 2:
                    continue
                vmin, vmax = (PAPER_HEATMAP_VMIN, PAPER_HEATMAP_VMAX) if args.paper_only else (None, None)
                plt.figure(figsize=(12, 10))
                sns.heatmap(
                    pivot,
                    annot=True,
                    fmt='.1f',
                    cmap='RdYlGn_r',
                    vmin=vmin,
                    vmax=vmax,
                    cbar_kws={'label': label, 'shrink': 0.8},
                    linewidths=0.5,
                    annot_kws={'fontsize': 9},
                )
                plt.title(f'{joint} {metric.upper()} by camera (Y={y_val}) [11: Y-flip]', fontsize=16)
                plt.xlabel('Camera Z', fontsize=14)
                plt.ylabel('Camera X', fontsize=14)
                plt.xticks(fontsize=11)
                plt.yticks(fontsize=11)
                plt.tight_layout()
                fname = out_dir / f'heatmap_{joint}_{metric}_Y{y_suffix}.jpg'
                plt.savefig(fname, dpi=200, bbox_inches='tight', format='jpg')
                plt.close()
                print(f"[SAVE] {fname}")

    print("[DONE] All heatmaps generated.")


if __name__ == '__main__':
    main()
