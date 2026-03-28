"""
座標変換モジュール（Y軸反転修正版）

MediaPipe の Y 軸は画像下向き正、Unity GT は上向き正。
MediaPipe 相対座標の Y を反転して Unity 系に揃える。
"""

import numpy as np
from typing import Dict, Tuple
from scripts.logger import get_logger


class CoordinateTransformer:
    def __init__(self):
        self.logger = get_logger("CoordinateTransformer")
        self.hip_joints = ['LEFT_HIP', 'RIGHT_HIP']
        self.logger.info("CoordinateTransformer initialized (Y-flip for MediaPipe)")

    def right_to_left_hand(self, coords: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        transformed = {}
        for joint_name, coord in coords.items():
            transformed[joint_name] = np.array([coord[0], coord[1], coord[2]], dtype=np.float64)
        return transformed

    def calculate_hip_center(self, coords: Dict[str, np.ndarray]) -> np.ndarray:
        left_hip = coords.get('LEFT_HIP')
        right_hip = coords.get('RIGHT_HIP')
        if left_hip is None or right_hip is None:
            raise ValueError("Hip joints not found")
        return (left_hip + right_hip) / 2.0

    def to_relative_coordinates(self, coords: Dict[str, np.ndarray], hip_center: np.ndarray) -> Dict[str, np.ndarray]:
        return {name: coord - hip_center for name, coord in coords.items()}

    def transform_ground_truth(self, gt_coords: Dict[str, np.ndarray]) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
        lh_coords = self.right_to_left_hand(gt_coords)
        hip_center = self.calculate_hip_center(lh_coords)
        return self.to_relative_coordinates(lh_coords, hip_center), hip_center

    def transform_mediapipe(self, mp_coords: Dict[str, np.ndarray]) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
        hip_center = self.calculate_hip_center(mp_coords)
        relative = self.to_relative_coordinates(mp_coords, hip_center)
        # Y軸反転: MediaPipe は Y 下向き正 → Unity は Y 上向き正 に合わせる
        for name in relative:
            relative[name] = np.array([relative[name][0], -relative[name][1], relative[name][2]], dtype=np.float64)
        return relative, hip_center

    def calculate_angle_xy(self, coord: np.ndarray) -> float:
        return np.arctan2(coord[1], coord[0])

    def calculate_angle_xz(self, coord: np.ndarray) -> float:
        return np.arctan2(coord[2], coord[0])

    def normalize_angle(self, angle: float) -> float:
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle

    def calculate_differences(self, gt_coords: Dict[str, np.ndarray], mp_coords: Dict[str, np.ndarray]) -> Dict:
        differences = {}
        for joint_name in gt_coords.keys():
            if joint_name not in mp_coords:
                continue
            gt = gt_coords[joint_name]
            mp = mp_coords[joint_name]
            error_3d = np.linalg.norm(mp - gt)
            theta_gt = self.calculate_angle_xy(gt)
            theta_mp = self.calculate_angle_xy(mp)
            delta_theta = self.normalize_angle(theta_mp - theta_gt)
            psi_gt = self.calculate_angle_xz(gt)
            psi_mp = self.calculate_angle_xz(mp)
            delta_psi = self.normalize_angle(psi_mp - psi_gt)
            differences[joint_name] = {
                'gt_coord': gt, 'mp_coord': mp, 'delta_xyz': mp - gt, 'error_3d': error_3d,
                'theta_gt': theta_gt, 'theta_mp': theta_mp, 'delta_theta': delta_theta,
                'delta_theta_deg': np.degrees(delta_theta),
                'psi_gt': psi_gt, 'psi_mp': psi_mp, 'delta_psi': delta_psi,
                'delta_psi_deg': np.degrees(delta_psi),
            }
        return differences
