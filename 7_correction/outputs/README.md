# outputs/ — 生成物フォルダ

このフォルダは **スクリプト実行時に自動生成**されるファイルを格納します。
`.gitignore` で除外されているため、Git には含まれません。

再生成方法は [`../README.md`](../README.md) の Quick Start セクションを参照してください。

---

## フォルダ構成

```
outputs/
├── RUN_REPORT.md        実行レポート（Phase A/B 詳細結果）
├── bias_tables/         Phase A: バイアステーブル（キャリブレーション結果）
├── results/             Phase B + 追加分析の評価 CSV
└── figures/             論文用・分析用の図（PNG）
```

---

## `bias_tables/` — Phase A 出力（バイアステーブル）

`experiments/run_calibration.py` で生成される、各モデルのバイアス推定値。

| ファイル | モデル | 説明 |
|---------|--------|------|
| `model2_joint_bias.csv` | Model 2 | 関節別定数バイアス（8 関節 × Δθ/Δψ の平均 MAE） |
| `model3_height_bias.csv` | Model 3 | カメラ高さ層別バイアス（4 層 × 関節） |
| `model4_viewbin_az8.csv` | Model 4 | 視点ビン別バイアス（方位角 8 × 高さ 4 × 関節） |
| `model5_linear_global.json` | Model 5 | 全体線形 OLS 係数（β ベクトル + 切片） |

---

## `results/` — 評価 CSV

### メイン評価（`experiments/run_evaluation.py` 生成）

| ファイル | 説明 |
|---------|------|
| `evaluation_results_az8.csv` | Model 1〜5 の MAE 改善率（known/unknown-view） |
| `grid_search_results.csv` | n_azimuth × n_distance のグリッドサーチ結果（スコア一覧） |
| `bin_coverage_az8.csv` | ビンごとのカバレッジ（データ点数） |
| `local_linear_fits_az8.csv` | ビン × 関節ごとの局所線形 R²・OLS 係数 |

### 符号付き補正分析（`scripts/signed_bias_eval.py` 生成）

| ファイル | 説明 |
|---------|------|
| `signed_bias_results.csv` | M4S/M4U/M2S/M2U の known/unknown MAE（λ=1.0） |
| `lambda_sensitivity.csv` | Model 4S の λ=0〜1.5 感度分析 |
| `signed_bias_per_joint.csv` | Model 4S の関節別改善率（known-view） |

### 追加分析（`scripts/gen_ablation_failure.py`, `model6_eval.py`, `r2_vs_correction.py` 生成）

| ファイル | 生成スクリプト | 説明 |
|---------|---------------|------|
| `failure_analysis.csv` | `gen_ablation_failure.py` | 低 R² ビンの詳細（関節・高さ・ビン ID） |
| `model6_results.csv` | `model6_eval.py` | Model 6 の τ 推定値・L/R ヒップ Δψ 相関係数 |
| `r2_vs_correction.csv` | `r2_vs_correction.py` | ビン別 局所 R² vs 補正改善率・Pearson r |

---

## `figures/` — 図一覧（PNG）

### `scripts/gen_signed_figs.py` 生成

| ファイル | 内容 |
|---------|------|
| `fig_signed_vs_unsigned.png` | signed vs unsigned 補正の MAE 棒グラフ比較 |
| `fig_lambda_sensitivity.png` | λ 感度分析：λ vs 平均 |Δθ| 折れ線 |
| `fig_signed_per_joint.png` | 関節別改善率（Model 4S, known-view） |

### `scripts/gen_ablation_failure.py` 生成

| ファイル | 内容 |
|---------|------|
| `fig_ablation_naz.png` | n_az=4/8/12/16 の平均 R² 棒グラフ |
| `fig_failure_analysis.png` | 低 R² ビンの分布ヒートマップ |

### `scripts/model6_eval.py` 生成

| ファイル | 内容 |
|---------|------|
| `fig_model6_hip_corr.png` | 補正前後の L/R ヒップ Δψ 散布図（相関係数付き） |

### `scripts/r2_vs_correction.py` 生成

| ファイル | 内容 |
|---------|------|
| `fig_r2_vs_correction.png` | 局所 R² vs 補正改善率の散布図（Pearson r 付き） |

---

## 再生成コマンド

```bash
cd 7_correction

# Phase A/B（本実装）
python experiments/run_calibration.py
python experiments/run_evaluation.py
python experiments/grid_search.py       # オプション

# 追加分析スクリプト（scripts/ 参照）
python scripts/signed_bias_eval.py
python scripts/gen_signed_figs.py
python scripts/gen_ablation_failure.py
python scripts/model6_eval.py
python scripts/r2_vs_correction.py
```
