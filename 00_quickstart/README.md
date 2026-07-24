# 初見ユーザー向け クイックスタート

最小手順です。詳細・フォルダ説明はルートの [`README.md`](../README.md) を参照してください。

**現在の既定データは v2（動画）です。** `config.py` で `DATASET_VERSION = "v2"` になっていることを確認してください。

---

## まずどちらのラインか選ぶ

| やりたいこと | 実行するもの |
|---|---|
| **論文の結果を再現**（動画 2 本・補正モデル本線） | `python run_world_phase_correction.py` |
| **576 カメラのバイアス調査**（下記 v2 手順） | `python run_v2_pipeline.py` |
| v1（旧 JPG） | `python run.py` |

補正モデル本線の最終形は world landmarks + 歩行位相索引です。
入力が揃っているかは `python run_world_phase_correction.py --check` で確認できます。
詳細: [`docs/11_WORLD_LANDMARK_MODEL.md`](../docs/11_WORLD_LANDMARK_MODEL.md)

---

## v2（576 カメラ調査ライン）

### 1. 依存パッケージ

```bash
pip install -r requirements.txt
```

### 2. データ

`01_input_videos/CapturedFrames_{X}_{Y}_{Z}/` に次があること:

- `video.mp4`
- `gt_joints.csv`

MediaPipe CSV は `02_mediapipe_v2/mediapipe_processed_csv/Y=*/`（未処理なら次のコマンドに `--with-mediapipe`）。

### 3. パイプライン

```bash
python run_v2_pipeline.py                  # MP 済み想定
python run_v2_pipeline.py --with-mediapipe # MP から全部
python run_v2_pipeline.py --no-dashboard   # GUI なし
```

### 4. ダッシュボード

| GUI | コマンド | URL |
|-----|----------|-----|
| 補正・時系列（推奨） | `python 09_calibration_framework/dashboard/app.py` | http://127.0.0.1:8051/ |
| 旧統合 GUI | `python 07_dashboard/app.py` | http://127.0.0.1:8050/ |

---

## v1（旧・JPG）

`config.py` で `DATASET_VERSION = "v1"` にしたうえで:

```bash
# 01_input_photos/CapturedFrames_*/ に JPG + synced GT
python run.py
python run.py --no-mediapipe   # 02 が既にある場合
python 07_dashboard/app.py     # http://127.0.0.1:8050/
```

v1 は同期ずれ（約 −3 フレーム）があります。詳細: [`docs/03_SYNC_ISSUE_REPORT.md`](../docs/03_SYNC_ISSUE_REPORT.md)
