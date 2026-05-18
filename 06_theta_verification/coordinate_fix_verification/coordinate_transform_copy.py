"""
座標変換のコピー（Y軸反転検証用）

05_direction_detection の coordinate_transform と同等だが、
MediaPipe の Y 反転オプションを追加。
"""

import numpy as np
from typing import Dict, Tuple


def calculate_angle_xy(x: float, y: float) -> float:
    """XY平面での角度 theta = arctan2(y, x) [rad]"""
    return np.arctan2(y, x)


def calculate_angle_xz(x: float, z: float) -> float:
    """XZ平面での角度 psi = arctan2(z, x) [rad]"""
    return np.arctan2(z, x)


def normalize_angle(angle: float) -> float:
    """角度を -pi ～ pi に正規化"""
    while angle > np.pi:
        angle -= 2 * np.pi
    while angle < -np.pi:
        angle += 2 * np.pi
    return angle


def compute_delta_theta_psi(
    gt_x: float, gt_y: float, gt_z: float,
    mp_x: float, mp_y: float, mp_z: float,
    mp_y_flip: bool = False,
) -> Tuple[float, float]:
    """
    delta_theta, delta_psi を計算。

    Args:
        mp_y_flip: True なら MediaPipe の Y を反転してから角度計算
                   (MP: Y下向き正 → Unity: Y上向き正 に合わせる)
    """
    theta_gt = calculate_angle_xy(gt_x, gt_y)
    psi_gt = calculate_angle_xz(gt_x, gt_z)

    mp_y_use = -mp_y if mp_y_flip else mp_y
    theta_mp = calculate_angle_xy(mp_x, mp_y_use)
    psi_mp = calculate_angle_xz(mp_x, mp_z)

    delta_theta = normalize_angle(theta_mp - theta_gt)
    delta_psi = normalize_angle(psi_mp - psi_gt)

    return np.degrees(delta_theta), np.degrees(delta_psi)
