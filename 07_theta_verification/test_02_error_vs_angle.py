"""
テスト02: error_3d と |Δθ| の関係

仮説: error_3d が小さいのに |Δθ| が大きいケースが多ければ、
      座標系の回転（角度の定義の違い）の影響が疑われる
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent.parent
DETAILED_CSV = BASE / "06_direction_detection" / "output" / "processed_data" / "detailed_results.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    if not DETAILED_CSV.exists():
        print(f"[ERROR] 見つかりません: {DETAILED_CSV}")
        return 1

    df = pd.read_csv(DETAILED_CSV)
    elbows = df[df["joint"].isin(["LEFT_ELBOW", "RIGHT_ELBOW"])].copy()
    elbows["abs_delta_theta"] = elbows["delta_theta_deg"].abs()

    # 相関係数
    r = np.corrcoef(elbows["error_3d"], elbows["abs_delta_theta"])[0, 1]
    print(f"error_3d と |Δθ| の相関係数: {r:.4f}")

    # 四分位で分割
    e33 = elbows["error_3d"].quantile(0.33)
    e67 = elbows["error_3d"].quantile(0.67)
    low_err = elbows[elbows["error_3d"] <= e33]
    mid_err = elbows[(elbows["error_3d"] > e33) & (elbows["error_3d"] <= e67)]
    high_err = elbows[elbows["error_3d"] > e67]

    print("\n=== error_3d no sanbun'i goto no |delta_theta| heikin ===")
    print(f"  error_3d small (<={e33:.3f}): |delta_theta| mean = {low_err['abs_delta_theta'].mean():.1f} deg")
    print(f"  error_3d mid:                |delta_theta| mean = {mid_err['abs_delta_theta'].mean():.1f} deg")
    print(f"  error_3d large (>{e67:.3f}): |delta_theta| mean = {high_err['abs_delta_theta'].mean():.1f} deg")

    # 矛盾ケース: error_3d が小さいのに |Δθ| が 90° 以上
    suspicious = elbows[(elbows["error_3d"] < 0.35) & (elbows["abs_delta_theta"] > 90)]
    print(f"\nSuspicious (error_3d<0.35 and |delta_theta|>90): {len(suspicious)} / {len(elbows)} ({100*len(suspicious)/len(elbows):.1f}%)")
    if len(suspicious) > 0:
        out_csv = OUTPUT_DIR / "suspicious_small_error_large_angle.csv"
        suspicious.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print(f"[SAVE] {out_csv}")

    print("\n-> If many cases have small error_3d but large |delta_theta|, coordinate rotation may be involved")


if __name__ == "__main__":
    sys.exit(main() or 0)
