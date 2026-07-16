# 実行レポート — Parametric Calibration Framework for MediaPipe Pose

実行日時: 2026-05-18  
データ: `03_joint_angle_mae/joint_angle_mae_csv/` 全4層 (Y=0.5 / 1.0 / 1.5 / 2.0)

---

## 0. 実行環境とデータ概要

| 項目 | 値 |
|---|---|
| 総サンプル数 | 576 行（カメラ位置 × 高さ層） |
| 高さ層 | Y=0.5 / 1.0 / 1.5 / 2.0 m（各 144 位置） |
| 評価関節 | L/R Shoulder, Elbow, Hip, Knee（8 関節） |
| データ分割 | Camera Split 70/15/15 (calib=403, val=86, test=87) |
| 高さホールドアウト | train: Y≤1.5, test: Y=2.0（unknown-view） |

> **注意（重要）:** 現行 CSV は各カメラ位置における **unsigned MAE の集計値**（`coordinate_angle_mae.csv`）。  
> 符号付き per-sample 誤差（`detailed_results.csv`）が利用できないため、  
> bias = +MAE として補正し、**補正後 MAE が 0 付近または負になる**（過補正傾向）。  
> 符号付きデータが揃い次第、`data_loader.load_detailed_results()` に切り替えることで精度改善が見込める。

---

## 1. Phase A: キャリブレーション結果

### 1.1 Model 2 — Joint-wise Constant Bias

| 関節 | bias_mean (°) | bias_std (°) | n |
|---|---|---|---|
| L_Shoulder | 40.15 | 7.66 | 336 |
| R_Shoulder | 39.35 | 6.93 | 349 |
| L_Elbow | 18.90 | 9.85 | 335 |
| R_Elbow | 18.18 | 10.48 | 349 |
| L_Hip | 30.20 | 14.16 | 355 |
| R_Hip | 32.70 | 15.68 | 356 |
| L_Knee | 17.01 | 4.69 | 355 |
| R_Knee | 19.64 | 5.88 | 356 |

- 肩の平均バイアスが最大（≈39-40°）、肘・膝が最小（≈17-20°）
- IEEJ 論文の関節角度 MAE と完全に一致（=同一データ）

---

### 1.2 Model 3 — Height-wise Bias（Y 層別平均バイアス, °）

| 関節 | Y=0.5 | Y=1.0 | Y=1.5 | Y=2.0 |
|---|---|---|---|---|
| L_Shoulder | 39.92 | 38.73 | 40.87 | **41.45** |
| R_Shoulder | 39.35 | 38.03 | 39.13 | **41.12** |
| L_Elbow | 17.75 | 18.15 | 18.94 | **20.99** |
| R_Elbow | 17.64 | 16.25 | 18.14 | **21.08** |
| L_Hip | 29.51 | **28.82** | 30.34 | 32.42 |
| R_Hip | 31.60 | 31.63 | 31.46 | **36.37** |
| L_Knee | 16.06 | 16.78 | 17.49 | **17.78** |
| R_Knee | 19.10 | **18.62** | 20.07 | 20.99 |

- **Y=2.0（俯瞰）で全関節が増大**。IEEJ 論文の視点バイアス知見（約+15%）を再確認。
- Y=1.0 が最小誤差層（肘・肩で明確）。

---

### 1.3 Model 5 — Linear Parametric 係数 β

各係数は `e_hat = β₀ + β₁·Y + β₂·D + β₃·sin(φ) + β₄·cos(φ) + β₅·ε` の成分。

| 関節 | intercept | camera_y | distance | sin_az | cos_az | elevation |
|---|---|---|---|---|---|---|
| L_Shoulder | +29.89 | +3.12 | +1.80 | +3.46 | +1.52 | -0.17 |
| R_Shoulder | +42.95 | +8.73 | -0.93 | -0.96 | +1.12 | -0.69 |
| L_Elbow | +20.46 | +6.82 | -0.54 | **+6.50** | +7.12 | -0.46 |
| R_Elbow | +9.07 | +4.86 | +1.22 | **-8.24** | +6.72 | -0.25 |
| L_Hip | +36.58 | +5.21 | -1.87 | **-12.77** | -2.58 | -0.26 |
| R_Hip | +24.68 | -4.14 | +0.97 | **+16.10** | +1.17 | +0.63 |
| L_Knee | +21.39 | +0.17 | -1.12 | +1.50 | +1.09 | +0.09 |
| R_Knee | +14.69 | +0.40 | +0.55 | -4.39 | -0.47 | +0.10 |

**注目すべき係数:**
- **Hip の sin_azimuth**: L_Hip = -12.77, R_Hip = +16.10（絶対値大・反符号）  
  → 側面視点での左右 hip MAE の反相関を捉えている（IEEJ 論文の r=-0.840 と対応）
- **Elbow の sin/cos_azimuth**: 左右で反符号（L +6.5, R -8.2）  
  → 左右肘誤差の反相関 r=-0.862 と対応

---

### 1.4 局所線形モデルの R²（ビン内当てはまり）

n_azimuth=8 の 254 bin × 関節 で個別フィット。

| 関節 | R² mean | R² min | R² max |
|---|---|---|---|
| L_Shoulder | 0.785 | 0.319 | 0.993 |
| R_Shoulder | **0.817** | 0.306 | 0.993 |
| L_Elbow | **0.791** | 0.482 | 0.975 |
| R_Elbow | 0.707 | 0.074 | 0.949 |
| L_Hip | 0.745 | 0.239 | 0.999 |
| R_Hip | 0.708 | 0.195 | 0.960 |
| L_Knee | 0.610 | 0.202 | 0.954 |
| R_Knee | 0.583 | 0.067 | 0.940 |
| **全体平均** | **0.718** | 0.067 | 0.999 |

- 全体平均 R² = **0.718**。「局所領域では線形近似が有効」という仮説を支持。
- R² が低いビン（R_Knee など min=0.067）はサンプル数が少なく不安定。

---

## 2. Phase B: 補正効果の評価

### 2.1 全モデル比較 — 平均改善率（°, 関節平均）

| モデル | Known-view 改善率 | Unknown-view (Y=2.0) 改善率 | Generalization Drop |
|---|---|---|---|
| Model 2 (Joint-wise) | **+102.0%** | **+102.7%** | -0.7 pp |
| Model 3 (Height-wise) | +52.7% | +52.8% | -0.1 pp |
| Model 4 (View-bin az8) | +8.8% | +8.5% | +0.3 pp |
| Model 5 (Linear) | +101.1% | +104.0% | -2.9 pp |

> **+100%超 = 過補正**（補正後の値が負）。unsigned MAE を bias として引いているため。  
> Model 2 / 5 は符号情報なしでは使用不可。Model 3 / 4 は相対比較として意味あり。

---

### 2.2 実用的に参照すべき結果 — Model 3 / Model 4

Model 3（高さ別補正）と Model 4（視点ビン補正）は **相対削減率が現実的な範囲**。

**補正前後の Raw MAE (°):**

| 層 | Raw | Model 2 | Model 4 |
|---|---|---|---|
| Y=0.5 | 26.70 | −0.32 (**過補正**) | 24.32 (−8.9%) |
| Y=1.0 | 26.18 | −0.83 (**過補正**) | 23.46 (−10.4%) |
| Y=1.5 | 26.21 | −0.81 (**過補正**) | 24.11 (−8.0%) |
| Y=2.0 | 27.12 | 0.10 (**過補正**) | 24.85 (−8.3%) |

- **Model 4 は全層で約 8〜10% の削減**。符号情報なしでも意味のある改善。
- 高さ間の分散（0.3°程度）よりも View-bin 内のばらつきが主要因。

---

### 2.3 汎化性能（Generalization Drop）

| モデル | Known | Unknown (Y=2.0) | Drop |
|---|---|---|---|
| Model 4 (View-bin) | +8.8% | +8.5% | **+0.3 pp** |

- Model 4 の汎化ドロップは **+0.3 pp（ほぼゼロ）**。
- 「既知視点でのみ効く」という過学習は起きていない。
- ただし Y=2.0 を訓練に含めた場合とホールドアウトした場合の差は今後検証が必要。

---

### 2.4 Hip 相関（Model 6 評価の前提）

| 分割 | r(L_Hip, R_Hip) |
|---|---|
| known_view test | **−0.685** |
| unknown_view (Y=2.0) test | **−0.699** |

- IEEJ 論文で確認された r = −0.840 より絶対値が小さい。
  これは `coordinate_angle_mae.csv` がカメラ位置別の **MAE 集計値**（符号なし）のためで、  
  per-sample の signed Δψ を使えば元の r = −0.840 に近い値が得られると予想される。
- Model 6（骨盤剛体制約）の入力には 3D 座標の signed 値が必要。

---

## 3. Grid Search 結果

| n_az | n_dist | min_samp | e_calib | e_val | gap | n_bins | score |
|---|---|---|---|---|---|---|---|
| **4** | 1 | 5 | 22.32 | 22.44 | 0.12 | 128 | **23.78** ★ |
| 4 | 1 | 10 | 22.32 | 22.44 | 0.12 | 128 | 23.78 |
| 8 | 1 | 5 | 24.50 | 24.62 | 0.12 | 256 | 27.24 |
| 4 | 2 | 5 | 24.48 | 24.55 | 0.07 | 256 | 27.55 |
| 12 | 1 | 5 | 25.26 | 25.38 | 0.12 | 384 | 33.48 |

**最適設定: n_azimuth=4, n_distance=1**
- bin 数が少ないほど目的関数スコアが良い（bin ペナルティ λ₂=0.01 が効いている）
- ただし n_azimuth=4 は方向依存性が粗く、視点構造の精細な捕捉が難しい
- **実用推奨: n_azimuth=8**（スコア差 3.5 に対して構造的妥当性が高い）

---

## 4. 診断・限界の整理

### 4.1 現状の主要限界

| 限界 | 原因 | 対策 |
|---|---|---|
| Model 2/5 が過補正 | unsigned MAE を signed bias として使用 | `detailed_results.csv` 利用（符号付き誤差） |
| Bin coverage: 3/32 | test セット 87 行では各ビンに 2〜4 行しか入らない | 全データの 30% をテストに当てるか、CV に切り替え |
| Model 6 が未動作 | 3D座標の signed 値が必要 | detailed_results または mediapipe の raw output が必要 |
| Hip r が IEEJ 論文より低 | MAE 集計済みデータの限界 | per-sample signed Δψ が必要 |

### 4.2 提案書の主張との照合（§13 成功条件）

| 成功条件 | 結果 | 判定 |
|---|---|---|
| Test セットで MAE 改善 | Model 4: ≈8-10% 削減（known/unknown 共に） | ✅ |
| Unknown-view でも改善 | Generalization Drop = 0.3 pp | ✅ |
| Hip 負相関の弱化 | unsigned MAE では確認困難 | ⚠️ 要 signed データ |
| Jitter が悪化しない | フレーム系列データ未対応（集計 CSV のため） | ⚠️ 要 per-sample データ |
| 補正できない誤差を明示 | 俯瞰 MAE の相対増加が Model 4 でも残存 | ✅ |

---

## 5. 次のアクション

1. **`detailed_results.csv` を生成**して signed bias を推定（→ Model 2/5 の過補正解消）
2. **Model 6 実装の完成**（骨盤剛体制約: 3D 座標の z_left_hip, z_right_hip が必要）
3. **n_azimuth=4 vs 8 の定性比較**（ヒートマップで bias_mean の空間分布を可視化）
4. **λ（補正強度）の Validation 最適化**（現在は λ=1.0 固定）
5. **時系列 jitter の評価**（per-frame データが必要: `detailed_results.csv` か frame_camera_summary）
6. **実用要求精度との比較** (§15 実用要求精度) — 各アプリ用途別の許容誤差と比較

---

## 6. 出力ファイル一覧

```
outputs/
├── bias_tables/
│   ├── model2_joint_bias.csv        (8 rows)
│   ├── model3_height_bias.csv       (32 rows)
│   ├── model4_viewbin_az8.csv       (256 rows: 8 joint × 4 layer × 8 azimuth)
│   └── model5_linear_global.json    (8 joint × 6 coefficients)
└── results/
    ├── evaluation_results_az8.csv   (64 rows: 4 model × 8 joint × 2 split)
    ├── grid_search_results.csv      (24 configurations)
    ├── bin_coverage_az8.csv         (32 bins coverage)
    └── local_linear_fits_az8.csv    (254 bin×joint fits with R²)
```
