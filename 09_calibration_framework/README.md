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
├── README.md           このファイル
├── IMPLEMENTATION.md   実装詳細（モジュール別 API）
├── CODE_REVIEW.md      コードレビューガイド
│
├── src/                実装本体（コアライブラリ）
│   ├── config.py           定数・パス定義（入出力先を一元管理）
│   ├── data_loader.py      CSV 読み込み・カメラ特徴量付加
│   ├── features.py         View-space Binning（方位角・高さ・距離）
│   ├── phase_a/            Phase A: バイアス推定（GT 必須）
│   │   ├── bias_estimator.py   Model 2〜4 バイアステーブル構築
│   │   └── linear_estimator.py Model 5 全体線形 OLS
│   ├── phase_b/            Phase B: 補正適用（GT 不要・推論時に使用）
│   │   ├── corrector.py        Model 2〜5 補正
│   │   └── pelvis.py           Model 6 骨盤剛体制約
│   └── evaluation/         評価指標・データ分割
│       ├── metrics.py          MAE・RMSE・改善率等
│       └── split.py            camera-level 70/15/15 分割
│
├── experiments/        本実装の実行スクリプト（順番に実行）
│   ├── run_calibration.py  Phase A: バイアステーブル生成
│   ├── run_evaluation.py   Phase B: 全モデル評価
│   └── grid_search.py      ハイパーパラメータ探索（任意）
│
├── scripts/            追加分析・図生成スクリプト（論文用）
│   ├── README.md           ← 各スクリプトの詳細説明
│   ├── signed_bias_eval.py 符号付き補正評価（M4S vs M4U）
│   ├── gen_signed_figs.py  符号付き評価の図生成
│   ├── gen_ablation_failure.py  n_az アブレーション＋低 R² 失敗ケース
│   ├── model6_eval.py      Model 6 骨盤剛体制約の評価
│   └── r2_vs_correction.py 局所 R² vs 補正効果の相関分析
│
├── dashboard/          ブラウザ GUI（Dash）
│   ├── app.py              ポート 8051 で起動
│   └── requirements.txt
│
├── docs/               設計ドキュメント・分析レポート
│   ├── README.md           ← 各ドキュメントの説明
│   ├── 01_補正モデル仕様.md
│   ├── 02_局所線形補正フレームワーク提案.md
│   ├── 03_補正アーキテクチャ図.md
│   ├── 04_局所線形性評価の解説.md
│   ├── 05_linearity_analysis.md  生データ線形性分析レポート
│   └── 06_signed_bias_analysis.md  符号付き補正分析レポート
│
└── outputs/            生成物（Git 除外・ローカルのみ）
    ├── README.md           ← 各ファイルの説明
    ├── RUN_REPORT.md       Phase A/B 詳細実行レポート
    ├── bias_tables/        Phase A 出力（model2〜5 バイアステーブル）
    ├── results/            評価 CSV（グリッドサーチ・signed 評価等）
    └── figures/            論文用図（PNG）
```

---

## 既知の限界と今後の作業

| 課題 | 状態 | 詳細 |
|---|---|---|
| unsigned MAE → 過補正 | **解決済み** | `detailed_results.csv` + `scripts/signed_bias_eval.py` で符号付き補正を実装 |
| λ=1.0 固定 | **解析済み** | `scripts/signed_bias_eval.py` の λ 感度分析で最適値は 0.75〜1.0 と判明 |
| Model 6（骨盤）が未完成 | **部分実装** | `scripts/model6_eval.py` で検証済み。GT の z 差分が 0 のため τ 推定に課題あり |
| R² vs 補正効果の乖離 | **発見・記録済み** | 局所 R²（MAE 空間）と補正効果（方向角空間）はほぼ無相関（Pearson r ≈ 0） |
