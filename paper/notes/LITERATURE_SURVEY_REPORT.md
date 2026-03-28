# 参考文献調査レポート

**作成日**: 2026-03-15  
**目的**: `paper/source/main.tex` Related Work セクション（§2）および参考文献リストへの追記に用いた文献の詳細情報を記録する。  
**対応する `\bibitem` キー**: 各節末尾に記載  

---

## 概要

| カテゴリ | 追加文献数 | `\bibitem` キー |
|---|---|---|
| §2.1 MediaPipe/BlazePose 独立評価 | 1 | `mroz2021` |
| §2.2 合成GT・シミュレーション | 3 | `surreal`, `agora`, `peoplesanspeople` |
| §2.3 単眼3D推定・深度曖昧性 | 2 | `mehta2017`, `vnect` |
| §2.4 骨格制約モデル | 2 | `poseformer`, `motionbert` |
| **合計（新規）** | **8** | — |
| 既存文献（変更なし） | 7 | `mediapipe`, `mediapipe_coord_issue`, `blazepose`, `unity`, `h36m`, `coco`, `openpose` |
| **参考文献総数** | **15** | — |

---

## §2.1 — MediaPipe and BlazePose Accuracy

### \bibitem{mroz2021} — Mroz et al., BioSMART 2021

| 項目 | 内容 |
|---|---|
| **タイトル** | Comparing the Quality of Human Pose Estimation with BlazePose or OpenPose |
| **著者** | Sarah Mroz, N. Baddour, Connor McGuirk, P. Juneau, Albert Tu, Kevin Cheung, E. Lemaire |
| **発表先** | 4th International Conference on Bio-Engineering for Smart Technologies (BioSMART), IEEE, 2021 |
| **DOI** | 10.1109/BioSMART54244.2021.9677850 |
| **IEEE Xplore ID** | 9677850 |

#### 主要な発見・数値

- **BlazePose 精度**: PCK = 0.77（高性能ワークステーション）、PCK = 0.72（一般PC）
- **OpenPose 精度**: PCK = 0.83（高性能ワークステーション）、PCK = 0.81（一般PC）
- **BlazePose 速度**: 0.0075 s/フレーム（高性能ワークステーション）→ OpenPose の 0.107 s/フレームと比較して **約14倍高速**
- **一般PC**: BlazePose 0.022 s vs OpenPose 0.293 s

#### 結論・示唆

- BlazePose はリアルタイム性が必要なアプリケーション（スポーツ分析、モバイル）に適する
- OpenPose は精度では優位だが計算コストが高い
- この比較はスポーツ動作（バスケットボール）データセットで実施されており、多視点評価は含まれない

#### 本研究との関連

- 本研究が多視点評価という独立した軸で貢献することを正当化する文献
- 「精度・速度トレードオフは既知だが、多視点精度は未評価」というギャップの根拠

#### 本文での引用箇所

```tex
Mroz~et~al.~\cite{mroz2021} compared BlazePose with
OpenPose~\cite{openpose} on a standardised benchmark and found BlazePose to
be substantially faster (0.008\,s vs.\ 0.107\,s per frame on the same
hardware) at the cost of slightly lower accuracy (PCK 0.77 vs.\ 0.83).
```

---

## §2.2 — Simulation-Based Ground Truth Collection

### \bibitem{surreal} — Varol et al., CVPR 2017

| 項目 | 内容 |
|---|---|
| **タイトル** | Learning from Synthetic Humans |
| **著者** | Gul Varol, Javier Romero, Xavier Martin, Naureen Mahmood, Michael J. Black, Ivan Laptev, Cordelia Schmid |
| **発表先** | IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2017, pp. 109–117 |
| **arXiv** | 1701.01370 |
| **プロジェクトページ** | https://www.di.ens.fr/willow/research/surreal/ |

#### 主要な発見・数値

- **データ規模**: 6,500,000 フレーム以上の合成画像（3Dモーションキャプチャデータから生成）
- **使用ボディモデル**: SMPL（Skinned Multi-Person Linear Model）
- **アノテーション**: 2D/3D ポーズ・深度マップ・セグメンテーションマスク・オプティカルフロー・表面法線
- **転移学習の効果**: SURREAL で事前学習したモデルは Human3.6M・YouTube Pose などの実画像でも有効

#### 方法論の特徴

- MoSh手法でモーションキャプチャマーカーデータからSMPLパラメータを推定
- フォトリアリスティックなレンダリングで多様な外見・視点・ポーズを生成
- 手動アノテーションなしで大規模な教師あり学習データを提供

#### 本研究との関連

- 「合成環境でGTを収集する」というアプローチの先行事例として直接的に関連
- Unity環境で完全なGTを取得する本研究の正当性を裏付ける
- ただし SURREAL は視点サンプリングを系統的には行っておらず、本研究の視点網羅性は独自の貢献

#### 本文での引用箇所

```tex
Varol~et~al.~\cite{surreal} introduced SURREAL, rendering over 6~million
photo-realistic frames of SMPL-body avatars with perfect 2-D/3-D pose,
depth, and segmentation labels; models pre-trained on SURREAL transfer
effectively to real-world benchmarks including Human3.6M~\cite{h36m}.
```

---

### \bibitem{agora} — Patel et al., CVPR 2021

| 項目 | 内容 |
|---|---|
| **タイトル** | AGORA: Avatars in Geography Optimized for Regression Analysis |
| **著者** | Priyanka Patel, Chun-Hao P. Huang, Joachim Tesch, David T. Hoffmann, Shashank Tripathi, Michael J. Black |
| **発表先** | IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2021 |
| **arXiv** | 2104.14643 |
| **プロジェクトページ** | https://agora.is.tue.mpg.de/ |

#### 主要な発見・数値

- **データ規模**: 約14,000枚の訓練画像・約3,000枚のテスト画像、1画像あたり5〜15人
- **個人クロップ数**: 173,000件以上
- **ボディモデル**: SMPL-X（顔・手の表現を含む拡張モデル）
- **身体スキャン**: 4,240体の高品質テクスチャ付きスキャン（257体の子供を含む）

#### 方法論の特徴

- 自然な屋外環境（3Dレンダリング環境 or HDRIライティング）に人体スキャンを合成
- 子供の体型にSMPL-Xモデルを拡張（既存手法のほとんどが子供で精度が低いことを発見）
- AGORAで微調整すると3DPWベンチマーク性能も向上（ドメイン転移確認）

#### 本研究との関連

- 多様な人物・環境条件での合成GT収集の最先端事例
- 本研究との違い：AGORAは身体形状の多様性が焦点、本研究は **カメラ視点の系統的サンプリング** が焦点

#### 本文での引用箇所

```tex
Patel~et~al.~\cite{agora} extended this paradigm with AGORA, compositing
4,240 high-quality textured body scans into natural outdoor environments
and demonstrating that training on realistic synthetic data improves
regression performance on the 3DPW benchmark.
```

---

### \bibitem{peoplesanspeople} — Ebadi et al., arXiv 2021

| 項目 | 内容 |
|---|---|
| **タイトル** | PeopleSansPeople: A Synthetic Data Generator for Human-Centric Computer Vision |
| **著者** | Salehe Erfanian Ebadi et al.（Unity Technologies） |
| **発表先** | arXiv:2112.09290 (2021年12月提出)；拡張版 PSP-HDRI+ は ICML 2022 Workshop に採択 |
| **リポジトリ** | https://github.com/Unity-Technologies/PeopleSansPeople |
| **プロジェクトページ** | https://unity-technologies.github.io/PeopleSansPeople/ |

#### 主要な発見・数値

- **生成データ形式**: COCO形式のキーポイントラベル・2D/3Dバウンディングボックス・インスタンス/意味的セグメンテーション
- **事前学習 → 微調整の効果（少データ体制）**: KeypointAP = 60.37 ± 0.48（実データのみ 55.80 AP、ImageNet事前学習 57.50 AP を上回る）
- **豊富データ体制**: 63.47 ± 0.19 AP（実データのみ 62.00 AP を上回る）
- **Unity 使用**: ドメインランダム化機能あり、macOS/Linux バイナリで利用可能

#### 方法論の特徴

- **ゲームエンジン活用**: Unity のシミュレーション環境でライティング・カメラ・人物ポーズを完全制御
- **プライバシー保護**: 実際の人物データなしで人間中心の学習データを生成
- 本研究と同じ Unity を用いて 合成データを収集する事例

#### 本研究との関連

- **最も直接的な先行事例**: 同じUnityエンジンでキーポイントGTを生成
- 本研究との違い：PeopleSansPeopleは訓練データ生成が目的、本研究は **既存モデル（MediaPipe）の評価** が目的
- Unity + 系統的カメラ配置という本研究のアーキテクチャの先例を提供

#### 本文での引用箇所

```tex
Ebadi~et~al.~\cite{peoplesanspeople} released PeopleSansPeople, a
Unity-based synthetic data generator that produces COCO-format keypoint
annotations; pre-training on PeopleSansPeople data and fine-tuning on real
COCO images achieves keypoint AP of 63.5, surpassing a real-data-only
baseline of 62.0~AP in the high-data regime.
```

---

## §2.3 — Monocular 3D Pose Estimation and Depth Ambiguity

### \bibitem{mehta2017} — Mehta et al., 3DV 2017

| 項目 | 内容 |
|---|---|
| **タイトル** | Monocular 3D Human Pose Estimation in the Wild Using Improved CNN Supervision |
| **著者** | Dushyant Mehta, Helge Rhodin, Dan Casas, Pascal Fua, Oleksandr Sotnychenko, Weipeng Xu, Christian Theobalt |
| **発表先** | 5th International Conference on 3D Vision (3DV), IEEE, 2017, pp. 506–516 |
| **DOI** | 10.1109/3DV.2017.00064 |
| **arXiv** | 1611.09813 |
| **所属** | Max Planck Institute for Informatics (GVV Group), EPFL, Universidad Rey Juan Carlos |

#### 主要な発見・数値

- **MPI-INF-3DHP データセット** を導入: 8俳優 × 8活動 × 14カメラ視点、130万フレーム以上
  - 屋内スタジオ + 屋外環境を含む（Human3.6Mは屋内のみ）
  - 多様な服装・オクルージョンを含む
- **転移学習手法**: 2Dポーズデータセット（MPII）と3Dデータセット（Human3.6M）を同時学習
- **汎化性能**: in-the-wild 動画でも有効な推定が可能

#### 方法論の特徴

- CNN でヒートマップと3D座標を同時回帰
- 2Dアノテーションのみのデータセットから3D学習へ転移
- コミュニティ動画・低品質カメラへの適用を実証

#### 深度曖昧性の問題

- 単眼カメラからの3D復元は本質的に不良設定問題（1つの2D投影に複数の3D配置が対応）
- 訓練データの視点偏り（正面偏重）が非正面視点での汎化を妨げる
- この問題が本研究のΔψ大誤差（カメラ正面以外での精度低下）の理論的背景

#### 本研究との関連

- 単眼深度推定の固有限界・訓練データ視点偏りを議論する文献
- 本研究で観察した「Y=2.0（俯瞰）でのMAE増加」「エルボーΔθ約58°の残留誤差」の先行理論

#### 本文での引用箇所

```tex
Mehta~et~al.~\cite{mehta2017} improved generalisation to in-the-wild scenes
through multi-dataset transfer learning and introduced the MPI-INF-3DHP
benchmark, which includes greater viewpoint diversity than
Human3.6M~\cite{h36m}; nevertheless, lateral and overhead perspectives
remain under-represented in standard training corpora.
```

---

### \bibitem{vnect} — Mehta et al., SIGGRAPH 2017

| 項目 | 内容 |
|---|---|
| **タイトル** | VNect: Real-time 3D Human Pose Estimation with a Single RGB Camera |
| **著者** | Dushyant Mehta et al.（Max Planck Institute for Informatics） |
| **発表先** | ACM Transactions on Graphics (SIGGRAPH), vol. 36, no. 4, pp. 44:1–44:14, 2017 |
| **プロジェクトページ** | https://vcai.mpi-inf.mpg.de/projects/VNect/ |
| **arXiv** | 1705.01583 |

#### 主要な発見・数値

- **初のリアルタイム単眼3Dポーズ推定**（GPU不要の設定でも動作）
- CNNによる2D/3D関節位置の同時回帰 + キネマティックスケルトンフィッティング
- アウトドアシーン・コミュニティ動画・低品質カメラで動作実証

#### 骨格制約の観点

- **キネマティックスケルトンフィッティング**: ボーン長制約・時間的安定性を強制
- ペルビスを含む関節ツリーにIKベースのフィッティングを適用
- 本研究で指摘する「骨盤剛体制約の欠如」問題を部分的に扱う先行事例

#### 本研究との関連

- 骨格制約（ボーン長一貫性）による3D推定の安定化という文脈で引用
- MediaPipe の制約なしアーキテクチャとの対比材料

#### 本文での引用箇所（§2.4）

```tex
Mehta~et~al.~\cite{vnect} demonstrated real-time monocular 3-D pose
estimation with a kinematic skeleton fitting stage that enforces
bone-length consistency and temporal stability across frames.
```

---

## §2.4 — Skeletal Constraint Models

### \bibitem{poseformer} — Zheng et al., ICCV 2021

| 項目 | 内容 |
|---|---|
| **タイトル** | 3D Human Pose Estimation with Spatial and Temporal Transformers |
| **著者** | Ce Zheng, Sijie Zhu, Matias Mendieta, Taojiannan Yang, Chen Chen, Zhengming Ding |
| **発表先** | IEEE/CVF International Conference on Computer Vision (ICCV), 2021, pp. 11656–11666 |
| **arXiv** | 2103.10455 |
| **GitHub** | https://github.com/zczcwh/PoseFormer |

#### 主要な発見・数値

- **Human3.6M**: 81フレーム入力で MPJPE = **44.3mm**（当時の最先端）
- **MPI-INF-3DHP**: 複数メトリクスで高性能
- CNN を一切使用しない純粋なTransformer構造

#### アーキテクチャ

- **Spatial Transformer**: 各フレーム内の17関節間の局所的な関係をモデル化
- **Temporal Transformer**: フレーム間の長距離依存を制約なく捉える（RNNのように時間窓制限なし）
- 動画中央フレームの3Dポーズを出力

#### 骨格制約の観点

- Spatialアテンションが関節間の解剖学的関係を暗黙的に学習
- 明示的なボーン長拘束やペルビス剛体制約は組み込まれていない
- 本研究で指摘する「骨盤剛体拘束の欠如」はPoseFormerも同様に抱える課題

#### 本研究との関連

- 現在の3D姿勢推定SoTAを示す文献として引用
- 「それでも骨盤剛体制約は明示的に組み込まれていない」という議論の根拠

#### 本文での引用箇所

```tex
PoseFormer~\cite{poseformer} is a purely transformer-based video pose
estimator that captures long-range spatio-temporal joint relations without
convolutional layers, achieving 44.3\,mm MPJPE on Human3.6M.
```

---

### \bibitem{motionbert} — Zhu et al., ICCV 2023

| 項目 | 内容 |
|---|---|
| **タイトル** | MotionBERT: A Unified Perspective on Learning Human Motion Representations |
| **著者** | Wentao Zhu et al.（Peking University 等） |
| **発表先** | IEEE/CVF International Conference on Computer Vision (ICCV), 2023 |
| **arXiv** | 2210.06551 |
| **プロジェクトページ** | https://motionbert.github.io/ |

#### 主要な発見・数値

- **Human3.6M**: MPJPE = **39.2mm**（2023年時点での最先端水準）
- スクラッチから学習した場合でも最高水準を達成
- ダウンストリームタスク（ポーズ推定・行動認識・メッシュ復元）への汎化

#### アーキテクチャ

- **DSTformer (Dual-stream Spatio-temporal Transformer)**: 空間・時間の長距離関係を包括的にモデル化
- **事前学習パラダイム**: ノイズのある2D観測から3Dモーションを復元するタスクで事前学習
- 幾何学的・運動学的・物理的な事前知識を表現に組み込む

#### 骨格制約の観点

- 運動学的・物理的事前知識を学習ベースで組み込む
- 明示的なペルビス剛体制約はやはり組み込まれていない
- 「暗黙的な物理制約で一部対処できるが、明示的な骨盤制約がより効果的」という議論の裏付け

#### 本研究との関連

- 最新のSoTAモデルを引用することで、骨盤剛体制約が未解決課題であることを示す
- 本研究の「Future Work: ペルビス剛体制約」提案の妥当性を支持

#### 本文での引用箇所

```tex
MotionBERT~\cite{motionbert} pre-trains a Dual-stream Spatio-temporal
Transformer to recover 3-D motion from noisy 2-D observations, embedding
geometric and physical priors that generalise to mesh recovery and action
recognition, achieving 39.2\,mm MPJPE on Human3.6M.
```

---

## main.tex への反映状況

| `\bibitem` キー | 追加済み | 使用セクション |
|---|---|---|
| `mroz2021` | ✓ | §2.1 |
| `surreal` | ✓ | §2.2 |
| `agora` | ✓ | §2.2 |
| `peoplesanspeople` | ✓ | §2.2 |
| `mehta2017` | ✓ | §2.3 |
| `vnect` | ✓ | §2.4 |
| `poseformer` | ✓ | §2.4 |
| `motionbert` | ✓ | §2.4 |

**参考文献総数**: 15件（既存7件 + 新規8件）

---

## 今後の課題（参考文献関連）

1. **mroz2021 の詳細確認**: IEEE Xplore でフルテキストアクセスし、具体的なベンチマーク詳細・データセット名を確認
2. **agora のページ番号追記**: CVPR 2021 の正確なページ番号が未確認（`in \textit{Proc. CVPR}, 2021.` のまま）
3. **vnect の著者リスト補完**: 現在 `D.~Mehta et al.` と略記 → フル著者リストへの展開を検討
4. **motionbert のページ番号**: ICCV 2023 の正確なページ番号が未確認
5. **mediapipe_coord_issue**: GitHub Issue は一般的に査読論文では引用不可の場合がある → ジャーナル投稿時に脚注化を検討

---

## 参考: 検討したが採用しなかった文献

| 文献 | 検討理由 | 不採用理由 |
|---|---|---|
| Kocabas et al. (VIBE, CVPR 2020) | MediaPipe の independent evaluation | 実際にはMediaPipe評価論文ではない（video pose estimation） |
| Frontiers in Rehabilitation Sciences 2023 (gait analysis) | MediaPipeを臨床で評価した事例 | 著者情報確認に追加調査が必要で今回はスコープ外 |
| SURREAL 拡張版 / Synthetic4Humans | §2.2 の強化 | 既に3本(SURREAL/AGORA/PSP)で十分と判断 |
