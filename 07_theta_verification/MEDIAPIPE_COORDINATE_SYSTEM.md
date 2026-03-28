# MediaPipe Pose 座標系の公式仕様と検証

本ドキュメントは、MediaPipe Pose の world_landmarks が出力する3D座標系について、公式情報と検証結果をまとめる。

---

## 0. GT と MediaPipe の座標系対照表（本研究で使用するデータ）

### Unity Ground Truth（synced_joint_positions.csv）

| 項目 | 内容 |
|------|------|
| 座標系 | Unity ワールド座標（左手系・Y-up） |
| 単位 | メートル |
| X 軸 | 右向きが正 |
| Y 軸 | **上向きが正**（頭方向） |
| Z 軸 | 前向きが正 |
| 原点 | 処理時に腰中心へ変換 |

### MediaPipe pose_landmarks（02_mediapipe_processed/*.csv）

| 項目 | 内容 |
|------|------|
| 座標系 | 画像・カメラ座標系（カメラごとに異なる） |
| 単位 | 正規化（x,y: 0〜1、z: 相対深度） |
| X 軸 | 画像の横方向（右向きが正） |
| Y 軸 | **画像の縦方向（下向きが正、上=0・下=1）** |
| Z 軸 | 奥行き（腰中心基準、小さい=カメラ寄り） |
| 原点 | 処理時に腰中心へ変換 |

### 主な相違点（角度計算への影響）

| 相違 | 影響 |
|------|------|
| **Y 軸の向きが逆**（GT: 上向き正、MP: 下向き正） | θ = arctan2(y,x) で θ_mp ≈ -θ_gt となり、Δθ が系統的に大きくなる（例: θ_gt=60° のとき Δθ≈-120°） |
| 座標系がカメラ依存（MP） vs ワールド固定（GT） | カメラごとに MediaPipe の軸の向きが変わるため、複数カメラで平均すると座標系差が誤差に含まれる |
| 尺度の違い（m vs 正規化） | 角度計算には影響しない（arctan2 は比のみに依存） |

---

## 1. 公式ドキュメントの記述

### 公式ガイド（Python / ai.google.dev）

- **WorldLandmarks**: メートル単位の実世界3D座標
- **原点**: 腰（hips）の中点
- **軸の向き**: **記載なし**

### レガシー Pose ガイド（google.github.io/mediapipe）

- 同様に「腰中心の実世界3D座標（メートル）」のみ記載
- 軸の向き（X/Y/Z がどちら向きか）は**明記されていない**

---

## 2. GitHub Issue #3370

**URL**: https://github.com/google/mediapipe/issues/3370

> "The documentation only describes the origin of the coordinate system. **I'm wondering what's the orientation?**"

- 2022年5月に報告
- 座標系の向きがドキュメントにない旨の指摘
- 現時点でも公式ドキュメントには未追記

---

## 3. BlazePose GHUM Holistic 論文（2022）

**出典**: BlazePose GHUM Holistic: Real-time 3D Human Landmarks and Pose Estimation (arXiv:2206.11678)

> "The BlazePose GHUM Holistic network outputs 33 body landmarks, and 21 landmarks for each hand, **in a root-centered 3D camera coordinate system**."

- **root-centered**: 原点は腰（root）
- **camera coordinate system**: 座標系の向きは**カメラ依存**
- カメラが変われば、同じ関節でも座標系の軸の向きが変わる

---

## 4. 軸の向き（文献・コミュニティ情報）

公式ドキュメント外の情報による概説：

| 軸 | 向き | 備考 |
|----|------|------|
| X | 左右 | 画像平面の横方向 |
| Y | 上下 | 画像平面の縦方向 |
| Z | 奥行き | 負 = カメラ寄り、正 = カメラの奥側 |

※ これらはカメラごとに回転するため、ワールド座標系とは一致しない。

---

## 5. 本研究への示唆

- MediaPipe の出力は**カメラ座標系**である
- 本研究では複数カメラ（約505種類）から得た MediaPipe 座標をそのまま比較している
- カメラごとに座標系が回転するため、複数カメラの θ / ψ をそのまま平均すると、**座標系の差が誤差に含まれる**
- 肘の約 ±121° の Δθ は、MediaPipe の推定誤差というより、**座標系ミスマッチの寄与が大きい**可能性が高い

### 今後の検証・対策

- カメラ外パラメータを用いて MediaPipe 座標を Unity ワールド座標系に変換してから Δθ / Δψ を再計算する
- または、同一カメラ内でのみ比較し、カメラ間の平均は行わない設計とする

---

## 6. 参考リンク

- [Pose landmark detection guide (Python)](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python)
- [Pose landmark detection guide (Overview)](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- [Legacy MediaPipe Pose](https://google.github.io/mediapipe/solutions/pose.html)
- [GitHub Issue #3370: Orientation of pose world landmarks](https://github.com/google/mediapipe/issues/3370)
- [BlazePose GHUM Holistic (arXiv:2206.11678)](https://arxiv.org/abs/2206.11678)
