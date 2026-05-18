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

## ディレクトリ構成

番号付きフォルダは処理段階の目安です。**`run.py` が自動で回すのは** ステップ0（MediaPipe: `01`→`02`）〜ステップ5（`verify_paper_data.py`）と、完了時の **`07_dashboard` 起動（オプション）** までです。`06_theta_verification` と `08_dev` は手動実行用です。

```
├── run.py / config.py / verify_paper_data.py
├── synced_joint_positions.csv  # Unity GT（ローカル作業時。Git 方針は .gitignore 参照）
├── requirements.txt
├── docker-compose.yml
│
├── docs/                     # 再現性・Zeval 対応表
├── docker/
├── paper/
├── tools/                    # 移行スクリプトなど
│
├── 00_quickstart/
├── 01_input_photos/          # 入力画像（大容量のため通常 .gitignore）
├── 02_mediapipe_processed/   # MediaPipe バッチ出力（Y=0.5 … Y=2.0 配下に CSV）
├── 03_joint_angle_mae/       # 3点角 MAE（層別 CSV・統合・ヒートマップ）
├── 04_max_angle_error/       # 最大角度誤差
├── 05_direction_detection/   # 方向角・相関（論文 processed 系の主出力）
├── 06_theta_verification/    # θ・座標系検証（run.py 対象外）
├── 07_dashboard/             # Dash 可視化（run.py 末尾で起動可）
└── 08_dev/                   # 開発メモ（run.py 対象外）
```

MediaPipe の CSV は **リポジトリ直下ではなく** 常に `02_mediapipe_processed/Y=0.5/` のように `Y=` 接頭辞付きフォルダへ出ます（ルートに `0.5` だけのフォルダがあれば誤配置です）。

---

## Docker で実行

```bash
docker compose up --build
```

→ http://localhost:8050/ でダッシュボードにアクセス。`docker/` の Dockerfile を参照。

---

## 詳細

- **初見向け**: `00_quickstart/`
- **Docker**: `docker/`、`docker-compose.yml`
- **論文・考察**: `paper/`（Overleaf 用は `paper/source/main.tex` と `paper/source/IEEJ_*`）
- **開発者向け**: `08_dev/README.md`
- **旧パイプライン**: `run_full_pipeline.py` → `run.py` に委譲
- **ローカル作業コピー Zeval_DataSet との対応**: `docs/ZEVAL_DATASET_LAYOUT.md`
- **再現性・検証**: `docs/REPRODUCTION.md`、`python verify_paper_data.py`

### 公開用リポジトリについて

解析コードは上記 GitHub を正とします。生画像・全中間 CSV は容量のため Git に含めない想定で、不足分は Zenodo のデータセット（DOI）から補完します。

**MediaPipe 中間 CSV（ZIP）**  
DOI: [10.5281/zenodo.19296530](https://doi.org/10.5281/zenodo.19296530)  
展開後の `mediapipe_processed_csv/Y=0.5/` … `Y=2.0/` を `02_mediapipe_processed/` 配下に置くと、以降のパイプラインと整合します（詳細はレコードの Description を参照）。Zenodo レコードの **Related works** に GitHub URL を登録しておくと、データとコードの対応が明確になります。
