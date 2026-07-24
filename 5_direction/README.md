# 5_direction

MediaPipe Pose の方向角誤差（Δθ: 仰角方向、Δψ: 方位角方向）を計算し、
カメラ視点との相関分析・ダッシュボードを提供するモジュールです。

**重要:** このモジュールが生成する `detailed_results.csv` は
`7_correction` の符号付き補正（Model 4S など）の前提データです。

---

## 座標系について

MediaPipe は画像座標（Y 下向き正）、Unity GT は世界座標（Y 上向き正）を使用します。
このモジュールでは相対座標化の際に **MediaPipe の Y を反転**して座標系を統一しています。

```
MediaPipe: x 右, y 下, z 奥  →  y を反転  →  x 右, y 上, z 奥（Unity に合わせる）
```

---

## ファイル構成

```
5_direction/
├── README.md                   このファイル
├── config.py                   モジュール設定（パス・定数）
├── process_all_data.py         メインエントリ（全データ処理・CSV 出力）
├── interactive_dashboard.py    ローカルインタラクティブダッシュボード
│
├── scripts/                    処理モジュール群
│   ├── data_loader.py              データ読み込み（MediaPipe CSV・GT CSV）
│   ├── coordinate_transform.py     座標変換（Y 軸反転・方向角計算）
│   ├── compute_correlation.py      相関行列・高相関ペア抽出
│   ├── logger.py                   ログ設定
│   └── heatmap/
│       └── joint_camera_heatmap.py ヒートマップ生成
│
├── output/                     生成物（Git 除外）
│   ├── processed_data/
│   │   ├── detailed_results.csv        ← 最重要出力：フレーム × 関節の符号付き方向角誤差
│   │   ├── frame_camera_summary.csv    カメラ × フレームのサマリー
│   │   └── joint_summary.csv          関節別の統計サマリー
│   ├── correlation_analysis/           カメラ特徴量との相関行列・高相関ペア CSV
│   ├── logs/                           処理ログ
│   ├── debug_data/                     デバッグ用中間データ
│   └── validation_results/             検証結果
│
└── paper/
    └── 論文の変更点.md                 このモジュールに関連する論文変更メモ
```

---

## 実行方法

```bash
cd 5_direction
python process_all_data.py
```

処理には数分かかります（全4高さ層 × 全カメラ位置）。

---

## 出力ファイルの説明

### `detailed_results.csv`（最重要）

フレームレベルの符号付き方向角誤差。`7_correction` の符号付き補正に使用。

| カラム | 説明 |
|--------|------|
| `camera` | カメラ名（`CapturedFrames_X_Y_Z` 形式） |
| `frame` | フレーム番号 |
| `joint` | 関節名（例: `LEFT_SHOULDER`） |
| `delta_theta_deg` | 仰角方向誤差 Δθ（度、符号付き） |
| `delta_psi_deg` | 方位角方向誤差 Δψ（度、符号付き） |

### `frame_camera_summary.csv`

カメラ × フレームの集計値。フレーム平均の Δθ/Δψ。

### `joint_summary.csv`

関節別の統計サマリー（平均 |Δθ|、平均 |Δψ|、標準偏差等）。

---

## 前提データ

| ファイル | 場所 | 説明 |
|---------|------|------|
| MediaPipe CSV | `9_legacy_v1/mediapipe_processed/mediapipe_processed_csv/Y=*/` | フレーム別 3D 関節座標 |
| Unity GT CSV | `synced_joint_positions.csv`（リポジトリ直下） | グラウンドトゥルース関節座標 |

---

## 関連モジュール

- **入力元:** `9_legacy_v1/mediapipe_processed/` (MediaPipe CSV), `synced_joint_positions.csv` (GT)
- **出力先:** `7_correction/` が `detailed_results.csv` を使用
- **ダッシュボード:** `8_dashboard/` の可視化でも参照
