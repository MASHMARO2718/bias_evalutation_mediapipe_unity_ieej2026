# scripts/ — 分析・図生成スクリプト一覧

このフォルダには、**論文用の追加分析**と**図生成**のためのスタンドアロンスクリプトが格納されています。
`experiments/` の本実装スクリプトとは独立して実行できます。

実行する場合はリポジトリルートからではなく **`09_calibration_framework/` ディレクトリ内**で行ってください。

```bash
cd 09_calibration_framework
python scripts/<script_name>.py
```

---

## スクリプト一覧

### `signed_bias_eval.py` — 符号付きバイアス補正の評価

**目的:** `detailed_results.csv`（方向角誤差 `delta_theta_deg`, `delta_psi_deg`）を使い、
符号付き補正（signed）と符号なし補正（unsigned）を比較する。

**入力:**
- `05_direction_detection/output/processed_data/detailed_results.csv`
- `09_calibration_framework/src/config.py`（パス定義）

**出力（`outputs/results/`）:**

| ファイル | 説明 |
|---------|------|
| `signed_bias_results.csv` | 各モデル（M2S/M2U/M4S/M4U）の known-view / unknown-Y2 MAE |
| `lambda_sensitivity.csv` | Model 4S で λ を 0〜1.5 変化させたときの MAE |
| `signed_bias_per_joint.csv` | 関節別の補正前後 MAE と改善率（Model 4S, known-view） |

**モデル定義:**

| コード | 説明 |
|--------|------|
| `M4S` | View-bin + **signed** バイアス（推奨） |
| `M4U` | View-bin + unsigned バイアス（比較用） |
| `M2S` | Joint-wise constant + signed |
| `M2U` | Joint-wise constant + unsigned |

---

### `gen_signed_figs.py` — 符号付き評価の図生成

**目的:** `signed_bias_eval.py` の出力 CSV から論文用の図を生成する。

**入力（`outputs/results/`）:**
- `signed_bias_results.csv`
- `lambda_sensitivity.csv`
- `signed_bias_per_joint.csv`

**出力（`outputs/figures/`）:**

| ファイル | 説明 |
|---------|------|
| `fig_signed_vs_unsigned.png` | M4S vs M4U の MAE 比較棒グラフ |
| `fig_lambda_sensitivity.png` | λ 感度分析：λ vs MAE 折れ線グラフ |
| `fig_signed_per_joint.png` | 関節別改善率の棒グラフ |

**実行順序:** `signed_bias_eval.py` → `gen_signed_figs.py`

---

### `gen_ablation_failure.py` — アブレーション＋失敗ケース分析

**目的:**
1. **n_azimuth アブレーション**: 方位角ビン数（n_az）を 4, 8, 12, 16 と変化させて R² スコアへの影響を調べる
2. **失敗ケース分析**: 低 R²（< 0.5）のビンを特定し、その要因（遮蔽・関節・カメラ高さ）を分析

**入力:**
- `05_direction_detection/output/processed_data/detailed_results.csv`
- `outputs/results/local_linear_fits_az8.csv`（R² データ）

**出力（`outputs/figures/` および `outputs/results/`）:**

| ファイル | 説明 |
|---------|------|
| `outputs/figures/fig_ablation_naz.png` | n_az 別の平均 R² 棒グラフ |
| `outputs/figures/fig_failure_analysis.png` | 低 R² ビンの分布ヒートマップ |
| `outputs/results/failure_analysis.csv` | 低 R² ビンの詳細データ |

---

### `model6_eval.py` — Model 6（骨盤剛体制約）の評価

**目的:** 左右ヒップ関節の符号付き方位角誤差（Δψ）の逆相関を骨盤剛体制約で解消できるか検証する。

**背景:** MediaPipe は単一カメラから 3D 推定するため、左右ヒップの z 座標を独立に推定することができず、
カメラ方向によって一方が過大・他方が過小になる系統誤差が生じる。

**入力:**
- `05_direction_detection/output/processed_data/detailed_results.csv`
- `synced_joint_positions.csv`（Unity GT 関節座標）

**出力（`outputs/figures/` および `outputs/results/`）:**

| ファイル | 説明 |
|---------|------|
| `outputs/figures/fig_model6_hip_corr.png` | 補正前後の L/R ヒップ Δψ 散布図 |
| `outputs/results/model6_results.csv` | τ 推定値・補正前後の相関係数 |

**注意:** Unity GT では左右ヒップが共通の "Hips" ボーンにマッピングされているため、
GT の z 差分が常に 0 となり `τ=0` が推定される。
実用的な τ は MediaPipe 出力の分布パーセンタイルから設定することを推奨。

---

### `r2_vs_correction.py` — R² と補正効果の相関分析

**目的:** 局所線形 R²（MAE ベース）と方向角補正改善率との相関を調べる。

**動機:** 「R² が高いほど補正が効く」という直感的仮説を検証する。
結果として **ほぼ無相関または弱い負の相関** が観測され、
これは R²（関節角 MAE の局所線形性）と補正効果（方向角誤差の改善）が
異なる誤差空間に属することを示唆する重要な発見となった。

**入力:**
- `outputs/results/local_linear_fits_az8.csv`（局所 R²）
- `outputs/results/signed_bias_results.csv`（補正改善率）

**出力（`outputs/figures/` および `outputs/results/`）:**

| ファイル | 説明 |
|---------|------|
| `outputs/figures/fig_r2_vs_correction.png` | R² vs 補正改善率の散布図＋相関係数 |
| `outputs/results/r2_vs_correction.csv` | ビン別 R²・改善率・Pearson r |

---

## 実行推奨順序

```
1. signed_bias_eval.py        # 符号付き補正テーブル・評価指標
2. gen_signed_figs.py         # ↑ の可視化
3. gen_ablation_failure.py    # アブレーション・失敗ケース
4. model6_eval.py             # Model 6 検証
5. r2_vs_correction.py        # R² vs 補正効果（3 の後に実行）
```

前提として `experiments/run_calibration.py` と `experiments/run_evaluation.py` が完了し、
`outputs/results/local_linear_fits_az8.csv` が存在することを確認してください。
