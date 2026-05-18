# 再現性（Reproducibility）

解析リポジトリ: [github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026](https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026)

## 論文数値の検証

```bash
pip install -r requirements.txt
python verify_paper_data.py
```

- **表1（関節角 MAE）**: `03_joint_angle_mae/Y=0.5/`〜`Y=2.0/` 各フォルダの `coordinate_angle_mae.csv` を結合した統計と、`paper/source/IEEJ_ja/main.tex` の表を照合します。
- **方向角・股関節**: `05_direction_detection/output/processed_data/joint_summary.csv` および `detailed_results.csv`（後者は任意）を使用します。

## `detailed_results.csv` が無い場合

全フレーム・全カメラのプール観測 CSV（約 70 MB 級）はリポジトリに含めていません。次で再生成できます。

```bash
python 05_direction_detection/process_all_data.py
python 05_direction_detection/scripts/compute_correlation.py
```

前提: `synced_joint_positions.csv` と `02_mediapipe_processed/Y=*/CapturedFrames_*.csv` がローカルに揃っていること。

## 関節角 MAE の再計算

各高さ層ディレクトリで:

```bash
python 03_joint_angle_mae/Y=0.5/run_cal_mae.py
python 03_joint_angle_mae/Y=1.0/run_cal_mae.py
python 03_joint_angle_mae/Y=1.5/run_cal_mae.py
python 03_joint_angle_mae/Y=2.0/run_cal_mae.py
```

または `python run.py` のステップ 1（`02_` に MediaPipe CSV がある場合）。

## 完全な生データ（画像・全 CSV）

リポジトリサイズ制約のため、キャプチャ画像と中間 CSV の**全量**は別アーカイブでの公開とします。MediaPipe 処理済み CSV のアーカイブは Zenodo **DOI [10.5281/zenodo.19296530](https://doi.org/10.5281/zenodo.19296530)**（ZIP 展開後を `02_mediapipe_processed/` に合わせて配置）。
