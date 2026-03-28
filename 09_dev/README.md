# 開発者・デバッグ用

通常の利用では不要です。

## オプションスクリプト

| フォルダ | スクリプト | 用途 |
|----------|------------|------|
| 07_theta_verification | test_*.py, run_all.py | 肘誤差検証テスト |
| paper | create_camera_layout.py, source/prepare_ieej_overleaf.py | 論文用図・IEEJ 同梱物同期 |

## 本番で必要なもの

- `run.py` … パイプライン実行
- `08_dashboard/app.py` … 可視化
- `verify_paper_data.py` … 論文検証

## 注意

- **03_cal_mae**: フォルダが存在しない場合、run.py のステップ1はスキップされます。表1検証・04_mae_heatmap には 03_cal_mae の出力が必要です。
- **04_mae_heatmap**: check_*, analyze_* は削除済み
- **docs/**: DOCKER.md, DIRECTORY_ANALYSIS_REPORT.md
