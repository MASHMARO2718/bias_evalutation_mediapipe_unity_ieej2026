#!/usr/bin/env python3
"""
MediaPipe 3D Pose Landmarker 動画バッチ処理スクリプト（v2 データセット用）

10_input_videos/CapturedFrames_{X}_{Y}_{Z}/video.mp4 を読み込み、
フレームごとに MediaPipe Pose を適用して
20_pose_correction/mediapipe_processed_csv/Y={y}/CapturedFrames_{X}_{Y}_{Z}.csv を出力する。

出力 CSV は v1（mediapipe_batch_processor.py）と同一形式:
    frame_id, landmark, x, y, z, visibility, image_path

MediaPipe 設定も v1 と同一（static_image_mode=True, model_complexity=1,
min_detection_confidence=0.5）で、v1/v2 の結果を直接比較できるようにする。

使用方法:
    python mediapipe_video_processor.py
    python mediapipe_video_processor.py --input_dir ../10_input_videos --max_videos 5
    python mediapipe_video_processor.py --overwrite   # 既存 CSV を再生成
"""

import re
import sys
import csv
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import mediapipe as mp
from tqdm import tqdm

LANDMARK_NAMES = [
    'NOSE', 'LEFT_EYE_INNER', 'LEFT_EYE', 'LEFT_EYE_OUTER',
    'RIGHT_EYE_INNER', 'RIGHT_EYE', 'RIGHT_EYE_OUTER', 'LEFT_EAR',
    'RIGHT_EAR', 'MOUTH_LEFT', 'MOUTH_RIGHT', 'LEFT_SHOULDER',
    'RIGHT_SHOULDER', 'LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_WRIST',
    'RIGHT_WRIST', 'LEFT_PINKY', 'RIGHT_PINKY', 'LEFT_INDEX',
    'RIGHT_INDEX', 'LEFT_THUMB', 'RIGHT_THUMB', 'LEFT_HIP',
    'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE', 'LEFT_ANKLE',
    'RIGHT_ANKLE', 'LEFT_HEEL', 'RIGHT_HEEL', 'LEFT_FOOT_INDEX',
    'RIGHT_FOOT_INDEX',
]

ALLOWED_HEIGHTS = (0.5, 1.0, 1.5, 2.0)
FOLDER_PATTERN = re.compile(
    r'CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)'
)


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mediapipe_v2_processing.log', encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def y_folder_from_name(folder_name: str, logger: logging.Logger) -> str:
    """CapturedFrames_X_Y_Z からカメラ高さ Y を解析し 'Y=0.5' 等を返す（v1 と同一ロジック）"""
    m = FOLDER_PATTERN.match(folder_name)
    if m:
        y = float(m.group(2))
        for allowed in ALLOWED_HEIGHTS:
            if abs(y - allowed) < 1e-6:
                return f"Y={allowed}"
    logger.warning(f"Y判定失敗: {folder_name} -> Y=0.5 にフォールバック")
    return "Y=0.5"


class VideoMediaPipeProcessor:
    """動画 → MediaPipe Pose → CSV"""

    def __init__(self):
        self.logger = setup_logging()
        # v1 と同一設定（結果の比較可能性を保つ）
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process_frame(self, frame_bgr, frame_id: int, video_ref: str) -> Optional[Dict]:
        """1フレームを処理。品質不足（有効ランドマーク<5）は None を返す（v1 と同一基準）"""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            return {
                'frame_id': frame_id,
                'image_path': video_ref,
                'landmarks': [],
            }

        landmarks = []
        valid_count = 0
        for i, lm in enumerate(results.pose_landmarks.landmark):
            landmarks.append({
                'landmark_name': LANDMARK_NAMES[i],
                'x': lm.x, 'y': lm.y, 'z': lm.z,
                'visibility': lm.visibility,
            })
            if lm.visibility > 0.5:
                valid_count += 1

        if valid_count < 5:
            self.logger.warning(f"品質不足で除外: {video_ref} (有効ランドマーク: {valid_count})")
            return None

        return {
            'frame_id': frame_id,
            'image_path': video_ref,
            'landmarks': landmarks,
        }

    def process_video(self, video_path: Path) -> List[Dict]:
        """動画の全フレームを処理して結果リストを返す"""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            self.logger.error(f"動画を開けません: {video_path}")
            return []

        results = []
        frame_id = 0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        with tqdm(total=total, desc=f"  {video_path.parent.name}", leave=False) as pbar:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                video_ref = f"{video_path.parent.name}/video.mp4#frame={frame_id}"
                result = self.process_frame(frame, frame_id, video_ref)
                if result is not None:
                    results.append(result)
                frame_id += 1
                pbar.update(1)
        cap.release()
        return results

    def save_csv(self, results: List[Dict], csv_path: Path):
        """v1 と同一形式の CSV を保存"""
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['frame_id', 'landmark', 'x', 'y', 'z', 'visibility', 'image_path']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                for lm in result['landmarks']:
                    writer.writerow({
                        'frame_id': result['frame_id'],
                        'landmark': lm['landmark_name'],
                        'x': lm['x'], 'y': lm['y'], 'z': lm['z'],
                        'visibility': lm['visibility'],
                        'image_path': result['image_path'],
                    })

    def cleanup(self):
        try:
            self.pose.close()
        except Exception:
            pass


def main():
    script_dir = Path(__file__).parent
    parser = argparse.ArgumentParser(description='MediaPipe 動画バッチ処理（v2）')
    parser.add_argument('--input_dir', default=str(script_dir.parent / '10_input_videos'),
                        help='入力ディレクトリ（CapturedFrames_* フォルダを含む）')
    parser.add_argument('--output_base_dir', default=str(script_dir / 'mediapipe_processed_csv'),
                        help='出力ベースディレクトリ（Y=0.5 … Y=2.0 配下に CSV）')
    parser.add_argument('--overwrite', action='store_true',
                        help='既存 CSV を再生成する（デフォルトはスキップ）')
    parser.add_argument('--max_videos', type=int, help='処理する最大動画数（テスト用）')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_base = Path(args.output_base_dir)

    if not input_dir.exists():
        print(f"エラー: 入力ディレクトリが存在しません: {input_dir}")
        sys.exit(1)

    video_paths = sorted(input_dir.glob('CapturedFrames_*/video.mp4'))
    if not video_paths:
        print(f"エラー: 動画が見つかりません: {input_dir}/CapturedFrames_*/video.mp4")
        sys.exit(1)

    if args.max_videos:
        video_paths = video_paths[:args.max_videos]

    processor = VideoMediaPipeProcessor()
    processor.logger.info(f"動画数: {len(video_paths)}")

    done, skipped, failed = 0, 0, 0
    start_time = time.time()
    try:
        for i, video_path in enumerate(video_paths, 1):
            folder_name = video_path.parent.name
            y_folder = y_folder_from_name(folder_name, processor.logger)
            csv_path = output_base / y_folder / f"{folder_name}.csv"

            if csv_path.exists() and not args.overwrite:
                skipped += 1
                continue

            processor.logger.info(f"[{i}/{len(video_paths)}] {folder_name}")
            results = processor.process_video(video_path)
            if not results:
                processor.logger.error(f"処理失敗（結果なし）: {folder_name}")
                failed += 1
                continue

            processor.save_csv(results, csv_path)
            done += 1
    finally:
        processor.cleanup()

    elapsed = time.time() - start_time
    processor.logger.info(
        f"完了: 処理 {done} / スキップ {skipped} / 失敗 {failed} （{elapsed:.1f} 秒）"
    )


if __name__ == '__main__':
    main()
