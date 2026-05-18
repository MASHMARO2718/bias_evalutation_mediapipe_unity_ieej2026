# Code Review Guide

コードレビュー担当者向けのナビゲーションガイド。  
全体設計は [`IMPLEMENTATION.md`](IMPLEMENTATION.md)、研究背景は [`docs/`](docs/) を参照。

---

## 1. どこから読むか

### 初回レビュー推奨順

```
config.py          → 定数・パス定義（全体の前提を理解）
data_loader.py     → 入力データの構造と前処理
features.py        → ビン割り当てロジック
phase_a/bias_estimator.py    → Model 2〜4 の核心
phase_a/linear_estimator.py  → Model 5 OLS
phase_b/corrector.py         → 補正の適用
evaluation/metrics.py        → 評価指標の定義
experiments/run_evaluation.py → エンドツーエンドの流れ
```

---

## 2. データフロー

```
coordinate_angle_mae.csv (4層)
        │
        ▼
data_loader.load_angle_mae_all_layers()
        │  camera_x/y/z をパース → distance, azimuth_deg, elevation_deg を付加
        ▼
evaluation/split.camera_split()      ← 70/15/15 でカメラ単位に分割
        │
        ├─ df_calib ─→ phase_a/bias_estimator.estimate_*()  → bias_table (CSV/JSON)
        │              phase_a/linear_estimator.fit_all_joints()
        │
        ├─ df_val   ─→ grid_search でハイパーパラメータ最適化
        │
        └─ df_test  ─→ phase_b/corrector.apply_*()         → df_corrected
                        evaluation/metrics.improvement_rate()
                        evaluation/metrics.generalization_drop()
```

---

## 3. モジュール別レビューポイント

### `src/config.py`
- **チェック:** `REPO_ROOT = Path(__file__).resolve().parents[2]`  
  `src/config.py` から 2 階層上 = `09_calibration_framework/` の親リポジトリ root になる。
  フォルダ構造を変えると壊れる。

### `src/data_loader.py`
- `_parse_camera_column(df)`: フォルダ名（例 `CapturedFrames_-1.0_0.5_-3.0`）から  
  `camera_x=-1.0, camera_y=0.5, camera_z=-3.0` を正規表現で抽出。
  → **新しい命名規則に変更する場合はここを修正**
- `_add_camera_features(df)`: distance = √(x²+z²), azimuth = atan2(x, z) を計算。  
  `azimuth_deg` は `(-180, 180]` の範囲。`features.assign_azimuth_bin()` がこれを使う。

### `src/features.py`
- `assign_azimuth_bin(df, n_azimuth)`:  
  `azimuth_deg` を `[0, 360)` に変換後、等幅で `n_azimuth` 分割。  
  **注意:** 元の azimuth が `atan2` 由来で北(0°)≠0 ラジアンなのでオフセット変換あり。
- `_compute_reliability(group)`:  
  `w = n / (n + n_ref) × (1 - std/std_ref)` のような形で小サンプル・高分散ビンの信頼度を下げる。  
  `n_ref=10, std_ref=5.0` はヒューリスティック。→ **チューニング候補**

### `src/phase_a/bias_estimator.py`
- `estimate_viewbin_bias(df_calib, n_azimuth)`:  
  `height_bin × azimuth_bin` の複合キーで group-by し `bias_mean` を計算。  
  → ビンに 1 サンプルしかない場合も bias_std=0 で保存される（後段で reliability_weight が低くなる）
- `_compute_reliability`:  
  信頼度重み `w ∈ [0, 1]` を返す。n=1 のビンは w≈0 になりほぼ補正されない。

### `src/phase_a/linear_estimator.py`
- `build_feature_matrix(df)`:  
  `x = [1, camera_y, distance, sin(azimuth), cos(azimuth), elevation]`  
  elevation は `camera_y / distance` で計算（仰角の代理変数）。
- `fit_linear_model(X, y)`:  
  `scipy.linalg.lstsq` による OLS。正規化 ridge は `regularize > 0` で有効化可能（デフォルト 0）。
- `fit_local_linear_models(df, beta_global, n_azimuth)`:  
  ビン内サンプル数 `< min_samples` の場合は global beta にフォールバック。  
  → **`min_samples` は grid_search の対象**

### `src/phase_b/corrector.py`
- `apply_viewbin_bias(df, bias_table, n_azimuth, lam, use_reliability)`:  
  補正式: `x_corr = x_mp - lam × w × bias_mean`  
  マッチするビン行が bias_table にない場合は **補正なし（0 補正）**。  
  → **未知ビンへの対応が必要な場合はここに fallback ロジックを追加**
- `compute_improvement(df, joint_cols)`:  
  改善率 = `(raw_mae - corr_mae) / raw_mae × 100`  
  `raw_mae = 0` のカラムは `NaN` になる（実データでは起きにくい）。

### `src/phase_b/pelvis.py`
- `estimate_pelvis_tau(df_gt)`: GT の `z_left_hip - z_right_hip` の Percentile から τ を推定。  
  → **現在 `coordinate_angle_mae.csv` には 3D 座標なし。`detailed_results.csv` が必要。**
- `apply_pelvis_rigidity(df, tau)`: `Δz_hip` を `[-τ, τ]` でクリップ。  
  アイデアはシンプルだが clip 後に骨盤以下の全関節を再計算する必要がある（未実装）。

### `src/evaluation/metrics.py`
- `improvement_rate(raw_mae, corr_mae)`: scalar/array いずれも受け付ける。  
  **注意:** 現行は unsigned MAE を直接比較しているため Model 2/5 で 100% 超になる（過補正）。
- `generalization_drop(imp_known, imp_unknown)`:  
  正値 = 汎化が悪い（known > unknown）、負値 = unknown の方が改善（本実装の結果）。

### `src/evaluation/split.py`
- `camera_split(df, camera_col, seed)`:  
  `camera_col`（デフォルト `folder_name`）でユニークなカメラ IDを抽出し、random split。  
  **同一カメラが calib/val/test に混ざらない** ことを保証する（行レベルでなくカメラレベルの分割）。
- `height_holdout_split(df, test_heights)`:  
  height_label でフィルタ。Camera Split と独立して呼べる。

---

## 4. 非自明な設計判断

| 判断 | 理由 | 代替案 |
|---|---|---|
| カメラ単位で split | 同一カメラの複数フレームがリークしないように | frame 単位 split（フレーム独立性が高い場合） |
| unsigned MAE を bias として使用 | `detailed_results.csv` 未利用時の近似 | signed per-sample 誤差（利用可能なら優先） |
| `scipy.linalg.lstsq` で OLS | sklearn 不要・軽量 | `sklearn.linear_model.Ridge` に置換可 |
| reliability weight = n-based | 小サンプルビンで過補正を抑制 | 固定 min_samples でビン除外 |
| β フォールバック (global → local) | データ不足ビンで局所モデルが不安定になるため | KNN 補間、距離重み付き |

---

## 5. テスト方法

### 単体確認（スモークテスト）

```python
import sys; sys.path.insert(0, '.')
from src.data_loader import load_angle_mae_all_layers
from src.features import apply_all_bins
from src.evaluation.split import camera_split

df = load_angle_mae_all_layers()
df_calib, df_val, df_test = camera_split(df)
df_calib = apply_all_bins(df_calib)
print(df_calib.shape, df_calib.columns.tolist())
```

### 主要な境界値

| テスト | 確認内容 |
|---|---|
| `camera_split` で `seed` を変える | 分割結果の安定性 |
| `n_azimuth=1` で `assign_azimuth_bin` | 全行が bin=0 になること |
| bias_table に存在しないビン | `apply_viewbin_bias` が補正なしで返すこと |
| `lam=0.0` | 補正後 = 補正前（恒等変換） |
| `lam=2.0` | 2倍の過補正（テスト用） |

---

## 6. 既知の TODO / 改善候補

```
phase_b/pelvis.py     - apply_pelvis_rigidity: 骨盤以下の再計算が未実装
src/phase_b/          - Model 7 (kinematic.py) が未実装（要 3D 座標入力）
experiments/          - λ の Validation 最適化ループが未実装
src/evaluation/       - temporal_jitter: per-sample 時系列データが必要
src/features.py       - n_ref / std_ref のハイパーパラメータ化
```
