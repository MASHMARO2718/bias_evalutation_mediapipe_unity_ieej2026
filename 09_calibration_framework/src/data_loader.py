"""
data_loader.py — 全 CSV を統一した DataFrame 形式で読み込む

提案書との対応:
  §4.1 Phase A Calibration 入力
       - Unity GT (座標・角度・θ,ψ)
       - MediaPipe 出力 (座標・角度・θ,ψ・confidence)
       - カメラ情報 (X, Y, Z, distance, azimuth, elevation)
  §4.3 テーブルの具体例 (joint, height, azimuth_bin, metric, bias)

利用可能な CSV（§4.6 Calibration dataset 候補1）:
  - coordinate_angle_mae.csv : カメラ位置 × 関節 の角度 MAE（符号なし平均絶対誤差）
  - frame_camera_summary.csv : フレーム × カメラ の Δθ/Δψ 統計
  - joint_summary.csv        : 関節ごとの全カメラ統合方向角統計
  - detailed_results.csv     : 全観測の符号付き誤差（git 除外・要ローカル生成）

注意: 現行の CSV は既にバイアス量を集計した「集計済みデータ」。
      per-sample の符号付き誤差は detailed_results.csv が必要。
      detailed_results.csv が存在しない場合は MAE を unsigned bias として使用する
      ことをこのモジュールの get_combined_angle_data() で明示する。
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from .config import DATA, JOINT_COLS_ANGLE, LAYER_HEIGHTS


# ──────────────────────────────────────────────────────────────────
# 1. 関節角度 MAE（カメラ位置別）
# ──────────────────────────────────────────────────────────────────

def load_angle_mae_single_layer(layer: str) -> pd.DataFrame:
    """
    1層分の coordinate_angle_mae.csv を読み込み、カメラ特徴量を付加して返す。

    Returns
    -------
    df : columns = [folder_name, camera_x, camera_y, camera_z,
                    <JOINT_COLS_ANGLE>, distance, azimuth_deg, elevation_deg]
    """
    path = DATA["angle_mae"][layer]
    if not Path(path).exists():
        raise FileNotFoundError(f"angle_mae CSV not found: {path}")

    df = pd.read_csv(path)

    # カメラ特徴量を計算して付加  §4.1 カメラ情報 (distance, azimuth, elevation)
    df = _add_camera_features(df, x_col="camera_x", y_col="camera_y", z_col="camera_z")
    return df


def load_angle_mae_all_layers() -> pd.DataFrame:
    """
    4層 (Y=0.5/1.0/1.5/2.0) の angle MAE CSV を縦結合して返す。

    提案書 §4.6 候補1: 前論文の Unity データをそのまま使う
    Returns
    -------
    df : 上記 + 列 height_label (str: "Y=0.5" 等)
    """
    frames = []
    for layer_key, path in DATA["angle_mae"].items():
        if not Path(path).exists():
            print(f"[WARNING] Not found, skipping: {path}")
            continue
        df = load_angle_mae_single_layer(layer_key)
        df["height_label"] = layer_key
        frames.append(df)

    if not frames:
        raise RuntimeError("angle_mae CSV が1つも見つかりません。")

    combined = pd.concat(frames, ignore_index=True)
    print(f"[load_angle_mae_all_layers] {len(combined)} rows, "
          f"layers={combined['height_label'].unique().tolist()}")
    return combined


# ──────────────────────────────────────────────────────────────────
# 2. フレーム×カメラ 方向角統計
# ──────────────────────────────────────────────────────────────────

def load_frame_camera_summary() -> pd.DataFrame:
    """
    frame_camera_summary.csv を読み込みカメラ特徴量を付加する。

    columns (追加後):
      frame_id, camera, num_joints,
      mean_abs_delta_theta, mean_abs_delta_psi, ...,
      camera_x, camera_y, camera_z, distance, azimuth_deg, elevation_deg, height_label
    """
    path = DATA["frame_camera_summary"]
    if not Path(path).exists():
        raise FileNotFoundError(f"frame_camera_summary.csv not found: {path}")

    df = pd.read_csv(path)

    # 'camera' 列 = "CapturedFrames_X_Y_Z" からカメラ座標を抽出
    df = _parse_camera_column(df, camera_col="camera")
    df = _add_camera_features(df, x_col="camera_x", y_col="camera_y", z_col="camera_z")
    df["height_label"] = df["camera_y"].apply(_y_to_layer_label)

    print(f"[load_frame_camera_summary] {len(df)} rows")
    return df


# ──────────────────────────────────────────────────────────────────
# 3. 関節サマリ（全カメラ統合）
# ──────────────────────────────────────────────────────────────────

def load_joint_summary() -> pd.DataFrame:
    """
    joint_summary.csv を読み込む。
    columns: joint, theta_mean, theta_std, theta_abs_mean,
             psi_mean, psi_std, psi_abs_mean, error3d_mean, error3d_std
    """
    path = DATA["joint_summary"]
    if not Path(path).exists():
        raise FileNotFoundError(f"joint_summary.csv not found: {path}")
    df = pd.read_csv(path)
    print(f"[load_joint_summary] {len(df)} joints")
    return df


# ──────────────────────────────────────────────────────────────────
# 4. 詳細結果（per-sample 符号付き誤差）
# ──────────────────────────────────────────────────────────────────

def load_detailed_results() -> Optional[pd.DataFrame]:
    """
    detailed_results.csv（大容量・git 除外）を読み込む。
    存在しない場合は None を返し、呼び出し元で MAE ベースの近似に切り替える。

    これが利用可能なとき: Phase A §4.1 で符号付き e = MP - GT が直接得られる。
    利用不可なとき: load_angle_mae_all_layers() の unsigned MAE を bias の上限として使用。
    """
    path = DATA["detailed_results"]
    if not Path(path).exists():
        print("[INFO] detailed_results.csv が見つかりません。"
              "unsigned MAE (coordinate_angle_mae.csv) を使用します。")
        return None

    df = pd.read_csv(path)
    df = _parse_camera_column(df, camera_col="camera")
    df = _add_camera_features(df, x_col="camera_x", y_col="camera_y", z_col="camera_z")
    df["height_label"] = df["camera_y"].apply(_y_to_layer_label)
    print(f"[load_detailed_results] {len(df)} rows")
    return df


# ──────────────────────────────────────────────────────────────────
# 5. 統合角度データ（メインの calibration 入力）
# ──────────────────────────────────────────────────────────────────

def get_combined_angle_data() -> Dict[str, pd.DataFrame]:
    """
    Phase A §4.1 の入力データを一括取得して辞書で返す。

    Returns
    -------
    {
      "angle_mae"          : カメラ位置 × 関節角度 MAE（符号なし、4層）
      "frame_camera"       : フレーム × カメラ の Δθ/Δψ 統計
      "joint_summary"      : 関節別全カメラ統合統計
      "detailed" (optional): per-sample 符号付き誤差（なければ None）
    }
    """
    return {
        "angle_mae":     load_angle_mae_all_layers(),
        "frame_camera":  load_frame_camera_summary(),
        "joint_summary": load_joint_summary(),
        "detailed":      load_detailed_results(),
    }


# ──────────────────────────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────────────────────────

def _parse_camera_column(df: pd.DataFrame, camera_col: str = "camera") -> pd.DataFrame:
    """
    "CapturedFrames_X_Y_Z" 形式の文字列列からカメラ座標 (X, Y, Z) を数値列として抽出する。

    例: "CapturedFrames_-1.0_0.5_-3.0" → camera_x=-1.0, camera_y=0.5, camera_z=-3.0
    """
    split = df[camera_col].str.replace("CapturedFrames_", "", regex=False).str.split("_", expand=True)
    df = df.copy()
    df["camera_x"] = pd.to_numeric(split[0])
    df["camera_y"] = pd.to_numeric(split[1])
    df["camera_z"] = pd.to_numeric(split[2])
    return df


def _add_camera_features(
    df: pd.DataFrame,
    x_col: str = "camera_x",
    y_col: str = "camera_y",
    z_col: str = "camera_z",
) -> pd.DataFrame:
    """
    カメラ座標 (X, Y, Z) からモデル特徴量を計算して列として追加する。

    §4.1 カメラ情報:
      distance  = sqrt(X² + Z²)  （水平距離、アバターは原点）
      azimuth   = atan2(X, Z)    （単位: 度。Z+ を 0° として時計回り正）
      elevation = atan2(Y, distance) （単位: 度）

    §6.5 Model 5 特徴量ベクトル: x = [1, Y, D, sin(φ), cos(φ), ε]
    """
    df = df.copy()
    cx = df[x_col].to_numpy(dtype=float)
    cy = df[y_col].to_numpy(dtype=float)
    cz = df[z_col].to_numpy(dtype=float)

    # 水平距離
    dist = np.sqrt(cx**2 + cz**2)
    dist = np.where(dist == 0, 1e-9, dist)   # ゼロ除算回避

    # 方位角: atan2(X, Z)（北=0、東=90）
    azimuth_rad = np.arctan2(cx, cz)

    # 仰角: atan2(Y, horizontal_distance)
    elevation_rad = np.arctan2(cy, dist)

    df["distance"]     = dist
    df["azimuth_deg"]  = np.degrees(azimuth_rad)
    df["elevation_deg"] = np.degrees(elevation_rad)

    # 線形モデル用の sin/cos 成分  §6.5
    df["sin_azimuth"]  = np.sin(azimuth_rad)
    df["cos_azimuth"]  = np.cos(azimuth_rad)

    return df


def _y_to_layer_label(y: float) -> str:
    """カメラ高さ Y を "Y=0.5" 等の文字列ラベルに変換する。"""
    for h in LAYER_HEIGHTS:
        if abs(y - h) < 0.05:
            return f"Y={h}"
    return f"Y={y:.1f}"
