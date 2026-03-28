# Y軸反転の検証

06_direction_detection の coordinate_transform を変更せず、
07_theta_verification 内で Y 反転の効果を検証する。

## 実行

```bash
cd 07_theta_verification/coordinate_fix_verification
python verify_y_flip.py
```

## 出力

- `output/y_flip_joint_comparison.csv`: 関節ごとの Original vs Y-flip 比較

## 前提

- `06_direction_detection/output/processed_data/detailed_results.csv` が存在すること
