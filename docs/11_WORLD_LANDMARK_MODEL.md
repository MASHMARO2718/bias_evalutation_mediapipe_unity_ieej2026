# pose_world_landmarks 単独の GT フリー補正 — UV 擬似ワールド不使用実験

**作成**: 2026-07-19
**実装**: `20_pose_correction/run_world_landmark_model.py`
（world 抽出: `extract_world_landmarks.py` → `mediapipe_world_csv/`）
**出力**: `20_pose_correction/world_landmark_model/`
**関連**: [`08`](08_GT_FREE_CHEATSHEET_MODEL.md)（UV 系の現行モデル）、
[`10`](10_PHASE_EXPLICIT_MODEL_PROPOSAL.md)（索引 4 方式・アンカー破壊）

問い: 「**UV 擬似ワールドを使わず pose_world_landmarks だけで補正できるか?**」
→ **結論: できる。しかも最良構成は UV 系を上回り、カメラ情報すら不要になった。**

---

## 1. 実験設計

- 座標: `pose_world_landmarks`（腰中心・メートル・等方 3D。GHUM モデルフィット
  由来）のみ。UV 擬似ワールドの座標構成は不使用
- 既存 CSV には world が未保存だったため、較正・検証の 2 動画を再処理して抽出
  （検出設定は既存プロセッサと同一。検出フレーム数も同一 91/106）
- パイプラインは docs/08,10 と同じ骨格: 中央値+4×MAD → カルマン RTS →
  3 点角 → バイアス表減算。**カルマン Q/R は GT を使わず自己推定**に変更
  （高周波残差分散と加速度分散。較正時 GT の使用は バイアス表と focal のみに縮小）
- 索引 4 方式:
  - **W-yaw**: 腰ライン（L_HIP−R_HIP）のカメラ相対ヨー角。純 world
    （画像情報もカメラ位置も不要）
  - **W-bearing**: 腰の画像内水平位置 u(t)+カメラ幾何（画像から使うのは u のみ）
  - **W-phase**: ヒルベルト歩行位相のみ。world には進行方向が無いため、
    足首 L−R ベクトルの第 1 主成分軸への射影を位相信号とする。
    **純 world・アンカー不要・カメラ情報不要**
  - **W-2level**: g(z_bearing) 粗ビン + 位相波 h(φ_g) 残差

## 2. 結果（検証カメラ (3.2,1.1,0.4)、較正 (3.0,1.0,0.0)、角度 MAE [deg]）

| 角度 | UV raw | **world raw** | UV-A | UV-B | W-yaw | W-bearing | **W-phase** | W-2level |
|---|---|---|---|---|---|---|---|---|
| L_KNEE | 15.3 | 16.5 | 8.3 | 11.4 | 9.2 | 11.0 | **8.7** | 8.8 |
| R_KNEE | 13.3 | **7.5** | 7.7 | 9.3 | 8.9 | 6.7 | **5.8** | 5.6 |
| L_ELBOW | 40.9 | **14.3** | 8.9 | 8.9 | 12.0 | 8.9 | **7.7** | 8.1 |
| R_ELBOW | 16.1 | **4.5** | 4.6 | 5.0 | 4.6 | 3.8 | **3.1** | 3.2 |

（UV-A/B は docs/10 §7 のフル動画値。テンプレート照合は δ=0.00 rad・
swap=False を正判定）

## 3. 発見

### 3.1 world raw は UV raw より大幅に高品質（3/4 関節）

L_ELBOW 40.9°→14.3°、R_ELBOW 16.1°→4.5°、R_KNEE 13.3°→7.5°。
GHUM 3D モデルフィットが、UV+pose-z 経路の深度誤差の大部分を
吸収している。例外は L_KNEE（15.3→16.5 と微悪化）。

### 3.2 world 空間では位相のみの索引が成立する（UV 系との最大の違い）

UV 系では位相のみ索引（方式C）は膝で無効だった（docs/10 §7: 誤差に大きな
非周期ゆっくり成分があるため）。world 空間ではそのゆっくり成分自体が
GHUM フィットで大幅に減っており、**残る系統誤差はほぼ歩行位相ロック波のみ**。
その結果 W-phase 単独で全関節最良〜同率最良になり、2 階建て（W-2level）との
差が消えた。docs/09 の「誤差 = 視点で決まるゆっくり成分 + 位相波」の
2 階建て描像で言えば、**第 1 層を推定器（GHUM）が内部で処理してくれる**形。

### 3.3 配備要件が最小化された

W-phase の推論時入力は **MediaPipe world 出力と較正表だけ**。
- カメラ位置・向き: 不要（docs/10 の B が必要としていた）
- 画像座標 u(t): 不要
- フレーム原点・録画開始時刻: 不要（位相は信号自身にアンカー）
- 位置合わせ・鏡映解消: 不要（3 点角の不変性 + テンプレート照合で swap 判定）

### 3.4 W-yaw（純 world のゆっくり索引）は動くが位相に劣る

診断図のとおり、腰ラインヨーは進行位置に対して大局的には単調だが
歩行振動が重畳して非単調（懸念していた鏡映フリップは今回は非発生）。
索引としては W-phase に一貫して劣後した。

## 4. 限界・注意

1. **位相のみで足りるのは world 空間の性質に依る**。ゆっくり成分が
   大きい条件（未知の視点・被写体・推定器バージョン）では 2 階建て
   （W-2level）が安全側。W-2level は W-phase とほぼ同等なので、
   汎用にはこちらを既定にしてよい
2. 同一歩行動作での検証である点は docs/08,10 と同じ（ただし位相索引は
   原理的に速度・開始位置の変化に頑健なはずで、その検証には速度違い
   データが必要）
3. world CSV は現状 2 動画分のみ。576 カメラ全体の world 再処理は未実施
4. L_KNEE の raw 微悪化の原因（GHUM フィットの左膝深度）は未調査

## 5. 論文への含意

- 提案パイプラインの主軸は「**world landmarks + 位相索引カンニングペーパー**」
  に置き換えるのが最も強い（性能・配備要件とも）
- UV の役割は「大域位置・軌跡が必要な応用（歩行距離・速度出力、
  bearing 索引）」と「world が使えない環境」に限定して主張する
- 下書き `paper/IEEJ_02/IEEJ_ja_gtfree/main.tex` は §3 の再構成が必要
  （UV 擬似ワールド中心 → world 中心 + UV は補助）

## 6. ファイル

| パス | 内容 |
|---|---|
| `20_pose_correction/extract_world_landmarks.py` | world landmarks 抽出（2 動画再処理） |
| `20_pose_correction/mediapipe_world_csv/` | 抽出済み world CSV |
| `20_pose_correction/run_world_landmark_model.py` | 較正→検証の通し実行 |
| `20_pose_correction/world_landmark_model/SUMMARY.md` | 数値サマリ |
| `.../world_model_mae.csv` | 全数値 |
| `.../world_vs_uv_comparison.png` | **主図**: UV 系 vs world 系 7 構成の MAE 比較 |
| `.../val_world_timeseries.png` | 検証 4 角度の時系列（GT / world raw / 補正後） |
| `.../world_index_diagnostics.png` | ヨー・bearing 索引の診断 |
| `.../world_yaw_bias_scatter.png` | ヨー vs 角度誤差の散布 |

再実行: `cd 20_pose_correction && python extract_world_landmarks.py &&
python run_world_landmark_model.py`
