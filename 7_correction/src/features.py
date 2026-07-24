"""
features.py — View-space Binning（視点空間のビン分割）

提案書との対応:
  §8   View-space Binning Strategy
  §8.1 bin 分割の目的: 視点空間全体の複雑な誤差分布を局所線形近似可能な領域へ分割
  §8.2 bin 分割対象: camera_height, camera_azimuth, camera_distance, camera_elevation
  §8.3 bin 分割候補: azimuth_bins=[4,8,12,16], height_bins=[2,4], distance_bins=[1,2,3,4]
  §9.1 Grid Search: azimuth_bin_count 等をハイパーパラメータとして探索
"""

import numpy as np
import pandas as pd
from typing import Sequence, Optional


# ──────────────────────────────────────────────────────────────────
# 方位角ビン付与
# ──────────────────────────────────────────────────────────────────

def assign_azimuth_bin(
    df: pd.DataFrame,
    n_bins: int = 8,
    azimuth_col: str = "azimuth_deg",
    out_col: str = "azimuth_bin",
) -> pd.DataFrame:
    """
    方位角（-180°〜+180°）を n_bins 等分し、0-indexed の bin ID を付与する。

    §8.3 bin 分割候補: n_bins ∈ {4, 8, 12, 16}
    bin 幅 = 360° / n_bins。bin_id = floor((azimuth + 180) / width) % n_bins

    Parameters
    ----------
    df      : azimuth_deg 列を持つ DataFrame
    n_bins  : 分割数（ハイパーパラメータ）
    """
    df = df.copy()
    bin_width = 360.0 / n_bins

    # -180°〜+180° → 0°〜360° に正規化して等分
    azimuth_0to360 = (df[azimuth_col] + 180.0) % 360.0
    df[out_col] = (azimuth_0to360 // bin_width).astype(int) % n_bins
    return df


def assign_height_bin(
    df: pd.DataFrame,
    heights: Sequence[float] = (0.5, 1.0, 1.5, 2.0),
    y_col: str = "camera_y",
    out_col: str = "height_bin",
) -> pd.DataFrame:
    """
    カメラ高さ Y を最近傍の既知高さ層にスナップし bin ID を付与する。

    §8.2 camera_height が bin 分割対象
    """
    df = df.copy()
    heights = sorted(heights)
    height_arr = np.array(heights)

    def snap(y: float) -> int:
        idx = int(np.argmin(np.abs(height_arr - y)))
        return idx

    df[out_col] = df[y_col].apply(snap)
    df["height_label"] = df[out_col].apply(lambda i: f"Y={heights[i]}")
    return df


def assign_distance_bin(
    df: pd.DataFrame,
    n_bins: int = 2,
    dist_col: str = "distance",
    out_col: str = "distance_bin",
) -> pd.DataFrame:
    """
    水平距離を n_bins 等分して bin ID を付与する。

    §8.3 distance_bins ∈ {1, 2, 3, 4}
    n_bins=1 はビン分割なし（全データを1セルに統合）と同義。
    """
    df = df.copy()
    if n_bins <= 1:
        df[out_col] = 0
        return df

    # pandas qcut で分位数ベースの等頻度分割
    df[out_col] = pd.qcut(df[dist_col], q=n_bins, labels=False, duplicates="drop")
    df[out_col] = df[out_col].fillna(0).astype(int)
    return df


# ──────────────────────────────────────────────────────────────────
# ビン ID の複合キー生成
# ──────────────────────────────────────────────────────────────────

def make_bin_key(
    df: pd.DataFrame,
    joint_col: Optional[str] = "joint",
    height_col: str = "height_bin",
    azimuth_col: str = "azimuth_bin",
    metric_col: Optional[str] = "metric",
    distance_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    キー列 (joint, height_bin, azimuth_bin[, distance_bin][, metric]) を結合して
    bin_key 列（文字列）を生成する。

    §4.5 補正テーブル CSV のキー: joint, height_bin, azimuth_bin, metric
    この文字列キーが bias_table の行インデックスとして機能する。
    """
    df = df.copy()
    parts = []
    if joint_col and joint_col in df.columns:
        parts.append(df[joint_col].astype(str))
    parts.append(df[height_col].astype(str))
    parts.append(df[azimuth_col].astype(str))
    if distance_col and distance_col in df.columns:
        parts.append(df[distance_col].astype(str))
    if metric_col and metric_col in df.columns:
        parts.append(df[metric_col].astype(str))

    df["bin_key"] = pd.Series(["_".join(p) for p in zip(*[p.tolist() for p in parts])])
    return df


# ──────────────────────────────────────────────────────────────────
# 一括適用ヘルパー
# ──────────────────────────────────────────────────────────────────

def apply_all_bins(
    df: pd.DataFrame,
    n_azimuth: int = 8,
    heights: Sequence[float] = (0.5, 1.0, 1.5, 2.0),
    n_distance: int = 1,
) -> pd.DataFrame:
    """
    方位角・高さ・距離の全ビンを一括付与するヘルパー。

    §8.3 探索対象のハイパーパラメータ (n_azimuth, n_distance) を引数で渡す。
    height は離散値（データに高さが既に入っている）なのでスナップのみ。

    Parameters
    ----------
    n_azimuth  : 方位角ビン数（ハイパーパラメータ）
    heights    : 既知の高さ層
    n_distance : 距離ビン数（1 = 分割なし）
    """
    df = assign_azimuth_bin(df, n_bins=n_azimuth)
    df = assign_height_bin(df, heights=heights)
    df = assign_distance_bin(df, n_bins=n_distance)
    return df


# ──────────────────────────────────────────────────────────────────
# bin の統計情報（§17.4 感度分析・§17.6 信頼度用）
# ──────────────────────────────────────────────────────────────────

def compute_bin_stats(
    df: pd.DataFrame,
    value_cols: Sequence[str],
    group_cols: Sequence[str] = ("height_bin", "azimuth_bin"),
) -> pd.DataFrame:
    """
    各ビン内のサンプル数・値の統計を計算する。

    §17.4 ビン粒度感度分析: n (サンプル数) と分散が小さいビンが理想。
    §17.6 補正信頼度: bias_std と n から信頼度スコアを作るための素材。

    Returns
    -------
    DataFrame with columns:
      *group_cols, value_col, n, mean, std, median, reliability_weight
    """
    records = []
    grouped = df.groupby(list(group_cols))

    for key, grp in grouped:
        n = len(grp)
        row_base = dict(zip(group_cols, key if isinstance(key, tuple) else (key,)))
        row_base["n"] = n

        for col in value_cols:
            vals = grp[col].dropna()
            if len(vals) == 0:
                continue
            rec = dict(row_base)
            rec["metric"] = col
            rec["mean"]   = vals.mean()
            rec["std"]    = vals.std(ddof=1) if len(vals) > 1 else 0.0
            rec["median"] = vals.median()

            # §17.6 信頼度重み w = sigmoid に似た関数で n が大きく std が小さいほど 1 に近づく
            # ここでは簡易版: w = tanh(n / 100) * exp(-std / 30)
            w = float(np.tanh(n / 100.0) * np.exp(-rec["std"] / 30.0))
            rec["reliability_weight"] = min(max(w, 0.0), 1.0)

            records.append(rec)

    return pd.DataFrame(records)
