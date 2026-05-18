"""層別 coordinate_angle_mae.csv を統合し論文表1用の統計を出力する。"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
LAYERS = ["Y=0.5", "Y=1.0", "Y=1.5", "Y=2.0"]

frames = []
for layer in LAYERS:
    p = ROOT / layer / "coordinate_angle_mae.csv"
    if p.is_file():
        frames.append(pd.read_csv(p))
    else:
        print(f"警告: 見つかりません {p}")

if not frames:
    raise SystemExit("coordinate_angle_mae.csv が1つもありません")

df_combined = pd.concat(frames, ignore_index=True)

print(f"統合後のデータ数: {len(df_combined)} 行")

out_dir = ROOT
df_combined.to_csv(out_dir / "coordinate_angle_mae_combined.csv", index=False)
print(f"\n統合データを 'coordinate_angle_mae_combined.csv' に保存しました。\n")

joints = {
    "L_Shoulder": "左肩",
    "R_Shoulder": "右肩",
    "L_Elbow": "左肘",
    "R_Elbow": "右肘",
    "L_Hip": "左腰",
    "R_Hip": "右腰",
    "L_Knee": "左膝",
    "R_Knee": "右膝",
}

results = []
for joint_col, joint_name in joints.items():
    values = df_combined[joint_col].dropna()
    if len(values) > 0:
        mae = values.mean()
        median = values.median()
        max_error = values.max()
        results.append(
            {
                "関節": joint_name,
                "平均誤差 (度)": f"{mae:.1f}",
                "中央値 (度)": f"{median:.1f}",
                "最大誤差 (度)": f"{max_error:.1f}",
            }
        )
        print(f"{joint_name}:")
        print(f"  平均誤差: {mae:.1f}度")
        print(f"  中央値: {median:.1f}度")
        print(f"  最大誤差: {max_error:.1f}度")
        print(f"  データ数: {len(values)}")
        print()

df_table = pd.DataFrame(results)
print("=" * 60)
print("Table 1: 関節角度誤差の統計")
print("=" * 60)
print(df_table.to_string(index=False))
print("=" * 60)

df_table.to_csv(out_dir / "joint_angle_error_statistics.csv", index=False, encoding="utf-8-sig")
print(f"\n統計テーブルを 'joint_angle_error_statistics.csv' に保存しました。")

latex_table = df_table.to_latex(index=False, escape=False)
with open(out_dir / "joint_angle_error_statistics.tex", "w", encoding="utf-8") as f:
    f.write("\\begin{table}[h]\n")
    f.write("\\centering\n")
    f.write("\\caption{関節角度誤差の統計}\n")
    f.write("\\label{tab:joint_angle_error}\n")
    f.write(latex_table)
    f.write("\\end{table}\n")
print("LaTeX形式のテーブルを 'joint_angle_error_statistics.tex' に保存しました。")
