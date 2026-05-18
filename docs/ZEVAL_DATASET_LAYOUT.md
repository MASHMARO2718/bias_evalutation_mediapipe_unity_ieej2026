# Zeval_DataSet（ローカル作業コピー）の構造と本リポジトリとの対応

基準パス（開発者マシン上の例）: `C:\projects\MOTIONTRACK\Zeval_DataSet`

このディレクトリは論文・実験の**一次作業場**であり、番号付きフォルダ名や綴りの誤り（`ditection` / `proccesed` 等）が残ったままの状態で運用されてきた。  
**本リポジトリ**は GitHub 公開用にパイプラインを整理し、フォルダ番号と名称を学術的に説明しやすい形へリファクタリングしたものである。  
カメラ高さ別の MediaPipe CSV は **`02_mediapipe_processed/Y=0.5/` … `Y=2.0/`** に置く。リポジトリ直下に `0.5` のような数値フォルダだけがあるのは誤配置である（`.gitignore` で抑止）。

## トップレベル一覧

| 名前 | 内容・規模の目安 | 本リポジトリでの位置づけ |
|------|------------------|---------------------------|
| `synced_joint_positions.csv` | Unity GT 関節時系列（全カメラ共通） | ルート同名ファイルとして同型データを保持 |
| `1_Output_Photos/` | カメラ別フォルダ＋フレーム画像 | `01_input_photos/`（.gitignore で大容量除外推奨） |
| `2_medidapipe_proccesed/` | MediaPipe バッチ出力 CSV（綴りは歴史的誤記） | `02_mediapipe_processed/` |
| `3_Cal_MAE/` | カメラ別 `CapturedFrames_*.csv` と `coordinate_angle_comparison.py`、層別 `coordinate_angle_mae.csv` | `03_joint_angle_mae/`（計算ロジックは `coordinate_angle_comparison.py`） |
| `4_MAE_HEATMAP/` | MAE 統合・ヒートマップ用スクリプト、層別 CSV | `03_joint_angle_mae/` に統合 |
| `5_max_angle_error/` | 最大角度誤差・ヒートマップ | `04_max_angle_error/` |
| `6_Error_transition_for_each _frame/` | フレーム別遷移解析（スペース入りフォルダ名） | 本リポでは未番号付け移行（必要なら別途 `docs/` に手順のみ） |
| `7_direction_ditection/` | **Y 反転前**の方向角パイプライン・大量 `output`（旧世代） | 参照用。現行の再現は `11_` 側が論文と一致 |
| `8_Paper/` | 旧稿 md、図、相関フォルダなど | `paper/` に相当する素材の源流の一つ |
| `9_mediapipe_correction/` | 補正関連の試作 | 本リポでは `paper/archive` 等の文脈で言及のみ |
| `10_theta_verification/` | θ・座標系検証 | `06_theta_verification/` |
| `11_direction_ditection/` | **Y 反転修正後**の方向角・相関（論文の processed 系） | `05_direction_detection/` |

補足: `7_` と `11_` は同じ系統のパイプラインが二段あり、**論文（IEEJ_ja）の数値は `11_` 出力（本リポの `05_direction_detection/output`）と整合**させている。

## ファイル数の目安（参考）

- `1_Output_Photos/`: 数万～（画像主体）
- `7_direction_ditection/output/`: 非常に多い（旧出力の残存）
- `11_direction_ditection/output/processed_data/detailed_results.csv`: 約 70 MB 級（行数・関節×カメラ×フレーム）

## GitHub に含める／含めないの方針

| 種別 | 推奨 |
|------|------|
| スクリプト・設定 | リポジトリに含める |
| `coordinate_angle_mae.csv`（層別、数十 KB） | 論文表1再現用に**含めてよい** |
| `joint_summary.csv`、相関行列 CSV | **含めてよい**（小型） |
| `detailed_results.csv`（全観測） | **デフォルトは除外**（サイズ・GitHub 50MB ガイドライン）。再生成は `05_direction_detection/process_all_data.py` |
| 生画像・全フレーム MP CSV | **除外**。補完データセットは Zenodo 等の外部アーカイブ＋DOI を論文に記載するのが一般的 |

## データを Zeval から本リポへ同期するとき

1. MAE: `3_Cal_MAE/Y=*/coordinate_angle_mae.csv` → `03_joint_angle_mae/Y=*/`
2. 方向角サマリー・相関: `11_direction_ditection/output/` 配下の **CSV のみ**必要に応じてコピー
3. 計算根幹: `coordinate_angle_comparison.py` → `03_joint_angle_mae/coordinate_angle_comparison.py`

全文面の `detailed_results.csv` が必要な場合は、クローン後にパイプラインを実行するか、別途アーカイブから取得する（`docs/REPRODUCTION.md` 参照）。
