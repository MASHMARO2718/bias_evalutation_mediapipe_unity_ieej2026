# MotionTrack — MediaPipe × Unity GT バイアス評価

Unity で取得した関節 Ground Truth（GT）と MediaPipe Pose 推定を比較し、視点依存バイアスの分析・補正・可視化を行うリポジトリです。

**ソースコード:** [MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026](https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026)

| 項目 | 現在の既定 |
|------|------------|
| データセット | **v2**（動画 + フレーム同期 GT） |
| 切替 | ルート [`config.py`](config.py) の `DATASET_VERSION` |
| 推奨パイプライン | `python run_v2_pipeline.py` |
| 補正ダッシュボード | http://localhost:8051/（`09_calibration_framework`） |
| 旧ダッシュボード | http://localhost:8050/（`07_dashboard`） |

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
cd 09_calibration_framework/dashboard
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
| 入力 | `01_input_photos/` JPG × ~107/カメラ | `01_input_videos/` `video.mp4` + `gt_joints.csv` |
| GT | `synced_joint_positions_*.csv` | `gt_joints.csv`（`frame_id` / `time_sec`） |
| 同期 | 約 −3 フレームずれ | フレーム同期済み |
| MediaPipe | `02_mediapipe_processed/` | `02_mediapipe_v2/mediapipe_processed_csv/` |
| 論文 | IEEJ_01（提出済み） | IEEJ_02（補正・再評価） |

高さ層は共通で `Y=0.5 / 1.0 / 1.5 / 2.0`。フォルダ名は `CapturedFrames_{X}_{Y}_{Z}`（メートル）。

詳細: [`docs/03_SYNC_ISSUE_REPORT.md`](docs/03_SYNC_ISSUE_REPORT.md) · 進捗: [`docs/00_PROGRESS.md`](docs/00_PROGRESS.md)

---

## ディレクトリ構成

```
.
├── config.py                 # DATASET_VERSION / 入出力パス
├── requirements.txt
├── run_v2_pipeline.py        # ★ v2 推奨エントリ（03〜07, 09）
├── run.py                    # v1 向けエントリ（01→02→03〜05→07）
├── run_04_06_07.py           # 04/06/07 部分実行
├── verify_paper_data.py      # 論文用数値の整合チェック
├── clean_pipeline_outputs.py
├── docker-compose.yml
│
├── 00_quickstart/            # 初見向けメモ（主に v1 手順）
│
├── 01_input_photos/          # [v1] JPG + synced GT（カメラごとサブフォルダ）
├── 01_input_videos/          # [v2] video.mp4 + gt_joints.csv（576 カメラ）
│
├── 02_mediapipe_processed/   # [v1] Pose CSV（Y=*/CapturedFrames_*.csv）
├── 02_mediapipe_v2/          # [v2] Pose 処理・解析・オーバーレイ
│   ├── mediapipe_video_processor.py
│   ├── mediapipe_processed_csv/Y=*/
│   ├── overlay_mp_landmarks.py      # CSV を video に骨格重ね（再検出なし）
│   ├── overlay_videos/              # 重ね描き mp4 出力
│   ├── run_ma_noise_rejection.py    # 移動平均ノイズ低減実験（GT 基準）
│   ├── run_error_mc_analysis.py     # 関節誤差モンテカルロ解析
│   ├── run_uv_pseudo_world_correction.py  # UV 擬似ワールド補正（GT フリー）
│   └── uv_pseudo_world_correction/  # 同・結果（results_std_k3 / results_mad_k5）
│
├── 03_joint_angle_mae/       # 3点角 MAE（層別 CSV・統合表・ヒートマップ）
├── 04_max_angle_error/       # 最大角度誤差
├── 05_direction_detection/   # 方向角・相関（論文 processed 系の主出力）
├── 06_theta_verification/    # θ・座標系検証
├── 07_dashboard/             # Dash 可視化（port 8050）
├── 08_dev/                   # 開発メモ
├── 09_calibration_framework/ # ★ パラメトリック補正（研究本体 + GUI 8051）
│
├── docs/                     # プロジェクト横断ドキュメント
├── paper/                    # IEEJ_01 / IEEJ_02
├── tools/                    # GT アダプタ等
├── docker/
└── _backup_v1_outputs_*/     # v2 再実行前に退避した v1 出力
```

番号フォルダは処理段階の目安です。**現在の主戦場は v2 入力 → `02_mediapipe_v2` → `03`〜`07` → `09`** です。

---

## 各フォルダの中身（要点）

### 入力

| パス | 中身 |
|------|------|
| `01_input_videos/CapturedFrames_X_Y_Z/` | `video.mp4`（例: 1280×720, ~105f, 30fps）+ `gt_joints.csv` |
| `01_input_photos/CapturedFrames_X_Y_Z/` | JPG 連番 + `synced_joint_positions_*.csv`（v1） |

### MediaPipe（v2）

| パス | 中身 |
|------|------|
| `mediapipe_processed_csv/Y=*/CapturedFrames_*.csv` | `frame_id, landmark, x, y, z, visibility`（画像正規化座標） |
| `overlay_mp_landmarks.py` | 既存 CSV を動画に骨格重ね。左上に `現在/総フレーム` |
| `overlay_videos/Y=*/` | `*_mp_overlay.mp4` |
| `run_uv_pseudo_world_correction.py` | UV 大域位置から腰軌跡を復元し、進行方向直交成分を MAD フィルタで補正（GT フリー）。詳細: [`docs/07_UV_PSEUDO_WORLD_CORRECTION.md`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) |
| `uv_pseudo_world_correction/results_*/` | 同・結果（`results_mad_k5` が推奨構成） |

```bash
# 1 カメラ
python 02_mediapipe_v2/overlay_mp_landmarks.py --camera 3.0_1.0_0.0 --overwrite

# 全カメラ
python 02_mediapipe_v2/overlay_mp_landmarks.py
```

### 解析パイプライン（03〜07）

| フォルダ | 役割 | 主な出力 |
|----------|------|----------|
| `03_joint_angle_mae/` | GT vs MP の 3 点関節角 MAE | `joint_angle_mae_csv/Y=*/` |
| `04_max_angle_error/` | 最大角度誤差・ヒートマップ | `calculation/`, `max_angle_error_heatmap/` |
| `05_direction_detection/` | 方位・相関・processed CSV | `output/processed_data/` 等 |
| `06_theta_verification/` | 座標・θ 検証 | `output/`, `coordinate_fix_verification/` |
| `07_dashboard/` | 旧統合ダッシュボード | port **8050** |

### 補正フレームワーク（09）

詳細は [`09_calibration_framework/README.md`](09_calibration_framework/README.md)。

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
cd 09_calibration_framework
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
| `docs/00_PROGRESS.md` | 進捗メモ |
| `paper/IEEJ_01/` | バイアス評価論文（提出済み） |
| `paper/IEEJ_02/` | 局所線形補正論文（執筆中） |
| `tools/` | GT アダプタ等のユーティリティ |
| `_backup_v1_outputs_*/` | v2 上書き前の v1 結果退避 |

---

## コマンド早見表

| コマンド | 用途 |
|----------|------|
| `python run_v2_pipeline.py` | **v2 本流**（MP 済み想定で 03〜09） |
| `python run_v2_pipeline.py --with-mediapipe` | v2 を MediaPipe から |
| `python run_v2_pipeline.py --step N` | 特定ステップのみ |
| `python run.py` | **v1** 全パイプライン |
| `python run.py --no-mediapipe` | v1 で 02 以降のみ |
| `python 07_dashboard/app.py` | 旧 GUI → :8050 |
| `python 09_calibration_framework/dashboard/app.py` | 補正 GUI → :8051 |
| `python 02_mediapipe_v2/overlay_mp_landmarks.py` | MP 骨格オーバーレイ動画 |
| `python 02_mediapipe_v2/run_uv_pseudo_world_correction.py --torso-2d --robust-sigma --k-sigma 5` | UV 擬似ワールド補正（推奨構成） |
| `python verify_paper_data.py` | 論文数値の整合確認 |
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
| `07_dashboard` | `python 07_dashboard/app.py` | :8050 | 方向角・骨格など旧パイプライン可視化 |
| `09` Calibration | `python 09_calibration_framework/dashboard/app.py` | :8051 | ビン構造・補正モデル・角度時系列（カメラマップ付き） |

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
  展開後の `mediapipe_processed_csv/Y=0.5/` … `Y=2.0/` を `02_mediapipe_processed/` 配下に置くと v1 パイプラインと整合します。

---

## 関連ドキュメント（入口）

| ドキュメント | 内容 |
|--------------|------|
| [`00_quickstart/`](00_quickstart/) | 最小手順（主に v1） |
| [`docs/00_PROGRESS.md`](docs/00_PROGRESS.md) | 現状と作業ログ |
| [`docs/02_REPRODUCTION.md`](docs/02_REPRODUCTION.md) | 再現性 |
| [`09_calibration_framework/README.md`](09_calibration_framework/README.md) | 補正フレームワーク |
| [`09_calibration_framework/docs/07_correction_models.md`](09_calibration_framework/docs/07_correction_models.md) | 補正モデル 2–6 の説明 |
| [`08_dev/README.md`](08_dev/README.md) | 開発者メモ |
