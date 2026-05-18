"""
テスト01: カメラごとの肘 Δθ 分布

仮説: 座標系がカメラ依存なら、カメラごとに Δθ の平均が大きくばらつく
      MediaPipe の座標系がカメラ方向に依存しているか確認
"""

import sys
from pathlib import Path
import pandas as pd

# プロジェクトルート
BASE = Path(__file__).resolve().parent.parent
DETAILED_CSV = BASE / "05_direction_detection" / "output" / "processed_data" / "detailed_results.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def parse_camera_xyz(name: str):
    """CapturedFrames_X_Y_Z -> (x, y, z)"""
    try:
        parts = name.replace("CapturedFrames_", "").split("_")
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (IndexError, ValueError):
        return None, None, None


def main():
    if not DETAILED_CSV.exists():
        print(f"[ERROR] 見つかりません: {DETAILED_CSV}")
        return 1

    df = pd.read_csv(DETAILED_CSV)
    elbows = df[df["joint"].isin(["LEFT_ELBOW", "RIGHT_ELBOW"])].copy()

    # カメラ座標を付与
    xyz = elbows["camera"].apply(parse_camera_xyz)
    elbows["cam_x"] = [t[0] for t in xyz]
    elbows["cam_y"] = [t[1] for t in xyz]
    elbows["cam_z"] = [t[2] for t in xyz]

    # カメラごとの統計
    by_camera = elbows.groupby(["camera", "joint"]).agg(
        delta_theta_mean=("delta_theta_deg", "mean"),
        delta_theta_std=("delta_theta_deg", "std"),
        delta_theta_abs_mean=("delta_theta_deg", lambda x: x.abs().mean()),
        error_3d_mean=("error_3d", "mean"),
        count=("frame_id", "count"),
    ).reset_index()

    # 出力
    out_csv = OUTPUT_DIR / "elbow_delta_theta_by_camera.csv"
    by_camera.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {out_csv}")

    # サマリー表示
    print("\n=== Elbow delta_theta by camera ===")
    for joint in ["LEFT_ELBOW", "RIGHT_ELBOW"]:
        sub = by_camera[by_camera["joint"] == joint]
        print(f"\n{joint}:")
        print(f"  Cameras: {len(sub)}")
        print(f"  delta_theta mean range: {sub['delta_theta_mean'].min():.1f} - {sub['delta_theta_mean'].max():.1f} deg")
        print(f"  delta_theta mean std: {sub['delta_theta_mean'].std():.1f} deg")
        print(f"  Overall delta_theta mean: {sub['delta_theta_mean'].mean():.1f} deg")

    print("\n-> If camera-wise means vary a lot, camera-dependent coordinate system is suspected")


if __name__ == "__main__":
    sys.exit(main() or 0)
