# data_storage — 中間生成物・大容量データの置き場

スクリプト・各パッケージの README はリポジトリ側に残し、**再生成可能なデータ / 大容量成果物だけ**をここに集約する。  
元のコード側パスには Windows ジャンクション（またはハードリンク）があるため、既存スクリプトのデフォルトパスはそのまま動く。

Git には **この README のみ** を追跡する（`.gitignore`: `data_storage/**` + `!data_storage/README.md`）。

---

## リポジトリ全体との位置づけ

```
入力 (リポジトリ / ローカル)
  9_legacy_v1/input_photos/          … v1 JPG + synced GT
  1_input/          … v2 video.mp4 + gt_joints.csv（本線）
        │
        ▼  MediaPipe 等
中間生成物 ──► data_storage/intermediate/
        │
        ▼  03〜09 / 2_pose の実験スクリプト
実験出力 ────► data_storage/experiments/
        │
        ▼
コード・docs・paper/  … スクリプト・図表・論文（git 追跡）
```

| 領域 | リポジトリ上の役割 | data_storage 側 |
|------|-------------------|-----------------|
| 入力 | `01_input_*`（カメラ別 raw） | `raw/`（結合マスター等のアーカイブ） |
| MediaPipe 中間 CSV | `02_mediapipe_*` から参照（ジャンクション） | `intermediate/v1`, `intermediate/v2` |
| 実験スクリプト | `2_pose/run_*.py`, `analysis/`, README | （コードは移さない） |
| 実験結果 | 旧 `*/results*` パスから参照 | `experiments/*` |
| 下流パイプライン | `03`〜`09` が MP CSV / 出力を読む | 同上ジャンクション経由 |
| 設定 | ルート [`config.py`](../config.py) の `DATA_STORAGE` / `MP_DIR` | 実体はここに集約 |

---

## ディレクトリ構成

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

---

## 他フォルダとの対応（コード ↔ 実体）

| コード / ドキュメントから見えるパス | data_storage 実体 | 関連スクリプト・文書 |
|---|---|---|
| `9_legacy_v1/input_photos/` | （未移動・入力のまま） | v1: `run.py`, `docs/01`, `docs/03` |
| `1_input/` | `raw/v2/` に結合 GT のみ退避 | v2: `run_v2_pipeline.py`, `config.py` |
| `9_legacy_v1/mediapipe_processed/mediapipe_processed_csv/` | `intermediate/v1/mediapipe_processed_csv/` | `9_legacy_v1/mediapipe_processed/mediapipe_batch_processor.py` |
| `2_pose/mediapipe_processed_csv/` | `intermediate/v2/mediapipe_processed_csv/` | `mediapipe_video_processor.py`, `config.MP_DIR` |
| `2_pose/mediapipe_processed_csv_additional/` | `intermediate/v2/mediapipe_processed_csv_additional/` | GT-free / phase の検証カメラ |
| `2_pose/mediapipe_world_csv/` | `intermediate/v2/mediapipe_world_csv/` | `extract_world_landmarks.py` |
| `2_pose/overlay_videos/` | `intermediate/v2/overlay_videos/` | `overlay_mp_landmarks.py` |
| `2_pose/uv_pseudo_world_correction/results_*/` | `experiments/uv_pseudo_world_correction/results_*/` | `run_uv_pseudo_world_correction.py`, `docs/07`（README・`analysis/` はコード側） |
| `2_pose/ma_noise_rejection/results/` | `experiments/ma_noise_rejection/results/` | `run_ma_noise_rejection.py`, `docs/06` |
| `2_pose/error_mc_analysis/results/` | `experiments/error_mc_analysis/results/` | `run_error_mc_analysis.py`, `docs/05` |
| `2_pose/gt_free_model/`（生成物） | `experiments/gt_free_model/` | `run_gt_free_model.py`, `docs/08`（`analysis/` はコード側） |
| `2_pose/world_landmark_model/` | `experiments/world_landmark_model/` | `run_world_landmark_model.py`, `docs/11` |
| `2_pose/phase_explicit_model/` | `experiments/phase_explicit_model/` | `run_phase_explicit_model.py`, `docs/10` |
| `3_joint_angle_mae/joint_angle_mae_csv/*.csv` | `experiments/joint_angle_mae/` | `3_joint_angle_mae/*.py`, `run_v2_pipeline.py` |
| `5_direction/output/` | `experiments/direction_detection/output/` | `5_direction/`（scripts・README はコード側）, `docs/01` |
| `7_correction/outputs/{bias_tables,results,figures}/` | `experiments/calibration/outputs/` | `09_*/src/config.py`, `docs` 内 outputs README |
| `7_correction/scripts/output/` | `experiments/calibration/angle_timeseries/` | `09_*/scripts/plot_angle_timeseries.py` |
| `paper/`, `docs/` | （データは置かない） | 図表は必要分だけ paper 側にコピー |

---

## パイプライン上の依存（要約）

1. **入力** `1_input`（または v1 の `9_legacy_v1/input_photos`）
2. **中間** `intermediate/v*/mediapipe_processed_csv` ← MediaPipe
3. **角度 MAE** `experiments/joint_angle_mae` ← `3_joint_angle_mae`（MP CSV を読む）
4. **方向角** `experiments/direction_detection` ← `5_direction`
5. **補正フレームワーク** `experiments/calibration` ← `7_correction`（3・5 の集計を入力）
6. **v2 実験群**（UV / MA / ErrorMC / GT-free / world / phase）← `2_pose/run_*.py` が 2 の CSV と 1 の GT を読む

v2 本線のカメラ別 GT は `1_input/*/gt_joints.csv`。  
`raw/v2/synced_joint_positions.csv` は結合マスターの参照用アーカイブで、現行コードは参照しない。
