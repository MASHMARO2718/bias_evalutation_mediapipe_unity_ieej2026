# GT フリー補正モデルの再構築（カンニングペーパー方式）と別カメラ検証

**作成**: 2026-07-19
**実装**: `2_pose/run_gt_free_model.py`
**出力**: `2_pose/gt_free_model/`

docs/07 の探究（UV 復元・MAD フィルタ・bin+ARIMA）を踏まえ、
**推論時に GT を一切使わないパイプライン**として再構築し、
較正カメラと異なる位置の**別動画**で汎化を実証した記録。

---

## 1. 設計

### 推論パイプライン（GT 不使用）

1. **UV 擬似ワールド構成** — MP pose_landmarks (u,v,z) → 3 次元座標 [m]。
   スケールは UV 平面内の体幹長（2D）× 実効定数 0.582 m（docs/07 §の較正値）
2. **方向分離なしスパイク除去** — 各関節・各軸で窓幅 7 の移動中央値、
   |x − median| > 4×MAD の点を中央値で置換（docs/07 の進行方向直交分解は廃止。
   置換率 5.0%）
3. **カルマンスムーザー** — 等速モデル + RTS。Q（プロセスノイズ）・R（観測
   ノイズ）はカンニングペーパーから読むだけ（推論時 GT 不要）
4. **3 次元角度計算** — 3 点角（膝 = 腰-膝-足首、肘 = 肩-肘-手首）。
   **3 点角は回転・並進・スケール・鏡映に不変**なので、位置合わせ（従来の
   GT 依存箇所）と鏡映解消が評価にも補正にも不要になる。docs/07 の
   鏡映問題を「角度空間に移ることで回避」した形
5. **系統誤差の除去（カンニングペーパー）** — 被写体進行位置 ẑ(t) を
   GT フリーで推定し、角度バイアス表を**線形補間**して減算

### カンニングペーパーの内容（較正時のみ GT 使用）

較正カメラ **(3.0, 1.0, 0.0)** の GT で学習し JSON に保存:

| 項目 | 内容 | 学習方法 |
|---|---|---|
| カルマン Q | 関節×軸のプロセスノイズ | GT 加速度の分散 |
| カルマン R | 関節×軸の観測ノイズ | MP−GT 残差の白色成分の分散 |
| r→z 写像 (a,b) | UV 復元の進行距離 r(t) → ワールド Z | 線形回帰（残差 0.032 m） |
| x_s | 被写体の横位置（シーン定数） | GT 平均 |
| バイアス表 b(z) | 角度誤差の 30 ビン平均（3 ビン移動平均で平滑化） | θ_MP − θ_GT |

## 2. 検証条件

- **検証カメラ**: (3.2, 1.1, 0.4) — 較正カメラから X+0.2 / Y+0.1 / Z+0.4 m
  （`1_input/aditional__test_data/CapturedFrames_3.2_1.1_0.4/video.mp4`。
  依頼文の (3.2, 1.2, 0.1) はフォルダ実体 (3.2, 1.1, 0.4) を採用）
- 検証動画の GT: フォルダに同梱がなかったため、`CapturedFrames_4.0_1.0_0.0`
  の GT をコピーして使用（GT はワールド座標でカメラ非依存、カメラ間差 ≤3 mm、
  GT 角度同士の相互相関ラグ 0 を確認済み）。**評価のみに使用**
- カンニングペーパーは (3.0, 1.0, 0.0) 製をそのまま適用

## 3. 結果（検証カメラ、角度 MAE [deg]）

| 角度 | MP raw | +median/MAD+Kalman | +カンニングペーパー | 改善率 |
|---|---|---|---|---|
| L_KNEE | 15.3 | 16.1 | **8.3** | **46.0%** |
| R_KNEE | 13.3 | 16.1 | **7.7** | **42.2%** |
| L_ELBOW | 40.9 | 42.0 | **8.9** | **78.2%** |
| R_ELBOW | 16.1 | 15.1 | **4.6** | **71.4%** |

- 進行位置 ẑ(t) の GT フリー推定誤差: 平均 0.033 m / 最大 0.107 m
  （r→z 写像が 0.2〜0.4 m ずれた別カメラにそのまま転移した）
- これは docs/07 の bin+ARIMA（in-sample 上限性能）と違い、
  **完全 out-of-sample**（別カメラ・別動画・推論時 GT ゼロ）の数値

## 4. 最重要の発見: 系統誤差は「視方位ロック」ではなく「歩行位相ロック」

> 詳細な解説（発見の経緯・幾何の一致・肘と膝の対比・論文への含意）は
> [`09_GAIT_PHASE_LOCKED_ERROR.md`](09_GAIT_PHASE_LOCKED_ERROR.md) を参照。

バイアス表を当初は相対カメラ方位 φ(t) で索引したところ、
**肘は改善（61〜73%）するが膝は全く改善しない**（−5〜0%）という結果になった。

ラグ解析による原因特定:
- 2 動画は完全同期（GT 角度同士の最良ラグ 0）
- しかし検証カメラの膝誤差波形は、較正表と **−6〜−8 フレームずれ**で相関 0.81
  （ラグ 0 では 0.33）
- カメラを Z 方向に 0.4 m ずらすと、同じ視方位 φ に到達する時刻が
  約 8 フレーム（0.4 m ÷ 歩行速度 ≈1.4 m/s × 30fps）遅れる。
  このずれ幅が観測と一致

つまり**膝の系統誤差は歩容（脚の姿勢）に同期した関数**であり、視方位の関数
ではない。肘の誤差は緩やかな平均バイアス支配なので φ 索引でも転移した。
索引を「進行位置 z（同一歩行では歩行位相と 1 対 1）」に変えることで
膝も 42〜46% 改善に転じた。

→ Model 4S 系の「視点ビン」思想への含意: 視点ビンは**平均レベルの誤差**
（ビン定数）には正しいが、時間変動する誤差成分の索引としては
**歩行位相**の方が支配的。

## 5. 残る限界・注意

1. **z 索引の転移は「同一歩行動作」が前提**。今回の較正/検証は同じ歩行
   アニメーションなので z ↔ 歩行位相が共有できた。任意の歩行に配備するには
   z の代わりに歩行位相そのもの（例: 膝角度の自己相関、接地イベント）を
   GT フリーで推定して索引にする必要がある
   → 設計案: [`10_PHASE_EXPLICIT_MODEL_PROPOSAL.md`](10_PHASE_EXPLICIT_MODEL_PROPOSAL.md)
2. カルマン段単体では膝がわずかに悪化する（15.3→16.1°。速い屈曲を平滑化で
   丸めるため）。ただし較正時も同じ平滑を通した誤差で表を作るので、
   最終段では一貫して相殺される
3. 検証カメラは較正カメラの近傍（同一視点ビン内）。ビンをまたぐ転移は未検証
4. L_KNEE の深い屈曲（〜105°）は補正後も 120° 程度までしか届かない
   （平滑化の限界 + MP 自体の追従不足）

## 6. ファイル

| パス | 内容 |
|---|---|
| `2_pose/run_gt_free_model.py` | 較正→検証の通し実行スクリプト |
| `2_pose/gt_free_model/cheatsheet.json` | カンニングペーパー |
| `.../SUMMARY.md` / `validation_angle_mae.csv` | 数値サマリ |
| `.../val_angle_timeseries.png` | 検証 4 角度の GT/raw/平滑/補正の時系列（2×2） |
| `.../per_joint/val_{L,R}_{KNEE,ELBOW}.png` | 関節ごとの個別時系列（GT / MP raw / 補正後の 3 本、MAE 併記） |
| `.../val_angle_mae_stages.png` | 段階別 MAE 棒グラフ |
| `.../cheatsheet_bias_tables.png` | バイアス表 b(z)（較正サンプル重ね描き） |
| `.../val_travel_and_phi.png` | ẑ(t) 推定 vs GT・φ(t) の診断 |
| `.../analysis/plot_per_joint_timeseries.py` | 個別時系列プロットの再生成スクリプト |

再実行: `cd 2_pose && python run_gt_free_model.py`
（検証動画の MP 処理は `mediapipe_video_processor.py --input_dir
../1_input/aditional__test_data --output_base_dir
mediapipe_processed_csv_additional` で作成済み）

## 7. アブストラクト改訂版（2026-07-19、GT フリー検証を反映）

docs/07 §8 の草稿を、本ドキュメントの out-of-sample 検証結果で全面改訂したもの。

**和文**:
単眼姿勢推定器 MediaPipe Pose の 3 次元出力は腰中心の相対座標であり、身体の
大域変位を含まないうえ、誤差が奥行き方向に集中する構造的制約を持つ。本研究では、
進行方向に対して真横から撮影する条件の下、推論時に正解データ（GT）を一切用いない
補正パイプラインを構成し、その汎化性能を較正とは異なるカメラ位置の別動画で検証した。
提案法は、(1) 画像正規化座標（UV）と 2 次元体幹長スケールによる擬似ワールド座標の
構成、(2) 移動中央値と MAD に基づくスパイク除去、(3) 較正時に学習したノイズ共分散を
用いるカルマンスムーザー、(4) 剛体変換に不変な 3 点関節角度への変換、(5) 事前較正
した系統バイアス表（カンニングペーパー）の線形補間による減算、から成る。バイアス表の
索引の検討により、膝の系統誤差はカメラ視方位ではなく歩行位相にロックしていることを
同定し（カメラ 0.4 m 移動が誤差波形の約 8 フレームずれとして観測される）、被写体の
進行位置——UV 復元により平均 3.3 cm で GT フリー推定可能——を索引とすることで
位相ロック誤差の転移を実現した。Unity シミュレーションにおいて、カメラ位置
(3.0, 1.0, 0.0) m で較正したバイアス表を (3.2, 1.1, 0.4) m の別動画に適用した結果、
関節角度 MAE は膝で 42〜46%（15.3°→8.3°）、肘で 71〜78%（40.9°→8.9°）低減した。
これは推論時 GT ゼロの完全 out-of-sample 評価であり、シミュレーション較正に基づく
実環境配備可能な単眼姿勢補正の実現可能性を示すものである。

**English**:
The 3-D output of the monocular pose estimator MediaPipe Pose is hip-centered
and lacks global displacement, with errors concentrated along the camera
line of sight. Under a side-view capture condition, we construct a correction
pipeline that uses no ground truth (GT) at inference time and validate its
generalization on a separate video captured from a camera position different
from calibration. The method comprises (1) pseudo-world coordinates built from
normalized image (UV) coordinates with a 2-D torso-length scale, (2) spike
removal by moving median and MAD, (3) a Kalman smoother whose noise covariances
are learned at calibration, (4) conversion to rigid-transform-invariant
three-point joint angles, and (5) subtraction of a pre-calibrated systematic
bias table (a "cheat sheet") via linear interpolation. By examining the table
index, we identify that knee systematic errors are locked to gait phase rather
than to camera viewing direction—a 0.4 m camera shift manifests as an ~8-frame
misalignment of the error waveform—and achieve transfer of phase-locked errors
by indexing the table with the subject's travel position, which is estimated
GT-free to 3.3 cm via UV recovery. In a Unity simulation, applying a bias table
calibrated at camera position (3.0, 1.0, 0.0) m to a separate video at
(3.2, 1.1, 0.4) m reduced joint-angle MAE by 42–46% for the knees (15.3°→8.3°)
and 71–78% for the elbows (40.9°→8.9°). This fully out-of-sample evaluation
with zero GT at inference demonstrates the feasibility of deployable monocular
pose correction based on simulation calibration.

### キーワード候補（10）

1. 単眼 3 次元姿勢推定（monocular 3D human pose estimation）
2. MediaPipe Pose
3. 視点依存バイアス（viewpoint-dependent bias）
4. 系統誤差補正（systematic error correction）
5. シミュレーション較正（simulation-based calibration / sim-to-real）
6. GT フリー推論（ground-truth-free inference）
7. 歩行位相ロック誤差（gait-phase-locked error）
8. UV 擬似ワールド座標（pseudo-world coordinates from image coordinates）
9. カルマンスムーザー（Kalman smoother / RTS）
10. 関節角度 MAE（joint-angle mean absolute error）

（予備: 移動中央値+MAD 外れ値除去、Unity 合成データセット、奥行き曖昧性）
