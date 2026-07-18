# 初見ユーザー向け クイックスタート

最小手順です。詳細・フォルダ説明はルートの [`README.md`](../README.md) を参照してください。

**現在の既定データは v2（動画）です。** `config.py` で `DATASET_VERSION = "v2"` になっていることを確認してください。

---

## v2（推奨）

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

v1 は同期ずれ（約 −3 フレーム）があります。詳細: [`docs/SYNC_ISSUE_REPORT.md`](../docs/SYNC_ISSUE_REPORT.md)
