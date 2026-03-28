"""
全データ処理（Y軸反転修正版）
方向角誤差・相関の CSV を出力
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import config
from scripts.data_loader import DataLoader
from scripts.coordinate_transform import CoordinateTransformer
from scripts.logger import get_logger


def process_single_frame(loader, transformer, gt_df, mp_df, frame_id, camera_name):
    try:
        gt_coords_raw = loader.get_frame_coordinates(gt_df, frame_id, is_mediapipe=False)
        mp_coords_raw = loader.get_frame_coordinates(mp_df, frame_id, is_mediapipe=True)
        if not gt_coords_raw or not mp_coords_raw:
            return None
        gt_coords_relative, _ = transformer.transform_ground_truth(gt_coords_raw)
        mp_coords_relative, _ = transformer.transform_mediapipe(mp_coords_raw)
        differences = transformer.calculate_differences(gt_coords_relative, mp_coords_relative)
        results = []
        for joint_name, diff in differences.items():
            results.append({
                'frame_id': frame_id, 'camera': camera_name, 'joint': joint_name,
                'gt_x': diff['gt_coord'][0], 'gt_y': diff['gt_coord'][1], 'gt_z': diff['gt_coord'][2],
                'mp_x': diff['mp_coord'][0], 'mp_y': diff['mp_coord'][1], 'mp_z': diff['mp_coord'][2],
                'theta_gt_deg': diff['theta_gt'] * 180 / np.pi, 'theta_mp_deg': diff['theta_mp'] * 180 / np.pi,
                'delta_theta_deg': diff['delta_theta_deg'],
                'psi_gt_deg': diff['psi_gt'] * 180 / np.pi, 'psi_mp_deg': diff['psi_mp'] * 180 / np.pi,
                'delta_psi_deg': diff['delta_psi_deg'], 'error_3d': diff['error_3d'],
            })
        return results
    except Exception:
        return None


def create_summary(df_detailed):
    summary_data = []
    for (frame_id, camera), group in df_detailed.groupby(['frame_id', 'camera']):
        group_no_hip = group[~group['joint'].str.contains('HIP')]
        if len(group_no_hip) == 0:
            continue
        summary_data.append({
            'frame_id': frame_id, 'camera': camera, 'num_joints': len(group_no_hip),
            'mean_abs_delta_theta': group_no_hip['delta_theta_deg'].abs().mean(),
            'mean_abs_delta_psi': group_no_hip['delta_psi_deg'].abs().mean(),
            'max_abs_delta_theta': group_no_hip['delta_theta_deg'].abs().max(),
            'max_abs_delta_psi': group_no_hip['delta_psi_deg'].abs().max(),
            'median_abs_delta_theta': group_no_hip['delta_theta_deg'].abs().median(),
            'median_abs_delta_psi': group_no_hip['delta_psi_deg'].abs().median(),
            'std_delta_theta': group_no_hip['delta_theta_deg'].std(),
            'std_delta_psi': group_no_hip['delta_psi_deg'].std(),
        })
    return pd.DataFrame(summary_data)


def create_joint_summary(df_detailed):
    df_no_hip = df_detailed[~df_detailed['joint'].str.contains('HIP')]
    joint_summary = df_no_hip.groupby('joint').agg({
        'delta_theta_deg': ['mean', 'std', 'min', 'max', lambda x: x.abs().mean()],
        'delta_psi_deg': ['mean', 'std', 'min', 'max', lambda x: x.abs().mean()],
        'error_3d': ['mean', 'std', 'min', 'max'],
    }).round(2)
    joint_summary.columns = [
        'theta_mean', 'theta_std', 'theta_min', 'theta_max', 'theta_abs_mean',
        'psi_mean', 'psi_std', 'psi_min', 'psi_max', 'psi_abs_mean',
        'error3d_mean', 'error3d_std', 'error3d_min', 'error3d_max',
    ]
    return joint_summary.reset_index()


def main():
    logger = get_logger("ProcessAllData")
    logger.section("11: Process All Data (Y-flip fixed)")
    config.create_output_dirs()
    output_dir = config.OUTPUT_DIR / "processed_data"
    output_dir.mkdir(exist_ok=True)

    loader = DataLoader()
    transformer = CoordinateTransformer()
    gt_df = loader.load_ground_truth()
    logger.info(f"GroundTruth: {len(gt_df)} rows")

    all_cameras = []
    for y_range in config.Y_RANGES:
        cams = loader.list_available_cameras(y_range=y_range)
        all_cameras.extend(cams)
    cameras = all_cameras
    logger.info(f"Total cameras: {len(cameras)}")

    all_results = []
    for camera_idx, camera_name in enumerate(cameras, 1):
        logger.info(f"[{camera_idx}/{len(cameras)}] {camera_name}")
        try:
            mp_df = loader.load_mediapipe(camera_name)
            if mp_df is None or len(mp_df) == 0:
                continue
            gt_frames = set(gt_df['Frame'].unique())
            mp_frames = set(mp_df['frame_id'].unique())
            common_frames = sorted(gt_frames.intersection(mp_frames))
            if not common_frames:
                continue
            for frame_id in tqdm(common_frames, desc=f"  {camera_name}", leave=False):
                results = process_single_frame(loader, transformer, gt_df, mp_df, frame_id, camera_name)
                if results:
                    all_results.extend(results)
        except Exception as e:
            logger.error(f"  Failed: {e}")

    if not all_results:
        logger.error("No results!")
        return 1

    df_detailed = pd.DataFrame(all_results)
    df_summary = create_summary(df_detailed)
    df_joint_summary = create_joint_summary(df_detailed)

    detailed_file = output_dir / "detailed_results.csv"
    summary_file = output_dir / "frame_camera_summary.csv"
    joint_summary_file = output_dir / "joint_summary.csv"

    df_detailed.to_csv(detailed_file, index=False, encoding='utf-8-sig')
    df_summary.to_csv(summary_file, index=False, encoding='utf-8-sig')
    df_joint_summary.to_csv(joint_summary_file, index=False, encoding='utf-8-sig')

    logger.info(f"Saved: {detailed_file}")
    logger.info(f"Saved: {summary_file}")
    logger.info(f"Saved: {joint_summary_file}")
    logger.info(f"Mean |Delta theta|: {df_summary['mean_abs_delta_theta'].mean():.2f} deg")
    logger.info(f"Mean |Delta psi|: {df_summary['mean_abs_delta_psi'].mean():.2f} deg")
    logger.info("\n[Joint summary]\n" + df_joint_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
