import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# CSVファイルを読み込む
df = pd.read_csv('coordinate_max_angle_error.csv')

body_parts = ['Shoulder', 'Elbow', 'Hip', 'Knee']
lr = ['R', 'L']
camera_y_values = [0.5, 1.5]  # 両方のcamera_y値を処理

for camera_y in camera_y_values:
    for part in body_parts:
        for side in lr:
            column_name = f'{side}_{part}'
            df_filtered = df[df['camera_y'] == camera_y].copy()

            # ピボットテーブルを作成（x軸: camera_z, y軸: camera_x, 値: 指定した関節のMAE）
            pivot_table = df_filtered.pivot_table(
                values=column_name,
                index='camera_x',
                columns='camera_z',
                aggfunc='mean'
            )

            # ヒートマップを描画
            plt.figure(figsize=(12, 8))
            sns.heatmap(
                pivot_table,
                annot=True,
                fmt='.1f',
                cmap='RdYlGn_r',  # 赤が高誤差、緑が低誤差
                cbar_kws={'label': f'{side}_{part} MAE (degrees)'},
                linewidths=0.5,
                vmin=0,
                vmax=60
            )

            plt.title(f'{side}_{part} Angle Error Heatmap (camera_y = {camera_y})', fontsize=14)
            plt.xlabel('Camera Z Position', fontsize=12)
            plt.ylabel('Camera X Position', fontsize=12)
            plt.tight_layout()

            # 画像を保存
            filename = f'heatmap_{side.lower()}_{part.lower()}_y{camera_y}.png'
            plt.savefig(filename, dpi=150)
            plt.close()  # メモリリークを防ぐため、show()の代わりにclose()を使用
            print(f"Heatmap saved as '{filename}'")
