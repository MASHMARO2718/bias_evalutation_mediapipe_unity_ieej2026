#!/usr/bin/env python3
"""
pose_world_landmarks の抽出（world landmarks 比較実験用）

既存の mediapipe_video_processor.py は pose_landmarks（正規化 UV）しか
保存していないため、指定動画を再処理して pose_world_landmarks
（腰中心・メートル・等方 3D）を同じ CSV スキーマで保存する。
検出設定は既存プロセッサと同一（static_image_mode=True, complexity=1）。

出力: 2_pose/mediapipe_world_csv/<folder>.csv
      （frame_id, landmark, x, y, z, visibility, image_path）

使用例:
  python extract_world_landmarks.py            # 較正+検証の 2 動画
  python extract_world_landmarks.py --videos <video.mp4> ...
"""

import argparse
import csv
from pathlib import Path

import cv2
import mediapipe as mp

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "mediapipe_world_csv"

DEFAULT_VIDEOS = [
    BASE.parent / "1_input/CapturedFrames_3.0_1.0_0.0/video.mp4",
    BASE.parent / "1_input/aditional__test_data/CapturedFrames_3.2_1.1_0.4/video.mp4",
]

LANDMARK_NAMES = [lm.name for lm in mp.solutions.pose.PoseLandmark]


def process(video_path: Path, pose) -> list:
    cap = cv2.VideoCapture(str(video_path))
    rows = []
    fid = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.pose_world_landmarks:
            valid = sum(1 for lm in res.pose_world_landmarks.landmark
                        if lm.visibility > 0.5)
            if valid >= 5:
                for i, lm in enumerate(res.pose_world_landmarks.landmark):
                    rows.append({
                        "frame_id": fid,
                        "landmark": LANDMARK_NAMES[i],
                        "x": lm.x, "y": lm.y, "z": lm.z,
                        "visibility": lm.visibility,
                        "image_path": f"{video_path.parent.name}#frame{fid}",
                    })
        fid += 1
    cap.release()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", nargs="*", default=None)
    args = ap.parse_args()
    videos = [Path(v) for v in args.videos] if args.videos else DEFAULT_VIDEOS

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pose = mp.solutions.pose.Pose(
        static_image_mode=True, model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
    )
    for vp in videos:
        rows = process(vp, pose)
        out = OUT_DIR / f"{vp.parent.name}.csv"
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "frame_id", "landmark", "x", "y", "z", "visibility", "image_path"])
            w.writeheader()
            w.writerows(rows)
        n_frames = len({r["frame_id"] for r in rows})
        print(f"{vp.parent.name}: {n_frames} frames -> {out}")


if __name__ == "__main__":
    main()
