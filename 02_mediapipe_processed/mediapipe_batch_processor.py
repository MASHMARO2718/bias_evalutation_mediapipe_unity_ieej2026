#!/usr/bin/env python3
"""
MediaPipe 3D Pose Landmarker バッチ処理スクリプト
RTX3050 GPU活用 + 進捗管理 + エラーハンドリング

使用方法:
    python mediapipe_batch_processor.py --input_dir JPEG_OUTPUT --output_base_dir 02_mediapipe_processed
    # カメラ高さごとに Y=0.5, Y=1.0, Y=1.5, Y=2.0 配下へ CapturedFrames_*.csv を出力
"""

import os
import re
import sys
import csv
import json
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

import cv2
import numpy as np
import mediapipe as mp
from tqdm import tqdm
import pandas as pd

# GPU設定
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # RTX3050を明示的に指定

class MediaPipeProcessor:
    """MediaPipe 3D Pose Landmarker プロセッサ"""
    
    def __init__(self, model_path: Optional[str] = None, num_threads: int = 4):
        """
        Args:
            model_path: カスタムモデルパス（Noneの場合はデフォルト）
            num_threads: CPU並列処理スレッド数
        """
        self.num_threads = num_threads
        
        # MediaPipe初期化
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Pose Landmarker初期化（GPU使用）
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,  # バッチ処理用
            model_complexity=1,      # 標準精度
            enable_segmentation=False,
            min_detection_confidence=0.5,  # 標準閾値
            min_tracking_confidence=0.5    # 標準閾値
        )
        
        # 33ランドマークの名前定義
        self.landmark_names = [
            'NOSE', 'LEFT_EYE_INNER', 'LEFT_EYE', 'LEFT_EYE_OUTER',
            'RIGHT_EYE_INNER', 'RIGHT_EYE', 'RIGHT_EYE_OUTER', 'LEFT_EAR',
            'RIGHT_EAR', 'MOUTH_LEFT', 'MOUTH_RIGHT', 'LEFT_SHOULDER',
            'RIGHT_SHOULDER', 'LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_WRIST',
            'RIGHT_WRIST', 'LEFT_PINKY', 'RIGHT_PINKY', 'LEFT_INDEX',
            'RIGHT_INDEX', 'LEFT_THUMB', 'RIGHT_THUMB', 'LEFT_HIP',
            'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'LEFT_ANKLE',
            'RIGHT_ANKLE', 'LEFT_HEEL', 'RIGHT_HEEL', 'LEFT_FOOT_INDEX',
            'RIGHT_FOOT_INDEX'
        ]
        
        # ログ設定
        self.setup_logging()
        
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.DEBUG,  # DEBUGレベルに変更
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('mediapipe_processing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def process_single_image(self, image_path: str) -> Dict:
        """
        単一画像のMediaPipe処理
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            Dict: フレームID、ランドマーク座標、可視度情報
        """
        try:
            # 画像読み込み
            image = cv2.imread(str(image_path))
            if image is None:
                self.logger.warning(f"画像読み込み失敗: {image_path}")
                return None
                
            # BGR -> RGB変換
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # MediaPipe処理
            results = self.pose.process(image_rgb)
            
            if not results.pose_landmarks:
                # 詳細な失敗原因をログ出力
                self.logger.warning(f"姿勢検出失敗: {image_path}")
                self.logger.debug(f"  - 画像サイズ: {image_rgb.shape}")
                self.logger.debug(f"  - 画像範囲: {image_rgb.min()}-{image_rgb.max()}")
                if hasattr(results, 'pose_world_landmarks') and results.pose_world_landmarks:
                    self.logger.debug(f"  - ワールド座標: 検出済み")
                else:
                    self.logger.debug(f"  - ワールド座標: 未検出")
                
                # 検出失敗フレームも記録（オプション）
                frame_id = self.extract_frame_id(image_path)
                return {
                    'frame_id': frame_id,
                    'image_path': str(image_path),
                    'landmarks': [],  # 空のランドマークリスト
                    'detection_failed': True
                }
            else:
                # 成功ログ出力
                self.logger.info(f"姿勢検出成功: {image_path}")
                
            # フレームID抽出（ファイル名から）
            frame_id = self.extract_frame_id(image_path)
            
            # 結果を辞書形式で整理
            landmarks_data = {
                'frame_id': frame_id,
                'image_path': str(image_path),
                'landmarks': []
            }
            
            # 33ランドマークの座標と可視度を取得
            valid_landmarks = 0
            for i, landmark in enumerate(results.pose_landmarks.landmark):
                landmark_data = {
                    'landmark_name': self.landmark_names[i],
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
                landmarks_data['landmarks'].append(landmark_data)
                
                # 品質チェック: 可視度が高いランドマークをカウント
                if landmark.visibility > 0.5:
                    valid_landmarks += 1
            
            # 品質フィルタリング: 重要なランドマークの可視度が低い場合は除外
            if valid_landmarks < 5:  # 最低5個のランドマークが必要（標準）
                self.logger.warning(f"品質不足で除外: {image_path} (有効ランドマーク: {valid_landmarks})")
                return None
                
            return landmarks_data
            
        except Exception as e:
            self.logger.error(f"画像処理エラー {image_path}: {str(e)}")
            return None
    
    def extract_frame_id(self, image_path: str) -> int:
        """ファイル名からフレームIDを抽出"""
        filename = Path(image_path).stem
        # frame_0001.jpg -> 1
        if filename.startswith('frame_'):
            return int(filename.split('_')[1])
        return 0
    
    def process_batch_parallel(self, image_paths: List[str], max_workers: int = None) -> List[Dict]:
        """
        順次バッチ処理（MediaPipeのタイムスタンプエラー回避）
        
        Args:
            image_paths: 画像ファイルパスリスト
            max_workers: 並列処理数（使用しない）
            
        Returns:
            List[Dict]: 処理結果リスト
        """
        self.logger.info(f"順次処理開始: {len(image_paths)}枚")
        
        results = []
        with tqdm(total=len(image_paths), desc="MediaPipe処理中") as pbar:
            for path in image_paths:
                try:
                    result = self.process_single_image(path)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"処理エラー {path}: {str(e)}")
                finally:
                    pbar.update(1)
                        
        self.logger.info(f"処理完了: {len(results)}/{len(image_paths)}枚成功")
        return results
    
    def _get_y_folder_from_folder(self, folder_name: str) -> str:
        """CapturedFrames_X_Y_Z からカメラ高さ Y を解析し、Y=0.5 / Y=1.0 / Y=1.5 / Y=2.0 を返す"""
        m = re.match(r'CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)', folder_name)
        if m:
            y = float(m.group(2))
            for allowed in (0.5, 1.0, 1.5, 2.0):
                if abs(y - allowed) < 1e-6:
                    return f"Y={allowed}"
        self.logger.warning(f"Y判定失敗: {folder_name} -> Y=0.5 にフォールバック")
        return "Y=0.5"

    def save_to_csv_by_folder(self, results: List[Dict], output_base_dir: Optional[Path] = None):
        """
        フォルダ別にCSV形式で保存。カメラ高さ Y（0.5, 1.0, 1.5, 2.0）ごとに出力ディレクトリを分ける。
        
        Args:
            results: 処理結果リスト
            output_base_dir: 出力ベースディレクトリ（None の場合は画像と同じ場所）
        """
        self.logger.info("フォルダ別CSV保存開始（Y=0.5, Y=1.0, Y=1.5, Y=2.0 ごとに出力）")
        
        # (y_folder, folder_name) ごとに結果をグループ化
        grouped = {}  # (y_folder, folder_name) -> [results]
        for result in results:
            image_path = Path(result['image_path'])
            folder_path = image_path.parent
            folder_name = folder_path.name  # CapturedFrames_X_Y_Z
            
            y_folder = self._get_y_folder_from_folder(folder_name)
            key = (y_folder, folder_name)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(result)
        
        for (y_folder, folder_name), folder_data in tqdm(grouped.items(), desc="Y別CSV保存中"):
            if output_base_dir:
                out_dir = Path(output_base_dir) / y_folder
                out_dir.mkdir(parents=True, exist_ok=True)
                csv_path = out_dir / f"{folder_name}.csv"
            else:
                # 従来動作: 画像フォルダ直下に保存
                folder_path = Path(folder_data[0]['image_path']).parent
                csv_path = folder_path / "mediapipe_coords.csv"
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['frame_id', 'landmark', 'x', 'y', 'z', 'visibility', 'image_path']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in folder_data:
                    frame_id = result['frame_id']
                    image_path = result['image_path']
                    
                    for landmark_data in result['landmarks']:
                        writer.writerow({
                            'frame_id': frame_id,
                            'landmark': landmark_data['landmark_name'],
                            'x': landmark_data['x'],
                            'y': landmark_data['y'],
                            'z': landmark_data['z'],
                            'visibility': landmark_data['visibility'],
                            'image_path': image_path
                        })
            
            self.logger.info(f"CSV保存: {csv_path}")
        
        self.logger.info(f"全CSV保存完了: {len(grouped)}ファイル（カメラ高さ Y 別）")
    
    def get_image_paths(self, input_dir: str) -> List[str]:
        """
        入力ディレクトリから全画像パスを取得
        
        Args:
            input_dir: 入力ディレクトリパス
            
        Returns:
            List[str]: 画像ファイルパスリスト
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"入力ディレクトリが存在しません: {input_dir}")
            
        # 再帰的にJPEG画像を検索
        image_extensions = {'.jpg', '.jpeg', '.png'}
        image_paths = []
        
        for ext in image_extensions:
            image_paths.extend(input_path.rglob(f'*{ext}'))
            
        # パスを文字列に変換してソート
        image_paths = sorted([str(p) for p in image_paths])
        
        self.logger.info(f"画像ファイル発見: {len(image_paths)}枚")
        return image_paths
    
    def cleanup(self):
        """リソース解放"""
        if hasattr(self, 'pose'):
            try:
                self.pose.close()
            except Exception as e:
                self.logger.warning(f"MediaPipeクリーンアップエラー: {str(e)}")

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='MediaPipe 3D Pose Landmarker バッチ処理')
    parser.add_argument('--input_dir', required=True, help='入力画像ディレクトリ')
    default_out = Path(__file__).parent  # 02_mediapipe_processed 自体をデフォルト
    parser.add_argument('--output_base_dir', default=str(default_out), help='Y別出力のベース。デフォルト: 02_mediapipe_processed（Y=0.5, Y=1.0, Y=1.5, Y=2.0 配下）')
    parser.add_argument('--output_csv', help='出力CSVファイル（フォルダ別出力の場合は不要）')
    parser.add_argument('--num_threads', type=int, default=4, help='並列処理スレッド数')
    parser.add_argument('--max_images', type=int, help='処理する最大画像数（テスト用）')
    
    args = parser.parse_args()
    
    # プロセッサ初期化
    processor = MediaPipeProcessor(num_threads=args.num_threads)
    
    try:
        # 画像パス取得
        image_paths = processor.get_image_paths(args.input_dir)
        
        # テスト用に画像数制限
        if args.max_images:
            image_paths = image_paths[:args.max_images]
            processor.logger.info(f"テストモード: {len(image_paths)}枚に制限")
        
        # 並列処理実行
        start_time = time.time()
        results = processor.process_batch_parallel(image_paths)
        processing_time = time.time() - start_time
        
        # 結果保存（Y別フォルダにCSV出力）
        output_base = Path(args.output_base_dir)
        processor.save_to_csv_by_folder(results, output_base_dir=output_base)
        
        # 統計情報出力
        processor.logger.info(f"処理時間: {processing_time:.2f}秒")
        processor.logger.info(f"処理速度: {len(results)/processing_time:.2f}枚/秒")
        processor.logger.info(f"成功率: {len(results)/len(image_paths)*100:.1f}%")
        
        # 品質統計
        if results:
            total_landmarks = sum(len(result['landmarks']) for result in results)
            avg_visibility = sum(
                sum(landmark['visibility'] for landmark in result['landmarks']) / len(result['landmarks'])
                for result in results
            ) / len(results)
            processor.logger.info(f"平均可視度: {avg_visibility:.3f}")
            processor.logger.info(f"総ランドマーク数: {total_landmarks}")
        
    except Exception as e:
        processor.logger.error(f"メイン処理エラー: {str(e)}")
        sys.exit(1)
    finally:
        processor.cleanup()

if __name__ == "__main__":
    main()
