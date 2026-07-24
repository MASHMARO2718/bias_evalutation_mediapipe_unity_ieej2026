#!/usr/bin/env python3
"""
既存 MediaPipe CSV の 2D ランドマークを video.mp4 に重ね描きする（再検出なし・GTなし）。

入力:
  1_input/CapturedFrames_{X}_{Y}_{Z}/video.mp4
  2_pose/mediapipe_processed_csv/Y={y}/CapturedFrames_{X}_{Y}_{Z}.csv

出力:
  2_pose/overlay_videos/Y={y}/CapturedFrames_{X}_{Y}_{Z}_mp_overlay.mp4

使用例:
  python overlay_mp_landmarks.py --max_videos 1
  python overlay_mp_landmarks.py
  python overlay_mp_landmarks.py --overwrite
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
from tqdm import tqdm

# MediaPipe Pose 33 landmarks（mediapipe_video_processor.py と同一）
LANDMARK_NAMES = [
    "NOSE", "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER", "RIGHT_EYE", "RIGHT_EYE_OUTER", "LEFT_EAR",
    "RIGHT_EAR", "MOUTH_LEFT", "MOUTH_RIGHT", "LEFT_SHOULDER",
    "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW", "LEFT_WRIST",
    "RIGHT_WRIST", "LEFT_PINKY", "RIGHT_PINKY", "LEFT_INDEX",
    "RIGHT_INDEX", "LEFT_THUMB", "RIGHT_THUMB", "LEFT_HIP",
    "RIGHT_HIP", "LEFT_KNEE", "RIGHT_KNEE", "LEFT_ANKLE",
    "RIGHT_ANKLE", "LEFT_HEEL", "RIGHT_HEEL", "LEFT_FOOT_INDEX",
    "RIGHT_FOOT_INDEX",
]
NAME_TO_IDX = {n: i for i, n in enumerate(LANDMARK_NAMES)}

# mediapipe.solutions.pose.POSE_CONNECTIONS 相当（依存を避けるためハードコード）
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32),
]

FOLDER_PATTERN = re.compile(
    r"CapturedFrames_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)_([+-]?\d+\.?\d*)"
)
ALLOWED_HEIGHTS = (0.5, 1.0, 1.5, 2.0)

Point = Tuple[float, float, float]  # x_norm, y_norm, visibility
FrameLms = Dict[str, Point]


def y_folder_from_name(folder_name: str) -> Optional[str]:
    """CapturedFrames_X_Y_Z → 'Y=1.0' 等（CSV ディレクトリ名と一致）。"""
    m = FOLDER_PATTERN.fullmatch(folder_name)
    if not m:
        return None
    y = float(m.group(2))
    for allowed in ALLOWED_HEIGHTS:
        if abs(y - allowed) < 1e-6:
            return f"Y={allowed}"
    return f"Y={y}"


def load_landmarks_csv(csv_path: Path) -> Dict[int, FrameLms]:
    """frame_id -> {landmark_name: (x, y, visibility)}"""
    by_frame: Dict[int, FrameLms] = defaultdict(dict)
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                fid = int(float(row["frame_id"]))
                name = row["landmark"]
                x = float(row["x"])
                y = float(row["y"])
                vis = float(row.get("visibility") or 0.0)
            except (KeyError, ValueError):
                continue
            by_frame[fid][name] = (x, y, vis)
    return dict(by_frame)


def draw_landmarks(
    frame_bgr,
    lms: FrameLms,
    *,
    vis_thresh: float = 0.5,
    point_color=(0, 255, 0),
    line_color=(0, 200, 255),
):
    h, w = frame_bgr.shape[:2]
    pts: Dict[int, Tuple[int, int]] = {}
    for name, (xn, yn, vis) in lms.items():
        if vis < vis_thresh:
            continue
        idx = NAME_TO_IDX.get(name)
        if idx is None:
            continue
        px = int(round(xn * w))
        py = int(round(yn * h))
        pts[idx] = (px, py)

    for a, b in POSE_CONNECTIONS:
        if a in pts and b in pts:
            cv2.line(frame_bgr, pts[a], pts[b], line_color, 2, cv2.LINE_AA)

    for px, py in pts.values():
        cv2.circle(frame_bgr, (px, py), 4, point_color, -1, cv2.LINE_AA)
        cv2.circle(frame_bgr, (px, py), 5, (0, 0, 0), 1, cv2.LINE_AA)


def overlay_one(
    video_path: Path,
    csv_path: Path,
    out_path: Path,
    *,
    vis_thresh: float = 0.5,
) -> Tuple[str, int, int]:
    """
    Returns (status, n_frames_written, n_frames_with_landmarks)
    status: ok | skip_missing | fail
    """
    if not video_path.exists():
        return "skip_missing", 0, 0
    if not csv_path.exists():
        return "skip_missing", 0, 0

    by_frame = load_landmarks_csv(csv_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return "fail", 0, 0

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if fps <= 1e-3:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    if not writer.isOpened():
        cap.release()
        return "fail", 0, 0

    n_write = 0
    n_with = 0
    frame_id = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            lms = by_frame.get(frame_id)
            if lms:
                draw_landmarks(frame, lms, vis_thresh=vis_thresh)
                n_with += 1

            # 左上に「現在フレーム/総フレーム」（1-based 表示）
            denom = total_frames if total_frames > 0 else max(frame_id + 1, n_write + 1)
            frac = f"{frame_id + 1}/{denom}"
            x0, y0 = 8, 22
            cv2.putText(
                frame, frac, (x0, y0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA,
            )
            cv2.putText(
                frame, frac, (x0, y0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
            )

            writer.write(frame)
            n_write += 1
            frame_id += 1
    finally:
        writer.release()
        cap.release()

    return "ok", n_write, n_with


def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent
    parser = argparse.ArgumentParser(
        description="既存 MP CSV を video.mp4 に重ね描き（再検出なし）"
    )
    parser.add_argument(
        "--input_dir",
        default=str(root / "1_input"),
        help="CapturedFrames_*/video.mp4 があるディレクトリ",
    )
    parser.add_argument(
        "--csv_base_dir",
        default=str(script_dir / "mediapipe_processed_csv"),
        help="Y=*/CapturedFrames_*.csv のベース",
    )
    parser.add_argument(
        "--output_base_dir",
        default=str(script_dir / "overlay_videos"),
        help="出力ベース（Y=*/..._mp_overlay.mp4）",
    )
    parser.add_argument("--overwrite", action="store_true",
                        help="既存出力を上書き")
    parser.add_argument("--max_videos", type=int, default=None,
                        help="処理する最大本数（テスト用）")
    parser.add_argument(
        "--camera",
        default=None,
        help="1カメラのみ処理（例: CapturedFrames_3.0_1.0_0.0 または 3.0_1.0_0.0）",
    )
    parser.add_argument("--vis_thresh", type=float, default=0.5,
                        help="visibility しきい値")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    csv_base = Path(args.csv_base_dir)
    out_base = Path(args.output_base_dir)

    video_paths = sorted(input_dir.glob("CapturedFrames_*/video.mp4"))
    if not video_paths:
        print(f"エラー: 動画が見つかりません: {input_dir}/CapturedFrames_*/video.mp4")
        sys.exit(1)
    if args.camera:
        cam = args.camera
        if not cam.startswith("CapturedFrames_"):
            cam = f"CapturedFrames_{cam}"
        video_paths = [p for p in video_paths if p.parent.name == cam]
        if not video_paths:
            print(f"エラー: カメラが見つかりません: {cam}")
            sys.exit(1)
    if args.max_videos:
        video_paths = video_paths[: args.max_videos]

    print(f"動画数: {len(video_paths)}")
    print(f"CSV:    {csv_base}")
    print(f"出力:   {out_base}")

    done = skipped = failed = missing = 0
    t0 = time.time()
    summary_rows: List[str] = ["folder,status,frames,with_landmarks,out_path"]

    for video_path in tqdm(video_paths, desc="overlay"):
        folder = video_path.parent.name
        y_folder = y_folder_from_name(folder)
        if y_folder is None:
            failed += 1
            summary_rows.append(f"{folder},fail_name,0,0,")
            continue
        csv_path = csv_base / y_folder / f"{folder}.csv"
        out_path = out_base / y_folder / f"{folder}_mp_overlay.mp4"

        if out_path.exists() and not args.overwrite:
            skipped += 1
            summary_rows.append(f"{folder},skipped,0,0,{out_path}")
            continue

        status, n_frames, n_with = overlay_one(
            video_path, csv_path, out_path, vis_thresh=args.vis_thresh,
        )
        if status == "ok":
            done += 1
            summary_rows.append(f"{folder},ok,{n_frames},{n_with},{out_path}")
        elif status == "skip_missing":
            missing += 1
            summary_rows.append(f"{folder},missing,0,0,")
        else:
            failed += 1
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            summary_rows.append(f"{folder},fail,0,0,")

    out_base.mkdir(parents=True, exist_ok=True)
    summary_path = out_base / "overlay_summary.csv"
    summary_path.write_text("\n".join(summary_rows) + "\n", encoding="utf-8")

    elapsed = time.time() - t0
    print(
        f"完了: ok={done}  skip={skipped}  missing={missing}  fail={failed}  "
        f"({elapsed:.1f}s)"
    )
    print(f"要約: {summary_path}")


if __name__ == "__main__":
    main()
