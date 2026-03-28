# 08_theta_verification

121° 肘誤差の検証テスト用フォルダ。座標系ミスマッチの有無を確認する。

## ドキュメント

- **[MEDIAPIPE_COORDINATE_SYSTEM.md](MEDIAPIPE_COORDINATE_SYSTEM.md)**: MediaPipe Pose の座標系（公式仕様・論文・GitHub Issue）の整理と本研究への示唆

## 目的

- 肘の Δθ 約 ±121° が計算ミスか、座標系の違いか、本当の推定誤差かを切り分ける
- カメラごとの分布、error_3d との関係を分析
- MediaPipe がカメラ座標系で出力しているか検証

## 使い方

```bash
cd 08_theta_verification
python test_01_elbow_by_camera.py
python test_02_error_vs_angle.py
python test_03_single_camera_check.py
python test_04_coordinate_system.py   # 座標系検証
```

一括実行:

```bash
python run_all.py
```

## テスト概要

| テスト | 内容 |
|--------|------|
| test_01 | カメラごとの肘 Δθ 分布 |
| test_02 | error_3d 小 & \|Δθ\| 大のケース分析 |
| test_03 | 単一カメラごとの Δθ 統計 |
| test_04 | θ_gt のカメラ不変性、Δθ vs カメラ方位角、Δψ vs 仰角 |

## 前提

- `06_direction_detection/output/processed_data/detailed_results.csv` が存在すること
