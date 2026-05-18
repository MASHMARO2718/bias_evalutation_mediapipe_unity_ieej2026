# 09_calibration_framework

**Parametric Post-hoc Calibration Framework for MediaPipe Pose**  
MediaPipe Pose の視点依存バイアスをパラメトリックに補正する研究実装。

設計書: [`docs/01_補正モデル仕様.md`](docs/01_MediaPipe%20Pose%20補正モデル・アーキテクチャ仕様.md)  
実装詳細: [`IMPLEMENTATION.md`](IMPLEMENTATION.md)  
実行レポート: [`outputs/RUN_REPORT.md`](outputs/RUN_REPORT.md)  
コードレビューガイド: [`CODE_REVIEW.md`](CODE_REVIEW.md)

---

## Dashboard (GUI) — ブラウザで動くインタラクティブ可視化

```bash
cd 09_calibration_framework/dashboard
pip install -r requirements.txt
python app.py
# → http://localhost:8051 を開く
```

| タブ | 内容 |
|---|---|
| **Overview** | モデル比較・per-layer MAE・評価サマリー |
| **Bin Explorer** | カメラ位置マップ × 方位角ビン構造 (クリックで詳細) |
| **Linear Model** | 局所線形 R² ヒートマップ・OLS 係数 β |
| **Grid Search** | ハイパーパラメータ探索結果のインタラクティブ散布図 |

Cursor 不要。ブラウザだけで使えます。

---

## Quick Start

### 依存パッケージ

```bash
pip install pandas numpy scipy
```

### 実行順序

```bash
cd 09_calibration_framework

# 1. バイアステーブルを推定（Phase A）
python experiments/run_calibration.py

# 2. bin 設定の最適化（任意）
python experiments/grid_search.py

# 3. 全モデル評価（Phase B + 評価指標）
python experiments/run_evaluation.py
```

出力は `outputs/` に保存される。

---

## 前提データ

| ファイル | 場所 | 用途 |
|---|---|---|
| `coordinate_angle_mae.csv` | `../03_joint_angle_mae/joint_angle_mae_csv/Y=*/` | メイン入力（全4層必須） |
| `frame_camera_summary.csv` | `../05_direction_detection/output/processed_data/` | 方向角評価（任意） |
| `detailed_results.csv` | 同上（git除外・ローカル生成） | 符号付き補正（利用可なら優先） |

> `detailed_results.csv` がない場合でも動作するが、Model 2/5 は unsigned MAE を bias として使うため**過補正**になる。

---

## 実行結果サマリー（2026-05-18）

| 指標 | 値 |
|---|---|
| 総データ行数 | 576（4層 × 144カメラ位置） |
| データ分割 | calib 403 / val 86 / test 87 |
| 局所線形 R²（全ビン平均） | **0.718** |

### モデル比較（Joint Angle MAE 改善率）

| モデル | Known-view | Unknown-view (Y=2.0) | 汎化ドロップ |
|---|---|---|---|
| Model 2 (Joint-wise) | 102%* | 103%* | −0.7 pp |
| Model 3 (Height-wise) | **53%** | **53%** | −0.1 pp |
| Model 4 (View-bin az8) | **9%** | **9%** | +0.3 pp |
| Model 5 (Linear OLS) | 101%* | 104%* | −2.9 pp |

> *unsigned MAE 使用のため過補正（符号付き `detailed_results.csv` で解消予定）  
> Model 4 は符号なしでも有意な改善かつ汎化ドロップがほぼゼロ。

### Grid Search 最適設定

```
n_azimuth=4, n_distance=1  (score=23.78)
```
構造的妥当性を優先する場合は `n_azimuth=8` を推奨（score=27.24）。

---

## フォルダ構成

```
09_calibration_framework/
├── docs/               提案書（設計ドキュメント）
├── src/                実装本体
│   ├── config.py       定数・パス定義
│   ├── data_loader.py  CSV 読み込み・カメラ特徴量付加
│   ├── features.py     View-space Binning
│   ├── phase_a/        キャリブレーション（GT 必須）
│   │   ├── bias_estimator.py   Model 2〜4
│   │   └── linear_estimator.py Model 5 (OLS)
│   ├── phase_b/        補正適用（GT 不要）
│   │   ├── corrector.py        Model 2〜5 補正
│   │   └── pelvis.py           Model 6 骨盤剛体制約
│   └── evaluation/     評価
│       ├── metrics.py          全評価指標
│       └── split.py            データ分割
├── experiments/        実行スクリプト
│   ├── run_calibration.py
│   ├── run_evaluation.py
│   └── grid_search.py
└── outputs/            生成物（git 除外推奨）
    ├── bias_tables/    Phase A 出力
    ├── results/        評価結果
    └── figures/        図
```

---

## 既知の限界と今後の作業

| 課題 | 影響 | 対策 |
|---|---|---|
| unsigned MAE → 符号不明 | Model 2/5 が過補正 | `detailed_results.csv` 生成・利用 |
| Bin coverage 3/32 | 評価が粗い | per-sample signed データで CV に切り替え |
| Model 6/7 が未完成 | 骨盤・骨長補正なし | 3D 座標の signed 値が必要 |
| λ=1.0 固定 | 過補正リスク | Validation で λ を最適化 |
