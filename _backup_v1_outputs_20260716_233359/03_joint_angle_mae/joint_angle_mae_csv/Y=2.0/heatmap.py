"""同フォルダの coordinate_angle_mae.csv からヒートマップを生成（当層の camera_y のみ）。"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

HERE = Path(__file__).parent
y_tag = HERE.name.replace("Y=", "")
camera_y_values = [float(y_tag)]

df = pd.read_csv(HERE / "coordinate_angle_mae.csv")

body_parts = ["Shoulder", "Elbow", "Hip", "Knee"]
lr = ["R", "L"]

for y_value in camera_y_values:
    for part in body_parts:
        for side in lr:
            column_name = f"{side}_{part}"
            df_filtered = df[df["camera_y"] == y_value].copy()
            if df_filtered.empty:
                continue

            pivot_table = df_filtered.pivot_table(
                values=column_name,
                index="camera_x",
                columns="camera_z",
                aggfunc="mean",
            )

            plt.figure(figsize=(12, 8))
            sns.heatmap(
                pivot_table,
                annot=True,
                fmt=".1f",
                cmap="RdYlGn_r",
                cbar_kws={"label": f"{side}_{part} MAE (degrees)"},
                linewidths=0.5,
                vmin=0,
                vmax=60,
            )

            plt.title(f"{side}_{part} Angle Error Heatmap (camera_y = {y_value})", fontsize=14)
            plt.xlabel("Camera Z Position", fontsize=12)
            plt.ylabel("Camera X Position", fontsize=12)
            plt.tight_layout()

            fn = f"heatmap_{side.lower()}_{part.lower()}_y{y_value}.png"
            plt.savefig(HERE / fn, dpi=150)
            plt.close()
            print(f"Heatmap saved as '{fn}'")
