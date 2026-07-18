# カメラ位置と関節位置誤差の関連分析（Error · MC）

目的: **カメラ位置と関節位置の検出誤差の関連性を明らかにする**。

本メモは、腰原点の相対座標における誤差ベクトル \(Error\) と、腰→カメラ方向 \(MC\) の内積を用いる解析案をまとめる。あわせて、**現在リポジトリにある MediaPipe / GT データとの整合性・不足点**を明示する。

---

## 1. 記号定義

ある関節を \(n\) とする。

| 記号 | 意味 |
|------|------|
| \(GT_{uni}\) | 関節 \(n\) の Ground Truth（腰を原点とした相対座標） |
| \(MD_{uni}\) | 関節 \(n\) の MediaPipe（腰を原点とした相対座標） |
| \(M\) | GT における腰（ヒップ中心）のワールド座標（相対化の原点） |
| \(C\) | カメラ位置のワールド座標 |
| \(GT^{(n)}\) | 関節 \(n\) の GT ワールド座標 |
| \(MC_n = C - GT^{(n)}\) | **関節 \(n\) からカメラへ向かうベクトル**（\|MC\| は関節ごとに異なる） |

誤差ベクトル（腰相対）:

\[
Error = MD_{uni} - GT_{uni}
\]

判定指標:

\[
\cos\phi_n = \frac{Error \cdot MC_n}{\|Error\|\,\|MC_n\|}
\]

解釈の目安: **\(\cos\phi\) が 0 に近い**（\(Error \perp MC_n\)）ほど、誤差は当該関節への視線方向ではなく横方向に載っており、視点・カメラ配置の影響を議論しやすい。

> 注: 初期メモの \(MC = C - M\)（腰基準）だと \|MC\| が全関節で同一になる。実装では **関節基準** \(MC_n = C - GT^{(n)}\) を用いる。

---

## 2. 相対座標とは何か

### 2.1 ねらい

絶対位置（シーン内のどこに立っているか）を消し、**身体ローカルな関節配置**だけを残す。

腰中心 \(H\) を原点にした相対座標:

\[
p' = p - H
\]

- GT: \(H = M\)（例: `Hips`、または左右股関節の中点）
- MP: \(H =\) 左右 `LEFT_HIP` / `RIGHT_HIP` の中点（本プロジェクトの方向角解析と同じ）

こうすると \(GT_{uni}\)、\(MD_{uni}\) は「腰から見た関節の向き・相対位置」になり、平行移動の差を除去できる。

### 2.2 相対化で消えるもの / 残るもの

| | 説明 |
|--|------|
| 消える | ワールド原点の取り方、キャラクターの並進 |
| 残る | 回転（体の向き）、スケール、軸の向きの不一致、関節定義の差 |

したがって **腰相対にしただけでは、MediaPipe と Unity GT はまだ同じ空間とは限らない**。引き算 \(MD_{uni}-GT_{uni}\) を正当化するには、追加の軸合わせ・スケール合わせが必要（後述）。

### 2.3 \(MC_n\) の意味（視線方向）

実装・ダッシュボードでは関節ごとの

\[
MC_n = C - GT^{(n)}
\]

を用いる（§1）。単眼推定で不安定になりやすい **視線（奥行き）方向**の代理である。

正規化指標:

\[
\cos\phi_n = \frac{Error \cdot MC_n}{\|Error\|\,\|MC_n\|}
\]

> **歩行方向 \(D\)** に基づくノイズ除去（移動平均）は別ドキュメント  
> [`MOVING_AVERAGE_NOISE_REJECTION.md`](MOVING_AVERAGE_NOISE_REJECTION.md) を参照。\(D\) と \(MC_n\) は混同しないこと。

- \(\cos\phi \approx \pm 1\): 誤差が視線に沿う（奥行き型）
- \(\cos\phi \approx 0\): 誤差が視線に直交（画像面にほぼ平行な横ずれ型）

---

## 3. 幾何的解釈（なぜ内積を見るか）

単眼 Pose では、カメラ視線方向の深度が最も不定になりやすい。

- \(Error \parallel MC\)（内積の絶対値が大きい）  
  → 奥行き方向のずれが支配的、という読み
- \(Error \perp MC\)（内積 ≈ 0）  
  → ずれは視線に直交。左右反転・関節取り違え・視点依存の横バイアスなど、**カメラ配置と結びつけて議論しやすい成分**

ただし「内積が 0 に近い ⇒ カメラが原因」と一対一には断定できない。  
モデル誤差・Unity bone と BlazePose landmark の定義差でも直交成分は出る。  
実務では **カメラ方位ビンごとに \(\cos\phi\) や \(Error\cdot MC\) の分布を比較**する。

---

## 4. 現データとの整合性

### 4.1 データソース（v2）

| 種別 | パス | 中身 |
|------|------|------|
| 動画 | `01_input_videos/CapturedFrames_*/video.mp4` | 1280×720 など |
| GT | `01_input_videos/CapturedFrames_*/gt_joints.csv` | Unity `HumanBodyBones` ワールド座標 [m] |
| MediaPipe | `02_mediapipe_v2/mediapipe_processed_csv/Y=*/CapturedFrames_*.csv` | `pose_landmarks`（正規化画像座標） |
| カメラ位置 | フォルダ名 `CapturedFrames_{X}_{Y}_{Z}` | \(C = (X,Y,Z)\) [m]（Unity ワールド想定） |

### 4.2 座標系の現状

| | Ground Truth | MediaPipe（保存済み CSV） |
|--|--|--|
| 空間 | Unity ワールド（左手系・Y-up・メートル） | 画像・カメラ相対（x,y ∈ [0,1]、z は相対深度） |
| Y 軸 | 上向き正 | 下向き正 |
| 原点 | シーン原点（腰相対化前） | 画像左上（腰相対化前） |
| 本解析での腰相対 | \(GT_{uni} = p_{GT} - M\) で定義可能 | 左右 HIP 中点で相対化は可能だが、**単位・軸が GT と不一致** |

**重要:** 現行 CSV は `pose_world_landmarks` ではなく `pose_landmarks` のみ。  
そのため「腰相対にした MP」と「腰相対にした GT」をそのまま引いて \(Error\) を作ることは、**現状データだけでは厳密にはできない**。

### 4.3 既存パイプラインとの関係

| 解析 | 座標の扱い | 本メモ（Error·MC）との関係 |
|------|------------|---------------------------|
| 関節角度 MAE（`03_joint_angle_mae`） | 各系で独立に 3 点角 → 角度差のみ比較。位置の共通化なし | 位置誤差ベクトルは使っていない（矛盾ではないが別指標） |
| 方向角（`05_direction_detection`） | 腰相対 + **MP の Y 反転**のうえ \(\theta,\psi\) を比較 | 相対化・Y 合わせの思想は近いが、\(Error\) ベクトルや \(MC\) 内積は未実装 |
| キャリブレーション（`09_calibration_framework`） | 主に角度バイアス・方位ビン | 本メモは位置ベクトル指標の追加案 |

方向角用変換の実装箇所:

- `05_direction_detection/scripts/coordinate_transform.py`  
  - `transform_ground_truth`: 腰中心相対化  
  - `transform_mediapipe`: 腰中心相対化 + **Y 反転**

これは「角度比較用の最低限の軸合わせ」であり、**メートル空間での \(MD_{uni}-GT_{uni}\)** を保証するものではない。

### 4.4 整合している点 / していない点

**整合している**

- カメラ位置 \(C\) はフォルダ名から取得できる（既存評価と同じ）
- GT の \(M\)（腰）と関節ワールド座標は `gt_joints.csv` から取れる
- 「腰を原点にした相対座標」という発想は `05_direction_detection` と一致
- フレーム対応は v2 で `frame_id` 同期を前提にできる（v1 の約 3 フレームずれ問題は別途注意）

**整合していない / 不足**

1. **共通メートル空間がない**  
   MP が正規化画像座標のままでは \(Error = MD_{uni}-GT_{uni}\) が定義できない。
2. **\(MC\) と \(Error\) を同じ基底で書けない**  
   \(MC\) は Unity ワールド [m]、現行の MP 相対座標は画像正規化系。
3. **関節名の対応**は解剖学マッピングが必要（既存の肘・膝などの対応表を流用可能）。  
   GT の単一 `Hips` と MP の左右 HIP 中点の差にも注意。
4. **スケール**  
   たとえ Y を反転しても、MP の正規化長と GT のメートル長は一致しない。骨長正規化等が別途必要。

---

## 5. 本解析を現データで実施するための条件

\(Error \cdot MC\) を正当に計算するには、次のいずれかが必要。

### 案 A（推奨・厳密）: カメラ座標系で揃える

1. Unity のカメラ外部パラメータ（位置 \(C\)・姿勢）と内部パラメータで、GT 関節をカメラ座標へ変換  
2. MediaPipe は `pose_world_landmarks`（腰中心・メートル・カメラ系）を使うか、同等の 3D を取得  
3. 双方を腰相対化し \(Error\)、同じ系の \(MC\)（またはカメラ前方ベクトル）と内積

現状: **カメラ姿勢の数値・`pose_world_landmarks` 保存は未整備**。

### 案 B（近似）: 既存 CSV のまま方向成分だけ見る

1. `05` と同様に腰相対 + MP Y 反転  
2. 骨長などでスケールを仮合わせ  
3. \(MC\) も Unity 水平成分などで近似  

→ 実装は早いが、\(Error\) の定量値は近似。論文の主結果にするには弱い。

### 案 C: 位置ではなく既存角度指標との相関で代替

カメラ方位ビン × 角度 MAE / signed bias は既に計算済み。  
「カメラ配置と誤差」の議論は、厳密な \(Error\cdot MC\) の前段階としてこちらで可能な部分がある。

---

## 6. 実装・実行結果（案 B・既存 MP v2 データ）

スクリプト:

```bash
python 02_mediapipe_v2/run_error_mc_analysis.py
# テスト: python 02_mediapipe_v2/run_error_mc_analysis.py --max_cameras 5
```

処理内容（案 B）:

1. `mediapipe_processed_csv` + `gt_joints.csv` の共通 `frame_id`
2. 腰中心相対化、MP の Y 反転、肩–腰距離でスケール合わせ
3. \(MC_n = C - GT^{(n)}\)（カメラ − 関節 \(n\) の GT ワールド位置）
4. \(\cos\phi_n = (Error\cdot MC_n)/(|Error||MC_n|)\)（\|MC\|・cos は関節ごと）

出力ディレクトリ: `02_mediapipe_v2/error_mc_analysis/results/`

| ファイル | 内容 |
|----------|------|
| `error_mc_frame_joint.csv` | フレーム×関節の詳細（約 21 万行） |
| `error_mc_by_camera_joint.csv` | カメラ×関節の平均 |
| `error_mc_by_azimuth_joint.csv` | 高さ層×方位ビン×関節 |
| `error_mc_by_joint_overall.csv` | 関節全体集計 |
| `error_mc_abs_cos_heatmap.png` | 関節×方位の mean \|cos φ\| |
| `SUMMARY.md` | 実行サマリ |

初回フル実行（576 カメラ）の目安:

- mean \|cos φ\| ≈ 0.54（中央値 ≈ 0.55）
- \|cos φ\| < 0.3 の割合は関節ごとに `SUMMARY.md` / `error_mc_by_joint_overall.csv` を参照

※ 案 B は近似のため、厳密なカメラ座標系（案 A）ではない。

---

## 7. まとめ

| 項目 | 内容 |
|------|------|
| 正しい指標 | \(Error \cdot MC\)（\(Error \cdot MD_{uni}\) ではない） |
| 相対座標 | 腰を原点に並進を除去。回転・スケール・軸定義は別途揃えが必要 |
| 現データ | GT と \(C\) はワールドで揃う。MP は画像正規化座標のため **そのままでは Error を定義不可** |
| 既存コード | 角度 MAE は位置非対応。方向角は腰相対+Y反転。**Error·MC は案 B で実装済み** |
| 次の一手 | 厳密化には `pose_world_landmarks` またはカメラ投影（案 A）。歩行直交ノイズ除去は下記 |
| 関連（設計） | 進行方向直交成分の移動平均除去: [`MOVING_AVERAGE_NOISE_REJECTION.md`](MOVING_AVERAGE_NOISE_REJECTION.md) |

---

## 8. 関連ファイル

- 本解析スクリプト: `02_mediapipe_v2/run_error_mc_analysis.py`
- 出力: `02_mediapipe_v2/error_mc_analysis/results/`
- 移動平均ノイズ除去（設計）: [`MOVING_AVERAGE_NOISE_REJECTION.md`](MOVING_AVERAGE_NOISE_REJECTION.md)
- GT / 同期: `docs/UNITY_VIDEO_CAPTURE_PROMPT.md`, `docs/SYNC_ISSUE_REPORT.md`
- MP 座標系: `06_theta_verification/MEDIAPIPE_COORDINATE_SYSTEM.md`
- 腰相対 + Y 反転: `05_direction_detection/scripts/coordinate_transform.py`
- 関節 3 点角（位置非対応）: `03_joint_angle_mae/coordinate_angle_comparison.py`
- MP 検出 CSV: `02_mediapipe_v2/mediapipe_processed_csv/`
- GT CSV: `01_input_videos/CapturedFrames_*/gt_joints.csv`
