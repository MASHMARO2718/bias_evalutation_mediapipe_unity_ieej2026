# MotionTrack データ分析

GroundTruth（Unity）と MediaPipe の3D関節データを比較・可視化するパイプラインです。

**ソースコード（GitHub）:** [MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026](https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026)  
`git clone https://github.com/MASHMARO2718/bias_evalutation_mediapipe_unity_ieej2026.git`

---

## クイックスタート（3コマンド）

```bash
# 1. 依存パッケージのインストール
pip install -r requirements.txt

# 2. データ処理（画像があればパイプラインを最後まで自動実行）
python run.py

# 3. ダッシュボードは自動起動（--no-dashboard でスキップ可）
```

ブラウザで **http://127.0.0.1:8050/** を開いてください。

※ `01_input_photos/` に画像がなければ MediaPipe をスキップし、02 以降を実行。`--no-mediapipe` で明示的にスキップも可能。

---

## コマンド一覧

| コマンド | 説明 |
|----------|------|
| `python run.py` | 全パイプライン（01→02→03〜05→検証→07ダッシュボード既定ON） |
| `python run.py --no-dashboard` | ダッシュボード起動なし |
| `python run.py --no-mediapipe` | 02 以降のみ（02 が既にある場合） |
| `python run.py --dashboard` | 方向角処理（ステップ4）のみ＋ダッシュボード起動（約1分） |
| `python run.py --step 0` | MediaPipe のみ |
| `python run.py --step 4` | ステップ4のみ |
| `python 07_dashboard/app.py` | 可視化ダッシュボード起動 |

---

## データセットバージョン

`config.py` の `DATASET_VERSION` を切り替えるだけで v1（旧）/v2（新）を使い分けられます。

```python
# config.py
DATASET_VERSION = "v1"   # 旧データ（JPG・同期ずれあり）
# DATASET_VERSION = "v2" # 新データ（動画・フレーム同期済み）
```

| | v1（旧） | v2（新） |
|--|---------|---------|
| 収集日 | 2025-12 | 2026-07 |
| 入力形式 | `01_input_photos/` JPG × 107枚/カメラ | `01_input_videos/` video.mp4 + gt_joints.csv/カメラ |
| GT 形式 | `synced_joint_positions_*.csv`（Unity グローバル時刻）| `gt_joints.csv`（frame_id/time_sec 同期済み）|
| 同期 | 約 3 フレームのずれあり（IEEJ_01 論文のデータ） | フレーム完全同期 |
| MediaPipe 出力 | `02_mediapipe_processed/` | `02_mediapipe_v2/`（処理後に生成）|

詳細: [`docs/SYNC_ISSUE_REPORT.md`](docs/SYNC_ISSUE_REPORT.md)

---

## ディレクトリ構成

番号付きフォルダは処理段階の目安です。**`run.py` が自動で回すのは** ステップ0（MediaPipe: `01`→`02`）〜ステップ5（`verify_paper_data.py`）と、完了時の **`07_dashboard` 起動（オプション）** までです。`06_theta_verification` と `08_dev` は手動実行用です。

```
├── run.py / config.py / verify_paper_data.py
├── requirements.txt
├── docker-compose.yml
│
├── docs/                     # 再現性・Zeval 対応表・同期ずれレポート
├── docker/
├── paper/
├── tools/                    # 移行スクリプトなど
│
├── 00_quickstart/
│
├── # ─── v1 データ（旧・JPG キャプチャ・2025-12 収集） ────────────────────
├── 01_input_photos/          # v1 raw: JPG × 107枚 + synced_joint_positions_*.csv
├── 02_mediapipe_processed/   # v1 MediaPipe 出力（Y=0.5 … Y=2.0 配下に CSV）
│
├── # ─── v2 データ（新・動画キャプチャ・2026-07 収集） ────────────────────
├── 01_input_videos/          # v2 raw: video.mp4 + gt_joints.csv（フレーム同期済み）
├── 02_mediapipe_v2/          # v2 MediaPipe 出力（処理後に生成される）
│
├── # ─── 処理スクリプト（v1/v2 共通・config.py で切り替え） ────────────────
├── 03_joint_angle_mae/       # 3点角 MAE（層別 CSV・統合・ヒートマップ）
├── 04_max_angle_error/       # 最大角度誤差
├── 05_direction_detection/   # 方向角・相関（論文 processed 系の主出力）
├── 06_theta_verification/    # θ・座標系検証（run.py 対象外）
├── 07_dashboard/             # Dash 可視化（run.py 末尾で起動可）
├── 08_dev/                   # 開発メモ（run.py 対象外）
└── 09_calibration_framework/ # パラメトリック補正フレームワーク（研究提案実装）
```

MediaPipe の CSV は常に `02_mediapipe_processed/Y=0.5/`（v1）または `02_mediapipe_v2/mediapipe_processed_csv/Y=0.5/`（v2）のように `Y=` 接頭辞付きフォルダへ出ます。

---

## Docker で実行

```bash
docker compose up --build
```

→ http://localhost:8050/ でダッシュボードにアクセス。`docker/` の Dockerfile を参照。

---

## 補正フレームワーク（09_calibration_framework）

MediaPipe Pose の視点依存バイアスをパラメトリックに補正する研究実装です。  
詳細: [`09_calibration_framework/README.md`](09_calibration_framework/README.md)

### ダッシュボード（ブラウザで動作・Cursor 不要）

```bash
cd 09_calibration_framework/dashboard
pip install -r requirements.txt
python app.py
# → http://localhost:8051
```

| タブ | 内容 |
|---|---|
| Overview | モデル比較・per-layer MAE・評価サマリー |
| Bin Explorer | カメラ位置 × 方位角ビン構造のインタラクティブ可視化 |
| Linear Model | 局所線形 R² ヒートマップ・OLS 係数 β |
| Grid Search | ハイパーパラメータ探索結果 |
| Bin Reference | 全ビン種別（方位角・高さ・距離）の詳細一覧 |

### 補正パイプラインの実行

```bash
cd 09_calibration_framework
python experiments/run_calibration.py   # Phase A: バイアステーブル生成
python experiments/grid_search.py       # bin 設定の最適化（任意）
python experiments/run_evaluation.py    # Phase B: 全モデル評価
```

出力は `09_calibration_framework/outputs/` に保存されます。  
実行結果レポート: [`09_calibration_framework/outputs/RUN_REPORT.md`](09_calibration_framework/outputs/RUN_REPORT.md)

---

## 詳細

- **初見向け**: `00_quickstart/`
- **Docker**: `docker/`、`docker-compose.yml`
- **論文・考察**: `paper/`（下記「論文フォルダ」参照）
- **開発者向け**: `08_dev/README.md`
- **旧パイプライン**: `run_full_pipeline.py` → `run.py` に委譲
- **ローカル作業コピー Zeval_DataSet との対応**: `docs/ZEVAL_DATASET_LAYOUT.md`
- **再現性・検証**: `docs/REPRODUCTION.md`、`python verify_paper_data.py`
- **補正フレームワーク**: `09_calibration_framework/README.md`、`09_calibration_framework/CODE_REVIEW.md`

---

## 論文フォルダ

```
paper/
├── IEEJ_01/                    論文 1: MediaPipe バイアス評価（提出済み）
│   ├── README.md               LaTeX コンパイル手順・Overleaf 準備
│   ├── source/
│   │   ├── IEEJ_en/            英語版 LaTeX ソース（main.tex, ieej-e.cls, figs/）
│   │   └── IEEJ_ja/            日本語版 LaTeX ソース
│   └── submitted/              提出済み PDF・スライド
│
└── IEEJ_02/                    論文 2: 局所線形補正フレームワーク（執筆中）
    ├── README.md               論文 2 全体説明・コンパイル手順
    ├── IEEJ_en_calibration/    英語版（main.tex, ieej-e.cls, figs/） ← 主論文
    │   └── README.md           図一覧・セクション構成・キーワード
    └── IEEJ_ja_calibration/    日本語版（main.tex, generate_figs.py, PAPER_MEMO.md）
```

### 論文 2 のコンパイル

```bash
cd paper/IEEJ_02/IEEJ_en_calibration
pdflatex main.tex && pdflatex main.tex
```

### 公開用リポジトリについて

解析コードは上記 GitHub を正とします。生画像・全中間 CSV は容量のため Git に含めない想定で、不足分は Zenodo のデータセット（DOI）から補完します。

**MediaPipe 中間 CSV（ZIP）**  
DOI: [10.5281/zenodo.19296530](https://doi.org/10.5281/zenodo.19296530)  
展開後の `mediapipe_processed_csv/Y=0.5/` … `Y=2.0/` を `02_mediapipe_processed/` 配下に置くと、以降のパイプラインと整合します（詳細はレコードの Description を参照）。Zenodo レコードの **Related works** に GitHub URL を登録しておくと、データとコードの対応が明確になります。
