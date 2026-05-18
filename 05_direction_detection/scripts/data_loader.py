"""
データ読み込みモジュール（7 と同一）
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import config
from scripts.logger import get_logger


class DataLoader:
    def __init__(self):
        self.logger = get_logger("DataLoader")
        self.gt_csv = config.GT_CSV
        self.mp_dir = config.MP_DIR
        self.joint_mapping = config.JOINT_MAPPING
        self.logger.info("DataLoader initialized")

    def load_ground_truth(self, frame_id: Optional[int] = None) -> pd.DataFrame:
        if not self.gt_csv.exists():
            raise FileNotFoundError(f"GroundTruth CSV not found: {self.gt_csv}")
        df = pd.read_csv(self.gt_csv)
        if frame_id is not None:
            df = df[df['Frame'] == frame_id]
        return df

    def load_mediapipe(self, camera_position: str, y_range: str = None) -> pd.DataFrame:
        if y_range is None:
            try:
                parts = camera_position.replace('CapturedFrames_', '').split('_')
                y_coord = float(parts[1])
                y_range = f"Y={y_coord}" if y_coord in [0.5, 1.0, 1.5, 2.0] else config.DEFAULT_Y_RANGE
            except (IndexError, ValueError):
                y_range = config.DEFAULT_Y_RANGE
        mp_dir = self.mp_dir / y_range
        csv_file = mp_dir / f"{camera_position}.csv"
        if not csv_file.exists():
            raise FileNotFoundError(f"MediaPipe CSV not found: {csv_file}")
        return pd.read_csv(csv_file)

    def get_frame_coordinates(self, df: pd.DataFrame, frame_id: int, is_mediapipe: bool = False) -> Dict[str, np.ndarray]:
        if is_mediapipe:
            return self._extract_mediapipe_coords(df, frame_id)
        return self._extract_ground_truth_coords(df, frame_id)

    def _extract_mediapipe_coords(self, df: pd.DataFrame, frame_id: int) -> Dict[str, np.ndarray]:
        frame_data = df[df['frame_id'] == frame_id]
        if len(frame_data) == 0:
            return {}
        coords = {}
        for joint_name in self.joint_mapping.keys():
            joint_data = frame_data[frame_data['landmark'] == joint_name]
            if not joint_data.empty:
                coords[joint_name] = np.array([
                    joint_data['x'].values[0], joint_data['y'].values[0], joint_data['z'].values[0]
                ], dtype=np.float64)
        return coords

    def _extract_ground_truth_coords(self, df: pd.DataFrame, frame_id: int) -> Dict[str, np.ndarray]:
        frame_data = df[df['Frame'] == frame_id]
        if len(frame_data) == 0:
            return {}
        coords = {}
        gt_to_mediapipe_mapping = {
            'Hips': ['LEFT_HIP', 'RIGHT_HIP'],
            'LeftShoulder': 'LEFT_SHOULDER', 'RightShoulder': 'RIGHT_SHOULDER',
            'LeftLowerArm': 'LEFT_ELBOW', 'RightLowerArm': 'RIGHT_ELBOW',
            'LeftLowerLeg': 'LEFT_KNEE', 'RightLowerLeg': 'RIGHT_KNEE',
            'LeftFoot': 'LEFT_ANKLE', 'RightFoot': 'RIGHT_ANKLE',
            'LeftHand': 'LEFT_WRIST', 'RightHand': 'RIGHT_WRIST',
        }
        for gt_name, mp_name in gt_to_mediapipe_mapping.items():
            x_col, y_col, z_col = f"{gt_name}_X", f"{gt_name}_Y", f"{gt_name}_Z"
            if x_col in frame_data.columns:
                try:
                    coord = np.array([
                        float(frame_data[x_col].values[0]),
                        float(frame_data[y_col].values[0]),
                        float(frame_data[z_col].values[0])
                    ], dtype=np.float64)
                    if isinstance(mp_name, list):
                        for name in mp_name:
                            coords[name] = coord.copy()
                    else:
                        coords[mp_name] = coord
                except (ValueError, IndexError):
                    pass
        return coords

    def list_available_cameras(self, y_range: str = None) -> List[str]:
        if y_range is None:
            y_range = config.DEFAULT_Y_RANGE
        mp_dir = self.mp_dir / y_range
        if not mp_dir.exists():
            return []
        return sorted([f.stem for f in mp_dir.glob("*.csv")])
