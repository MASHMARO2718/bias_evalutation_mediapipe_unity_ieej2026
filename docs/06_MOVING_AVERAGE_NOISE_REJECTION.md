# 移動平均によるノイズ除去（進行方向直交成分）

目的: 被験者の**直線歩行**を前提に、検出誤差のうち進行方向に直交する成分をノイズとみなし、**移動平均から大きく外れたフレームを排除**してノイズを小さくする。

本ドキュメントは [`CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](CAMERA_JOINT_ERROR_MC_ANALYSIS.md)（Error · MC / \(\cos\phi\) 解析）と記号・前提を揃える。  
**歩行方向に基づく時間方向フィルタ**であり、カメラ視線方向解析（\(MC_n\)）とは役割が異なる（後述の対応表を参照）。

> 状態: **実装済み**（案 B 座標）。  
> スクリプト: `02_mediapipe_v2/run_ma_noise_rejection.py`  
> 結果: `02_mediapipe_v2/ma_noise_rejection/results/`  
> ダッシュボード: `09_calibration_framework/dashboard` → **MA Noise** タブ

---

## 1. 前提

| 項目 | 内容 |
|------|------|
| 動作 | 被験者は初期位置から終端位置まで **ワールド空間で直線歩行** |
| カメラ | 位置 \(c^{\mathrm{world}}\) は **固定**（本プロジェクトの各 `CapturedFrames_{X}_{Y}_{Z}` 内では一定） |
| フレーム | 時刻インデックスを \(n\) とする（動画 `frame_id` と対応） |
| 真値 | Unity GT ワールド座標（`gt_joints.csv`）を \(m_n^{\mathrm{world}}\) の参照に使える |
| 推定 | MediaPipe 側の対応点を \(m_n^{\mathrm{MP}}\) と書く（座標系合わせは §5） |

本リポジトリの歩行は、ドキュメント上おおむね \(Z\) 方向の往復に近いが、式では **実測の \(m_0\) と \(m_{\mathrm{final}}\) から \(D\) を定義**する（軸固定に依存しない）。

---

## 2. 記号定義

フレームを \(n\)、注目する基準点（例: 腰中心、または関節 \(j\)）の位置を \(m\) とする。

| 記号 | 意味 |
|------|------|
| \(n\) | フレーム番号（\(n = 0,1,\ldots,N\)） |
| \(m_n^{\mathrm{world}}\) | フレーム \(n\) における被験者（基準点）の **真の** ワールド座標 |
| \(m_0^{\mathrm{world}}\) | 初期位置（歩行開始） |
| \(m_{\mathrm{final}}^{\mathrm{world}}\) | 到達地点（歩行終了） |
| \(c^{\mathrm{world}}\) | カメラ位置（固定）。既存ドキュメントの \(C\) と同じ |
| \(m_n^{\mathrm{MP}}\) | MediaPipe が推定した同基準点の位置（共通座標へ変換後） |

### 2.1 進行方向ベクトル \(D\)

被験者は \(m_0^{\mathrm{world}}\) から \(m_{\mathrm{final}}^{\mathrm{world}}\) へ直線歩行すると仮定する。

\[
D = m_{\mathrm{final}}^{\mathrm{world}} - m_0^{\mathrm{world}}
\]

単位ベクトル:

\[
\hat{D} = \frac{D}{\|D\|} \quad (\|D\| > 0)
\]

\(D\) は **歩行の進行方向**であり、既存のカメラベクトル \(MC_n = C - GT^{(n)}\)（視線方向）とは別物である。

### 2.2 誤差ベクトル \(E_n\)

真の位置 \(m_n^{\mathrm{world}}\) と MediaPipe 位置 \(m_n^{\mathrm{MP}}\) の差を誤差とする。

\[
E_n = m_n^{\mathrm{MP}} - m_n^{\mathrm{world}}
\]

（符号の向きは一貫させればよい。以下では上式を採用。）

メモ中の「直線上の本来の \(m\)」は、ここでは **GT が与える真位置** \(m_n^{\mathrm{world}}\) と解釈する。  
理想直線上への射影 \(\tilde{m}_n\) を真値の代わりに使う変形は §4.3。

### 2.3 進行方向に直交する成分（ノイズベクトル \(\varepsilon_n\)）

\(D\) に直交する平面への正射影をノイズとする（3D では「\(D\) に垂直な1本の \(D_{\perp}\)」ではなく、**平面への射影**が自然）。

\[
\mathrm{proj}_{D}(E_n) = \bigl(E_n \cdot \hat{D}\bigr)\,\hat{D}
\]

\[
\varepsilon_n = E_n - \mathrm{proj}_{D}(E_n)
\quad\text{（すなわち } \varepsilon_n \perp D\text{）}
\]

解釈:

| 成分 | 意味 |
|------|------|
| \(\mathrm{proj}_{D}(E_n)\) | 進行方向に沿ったずれ（前後・歩行位相のずれに近い） |
| \(\varepsilon_n\) | 進行方向に直交するずれ（左右・上下の横ブレ＝**ノイズ候補**） |

スカラー指標として \(\|\varepsilon_n\|\) も用いる。

> メモの「\(D_{\mathrm{orth}}\) への正射影」は、実装上 \(\varepsilon_n = E_n - \mathrm{proj}_D(E_n)\) と同一視する。

---

## 3. 移動平均による外れ値除去

### 3.1 移動平均

窓幅 \(W\)（奇数を推奨、例: \(W=5\) または \(W=7\)）に対し、ノイズの移動平均を

\[
\bar{\varepsilon}_n = \frac{1}{|W_n|} \sum_{k \in W_n} \varepsilon_k
\]

とする。ただし \(W_n = \{\,k \mid \max(0,\, n-w) \le k \le \min(N,\, n+w)\,\},\; W=2w+1\)。  
因果的フィルタにする場合は過去のみ（\(k \le n\)）に制限する。

\(\|\varepsilon_n\|\) に対する移動平均 \(\overline{\|\varepsilon\|}_n\) を使う簡易版も可。

### 3.2 排除ルール

しきい値倍率 \(K > 1\)（例: \(K = 2\) または \(3\)）を定め、

\[
\|\varepsilon_n - \bar{\varepsilon}_n\| \;\;>\;\; K \cdot \sigma_n
\quad\text{または}\quad
\|\varepsilon_n\| \;\;>\;\; K \cdot \overline{\|\varepsilon\|}_n
\]

を満たすフレーム \(n\) を **外れ値（スパイクノイズ）として排除**する。

ここで \(\sigma_n\) は同窓内の \(\|\varepsilon_k - \bar{\varepsilon}_k\|\) または \(\|\varepsilon_k\|\) の標準偏差。

排除後の扱い（実装時に選択）:

1. **マスク**: そのフレームを MAE / \(\cos\phi\) / 時系列平均から除外  
2. **置換**: \(\varepsilon_n \leftarrow \bar{\varepsilon}_n\) として補正位置 \(m_n^{\mathrm{corr}} = m_n^{\mathrm{MP}} - (\varepsilon_n - \bar{\varepsilon}_n)\) を作る（横成分だけ平均に戻す）  
3. **補間**: 前後の有効フレームで \(m^{\mathrm{MP}}\) を線形補間

推奨の第一段は **1. マスク**（評価を歪めにくい）。

### 3.3 処理フロー

```text
m_0, m_final  →  D, D̂
毎フレーム n:
  E_n = m_n^MP − m_n^world
  ε_n = E_n − (E_n · D̂) D̂
移動平均 ε̄_n（窓 W）
|ε_n − ε̄_n| が閾値を大きく上回る → フレーム n を排除（または補正）
残ったフレームで角度 MAE / Error·MC 等を再集計
```

---

## 4. 既存ドキュメント・既存データとの整合性

### 4.1 記号対応表

| 本ドキュメント | [`CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](CAMERA_JOINT_ERROR_MC_ANALYSIS.md) | 備考 |
|----------------|------------------------------------------------------------------------|------|
| フレーム \(n\) | `frame_id` | 関節インデックスではない |
| \(c^{\mathrm{world}}\) | \(C\) | カメラ固定。フォルダ名の \((X,Y,Z)\) |
| \(m_n^{\mathrm{world}}\) | GT ワールド（例: 腰中心 \(M\)、または関節 \(GT^{(j)}\)） | `gt_joints.csv` |
| \(m_n^{\mathrm{MP}}\) | 共通座標へ変換後の MediaPipe 位置 | 生 CSV は画像正規化（案 B 変換が必要） |
| \(E_n\) | 同系の位置誤差（ワールド or 腰相対で定義を固定） | 符号・空間を一貫させる |
| \(D\) | （未定義だった進行方向） | **新規**。歩行軸 |
| \(MC_n = C - GT^{(n)}\) | 視線方向ベクトル | **別用途**（§4.2） |
| \(\cos\phi_n\) | \(E\) と \(MC_n\) の角度関係 | カメラ影響の解析 |
| \(\varepsilon_n\) | \(E\) の進行方向直交成分 | 時間方向ノイズ除去 |

### 4.2 \(D\) と \(MC_n\) を混同しない

| ベクトル | 定義 | 使う解析 |
|----------|------|----------|
| \(D\) | \(m_{\mathrm{final}} - m_0\)（歩行） | 本ドキュメントの \(\varepsilon\)・移動平均 |
| \(MC_n\) | \(C - GT^{(n)}\)（関節→カメラ） | Error·MC / \(\cos\phi\) ダッシュボード |

両方とも「誤差 \(E\) の向き」を議論するが、

- \(MC_n\): **空間（視点）** に対する誤差の分解  
- \(D\): **運動（歩行）** に対する誤差の分解  

であり、併用可能（例: 歩行直交ノイズを除いたうえで \(\cos\phi\) を再計算）。

### 4.3 真位置の取り方（2通り）

**A. GT を真値とする（推奨・現行データと整合）**

\[
m_n^{\mathrm{world}} = \text{GT の腰中心または関節位置}
\]

v2 では `frame_id` 同期済みの `gt_joints.csv` が使える。

**B. 理想直線上の点を真値とする**

直線 \(m_0 + s\,\hat{D}\)（\(s \in [0,\|D\|]\)）へ \(m_n^{\mathrm{GT}}\) または時間比例で射影した \(\tilde{m}_n\) を「本来の位置」とする。  
GT 自体の微小横ブレを真値に含めたくない場合に使う。

### 4.4 MediaPipe 座標（現状の制約）

[`CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](CAMERA_JOINT_ERROR_MC_ANALYSIS.md) と同じく、保存済み CSV は `pose_landmarks`（画像正規化）である。

したがって \(E_n = m_n^{\mathrm{MP}} - m_n^{\mathrm{world}}\) をメートル空間で書くには、従来どおり:

- **案 B**: 腰相対 + Y 反転 + 骨長スケール（近似、実装済み経路あり）  
- **案 A**: `pose_world_landmarks` またはカメラ投影（厳密、未整備）

が必要。移動平均フィルタも **同じ共通空間で定義した \(E_n,\varepsilon_n\)** に対して適用する。

### 4.5 既存パイプラインとの関係

| 既存処理 | 本手法との関係 |
|----------|----------------|
| 関節角度 MAE（`03_joint_angle_mae`） | 位置 \(E\) ではなく角度差。本フィルタ後のフレームマスクを共有可能 |
| Error·MC / \(\cos\phi\)（実装済み） | \(MC_n\) 解析。外れ値マスク後に再集計すると解釈が安定しうる |
| 方向角（`05_direction_detection`） | 腰相対+Y反転を \(m^{\mathrm{MP}}\) 整備に流用可能 |
| キャリブレーション角度補正 | 別系統（角度バイアス）。本手法は **位置系列のスパイク除去** |

---

## 5. 実装時の推奨パラメータ（初期値）

| パラメータ | 初期案 | 説明 |
|------------|--------|------|
| 基準点 \(m\) | 腰中心（左右 HIP 平均） | 歩行軌道が安定。関節ごとにも拡張可 |
| \(m_0, m_{\mathrm{final}}\) | GT 腰の先頭 / 末尾フレーム | または歩行区間の手動指定 |
| 窓 \(W\) | 5 または 7 | 30 fps なら約 0.17–0.23 s |
| 閾値 | \(K=3\)（\(\sigma\) 基準）または \(K=2\)（移動平均倍率） | データで調整 |
| 排除後 | マスク（評価から除外） | 補正置換は第二段 |

出力案:

- `results/ma_noise_reject_mask.csv` — `folder_name, frame_id, keep, ||ε||, ...`
- ダッシュボード: Angle Timeseries / Error·MC に「移動平均除去 ON」トグル

---

## 6. まとめ

1. 直線歩行の進行方向 \(D = m_{\mathrm{final}} - m_0\) を定義する。  
2. 誤差 \(E_n = m_n^{\mathrm{MP}} - m_n^{\mathrm{world}}\) を取る。  
3. \(D\) への平行成分を除いた \(\varepsilon_n\)（直交成分）をノイズとする。  
4. \(\varepsilon_n\)（または \(\|\varepsilon_n\|\)）の移動平均から大きく外れたフレームを排除する。  
5. \(D\)（歩行）と \(MC_n\)（視線）は別ベクトル。既存 Error·MC 解析と矛盾せず併用できる。  
6. 現行 MP CSV では案 B/A の座標揃えが前提（Error·MC ドキュメントと同じ制約）。

---

## 7. 関連ドキュメント

- カメラ–誤差解析: [`CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](CAMERA_JOINT_ERROR_MC_ANALYSIS.md)
- GT / 同期: [`UNITY_VIDEO_CAPTURE_PROMPT.md`](UNITY_VIDEO_CAPTURE_PROMPT.md), [`SYNC_ISSUE_REPORT.md`](SYNC_ISSUE_REPORT.md)
- MP 座標系: `06_theta_verification/MEDIAPIPE_COORDINATE_SYSTEM.md`
- Error·MC 実装: `02_mediapipe_v2/run_error_mc_analysis.py`
- ダッシュボード: `09_calibration_framework/dashboard/app.py`（Error · MC タブ）
