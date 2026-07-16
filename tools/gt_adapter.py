"""
GT（Ground Truth）CSV の列名差異を吸収するアダプター

v1 形式: Frame, Time, Hips_X, ...        （synced_joint_positions*.csv）
v2 形式: frame_id, time_sec, Hips_X, ... （gt_joints.csv）

読み込んだ DataFrame に両方の列名（Frame/Time と frame_id/time_sec）を
エイリアスとして持たせることで、既存コードがどちらの列名を参照しても動くようにする。

使用例:
    from tools.gt_adapter import load_gt_csv, find_gt_csv_for_camera

    # 任意の GT CSV を正規化して読み込み
    gt_df = load_gt_csv(path)          # Frame / frame_id 両方の列を持つ

    # v2: カメラフォルダから gt_joints.csv を解決
    path = find_gt_csv_for_camera("CapturedFrames_4.0_1.0_0.0", input_dir)
"""

from pathlib import Path
from typing import Optional, Union

import pandas as pd


def normalize_gt_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    GT DataFrame に v1/v2 両方の列名エイリアスを付与する。

    - v2 入力（frame_id, time_sec）→ Frame, Time 列を追加
    - v1 入力（Frame, Time）      → frame_id, time_sec 列を追加
    """
    df = df.copy()

    if 'frame_id' in df.columns and 'Frame' not in df.columns:
        df['Frame'] = df['frame_id']
    elif 'Frame' in df.columns and 'frame_id' not in df.columns:
        df['frame_id'] = df['Frame']

    if 'time_sec' in df.columns and 'Time' not in df.columns:
        df['Time'] = df['time_sec']
    elif 'Time' in df.columns and 'time_sec' not in df.columns:
        df['time_sec'] = df['Time']

    return df


def load_gt_csv(path: Union[str, Path]) -> pd.DataFrame:
    """GT CSV を読み込み、列名を正規化して返す。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"GT CSV not found: {path}")
    return normalize_gt_columns(pd.read_csv(path))


def find_gt_csv_for_camera(
    camera_position: str,
    input_dir: Union[str, Path],
) -> Optional[Path]:
    """
    カメラフォルダ名（例: CapturedFrames_4.0_1.0_0.0）から GT CSV パスを解決する。

    v2: {input_dir}/{camera_position}/gt_joints.csv
    v1: {input_dir}/{camera_position}/synced_joint_positions_*.csv

    見つからない場合は None を返す。
    """
    folder = Path(input_dir) / camera_position
    if not folder.exists():
        return None

    v2_path = folder / "gt_joints.csv"
    if v2_path.exists():
        return v2_path

    v1_candidates = sorted(folder.glob("synced_joint_positions*.csv"))
    if v1_candidates:
        return v1_candidates[0]

    return None
