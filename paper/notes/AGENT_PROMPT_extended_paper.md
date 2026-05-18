# 査読論文執筆エージェントへの指示

## あなたの役割

この研究プロジェクトのデータと既存論文を読み込み、**8ページの英語査読論文（フルペーパー）** を執筆することがあなたの仕事です。

---

## プロジェクト概要（必ず最初に読むこと）

**研究テーマ**: Unity 環境で収集した Ground Truth を用いた MediaPipe 姿勢推定の精度評価

**既存論文（4ページ）のパス**:
```
c:\projects\MOTIONTRACK\Zeval_DataSet_organized\docs\paper\Zeval_IEEJ_submit.pdf
```
この PDF を最初に全文読むこと。これが今回拡張する元論文です。

**英語 LaTeX 草稿**:
```
c:\projects\MOTIONTRACK\Zeval_DataSet_organized\07_paper\paper_en.md
```
英語版の骨格（LaTeX）がある。これをベースに8ページへ拡張する。

---

## フォルダ構成と重要ファイル

```
c:\projects\MOTIONTRACK\Zeval_DataSet_organized\
├── synced_joint_positions.csv        # Unity GT データ（触らない）
├── config.py                          # パス・設定定義
│
├── 02_mediapipe_processed/            # MediaPipe 出力 CSV（パイプライン実行で生成）
│
├── 03_joint_angle_mae/                # 関節角度 MAE（一次：per-camera CSV・統合・ヒートマップ）
│
├── 04_max_angle_error/                # 最大角度誤差
│
├── 05_direction_detection/            # 方向角誤差・相関分析（最重要）
│   ├── process_all_data.py
│   ├── scripts/
│   │   ├── coordinate_transform.py    # Y軸反転の実装
│   │   ├── compute_correlation.py     # 相関行列の計算
│   │   └── heatmap/joint_camera_heatmap.py
│   └── output/
│       ├── processed_data/
│       │   ├── detailed_results.csv   # 全フレーム・全カメラの方向角誤差
│       │   ├── joint_summary.csv      # 関節別サマリー
│       │   └── frame_camera_summary.csv
│       └── correlation_analysis/
│           ├── correlation_matrix_theta.csv
│           ├── correlation_matrix_psi.csv
│           ├── high_correlation_pairs_theta.csv
│           └── high_correlation_pairs_psi.csv
│
└── 07_paper/                          # 論文関連資料
    ├── paper_en.md                    # 英語 LaTeX 草稿（ベース）
    ├── データ出典記録.md               # 各表・図のデータソース
    ├── 実験結果の検証報告.md           # データの整合性確認済み結果
    └── 追加図表の提案.md              # 8ページ化に向けた追加図表案
```

---

## 既存論文の主要な数値（検証済み）

以下の数値は `07_paper/実験結果の検証報告.md` で照合済み。執筆時に使ってよい。

### Table 1: 関節角度誤差（Joint Angle MAE）
| Joint | MAE (deg) | Median (deg) | Max (deg) |
|-------|-----------|--------------|-----------|
| Left shoulder | 39.8 | 39.2 | 70.1 |
| Right shoulder | 39.0 | 40.0 | 58.2 |
| Left elbow | 18.6 | 15.9 | 56.9 |
| Right elbow | 18.2 | 13.6 | 46.2 |
| Left hip | 30.2 | 29.4 | 66.0 |
| Right hip | 33.3 | 32.2 | 81.7 |
| Left knee | 17.0 | 16.6 | 43.4 |
| Right knee | 19.5 | 19.4 | 62.3 |

### 方向角誤差（05_direction_detection と照合済み）
- 肘 |∆θ| 平均：左 58.3°、右 59.3°（座標系統一後）
- 肩 |∆θ| 平均：左 10.4°、右 9.3°（座標系統一後に大幅改善）
- 腰 |∆ψ| 平均：左 88.9°、右 91.1°
- LEFT_HIP–RIGHT_HIP 相関：r = -0.8402
- LEFT_ELBOW–RIGHT_ELBOW 相関：r = -0.8622

### 相関分析（Table 2: ∆θ, Table 3: ∆ψ）
詳細は `05_direction_detection/output/correlation_analysis/` の CSV を読むこと。

---

## 執筆指示：8ページ査読論文の構成

既存の4ページ論文（IEEJ）を**情報量2倍以上**に拡張する。ターゲットジャーナルは IEEE Access や Sensors（MDPI）相当の英語査読論文を想定。

### 各セクションの方針

#### 1. Abstract（0.5ページ）
- 4ページ版より詳しく、定量的な主要結果を3〜4文で明示
- Contribution を bullet point で記述するスタイルも検討

#### 2. Introduction（1〜1.5ページ）
4ページ版から大幅拡充：
- **先行研究レビュー**を充実させる
  - BlazePose（Bazarevsky et al., 2020）の精度報告
  - Human3.6M・COCO データセットの視点バイアス問題
  - 既存の monocular 3D pose estimation の限界（depth ambiguity）
  - Unity/シミュレーション環境を使った GT 収集の先行例
- **本研究の Contribution** を明示的にリスト化（3〜4点）
  - 505カメラ・多視点評価の規模
  - 座標系統一（Y軸反転）による体系的補正の提案
  - 方向角誤差と相関パターンの定量化
  - 実用上の適用限界の明確化

#### 3. Related Work（1ページ）
4ページ版にはない独立セクションを追加：
- MediaPipe / BlazePose の精度評価に関する既存研究
- シミュレーション環境（Unity 等）を使った評価手法
- 単眼カメラの深度推定限界に関する研究
- 骨格モデルの剛体制約に関する研究

#### 4. Experimental Method（1〜1.5ページ）
4ページ版から拡充：
- Unity 環境の詳細（Y-Bot アバター、アニメーション設定、物理パラメータ）
- カメラ配置の詳細（グリッド設計の根拠、Y=0.5/1.0/1.5/2.0 の選択理由）
- MediaPipe の設定パラメータ（`static_image_mode=True`, `model_complexity=1`, `min_detection_confidence=0.5`）
- **座標系の統一手順**（4ページ版では簡略）を詳しく説明
  - Unity の Y軸上向き正 vs MediaPipe の Y軸下向き正
  - Y反転の具体的な変換式
  - `05_direction_detection/scripts/coordinate_transform.py` を参照して実装詳細を記述
- 可視度フィルタ（0.5未満除外）の影響

#### 5. Results（2〜2.5ページ）
4ページ版から大幅拡充：

**5.1 Joint Angle MAE（Table 1）**
- 現行の Table 1 に加えて、カメラ高さ層別（Y = 0.5, 1.0, 1.5, 2.0 m）の比較も追加
- カメラ高さによる誤差変化の考察

**5.2 Direction Angle Error（∆θ, ∆ψ）**
- 全関節の ∆θ・∆ψ 統計をまとめた **新しい Table** を追加（4ページ版にない）
  - `05_direction_detection/output/processed_data/joint_summary.csv` から取得
- 座標系統一前後の比較（肘 ∆θ が改善することを数値で示す）
- Y レイヤー別のヒートマップ比較（`07_paper/追加図表の提案.md` 参照）

**5.3 Inter-joint Correlation（Table 2, 3）**
- ∆θ・∆ψ 相関行列ヒートマップ（Figure 6）を現行の小さい図から拡充
- `correlation_matrix_theta.csv` / `correlation_matrix_psi.csv` の全体を可視化
- `07_paper/追加図表の提案.md` の「相関行列のヒートマップ」案を参照

**5.4 Camera Viewpoint Dependency**
- カメラ位置（X, Z）と誤差の関係を示す図（`07_paper/追加図表の提案.md` 優先度5参照）
- フレームごとの最良/最悪カメラの誤差分布

**追加 Figure の候補**（`07_paper/追加図表の提案.md` を参照）:
1. 相関行列ヒートマップ（∆θ用・∆ψ用）← 最優先
2. 右肘 ∆θ・腰 ∆ψ の追加ヒートマップ
3. 各関節の ∆θ・∆ψ 箱ひげ図
4. Y レイヤー別ヒートマップ比較

#### 6. Discussion（1.5〜2ページ）
4ページ版の 4.1〜4.2 を大幅拡充：

**6.1 Coordinate System Unification Effect**
- Y軸反転の効果を before/after で定量比較

**6.2 Systematic Bias in Depth Estimation**
- 腰 ∆ψ ≈ 90° の原因（骨盤の剛体制約欠如）をより詳しく説明
- MediaPipe の骨格モデルの制約と本誤差の関係

**6.3 Left-Right Symmetric Error Pattern**
- 肘の左右反転（r = -0.862）の解釈（学習時の左右反転 augmentation の影響）
- 上肢の連動誤差（r = 0.72–0.77）の解釈

**6.4 Viewpoint Dependency**
- カメラ位置（視点）と誤差の相関パターン
- 学習データの視点分布バイアスとの関連

**6.5 Practical Implications**
- 2D 推定としては有用、3D 深度推定には限界
- どのアプリケーション（スポーツ分析、リハビリ等）で許容できるか

**6.6 Limitations**
- 本研究の限界（Unity アバターと実人間の差、単一人物の歩行のみ、等）

#### 7. Conclusion（0.5ページ）
- 主要な発見を箇条書きで明示
- 今後の課題（骨盤剛体制約モデル、ファインチューニング、等）

#### 8. References
- 既存の3件 + Related Work で追加する論文

---

## データへのアクセス方法

### パイプラインを再実行する場合
```bash
cd c:\projects\MOTIONTRACK\Zeval_DataSet_organized
python run.py --no-mediapipe --no-dashboard
```
これで `05_direction_detection/output/` に CSV が生成される。

### 既存データを直接読む場合
CSV ファイルを直接 Read ツールで読み込んで数値を確認すること。
- 方向角誤差サマリー: `05_direction_detection/output/processed_data/joint_summary.csv`
- 相関行列: `05_direction_detection/output/correlation_analysis/correlation_matrix_theta.csv`
- 詳細データ: `05_direction_detection/output/processed_data/detailed_results.csv`

---

## 既知の注意事項

### Table 1 の数値について
`07_paper/実験結果の検証報告.md` に記録あり：論文掲載の Table 1 の値（左肩 35.4° 等）と、現行パイプラインの出力（左肩 39.8° 等）に乖離がある。**査読論文では現行パイプライン（39.8° 等）の値を使用すること**。これが最新かつ再現可能なデータである。

### 方向角誤差の範囲
∆θ・∆ψ は -180°〜+180° の範囲。腰の ∆ψ ≈ 90° は「深度方向が見えない単眼カメラの限界」であり正しいデータ。100° 超えは異常値ではない。

### Y軸反転の適用
`05_direction_detection` の全出力は Y軸反転適用済み。実装は `05_direction_detection/scripts/coordinate_transform.py` を参照。

---

## 執筆上の注意

- **言語**: 英語（査読論文向けのフォーマル表現）
- **フォーマット**: LaTeX（`07_paper/paper_en.md` の LaTeX 構造を踏襲）
- **図表**: 既存の4ページ版にある図（Figure 1〜6）はすべて維持。新規図表を追加
- **出力先**: `07_paper/paper_extended.md`（または `.tex`）に保存すること
- **引用スタイル**: IEEE 形式

---

## 最初にやること（チェックリスト）

1. `docs/paper/Zeval_IEEJ_submit.pdf` を全文読む
2. `07_paper/paper_en.md` を全文読む
3. `07_paper/追加図表の提案.md` を読む
4. `07_paper/実験結果の検証報告.md` を読む
5. `05_direction_detection/output/processed_data/joint_summary.csv` を読んで数値を確認
6. `05_direction_detection/output/correlation_analysis/` の CSV を読んで相関値を確認
7. 上記を踏まえて 8ページ版の論文を執筆する
