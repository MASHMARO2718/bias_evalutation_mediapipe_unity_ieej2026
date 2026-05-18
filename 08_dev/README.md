# 開発者・デバッグ用

通常の利用では不要です。

## オプションスクリプト

| フォルダ | スクリプト | 用途 |
|----------|------------|------|
| 06_theta_verification | test_*.py, run_all.py | 肘誤差検証テスト |
| paper | create_camera_layout.py, source/prepare_ieej_overleaf.py | 論文用図・IEEJ 同梱物同期 |

## 本番で必要なもの

- `run.py` … パイプライン実行
- `07_dashboard/app.py` … 可視化
- `verify_paper_data.py` … 論文検証

## 注意

- **03_joint_angle_mae**: `Y=.../coordinate_angle_mae.csv` が無いとステップ1・表1検証はスキップ／失敗する。`run_cal_mae.py` は各 Y サブフォルダに配置する運用。
- **docs/**: DOCKER.md, DIRECTORY_ANALYSIS_REPORT.md
