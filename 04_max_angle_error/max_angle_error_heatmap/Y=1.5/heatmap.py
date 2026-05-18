import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

HERE = Path(__file__).parent
calc_csv = HERE.parent.parent / "calculation" / HERE.name / "coordinate_max_angle_error.csv"
df = pd.read_csv(calc_csv)

y_layer = float(HERE.name.replace("Y=", ""))
camera_y_values = [y_layer]

body_parts = ["Shoulder", "Elbow", "Hip", "Knee"]
lr = ["R", "L"]

for camera_y in camera_y_values:
    for part in body_parts:
        for side in lr:
            column_name = f"{side}_{part}"
            df_filtered = df[df["camera_y"] == camera_y].copy()
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

            plt.title(f"{side}_{part} Angle Error Heatmap (camera_y = {camera_y})", fontsize=14)
            plt.xlabel("Camera Z Position", fontsize=12)
            plt.ylabel("Camera X Position", fontsize=12)
            plt.tight_layout()

            filename = f"heatmap_{side.lower()}_{part.lower()}_y{camera_y}.png"
            plt.savefig(HERE / filename, dpi=150)
            plt.close()
            print(f"Heatmap saved as '{filename}'")
