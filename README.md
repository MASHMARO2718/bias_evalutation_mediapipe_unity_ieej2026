# MotionTrack — MediaPipe Pose × Unity GT バイアス評価・系統誤差補正

Unity で生成した歩行アニメーションの関節 Ground Truth（GT）と
[MediaPipe Pose](https://developers.google.com/mediapipe) の推定を **576 視点**で突き合わせ、

1. 視点依存バイアスの**評価**（どの視点で・どの関節が・どれだけずれるか）
2. 推論時に GT もカメラ情報も使わない**系統誤差補正**（シミュレーションで較正した誤差表の減算）

を行う研究用リポジトリです。

> Evaluation of viewpoint-dependent bias in MediaPipe Pose against Unity ground truth
> (576 cameras), and a calibration-table correction that needs only the estimator's
> output at inference time.

## 主な結果

| 発見・成果 | 数値 | 解説 |
|---|---|---|
| 関節角の系統誤差は視方位ではなく**歩行位相に同期**する（歩行位相ロック） | カメラ 0.4 m 移動 ≒ 誤差波形 8 フレームずれ | [`docs/09`](docs/09_GAIT_PHASE_LOCKED_ERROR.md) |
| **world landmarks + 歩行位相索引の較正表**だけで別カメラ動画を補正 | 角度 MAE 膝 5.8〜8.7° / 肘 3.1〜7.7° | [`docs/11`](docs/11_WORLD_LANDMARK_MODEL.md) |
| 推論時の入力は「MediaPipe 出力 + 較正表」のみ | カメラ位置・画像座標・GT すべて不要 | 同上 |
| 視点ビンの符号付き補正（576 カメラ調査ライン） | \|Δθ\| 65.9 / 72.6 % 改善 | [`7_correction/`](7_correction/README.md) |

---

## 1. セットアップ

動作確認環境: Windows 11 / Python 3.12

```bash
git clone https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026.git
cd bias_evalutation_mediapipe_unity_ieej2026
pip install -r requirements.txt
```

## 2. どれを実行すればいいか

目的の違う 2 本のライン（＋旧データ用の 1 本）があります。

| やりたいこと | コマンド | 規模 |
|---|---|---|
| **補正モデルの結果を再現**する | `python run_world_phase_correction.py` | 動画 2 本（較正 1 + 検証 1） |
| **576 カメラのバイアス調査**をやり直す | `python run_v2_pipeline.py` | 全 576 カメラ |
| v1（旧 JPG データ・同期ずれあり）を扱う | `python run.py` | 旧データ |

### 補正モデル本線（推奨の入口）

```bash
python run_world_phase_correction.py --check   # 入力が揃っているか確認
python run_world_phase_correction.py           # 最終形（world + 位相索引）を再現
python run_world_phase_correction.py --history # 過程の実験も再現（docs/07, 08, 10）
```

最終形は `2_pose/world_landmark_model/` に結果（MAE 表・時系列プロット）を出力します。

### 576 カメラ調査ライン

```bash
python run_v2_pipeline.py                  # MediaPipe CSV 生成済み前提で解析 3〜7
python run_v2_pipeline.py --with-mediapipe # 動画から全部やり直す
python run_v2_pipeline.py --step N         # 単一ステップのみ（0=MP, 1=MAE, ... 7=較正）
```

## 3. リポジトリ構成

番号は処理順（1 入力 → 2 姿勢推定 → 3〜6 解析 → 7 補正 → 8 可視化）です。

```
.
├── run_world_phase_correction.py  # ★ 補正モデル本線の入口
├── run_v2_pipeline.py             # ★ 576 カメラ調査ラインの入口
├── run.py                         # v1（旧データ）の入口
├── config.py                      # DATASET_VERSION（v1/v2）と共通パス
├── requirements.txt
│
├── 0_start/            # 最小手順メモ
├── 1_input/            # [入力] カメラ別 video.mp4 + gt_joints.csv（576 視点）
├── 2_pose/             # [姿勢推定] MediaPipe 抽出 + 補正モデル各種（run_*.py）
├── 3_joint_angle_mae/  # [解析] GT vs MP の 3 点関節角 MAE
├── 4_max_angle_error/  # [解析] 最大角度誤差・ヒートマップ
├── 5_direction/        # [解析] 方向角・相関
├── 6_theta_check/      # [解析] 座標系・θ の検証テスト
├── 7_correction/       # [補正] 視点ビン較正フレームワーク（src/experiments/GUI）
├── 8_dashboard/        # [可視化] 統合ダッシュボード
├── 9_legacy_v1/        # [旧] v1 の入力 JPG と MediaPipe CSV
│
├── scripts/            # 補助（論文数値検証・出力掃除・部分実行）
├── docs/               # 時系列番号付きドキュメント（下記索引）
├── data_storage/       # 中間生成物・実験出力の実体（git 追跡外、README のみ追跡）
├── tools/              # GT アダプタ等
└── docker/
```

補足:

- **`data_storage/`** — 大容量の中間 CSV・実験出力はここに集約し、コード側の従来パス
  （`2_pose/mediapipe_processed_csv/` など）には Windows ジャンクションを張っています。
  対応表は [`data_storage/README.md`](data_storage/README.md)。クローン直後はこれらの
  中間物が存在しないため、再生成（`--with-mediapipe` など）が必要です。
- **`paper/`** — 論文原稿はリポジトリに含めていません（ローカル管理）。

## 4. データの入手と再現性

| データ | 同梱状況 |
|---|---|
| GT（`1_input/*/gt_joints.csv`、576 視点） | **リポジトリに同梱** |
| 入力動画（`video.mp4`、576 本） | 容量の都合で**非同梱**（`.gitignore` 対象） |
| MediaPipe 中間 CSV（v2） | 非同梱。動画があれば `run_v2_pipeline.py --step 0` で再生成 |
| MediaPipe 中間 CSV（v1） | Zenodo: DOI [10.5281/zenodo.19296530](https://doi.org/10.5281/zenodo.19296530) |

論文記載値とパイプライン出力の突合せ:

```bash
python scripts/verify_paper_data.py
```

## 5. データセット（v1 / v2）

ルート [`config.py`](config.py) の `DATASET_VERSION` で切り替えます（既定 `"v2"`）。

| | v1（旧） | v2（現行・既定） |
|--|---------|-----------------|
| 収集 | 2025-12 JPG 連写 | 2026-07 動画キャプチャ |
| カメラ数 | 約 289 | **576**（高さ 4 × 位置 144） |
| 入力 | `9_legacy_v1/input_photos/` | `1_input/`（video.mp4 + gt_joints.csv） |
| GT 同期 | 約 −3 フレームずれ | フレーム同期済み（0±2） |

高さ層は `Y=0.5 / 1.0 / 1.5 / 2.0`、フォルダ名は `CapturedFrames_{X}_{Y}_{Z}`（m）。
同期問題の詳細: [`docs/03`](docs/03_SYNC_ISSUE_REPORT.md)

## 6. ドキュメント索引（時系列順）

| # | ドキュメント | 内容 |
|---|---|---|
| 00 | [`00_PROGRESS.md`](docs/00_PROGRESS.md) | 進捗メモ・作業ログ |
| 01 | [`01_ZEVAL_DATASET_LAYOUT.md`](docs/01_ZEVAL_DATASET_LAYOUT.md) | 外部データセット対応 |
| 02 | [`02_REPRODUCTION.md`](docs/02_REPRODUCTION.md) | 再現手順 |
| 03 | [`03_SYNC_ISSUE_REPORT.md`](docs/03_SYNC_ISSUE_REPORT.md) | v1 同期ずれの原因と対策 |
| 04 | [`04_UNITY_VIDEO_CAPTURE_PROMPT.md`](docs/04_UNITY_VIDEO_CAPTURE_PROMPT.md) | Unity 動画キャプチャ仕様 |
| 05 | [`05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md`](docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md) | 関節誤差モンテカルロ解析 |
| 06 | [`06_MOVING_AVERAGE_NOISE_REJECTION.md`](docs/06_MOVING_AVERAGE_NOISE_REJECTION.md) | 移動平均ノイズ低減 |
| 07 | [`07_UV_PSEUDO_WORLD_CORRECTION.md`](docs/07_UV_PSEUDO_WORLD_CORRECTION.md) | UV 擬似ワールド補正・スケール較正 |
| 08 | [`08_GT_FREE_CHEATSHEET_MODEL.md`](docs/08_GT_FREE_CHEATSHEET_MODEL.md) | 較正表方式の再構築と別カメラ検証 |
| 09 | [`09_GAIT_PHASE_LOCKED_ERROR.md`](docs/09_GAIT_PHASE_LOCKED_ERROR.md) | 歩行位相ロック誤差の発見と解説 |
| 10 | [`10_PHASE_EXPLICIT_MODEL_PROPOSAL.md`](docs/10_PHASE_EXPLICIT_MODEL_PROPOSAL.md) | 位相明示型モデルの設計と検証 |
| 11 | [`11_WORLD_LANDMARK_MODEL.md`](docs/11_WORLD_LANDMARK_MODEL.md) | **world landmarks 単独補正（最終形）** |

## 7. ダッシュボード

| GUI | 起動 | URL | 用途 |
|-----|------|-----|------|
| 補正フレームワーク | `python 7_correction/dashboard/app.py` | http://127.0.0.1:8051/ | ビン構造・補正モデル・角度時系列 |
| 統合（旧） | `python 8_dashboard/app.py` | http://127.0.0.1:8050/ | 方向角・骨格の可視化 |

## 8. 補助スクリプト（`scripts/`）

| スクリプト | 用途 |
|---|---|
| `verify_paper_data.py` | 論文記載値とパイプライン CSV の突合せ |
| `clean_pipeline_outputs.py` | パイプライン出力の掃除（GT は保持） |
| `run_04_06_07.py` | `4_max_angle_error` / `6_theta_check` / `8_dashboard` の部分実行 |
| `run_full_pipeline.py` | `run.py` の後方互換ラッパ |

## 9. Docker

```bash
docker compose up --build   # → http://localhost:8050/
```

---

## 既知の注意点

- `3_joint_angle_mae` の層別 CSV（`Y=*/coordinate_angle_mae.csv`）が無いと
  `scripts/verify_paper_data.py` の表 1 検証はスキップされます（`run_v2_pipeline.py --step 1` で生成）。
- MediaPipe の検出は非決定要素を含むため、`--with-mediapipe` からの再生成では
  数値が公表値と微小に変わることがあります。
- 中間生成物の実体はすべて `data_storage/`（git 追跡外）にあります。コード側パスとの
  対応表は [`data_storage/README.md`](data_storage/README.md) を参照してください。
