# Implementation Guide

**A Local-Linearity-Based Parametric Calibration Framework for MediaPipe Pose**

提案書 `docs/01_*.md` / `docs/02_*.md` の設計をそのまま Python 実装に落とした構成。

---

## フォルダ構成

```
09_A_Local-Linearity-Based_Parametric_Calibration.../
├── docs/                          提案書 (設計ドキュメント)
│   ├── 01_補正モデル・アーキテクチャ仕様.md
│   ├── 02_局所線形補正フレームワーク提案.md
│   └── 03_補正アーキテクチャ図.md
│
├── src/                           実装本体
│   ├── config.py                  パス・定数・ハイパーパラメータ既定値
│   ├── data_loader.py             CSV 読み込み・カメラ特徴量付加
│   ├── features.py                View-space Binning（方位角・高さ・距離ビン）
│   │
│   ├── phase_a/                   Phase A: キャリブレーション（GT 必須）
│   │   ├── bias_estimator.py      Model 2〜4: バイアステーブル推定・保存
│   │   └── linear_estimator.py   Model 5: OLS・局所線形モデル
│   │
│   ├── phase_b/                   Phase B: 補正適用（GT 不要）
│   │   ├── corrector.py           Model 2〜5 補正の適用・改善率計算
│   │   └── pelvis.py              Model 6: 骨盤剛体制約（τ 推定・clip 適用）
│   │
│   └── evaluation/                評価
│       ├── metrics.py             §9 全評価指標（MAE・hip_r・gap・jitter 等）
│       └── split.py               Camera Split / Height Hold-out
│
├── experiments/                   実行スクリプト
│   ├── run_calibration.py         Phase A 一括実行（バイアステーブル生成）
│   ├── run_evaluation.py          Phase B + 全モデル比較評価
│   └── grid_search.py             bin ハイパーパラメータ Grid Search
│
└── outputs/                       生成物（git 除外推奨）
    ├── bias_tables/               Phase A 出力 CSV / JSON
    ├── results/                   評価結果 CSV
    └── figures/                   図（任意）
```

---

## 提案書との対応表

| ファイル | 提案書セクション |
|---|---|
| `src/config.py` | §4.3 入出力定義, §8 分割比率, §6 モデル定数 |
| `src/data_loader.py` | §4.1 Phase A 入力, §4.6 データ候補 |
| `src/features.py` | §8 View-space Binning, §8.1〜8.3, §17.4 感度分析補助 |
| `src/phase_a/bias_estimator.py` | §6.3 Model2, §6.4 Model3, §6.5 Model4, §7.2 平均誤差推定, §4.5 テーブル形式 |
| `src/phase_a/linear_estimator.py` | §6.6 Model5, §7.3 最小二乗, §11 局所線形性評価, §02提案書§7 |
| `src/phase_b/corrector.py` | §4.2 Phase B, §4.4 補正式, §17.7 λ, §17.6 信頼度重み w |
| `src/phase_b/pelvis.py` | §6.7 Model6, §7.4 閾値推定, §9.4 hip 相関評価 |
| `src/evaluation/metrics.py` | §9 全評価指標, §13.1 成功条件, §17.8 jitter |
| `src/evaluation/split.py` | §8.2 Camera Split, §8.3 Height Hold-out, §17.4〜17.5 |
| `experiments/run_calibration.py` | §4.7 推奨研究デザイン 手順 1〜2 |
| `experiments/run_evaluation.py` | §4.7 手順 3〜5, §10.1 モデル比較, §13.1 成功条件 |
| `experiments/grid_search.py` | §9.1 Grid Search, §10 目的関数 |

---

## 実行手順

### 0. 依存関係
```bash
pip install pandas numpy scipy scikit-learn
```

### 1. Phase A（キャリブレーション）
```bash
python experiments/run_calibration.py
```
→ `outputs/bias_tables/` に `model2_joint_bias.csv`, `model4_viewbin_az8.csv`, `model5_linear_global.json` 等を生成。

### 2. Grid Search（任意・推奨）
```bash
python experiments/grid_search.py
```
→ `outputs/results/grid_search_results.csv` で最適 bin 設定を確認。

### 3. Phase B + 評価
```bash
python experiments/run_evaluation.py
```
→ `outputs/results/evaluation_results_az8.csv` に Known/Unknown-view 別の改善率を出力。

---

## 設計上の重要な注意点

### 利用可能データの限界
現行の CSV は **集計済み** データ（カメラ位置別 MAE、方向角の abs 平均）。
符号付き per-sample 誤差は `detailed_results.csv`（git 除外・ローカル生成）が必要。

| ファイル | 含む情報 | 用途 |
|---|---|---|
| `coordinate_angle_mae.csv` | カメラ位置 × 関節 の unsigned MAE | Model 2〜5 の calib（上限近似） |
| `frame_camera_summary.csv` | フレーム × カメラ の Δθ/Δψ abs 統計 | 方向角評価 §9.2 |
| `detailed_results.csv` | per-sample 符号付き誤差（git 除外） | 符号付き bias 推定（利用可能なら優先） |

### unsigned MAE を bias として使う場合
`e = MP - GT` の符号が不明なため `bias_mean = +MAE` とすると**過大推定**になる可能性あり。
`detailed_results.csv` が利用可能な環境では `data_loader.load_detailed_results()` を使い、
`bias_estimator.py` の `estimate_*` 関数の入力を signed error に切り替えること。

### 補正強度 λ と信頼度 w
- `lam=1.0`（既定）: 推定バイアスを全量引く
- `use_reliability=True`（既定）: n 小 / std 大 のビンでは補正を弱める
- grid_search 後に `lam` を validation で決定する場合は `run_evaluation.py` の `run(lam=...)` を利用

---

## 各モデルの補正式まとめ（提案書 §6）

| Model | 補正式 | 推定パラメータ |
|---|---|---|
| Model 0 | `x_corr = x_mp`（無補正） | なし |
| Model 1 | `y ← -y`（座標系統一） | なし（決定論的） |
| Model 2 | `x_corr = x_mp - b_j` | `b_j = mean(MAE_j)` per joint |
| Model 3 | `x_corr = x_mp - b_{j,h}` | per joint × height_bin |
| Model 4 | `x_corr = x_mp - λ·w·b_{j,h,a}` | per joint × height_bin × azimuth_bin |
| Model 5 | `x_corr = x_mp - x^T β_{j,k}` | β: OLS (per joint or per bin) |
| Model 6 | `Δz' = clip(Δz, -τ, τ)` で骨盤深度差をクリップ | `τ = P95` on GT |
| Model 7 | 骨長制約・運動連鎖（未実装、要 3D 座標入力） | `L_bone, r_gt` on GT |

---

## 評価指標まとめ（提案書 §9 / §17）

| 指標 | 式 | 場所 |
|---|---|---|
| Joint Angle MAE | `mean(|α_corr - α_gt|)` | `metrics.joint_angle_mae()` |
| Improvement Rate | `(E_raw - E_corr) / E_raw × 100` | `metrics.improvement_rate()` |
| Generalization Drop | `Imp_known - Imp_unknown` | `metrics.generalization_drop()` |
| Viewpoint Gap | `E_worst / E_best` | `metrics.viewpoint_gap()` |
| Hip Correlation | `r(Δψ_L, Δψ_R)` | `metrics.hip_correlation()` |
| Temporal Jitter | `mean|α_t - α_{t-1}|` | `metrics.temporal_jitter()` |

---

## 成功条件（提案書 §13.1）

以下を事前に定義し、実験後に確認する（査読耐性のため）:

1. Joint Angle MAE が test セットで低下している（calib only でなく）
2. Unknown-view (Y=2.0) でも一定の改善が見られる（Generalization Drop を記録）
3. hip 負相関 r が補正後に低下している（Model 6 が機能している証拠）
4. Jitter が raw より著しく増大していない（anatomical validity の代理）
5. 改善しない誤差（単眼深度曖昧性, unknown-view での限界）を明示している
