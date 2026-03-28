#!/usr/bin/env python3
"""カメラ配置図を生成（論文用）"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# カメラ位置: X, Z = -6 ~ 6 (13点) のうち、中央5×5 (-2 ~ 2) を除外
x_positions = []
z_positions = []

for x in range(-6, 7):  # -6 ~ 6
    for z in range(-6, 7):  # -6 ~ 6
        # 中央5×5 を除外
        if -2 <= x <= 2 and -2 <= z <= 2:
            continue
        x_positions.append(x)
        z_positions.append(z)

print(f"Total camera positions: {len(x_positions)}")

# 図を作成
fig, ax = plt.subplots(figsize=(8, 8))

# カメラ位置をプロット（単一色）
ax.scatter(x_positions, z_positions, marker='x', s=80, c='crimson', linewidths=1.5)

# アバターの進行方向を示す矢印（薄く）
# (0, 0, -3) から (0, 0, 3) へ向かう矢印
ax.arrow(0, -3, 0, 6, 
         head_width=0.4, head_length=0.3, 
         fc='gray', ec='gray', alpha=0.3, 
         linewidth=2, zorder=1)

# グリッド設定
ax.set_xlim(-7, 7)
ax.set_ylim(-7, 7)
ax.set_xticks(range(-6, 7))
ax.set_yticks(range(-6, 7))
ax.set_xlabel('X', fontsize=14)
ax.set_ylabel('Z', fontsize=14)
ax.set_aspect('equal')
ax.grid(True, linestyle='--', alpha=0.5)

# タイトルなし（論文では caption で説明）

plt.tight_layout()

# 保存
output_path = 'Images/camera_layout.png'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved: {output_path}")
