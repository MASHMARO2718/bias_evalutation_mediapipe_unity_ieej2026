# MotionTrack — MediaPipe × Unity GT バイアス評価

Unity で取得した関節 Ground Truth（GT）と MediaPipe Pose 推定を比較し、視点依存バイアスの分析・補正・可視化を行うリポジトリです。

**ソースコード:** [MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026](https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026)

## どれを実行すればいいか

このリポジトリには**目的の違う 2 本のライン**があります。まずどちらかを選んでください。

| やりたいこと | 実行するもの | 規模 | 解説 |
|---|---|---|---|
| **論文（IEEJ_02 / CANDAR）の結果を再現したい** | `python run_world_phase_correction.py` | 動画 2 本（較正 1 + 検証 1） | [`docs/11`](docs/11_WORLD_LANDMARK_MODEL.md) |
| **576 カメラのバイアス調査をやり直したい** | `python run_v2_pipeline.py` | 全 576 カメラ | 下記「解析パイプライン」 |
| v1（旧 JPG・同期ずれあり）を触りたい | `python run.py` | 旧データ | [`docs/03`](docs/03_SYNC_ISSUE_REPORT.md) |

**補正モデルの最終形**は world landmarks + 歩行位相索引（W-phase）です。
推論時の入力は「MediaPipe の world 出力 + 較正表」のみで、カメラ情報も画像座標も要りません。

```bash
python run_world_phase_correction.py --check   # 入力が揃っているか確認
python run_world_phase_correction.py           # 最終形を再現
python run_world_phase_correction.py --history # 過程の実験（docs/07, 08, 10）
```

| 項目 | 現在の既定 |
|------|------------|
| データセット | **v2**（動画 + フレーム同期 GT） |
| 切替 | ルート [`config.py`](config.py) の `DATASET_VERSION` |
| 補正ダッシュボード | http://localhost:8051/（`7_correction`） |
| 旧ダッシュボード | http://localhost:8050/（`8_dashboard`） |

## 主要結果ハイライト（2026-07-19 時点）

| 成果 | 数値 | 詳細 |
|------|------|------|
| **GT フリー補正の別カメラ検証**（推論時 GT ゼロ・完全 out-of-sample） | 角度 MAE 膝 **42〜46%** / 肘 **71〜78%** 改善（例: L_ELBOW 40.9°→8.9°) | [`docs/08`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) |
| **アンカーフリー化**（フレーム原点に依存しない配備形） | アンカー破壊テストで z-bearing 索引が全関節最良で生存（膝 8.2〜11.2°） | [`docs/10`](docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md) §7 |
| **world landmarks 単独補正**（UV 構成もカメラ情報も不要） | W-phase で膝 5.8〜8.7° / 肘 3.1〜7.7°（UV 系最良を更新）。推論時入力は MP 出力+較正表のみ | [`docs/11`](docs/11_WORLD_LANDMARK_MODEL.md) |
| 系統誤差は視方位でなく**歩行位相ロック**という発見 | カメラ 0.4 m 移動 = 誤差波形 ~8 フレームずれ | [`docs/08`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) §4 |
| UV からの腰軌跡復元（大域変位の GT フリー取得） | 平均誤差 **0.067 m**（真横 3 m） | [`docs/07`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) |
| 膝奥行き誤差の構造分解（bin+ARIMA、in-sample 上限） | \|e_X\| **82〜90%** 減 | [`docs/07`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) §7 |
| Model 4S 符号付き視点ビン補正（既存主結果） | \|Δθ\| **65.9 / 72.6%** 改善 | `7_correction/` |

改訂版アブストラクト＋キーワード候補: [`docs/08`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) §7 ·
論文構成の検討材料: [`paper/IEEJ_02/resume/`](paper/IEEJ_02/resume/README.md)

### ドキュメント索引（時系列順）

| # | ドキュメント | 内容 |
|---|---|---|
| 00 | [`00_PROGRESS.md`](docs/00_PROGRESS.md) | 進捗メモ・作業ログ（常時更新） |
| 01 | [`01_ZEVAL_DATASET_LAYOUT.md`](docs/01_ZEVAL_DATASET_LAYOUT.md) | 外部データセット対応 |
| 02 | [`02_REPRODUCTION.md`](docs/02_REPRODUCTION.md) | 再現手順 |
| 03 | [`03_SYNC_ISSUE_REPORT.md`](docs/03_SYNC_ISSUE_REPORT.md) | v1 同期ずれの原因と対策 |
| 04 | [`04_UNITY_VIDEO_CAPTURE_PROMPT.md`](docs/04_UNITY_VIDEO_CAPTURE_PROMPT.md) | Unity 動画キャプチャ仕様 |
| 05 | [`05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md) | 関節誤差 MC 解析 |
| 06 | [`06_MOVING_AVERAGE_NOISE_REJECTION.md`](docs/06_MOVING_AVERAGE_NOISE_REJECTION.md) | 移動平均ノイズ低減（GT 基準） |
| 07 | [`07_UV_PSEUDO_WORLD_CORRECTION.md`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) | UV 擬似ワールド補正・スケール較正・bin+ARIMA・関節マッピング監査 |
| 08 | [`08_GT_FREE_CHEATSHEET_MODEL.md`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) | **GT フリーモデル再構築と別カメラ検証（最新）** |
| 09 | [`09_GAIT_PHASE_LOCKED_ERROR.md`](docs/09_GAIT_PHASE_LOCKED_ERROR.md) | 歩行位相ロック誤差の発見経緯と解説 |
| 10 | [`10_PHASE_EXPLICIT_MODEL_PROPOSAL.md`](docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md) | 位相明示型モデル: 設計→実装検証（アンカー破壊テストで z-bearing / 2 階建てが生存） |
| 11 | [`11_WORLD_LANDMARK_MODEL.md`](docs/11_WORLD_LANDMARK_MODEL.md) | **world landmarks 単独補正（最新）**: W-phase が UV 系を上回り、カメラ情報も不要に |

---

## クイックスタート（v2）

```bash
pip install -r requirements.txt

# config.py で DATASET_VERSION = "v2" になっていること

# MediaPipe 済み前提で 03〜07, 09 を実行（ダッシュボード含む）
python run_v2_pipeline.py

# MediaPipe からやり直す場合
python run_v2_pipeline.py --with-mediapipe

# ダッシュボードを起動しない
python run_v2_pipeline.py --no-dashboard
```

補正フレームワーク GUI のみ使う場合:

```bash
cd 7_correction/dashboard
python app.py
# → http://localhost:8051/
```

v1（JPG・同期ずれあり）を使う場合は `DATASET_VERSION = "v1"` にし、`python run.py` を使います（後述）。

---

## データセット（v1 / v2）

| | **v1（旧）** | **v2（新・既定）** |
|--|-------------|-------------------|
| 収集 | 2025-12 | 2026-07 |
| カメラ数 | 約 289（一部高さ層） | **576**（4 高さ × 144 位置） |
| 入力 | `9_legacy_v1/input_photos/` JPG × ~107/カメラ | `1_input/` `video.mp4` + `gt_joints.csv` |
| GT | `synced_joint_positions_*.csv` | `gt_joints.csv`（`frame_id` / `time_sec`） |
| 同期 | 約 −3 フレームずれ | フレーム同期済み |
| MediaPipe | `9_legacy_v1/mediapipe_processed/` | `2_pose/mediapipe_processed_csv/` |
| 論文 | IEEJ_01（提出済み） | IEEJ_02（補正・再評価） |

高さ層は共通で `Y=0.5 / 1.0 / 1.5 / 2.0`。フォルダ名は `CapturedFrames_{X}_{Y}_{Z}`（メートル）。

詳細: [`docs/03_SYNC_ISSUE_REPORT.md`](docs/03_SYNC_ISSUE_REPORT.md) · 進捗: [`docs/00_PROGRESS.md`](docs/00_PROGRESS.md)

---

## ディレクトリ構成

```
.
├── config.py                 # DATASET_VERSION / 入出力パス
├── requirements.txt
├── run_world_phase_correction.py  # ★ 補正モデル本線（論文の最終結果）
├── run_v2_pipeline.py        # ★ 576 カメラ調査ライン（03〜07, 09）
├── run.py                    # v1 向けエントリ
├── docker-compose.yml
├── synced_joint_positions.csv # v1 マスター GT（config.GT_CSV）
│
├── scripts/                  # 補助スクリプト（検証・掃除・部分実行）
│   ├── verify_paper_data.py      # 論文用数値の整合チェック
│   ├── clean_pipeline_outputs.py
│   ├── run_04_06_07.py           # 04/06/07 部分実行
│   └── run_full_pipeline.py      # run.py の後方互換ラッパ
│
├── 0_start/            # 初見向けメモ（主に v1 手順）
│
├── 9_legacy_v1/input_photos/          # [v1] JPG + synced GT（カメラごとサブフォルダ）
├── 1_input/          # [v2] video.mp4 + gt_joints.csv（576 カメラ）
│
├── 9_legacy_v1/mediapipe_processed/   # [v1] Pose CSV（Y=*/CapturedFrames_*.csv）
├── 2_pose/          # [v2] Pose 処理・解析・オーバーレイ
│   ├── mediapipe_video_processor.py
│   ├── mediapipe_processed_csv/Y=*/
│   ├── overlay_mp_landmarks.py      # CSV を video に骨格重ね（再検出なし）
│   ├── overlay_videos/              # 重ね描き mp4 出力
│   ├── run_ma_noise_rejection.py    # 移動平均ノイズ低減実験（GT 基準）
│   ├── run_error_mc_analysis.py     # 関節誤差モンテカルロ解析
│   ├── run_uv_pseudo_world_correction.py  # UV 擬似ワールド補正（GT フリー）
│   └── uv_pseudo_world_correction/  # 同・結果（results_std_k3 / results_mad_k5）
│
├── 3_joint_angle_mae/       # 3点角 MAE（層別 CSV・統合表・ヒートマップ）
├── 4_max_angle_error/       # 最大角度誤差
├── 5_direction/   # 方向角・相関（論文 processed 系の主出力）
├── 6_theta_check/    # θ・座標系検証
├── 8_dashboard/             # Dash 可視化（port 8050）
├── 7_correction/ # ★ パラメトリック補正（研究本体 + GUI 8051）
│
├── docs/                     # プロジェクト横断ドキュメント
├── paper/                    # IEEJ_01 / IEEJ_02
├── tools/                    # GT アダプタ等
├── docker/
└── _backup_v1_outputs_*/     # v2 再実行前に退避した v1 出力
```

番号フォルダは処理段階の目安です。**現在の主戦場は v2 入力 → `2_pose` → `03`〜`07` → `09`** です。

---

## 各フォルダの中身（要点）

### 入力

| パス | 中身 |
|------|------|
| `1_input/CapturedFrames_X_Y_Z/` | `video.mp4`（例: 1280×720, ~105f, 30fps）+ `gt_joints.csv` |
| `9_legacy_v1/input_photos/CapturedFrames_X_Y_Z/` | JPG 連番 + `synced_joint_positions_*.csv`（v1） |

### MediaPipe（v2）

| パス | 中身 |
|------|------|
| `mediapipe_processed_csv/Y=*/CapturedFrames_*.csv` | `frame_id, landmark, x, y, z, visibility`（画像正規化座標） |
| `overlay_mp_landmarks.py` | 既存 CSV を動画に骨格重ね。左上に `現在/総フレーム` |
| `overlay_videos/Y=*/` | `*_mp_overlay.mp4` |
| `run_uv_pseudo_world_correction.py` | UV 大域位置から腰軌跡を復元し、進行方向直交成分を MAD フィルタで補正（GT フリー）。詳細: [`docs/07_UV_PSEUDO_WORLD_CORRECTION.md`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) |
| `uv_pseudo_world_correction/results_*/` | 同・結果（`results_mad_k5` が推奨構成） |
| `run_gt_free_model.py` | 推論時 GT ゼロの補正パイプライン（カンニングペーパー方式）。別カメラ検証で角度 MAE 膝 42〜46% / 肘 71〜78% 改善。詳細: [`docs/08_GT_FREE_CHEATSHEET_MODEL.md`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) |
| `gt_free_model/` | 同・カンニングペーパー JSON と検証結果 |
| `run_phase_explicit_model.py` | 位相明示型・アンカーフリー化の 4 方式比較（z-travel / z-bearing / phase / two-level + アンカー破壊テスト）。詳細: [`docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md`](docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md) §7 |
| `phase_explicit_model/` | 同・比較結果とプロット |
| `extract_world_landmarks.py` / `mediapipe_world_csv/` | pose_world_landmarks の抽出（world 実験用、2 動画分） |
| `run_world_landmark_model.py` | world landmarks 単独補正の 4 索引比較。詳細: [`docs/11_WORLD_LANDMARK_MODEL.md`](docs/11_WORLD_LANDMARK_MODEL.md) |
| `world_landmark_model/` | 同・結果とプロット |
| `mediapipe_processed_csv_additional/` | 追加検証動画（`aditional__test_data`）の MP 処理結果 |

```bash
# 1 カメラ
python 2_pose/overlay_mp_landmarks.py --camera 3.0_1.0_0.0 --overwrite

# 全カメラ
python 2_pose/overlay_mp_landmarks.py
```

### 解析パイプライン（03〜07）

| フォルダ | 役割 | 主な出力 |
|----------|------|----------|
| `3_joint_angle_mae/` | GT vs MP の 3 点関節角 MAE | `joint_angle_mae_csv/Y=*/` |
| `4_max_angle_error/` | 最大角度誤差・ヒートマップ | `calculation/`, `max_angle_error_heatmap/` |
| `5_direction/` | 方位・相関・processed CSV | `output/processed_data/` 等 |
| `6_theta_check/` | 座標・θ 検証 | `output/`, `coordinate_fix_verification/` |
| `8_dashboard/` | 旧統合ダッシュボード | port **8050** |

### 補正フレームワーク（09）

詳細は [`7_correction/README.md`](7_correction/README.md)。

| サブパス | 役割 |
|----------|------|
| `src/` | Phase A/B・特徴量・評価のコア |
| `experiments/` | `run_calibration.py` / `grid_search.py` / `run_evaluation.py` |
| `scripts/` | 符号付き評価・時系列プロット・論文用図 |
| `scripts/output/v1\|v2\|v3/` | 角度時系列（PNG/CSV）。v3 は横軸 0–120 固定 |
| `dashboard/app.py` | Overview / Bin Explorer / Linear / Grid Search / Raw / **Angle Timeseries**（port **8051**） |
| `docs/` | 補正モデル仕様・線形性・符号付き分析など |
| `outputs/` | バイアステーブル・評価 CSV・図 |

```bash
cd 7_correction
python experiments/run_calibration.py
python experiments/run_evaluation.py

# 角度時系列（全カメラ×関節）例
python scripts/batch_angle_timeseries.py --output-version v3 --frame-xlim 0 120
```

### ドキュメント・論文・その他

| パス | 内容 |
|------|------|
| `docs/03_SYNC_ISSUE_REPORT.md` | v1 同期ずれの原因と対策 |
| `docs/04_UNITY_VIDEO_CAPTURE_PROMPT.md` | Unity 動画キャプチャ仕様 |
| `docs/02_REPRODUCTION.md` | 再現手順 |
| `docs/01_ZEVAL_DATASET_LAYOUT.md` | 外部データセット対応 |
| `docs/06_MOVING_AVERAGE_NOISE_REJECTION.md` | 移動平均ノイズ低減（GT 基準） |
| `docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md` | 関節誤差 MC 解析 |
| `docs/07_UV_PSEUDO_WORLD_CORRECTION.md` | UV 擬似ワールド補正（GT フリー）と検証・関節マッピング監査 |
| `docs/08_GT_FREE_CHEATSHEET_MODEL.md` | GT フリーモデル再構築（カンニングペーパー方式）と別カメラ検証 |
| `docs/09_GAIT_PHASE_LOCKED_ERROR.md` | 歩行位相ロック誤差の発見経緯と解説 |
| `docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md` | 位相明示型モデル: 設計提案と実装検証（アンカーフリー化） |
| `docs/00_PROGRESS.md` | 進捗メモ |
| `paper/IEEJ_01/` | バイアス評価論文（提出済み） |
| `paper/IEEJ_02/` | 局所線形補正論文（執筆中） |
| `tools/` | GT アダプタ等のユーティリティ |
| `_backup_v1_outputs_*/` | v2 上書き前の v1 結果退避 |

---

## コマンド早見表

| コマンド | 用途 |
|----------|------|
| `python run_world_phase_correction.py` | **補正モデル本線**（論文の最終結果 W-phase） |
| `python run_world_phase_correction.py --check` | 補正モデルの入力が揃っているか確認 |
| `python run_world_phase_correction.py --history` | 過程の実験を再現（docs/07, 08, 10） |
| `python run_v2_pipeline.py` | **576 カメラ調査**（MP 済み想定で 03〜09） |
| `python run_v2_pipeline.py --with-mediapipe` | v2 を MediaPipe から |
| `python run_v2_pipeline.py --step N` | 特定ステップのみ |
| `python run.py` | **v1** 全パイプライン |
| `python run.py --no-mediapipe` | v1 で 02 以降のみ |
| `python 8_dashboard/app.py` | 旧 GUI → :8050 |
| `python 7_correction/dashboard/app.py` | 補正 GUI → :8051 |
| `python 2_pose/overlay_mp_landmarks.py` | MP 骨格オーバーレイ動画 |
| `python 2_pose/run_uv_pseudo_world_correction.py --torso-2d --robust-sigma --k-sigma 5` | UV 擬似ワールド補正（推奨構成） |
| `python scripts/verify_paper_data.py` | 論文数値の整合確認 |
| `docker compose up --build` | Docker でダッシュボード（:8050） |

`run_v2_pipeline.py` のステップ番号の目安:

| `--step` | 内容 |
|----------|------|
| 0 | MediaPipe 動画処理 |
| 1–2 | 03 関節角 MAE |
| 3 | 04 最大角度誤差 |
| 4 | 05 方向角 |
| 5 | 06 θ 検証 |
| 6 | 07 ダッシュボード |
| 7 | 09 キャリブレーション |

---

## ダッシュボード

| GUI | 起動 | URL | 主な用途 |
|-----|------|-----|----------|
| `8_dashboard` | `python 8_dashboard/app.py` | :8050 | 方向角・骨格など旧パイプライン可視化 |
| `09` Calibration | `python 7_correction/dashboard/app.py` | :8051 | ビン構造・補正モデル・角度時系列（カメラマップ付き） |

---

## Docker

```bash
docker compose up --build
```

→ http://localhost:8050/（詳細は `docker/`）

---

## 論文

```
paper/
├── IEEJ_01/                 # 論文1: MediaPipe バイアス評価（提出済み）
│   ├── source/IEEJ_en|ja/
│   └── submitted/
└── IEEJ_02/                 # 論文2: 局所線形補正（執筆中）
    ├── IEEJ_en_calibration/
    └── IEEJ_ja_calibration/
```

```bash
cd paper/IEEJ_02/IEEJ_en_calibration
pdflatex main.tex && pdflatex main.tex
```

各ディレクトリの README を参照してください。

---

## データ公開・大容量ファイル

- 解析コードは GitHub を正とします。
- `**/*.mp4` は `.gitignore` 対象（入力動画・オーバーレイはローカル保管）。
- MediaPipe 中間 CSV（ZIP）: DOI [10.5281/zenodo.19296530](https://doi.org/10.5281/zenodo.19296530)  
  展開後の `mediapipe_processed_csv/Y=0.5/` … `Y=2.0/` を `9_legacy_v1/mediapipe_processed/` 配下に置くと v1 パイプラインと整合します。

---

## 開発者向けメモ

通常の利用では不要なもの:

| 対象 | 用途 |
|------|------|
| `6_theta_check/test_*.py`, `run_all.py` | 肘誤差・座標系の検証テスト |
| `paper/create_camera_layout.py`, `paper/source/prepare_ieej_overleaf.py` | 論文用図・IEEJ 同梱物の同期 |

注意点:

- **`3_joint_angle_mae`**: `Y=*/coordinate_angle_mae.csv` が無いと
  `scripts/verify_paper_data.py` のステップ 1・表 1 検証はスキップまたは失敗します。
- **中間生成物の実体**は `data_storage/` にあり、旧パスには Windows
  ジャンクションが張られています。構成は [`data_storage/README.md`](data_storage/README.md)。

---

## 関連ドキュメント（入口）

| ドキュメント | 内容 |
|--------------|------|
| [`0_start/`](0_start/) | 最小手順（主に v1） |
| [`docs/00_PROGRESS.md`](docs/00_PROGRESS.md) | 現状と作業ログ |
| [`docs/02_REPRODUCTION.md`](docs/02_REPRODUCTION.md) | 再現性 |
| [`7_correction/README.md`](7_correction/README.md) | 補正フレームワーク |
| [`7_correction/docs/07_correction_models.md`](7_correction/docs/07_correction_models.md) | 補正モデル 2–6 の説明 |
| [`data_storage/README.md`](data_storage/README.md) | 中間生成物の置き場とフォルダ対応 |
