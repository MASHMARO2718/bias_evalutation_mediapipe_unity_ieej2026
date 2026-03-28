"""
Test 04: Coordinate system verification

Hypotheses:
  - MediaPipe outputs in camera coordinate system -> delta_theta correlates with camera azimuth
  - Unity theta_gt is camera-invariant for same (frame, joint)
  - delta_theta approx equals camera rotation (azimuth)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Project paths
BASE = Path(__file__).resolve().parent.parent
DETAILED_CSV = BASE / "06_direction_detection" / "output" / "processed_data" / "detailed_results.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def parse_camera_xyz(name: str):
    """CapturedFrames_X_Y_Z -> (x, y, z)"""
    try:
        parts = name.replace("CapturedFrames_", "").split("_")
        return float(parts[0]), float(parts[1]), float(parts[2])
    except (IndexError, ValueError):
        return None, None, None


def camera_azimuth_deg(cam_x: float, cam_z: float) -> float:
    """Azimuth in XZ plane (Unity): atan2(cam_x, cam_z), degrees."""
    return np.degrees(np.arctan2(cam_x, cam_z))


def camera_elevation_deg(cam_x: float, cam_y: float, cam_z: float) -> float:
    """Elevation: angle above horizontal (XZ plane). atan2(cam_y, sqrt(cx^2+cz^2)), degrees."""
    horiz = np.sqrt(cam_x**2 + cam_z**2)
    return np.degrees(np.arctan2(cam_y, horiz))


def main():
    if not DETAILED_CSV.exists():
        print(f"[ERROR] Not found: {DETAILED_CSV}")
        return 1

    df = pd.read_csv(DETAILED_CSV)

    # Add camera coordinates and angles
    xyz = df["camera"].apply(parse_camera_xyz)
    df["cam_x"] = [t[0] for t in xyz]
    df["cam_y"] = [t[1] for t in xyz]
    df["cam_z"] = [t[2] for t in xyz]
    df = df.dropna(subset=["cam_x", "cam_y", "cam_z"])

    df["camera_azimuth_deg"] = df.apply(
        lambda r: camera_azimuth_deg(r["cam_x"], r["cam_z"]), axis=1
    )
    df["camera_elevation_deg"] = df.apply(
        lambda r: camera_elevation_deg(r["cam_x"], r["cam_y"], r["cam_z"]), axis=1
    )

    results = []

    # 1. theta_gt camera invariance
    print("\n=== 1. theta_gt camera invariance ===")
    inv_stats = (
        df.groupby(["frame_id", "joint"])["theta_gt_deg"]
        .agg(["std", "count"])
        .reset_index()
    )
    max_std = inv_stats["std"].max()
    mean_std = inv_stats["std"].mean()
    results.append({
        "check": "theta_gt_invariance",
        "max_theta_gt_std_deg": max_std,
        "mean_theta_gt_std_deg": mean_std,
        "n_frame_joint_pairs": len(inv_stats),
    })
    print(f"  Max theta_gt std across cameras (per frame,joint): {max_std:.6f} deg")
    print(f"  Mean theta_gt std: {mean_std:.6f} deg")
    print(f"  -> theta_gt is camera-invariant: {max_std < 1e-4}")

    # 2 & 3. delta_theta vs azimuth, delta_psi vs elevation (for elbows)
    print("\n=== 2. delta_theta vs camera azimuth (elbows) ===")
    elbows = df[df["joint"].isin(["LEFT_ELBOW", "RIGHT_ELBOW"])].copy()
    if len(elbows) > 0:
        for joint in ["LEFT_ELBOW", "RIGHT_ELBOW"]:
            sub = elbows[elbows["joint"] == joint]
            r_theta = np.corrcoef(sub["delta_theta_deg"], sub["camera_azimuth_deg"])[0, 1]
            if np.isnan(r_theta):
                r_theta = 0.0
            print(f"  {joint}: Pearson r = {r_theta:.4f}")
            results.append({
                "check": "delta_theta_vs_azimuth",
                "joint": joint,
                "pearson_r": r_theta,
                "n_samples": len(sub),
            })

    print("\n=== 3. delta_psi vs camera elevation (elbows) ===")
    if len(elbows) > 0:
        for joint in ["LEFT_ELBOW", "RIGHT_ELBOW"]:
            sub = elbows[elbows["joint"] == joint]
            r_psi = np.corrcoef(sub["delta_psi_deg"], sub["camera_elevation_deg"])[0, 1]
            if np.isnan(r_psi):
                r_psi = 0.0
            print(f"  {joint}: Pearson r = {r_psi:.4f}")
            results.append({
                "check": "delta_psi_vs_elevation",
                "joint": joint,
                "pearson_r": r_psi,
                "n_samples": len(sub),
            })

    # Summary CSV
    summary = pd.DataFrame(results)
    out_csv = OUTPUT_DIR / "coordinate_verification.csv"
    summary.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n[SAVE] {out_csv}")

    # 4. Scatter plot (optional - matplotlib)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for idx, joint in enumerate(["LEFT_ELBOW", "RIGHT_ELBOW"]):
            sub = elbows[elbows["joint"] == joint]
            ax = axes[idx]
            ax.scatter(sub["camera_azimuth_deg"], sub["delta_theta_deg"], alpha=0.3, s=5)
            ax.set_xlabel("Camera azimuth (deg)")
            ax.set_ylabel("delta_theta (deg)")
            ax.set_title(joint)
            ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
        plt.tight_layout()
        out_png = OUTPUT_DIR / "delta_theta_vs_azimuth.png"
        plt.savefig(out_png, dpi=120, bbox_inches="tight")
        plt.close()
        print(f"[SAVE] {out_png}")
    except ImportError:
        print("[INFO] matplotlib not available, skip scatter plot")

    print("\n-> If delta_theta correlates with camera azimuth, camera-dependent coordinate system is supported")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
