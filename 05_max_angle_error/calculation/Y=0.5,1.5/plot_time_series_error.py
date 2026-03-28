#!/usr/bin/env python3
"""
時系列角度誤差プロットスクリプト
各座標・各関節ごとにフレーム単位の角度誤差を時系列グラフで可視化
"""

import os
import pandas as pd
import numpy as np
import glob
from pathlib import Path
import argparse
from typing import Dict, List, Tuple, Optional
import logging
import re
import matplotlib
matplotlib.use('Agg')  # GUI不要のバックエンド
import matplotlib.pyplot as plt

class TimeSeriesErrorPlotter:
    """時系列誤差グラフ作成クラス"""
    
    def __init__(self, output_dir: str = "graphs"):
        self.output_dir = output_dir
        self.setup_logging()
        
        # 関節定義（3点角）
        self.joint_definitions = {
            'L_Elbow': {
                'gt_points': ['LeftUpperArm', 'LeftLowerArm', 'LeftHand'],
                'mp_points': ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'],
                'display_name': 'Left Elbow'
            },
            'R_Elbow': {
                'gt_points': ['RightUpperArm', 'RightLowerArm', 'RightHand'],
                'mp_points': ['RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'],
                'display_name': 'Right Elbow'
            },
            'L_Knee': {
                'gt_points': ['LeftUpperLeg', 'LeftLowerLeg', 'LeftFoot'],
                'mp_points': ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'],
                'display_name': 'Left Knee'
            },
            'R_Knee': {
                'gt_points': ['RightUpperLeg', 'RightLowerLeg', 'RightFoot'],
                'mp_points': ['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'],
                'display_name': 'Right Knee'
            },
            'L_Shoulder': {
                'gt_points': ['Chest', 'LeftUpperArm', 'LeftLowerArm'],
                'mp_points': ['MID_SHOULDER', 'LEFT_SHOULDER', 'LEFT_ELBOW'],
                'display_name': 'Left Shoulder'
            },
            'R_Shoulder': {
                'gt_points': ['Chest', 'RightUpperArm', 'RightLowerArm'],
                'mp_points': ['MID_SHOULDER', 'RIGHT_SHOULDER', 'RIGHT_ELBOW'],
                'display_name': 'Right Shoulder'
            },
            'L_Hip': {
                'gt_points': ['Hips', 'LeftUpperLeg', 'LeftLowerLeg'],
                'mp_points': ['MID_HIP', 'LEFT_HIP', 'LEFT_KNEE'],
                'display_name': 'Left Hip'
            },
            'R_Hip': {
                'gt_points': ['Hips', 'RightUpperLeg', 'RightLowerLeg'],
                'mp_points': ['MID_HIP', 'RIGHT_HIP', 'RIGHT_KNEE'],
                'display_name': 'Right Hip'
            }
        }
    
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('time_series_plot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def extract_camera_coordinates(self, folder_name: str) -> Tuple[float, float, float]:
        """ファイル名からカメラ座標を抽出"""
        pattern = r'CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)'
        match = re.match(pattern, folder_name)
        
        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            z = float(match.group(3))
            return (x, y, z)
        else:
            self.logger.warning(f"座標抽出失敗: {folder_name}")
            return (0.0, 0.0, 0.0)
    
    def calculate_3point_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """3点角を計算（度数法）"""
        v1 = p1 - p2
        v2 = p3 - p2
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return np.nan
        
        cos_angle = dot_product / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def load_mediapipe_data(self, csv_path: str) -> pd.DataFrame:
        """MediaPipe CSVを読み込み"""
        df = pd.read_csv(csv_path)
        df = self.calculate_midpoints(df)
        return df
    
    def calculate_midpoints(self, df: pd.DataFrame) -> pd.DataFrame:
        """MediaPipeデータに中点を追加"""
        midpoints_data = []
        
        for frame_id in df['frame_id'].unique():
            frame_data = df[df['frame_id'] == frame_id]
            
            # MID_SHOULDER
            left_shoulder = frame_data[frame_data['landmark'] == 'LEFT_SHOULDER']
            right_shoulder = frame_data[frame_data['landmark'] == 'RIGHT_SHOULDER']
            
            if not left_shoulder.empty and not right_shoulder.empty:
                mid_shoulder = {
                    'frame_id': frame_id,
                    'landmark': 'MID_SHOULDER',
                    'x': (left_shoulder['x'].iloc[0] + right_shoulder['x'].iloc[0]) / 2,
                    'y': (left_shoulder['y'].iloc[0] + right_shoulder['y'].iloc[0]) / 2,
                    'z': (left_shoulder['z'].iloc[0] + right_shoulder['z'].iloc[0]) / 2,
                    'visibility': min(left_shoulder['visibility'].iloc[0], right_shoulder['visibility'].iloc[0]),
                    'image_path': left_shoulder['image_path'].iloc[0]
                }
                midpoints_data.append(mid_shoulder)
            
            # MID_HIP
            left_hip = frame_data[frame_data['landmark'] == 'LEFT_HIP']
            right_hip = frame_data[frame_data['landmark'] == 'RIGHT_HIP']
            
            if not left_hip.empty and not right_hip.empty:
                mid_hip = {
                    'frame_id': frame_id,
                    'landmark': 'MID_HIP',
                    'x': (left_hip['x'].iloc[0] + right_hip['x'].iloc[0]) / 2,
                    'y': (left_hip['y'].iloc[0] + right_hip['y'].iloc[0]) / 2,
                    'z': (left_hip['z'].iloc[0] + right_hip['z'].iloc[0]) / 2,
                    'visibility': min(left_hip['visibility'].iloc[0], right_hip['visibility'].iloc[0]),
                    'image_path': left_hip['image_path'].iloc[0]
                }
                midpoints_data.append(mid_hip)
        
        if midpoints_data:
            midpoints_df = pd.DataFrame(midpoints_data)
            df = pd.concat([df, midpoints_df], ignore_index=True)
        
        return df
    
    def load_ground_truth_data(self, csv_path: str) -> pd.DataFrame:
        """Ground Truth CSVを読み込み"""
        df = pd.read_csv(csv_path)
        
        if 'Frame' in df.columns:
            df = df.rename(columns={'Frame': 'frame_id'})
        
        return df
    
    def get_point_coordinates(self, df: pd.DataFrame, frame_id: int, point_name: str, 
                            data_type: str, visibility_threshold: float = 0.5) -> Optional[np.ndarray]:
        """指定フレーム・ポイントの座標を取得"""
        if data_type == 'mp':
            point_data = df[(df['frame_id'] == frame_id) & (df['landmark'] == point_name)]
            if point_data.empty:
                return None
            
            if point_data['visibility'].iloc[0] < visibility_threshold:
                return None
            
            return np.array([point_data['x'].iloc[0], point_data['y'].iloc[0], point_data['z'].iloc[0]])
        
        else:  # gt
            point_data = df[df['frame_id'] == frame_id]
            if point_data.empty:
                return None
            
            x_col = f"{point_name}_X"
            y_col = f"{point_name}_Y"
            z_col = f"{point_name}_Z"
            
            if x_col not in df.columns or y_col not in df.columns or z_col not in df.columns:
                return None
            
            x_val = point_data[x_col].iloc[0]
            y_val = point_data[y_col].iloc[0]
            z_val = point_data[z_col].iloc[0]
            
            if pd.isna(x_val) or pd.isna(y_val) or pd.isna(z_val):
                return None
            
            return np.array([x_val, y_val, z_val])
    
    def calculate_joint_errors_per_frame(self, mp_csv_path: str, gt_csv_path: str, 
                                        joint: str) -> Tuple[List[int], List[float]]:
        """
        特定関節の各フレームにおける誤差を計算
        
        Returns:
            Tuple[List[int], List[float]]: (フレームIDリスト, 誤差リスト)
        """
        mp_df = self.load_mediapipe_data(mp_csv_path)
        gt_df = self.load_ground_truth_data(gt_csv_path)
        
        if joint not in self.joint_definitions:
            return [], []
        
        joint_def = self.joint_definitions[joint]
        common_frames = sorted(set(mp_df['frame_id'].unique()) & set(gt_df['frame_id'].unique()))
        
        frame_ids = []
        errors = []
        
        for frame_id in common_frames:
            # GT角度計算
            gt_points = []
            for point_name in joint_def['gt_points']:
                point_coord = self.get_point_coordinates(gt_df, frame_id, point_name, 'gt')
                if point_coord is None:
                    break
                gt_points.append(point_coord)
            
            if len(gt_points) != 3:
                continue
            
            gt_angle = self.calculate_3point_angle(gt_points[0], gt_points[1], gt_points[2])
            
            # MP角度計算
            mp_points = []
            for point_name in joint_def['mp_points']:
                point_coord = self.get_point_coordinates(mp_df, frame_id, point_name, 'mp')
                if point_coord is None:
                    break
                mp_points.append(point_coord)
            
            if len(mp_points) != 3:
                continue
            
            mp_angle = self.calculate_3point_angle(mp_points[0], mp_points[1], mp_points[2])
            
            # 誤差計算
            if not np.isnan(gt_angle) and not np.isnan(mp_angle):
                abs_error = abs(gt_angle - mp_angle)
                frame_ids.append(frame_id)
                errors.append(abs_error)
        
        return frame_ids, errors
    
    def plot_time_series(self, frame_ids: List[int], errors: List[float], 
                        coordinate_name: str, camera_x: float, camera_y: float, camera_z: float,
                        joint: str, output_path: str):
        """時系列グラフを作成して保存"""
        if len(frame_ids) == 0 or len(errors) == 0:
            self.logger.warning(f"データなし: {coordinate_name} - {joint}")
            return
        
        # 統計情報を計算
        max_error = np.max(errors)
        max_error_frame = frame_ids[np.argmax(errors)]
        mean_error = np.mean(errors)
        
        # グラフ作成
        plt.figure(figsize=(12, 6))
        plt.plot(frame_ids, errors, linewidth=1.5, color='#2E86AB', alpha=0.8)
        
        # Y軸の範囲を0-60度に固定
        plt.ylim(0, 60)
        
        # 最大誤差ポイントをハイライト
        plt.scatter([max_error_frame], [max_error], color='red', s=100, zorder=5, 
                   label=f'Max Error: {max_error:.2f}° at Frame {max_error_frame}')
        
        # グリッド
        plt.grid(True, alpha=0.3, linestyle='--')
        
        # ラベルとタイトル
        joint_display_name = self.joint_definitions[joint]['display_name']
        plt.xlabel('Frame ID', fontsize=12, fontweight='bold')
        plt.ylabel('Angle Error (degrees)', fontsize=12, fontweight='bold')
        plt.title(f'{joint_display_name} - Camera Position ({camera_x}, {camera_y}, {camera_z})\n'
                 f'Mean Error: {mean_error:.2f}°, Max Error: {max_error:.2f}°',
                 fontsize=14, fontweight='bold')
        
        plt.legend(loc='upper right', fontsize=10)
        plt.tight_layout()
        
        # 保存
        plt.savefig(output_path, dpi=100, bbox_inches='tight', format='jpeg', pil_kwargs={'quality': 95})
        plt.close()
        
        self.logger.info(f"グラフ保存: {output_path}")
    
    def process_all_coordinates(self, mp_csv_pattern: str, gt_csv_path: str, joints: List[str]):
        """全座標・全関節のグラフを作成"""
        # 出力ディレクトリ作成
        os.makedirs(self.output_dir, exist_ok=True)
        
        # MediaPipe CSVファイルを取得（Windowsでのワイルドカード展開を考慮）
        if '*' in mp_csv_pattern or '?' in mp_csv_pattern:
            mp_csv_files = sorted(glob.glob(mp_csv_pattern))
        else:
            # 既に展開済みの場合（argparseが処理した場合）
            mp_csv_files = [mp_csv_pattern]
        
        if not mp_csv_files:
            self.logger.error(f"MediaPipe CSVが見つかりません: {mp_csv_pattern}")
            return
        
        self.logger.info(f"処理対象: {len(mp_csv_files)}座標 × {len(joints)}関節 = {len(mp_csv_files) * len(joints)}グラフ")
        
        total_graphs = 0
        for idx, mp_csv_path in enumerate(mp_csv_files, 1):
            file_name = Path(mp_csv_path).stem
            camera_x, camera_y, camera_z = self.extract_camera_coordinates(file_name)
            
            self.logger.info(f"[{idx}/{len(mp_csv_files)}] 処理中: {file_name}")
            
            for joint in joints:
                if joint not in self.joint_definitions:
                    self.logger.warning(f"不明な関節: {joint}")
                    continue
                
                # フレームごとの誤差を計算
                frame_ids, errors = self.calculate_joint_errors_per_frame(mp_csv_path, gt_csv_path, joint)
                
                if len(frame_ids) > 0:
                    # グラフを作成
                    output_filename = f"{file_name}_{joint}.jpg"
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    self.plot_time_series(frame_ids, errors, file_name, 
                                        camera_x, camera_y, camera_z, 
                                        joint, output_path)
                    total_graphs += 1
        
        self.logger.info(f"完了: {total_graphs}個のグラフを作成しました")

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='時系列角度誤差グラフ作成')
    parser.add_argument('--mp_csv', required=True, help='MediaPipe CSVファイルパス（ワイルドカード使用可: *.csv）')
    parser.add_argument('--gt_csv', required=True, help='Ground Truth CSVファイルパス')
    parser.add_argument('--output_dir', default='graphs', help='出力ディレクトリ')
    parser.add_argument('--joints', nargs='+', 
                       default=['L_Elbow', 'R_Elbow', 'L_Knee', 'R_Knee', 'L_Shoulder', 'R_Shoulder', 'L_Hip', 'R_Hip'],
                       help='処理する関節（指定しない場合は全関節）')
    
    args = parser.parse_args()
    
    plotter = TimeSeriesErrorPlotter(output_dir=args.output_dir)
    plotter.process_all_coordinates(args.mp_csv, args.gt_csv, args.joints)

if __name__ == "__main__":
    main()

