#!/usr/bin/env python3
"""論文数値とパイプライン CSV の突合せ（期待値は paper/source/IEEJ_ja/main.tex を正とする）。"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
MAE_DIR = BASE / "03_joint_angle_mae"
DIR05 = BASE / "05_direction_detection"

# IEEJ_ja 表 tab:joint_angle_error（列: mean, median, max deg）
PAPER_TABLE1 = {
    "L_Shoulder": (39.8, 39.2, 70.1),
    "R_Shoulder": (39.0, 40.0, 58.2),
    "L_Elbow": (18.6, 15.9, 56.9),
    "R_Elbow": (18.2, 13.6, 46.2),
    "L_Hip": (30.2, 29.4, 66.0),
    "R_Hip": (33.3, 32.2, 81.7),
    "L_Knee": (17.0, 16.6, 43.4),
    "R_Knee": (19.5, 19.4, 62.3),
}

# IEEJ_ja 表 tab:direction_angle_error — joint_summary 由来（|Δθ|平均, |Δψ|平均）。股関節は summary に無いので別検証。
PAPER_DIRECTION_ABS_MEAN = {
    "LEFT_SHOULDER": (10.4, 94.1),
    "RIGHT_SHOULDER": (9.3, 92.7),
    "LEFT_ELBOW": (58.3, 87.3),
    "RIGHT_ELBOW": (59.3, 88.6),
    "LEFT_WRIST": (84.3, 88.6),
    "RIGHT_WRIST": (91.5, 91.6),
    "LEFT_KNEE": (17.4, 84.7),
    "RIGHT_KNEE": (18.5, 87.2),
    "LEFT_ANKLE": (11.3, 90.6),
    "RIGHT_ANKLE": (11.9, 100.4),
}

# detailed_results から（IEEJ_ja 脚注・表と一致）
PAPER_HIP_FROM_DETAIL = {
    "LEFT_HIP": (83.5, 88.9),
    "RIGHT_HIP": (96.5, 91.1),
}


def main() -> None:
    print("=== 1. Table 1 (Joint Angle MAE) - primary: 03_joint_angle_mae ===")
    mae_layers = [
        MAE_DIR / "Y=0.5" / "coordinate_angle_mae.csv",
        MAE_DIR / "Y=1.0" / "coordinate_angle_mae.csv",
        MAE_DIR / "Y=1.5" / "coordinate_angle_mae.csv",
        MAE_DIR / "Y=2.0" / "coordinate_angle_mae.csv",
    ]
    parts = [p for p in mae_layers if p.is_file()]
    if len(parts) != 4:
        print(
            f"  スキップ: 層別 MAE CSV が4つ必要です（現在 {len(parts)}/4）。"
            "python tools/migrate_y_folders_to_layers.py 後に run_cal_mae を各層で実行してください。"
        )
    if len(parts) == 4:
        df = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
        for col, paper in PAPER_TABLE1.items():
            if col not in df.columns:
                print(f"  {col}: 列なし")
                continue
            v = df[col].dropna()
            m, med, mx = float(v.mean()), float(v.median()), float(v.max())
            ok = (
                abs(m - paper[0]) < 0.55
                and abs(med - paper[1]) < 1.05
                and abs(mx - paper[2]) < 2.05
            )
            print(f"  {col}: mean={m:.1f} med={med:.1f} max={mx:.1f}  paper={paper}  OK={ok}")

    js_path = DIR05 / "output" / "processed_data" / "joint_summary.csv"
    print("\n=== 2. Direction angles - joint_summary.csv (05_direction_detection) ===")
    if not js_path.is_file():
        print(f"  スキップ: {js_path} がありません")
    else:
        js = pd.read_csv(js_path)
        for _, row in js.iterrows():
            j = str(row["joint"])
            ta = float(row["theta_abs_mean"])
            pa = float(row["psi_abs_mean"])
            exp = PAPER_DIRECTION_ABS_MEAN.get(j)
            if exp:
                ok = abs(ta - exp[0]) < 0.55 and abs(pa - exp[1]) < 1.05
                print(f"  {j}: |d_theta|={ta:.1f} |d_psi|={pa:.1f}  paper={exp}  OK={ok}")
            else:
                print(f"  {j}: |d_theta|={ta:.1f} |d_psi|={pa:.1f}  (no IEEJ_ja row)")

    detail_path = DIR05 / "output" / "processed_data" / "detailed_results.csv"
    print("\n=== 3. Hip |delta theta|,|delta psi| mean - detailed_results (IEEJ_ja hips) ===")
    if not detail_path.is_file():
        print(f"  スキップ: {detail_path} がありません")
    else:
        df = pd.read_csv(detail_path, usecols=["joint", "delta_theta_deg", "delta_psi_deg"])
        for jnt, (et, ep) in PAPER_HIP_FROM_DETAIL.items():
            sub = df[df["joint"] == jnt]
            if len(sub) == 0:
                print(f"  {jnt}: データなし")
                continue
            ta = sub["delta_theta_deg"].abs().mean()
            pa = sub["delta_psi_deg"].abs().mean()
            ok = abs(float(ta) - et) < 0.55 and abs(float(pa) - ep) < 0.55
            print(
                f"  {jnt}: |d_theta|={float(ta):.1f} |d_psi|={float(pa):.1f}  "
                f"paper=({et},{ep})  OK={ok}"
            )

    print("\n=== 4. Data source memo ===")
    print("  05_direction_detection: GT=synced_joint_positions, MP=02_mediapipe_processed")
    print("  03_joint_angle_mae: per-camera MAE CSV（run_cal_mae 等で生成）→ create_statistics_table で集計可")
    print("  Y-flip: 方向角のみ 05_direction_detection/scripts/coordinate_transform.py")
    print("  関節角 MAE は座標反転の影響を受けない（3点角の幾何）")


if __name__ == "__main__":
    main()
