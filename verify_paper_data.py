#!/usr/bin/env python3
"""Verify paper numbers against actual data."""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
print("=== 1. Table 1 (Joint Angle MAE) - from 03_cal_mae ===")
df1 = pd.read_csv(BASE / "03_cal_mae/Y=0.5,1.5/coordinate_angle_mae.csv")
df2 = pd.read_csv(BASE / "03_cal_mae/Y=1.0.2.0/coordinate_angle_mae.csv")
df = pd.concat([df1, df2], ignore_index=True)
joints = ['L_Shoulder','R_Shoulder','L_Elbow','R_Elbow','L_Hip','R_Hip','L_Knee','R_Knee']
paper = {'L_Shoulder':(35.4,34.9,57.9),'R_Shoulder':(33.9,34.8,52.0),'L_Elbow':(14.7,13.5,49.7),
         'R_Elbow':(14.7,10.0,44.9),'L_Hip':(20.4,18.6,58.7),'R_Hip':(20.3,19.8,52.9),
         'L_Knee':(13.8,12.8,50.6),'R_Knee':(13.5,13.1,28.2)}
for c in joints:
    if c in df.columns:
        v = df[c].dropna()
        m, med, mx = v.mean(), v.median(), v.max()
        p = paper.get(c,(0,0,0))
        ok = abs(m-p[0])<0.5 and abs(med-p[1])<1 and abs(mx-p[2])<2
        print(f"  {c}: mean={m:.1f} med={med:.1f} max={mx:.1f}  paper={p}  OK={ok}")

print("\n=== 2. Direction angles - 06_direction_detection joint_summary ===")
js = pd.read_csv(BASE / "06_direction_detection/output/processed_data/joint_summary.csv")
for _, row in js.iterrows():
    j = row['joint']
    ta = row['theta_abs_mean']
    pa = row['psi_abs_mean']
    print(f"  {j}: |d_theta|={ta:.1f} |d_psi|={pa:.1f}")
print("  Paper: elbow |d_theta|~58, shoulder |d_theta|~10, hip |d_psi|~90")

print("\n=== 2b. Table 1 - try Y=0.5,1.5 only ===")
df_y05 = pd.read_csv(BASE / "03_cal_mae/Y=0.5,1.5/coordinate_angle_mae.csv")
for c in joints:
    if c in df_y05.columns:
        v = df_y05[c].dropna()
        if len(v) > 0:
            print(f"  {c}: mean={v.mean():.1f} (paper {paper.get(c,(0,0,0))[0]})")

print("\n=== 3. Data source check ===")
print("  06_direction_detection: GT=synced_joint_positions, MP=02_mediapipe_processed")
print("  03_cal_mae/04_mae_heatmap: uses 02_mediapipe_processed + 03_cal_mae outputs")
print("  Y-flip: applied ONLY in 06_direction_detection coordinate_transform")
print("  Table 1 (MAE): 3-point angles, Y-flip does NOT affect (relative angles)")
print("  Tables 2-3, heatmaps: from 11 (Y-flip applied)")
