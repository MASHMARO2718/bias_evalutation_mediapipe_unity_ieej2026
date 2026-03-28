# MotionTrack データ分析

GroundTruth（Unity）と MediaPipe の3D関節データを比較・可視化するパイプラインです。

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
| `python run.py` | 全パイプライン（01画像→09ダッシュボード） |
| `python run.py --no-dashboard` | ダッシュボード起動なし |
| `python run.py --no-mediapipe` | 02 以降のみ（02 が既にある場合） |
| `python run.py --dashboard` | 06 のみ＋ダッシュボード起動（約1分） |
| `python run.py --step 0` | MediaPipe のみ |
| `python run.py --step 4` | ステップ4のみ |
| `python 08_dashboard/app.py` | 可視化ダッシュボード起動 |

---

## ディレクトリ構成

```
├── run.py                    # メイン実行
├── config.py                 # 共通設定
├── requirements.txt
├── docker-compose.yml
│
├── docs/                     # ドキュメント（DOCKER.md 等）
├── docker/                   # Docker 定義
├── paper/                    # 論文原稿・図・IEEJ Overleaf 用サブフォルダ
│
├── 00_quickstart/            # 初見ユーザー向け
├── 02_mediapipe_processed/   # 入力データ
├── 03_cal_mae/               # 3点角MAE
├── 04_mae_heatmap/           # MAE統計
├── 05_max_angle_error/       # 最大角度誤差
├── 06_direction_detection/   # 方向角分析・出力
├── 07_theta_verification/    # θ検証・座標系確認
├── 08_dashboard/             # 可視化
└── 09_dev/                   # 開発者向け
```

---

## Docker で実行

```bash
docker compose up --build
```

→ http://localhost:8050/ でダッシュボードにアクセス。詳細は `docs/DOCKER.md` を参照。

---

## 詳細

- **初見向け**: `00_quickstart/`
- **Docker**: `DOCKER.md`
- **論文・考察**: `paper/`（Overleaf 用は `paper/source/main.tex` と `paper/source/IEEJ_*`）
- **開発者向け**: `09_dev/README.md`
- **旧パイプライン**: `run_full_pipeline.py` → `run.py` に委譲
