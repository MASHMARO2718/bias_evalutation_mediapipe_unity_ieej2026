# 05_direction_detection

MediaPipe の Y 軸反転を適用した正しい計算ロジック。方向角誤差・相関分析・ダッシュボードを提供。

## 変更点

- **Y 軸反転**: MediaPipe は画像座標で Y 下向き正、Unity GT は Y 上向き正。相対座標化時に MediaPipe の Y を反転して揃える。

## 実行

```bash
cd 05_direction_detection
python process_all_data.py
```

## 出力

7 と同様の CSV が `output/processed_data/` に出力される：

- `detailed_results.csv`
- `frame_camera_summary.csv`
- `joint_summary.csv`
