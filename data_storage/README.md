# data_storage — 中間生成物の置き場

スクリプト・README は各パッケージ側に残し、**再生成可能なデータだけ**をここに集約する。  
元パスには Windows ジャンクション / ハードリンクがあるため、既存スクリプトのデフォルトパスはそのまま使える。

```
data_storage/
├── README.md                          ← このファイル（git 追跡）
├── raw/                               ← 入力系の大容量アーカイブ（git 外）
│   └── v2/synced_joint_positions.csv  # 全カメラ結合マスター GT（参照用）
├── intermediate/                      ← パイプライン中間 CSV / 動画
│   ├── v1/
│   │   └── mediapipe_processed_csv/   # 旧 JPG 系 MediaPipe 出力
│   └── v2/
│       ├── mediapipe_processed_csv/   # 本線 576 カメラ
│       ├── mediapipe_processed_csv_additional/
│       ├── mediapipe_world_csv/
│       └── overlay_videos/
└── experiments/                       ← 実験・評価の出力
    ├── uv_pseudo_world_correction/
    │   ├── results_mad_k5/
    │   └── results_std_k3/
    ├── ma_noise_rejection/results/
    ├── error_mc_analysis/results/
    ├── gt_free_model/
    ├── world_landmark_model/
    ├── phase_explicit_model/
    ├── joint_angle_mae/
    ├── direction_detection/output/
    └── calibration/
        ├── outputs/                   # bias_tables / results / figures
        └── angle_timeseries/          # 09/scripts/output
```

## 対応するコード側パス（ジャンクション）

| コードから見えるパス | 実体 |
|---|---|
| `02_mediapipe_processed/mediapipe_processed_csv/` | `intermediate/v1/mediapipe_processed_csv/` |
| `02_mediapipe_v2/mediapipe_processed_csv/` | `intermediate/v2/mediapipe_processed_csv/` |
| `02_mediapipe_v2/uv_pseudo_world_correction/results_*/` | `experiments/uv_pseudo_world_correction/results_*/` |
| `05_direction_detection/output/` | `experiments/direction_detection/output/` |
| `09_calibration_framework/outputs/{bias_tables,results,figures}/` | `experiments/calibration/outputs/` |

v2 本線の入力は `01_input_videos/*/gt_joints.csv` + `video.mp4`。  
`raw/v2/synced_joint_positions.csv` は結合マスターの参照用アーカイブ（コードは参照しない）。
