# プロジェクト進捗メモ

**最終更新**: 2026-07-17  
**目標**: IEEJ_02 論文の完成（同期修正済み v2 データでの再評価結果を反映）

---

## 現状サマリ

| 項目 | 状態 |
|------|------|
| 同期ずれの発見・文書化 | 完了（v1 で約 −3 フレーム） |
| Unity 動画キャプチャ化 | 完了（別エージェント／Unity_1019） |
| v2 生データ配置 | 完了 `01_input_videos/`（576 カメラ） |
| MediaPipe v2 | 完了 `02_mediapipe_v2/`（576 CSV） |
| パイプライン 03〜07, 09 | 完了（v2 データで再実行） |
| 位相ずれ再確認（時系列グラフ） | 完了（v1/v2 比較可能） |
| IEEJ_02 への数値差し替え | **未着手** |

---

## データセット構成（2026-07-16 整理）

`config.py` の `DATASET_VERSION` で切り替え（現在 `"v2"`）。

| | v1（旧） | v2（新） |
|--|---------|---------|
| 収集 | 2025-12 JPG 連写 | 2026-07 動画キャプチャ |
| 入力 | `01_input_photos/` | `01_input_videos/`（video.mp4 + gt_joints.csv） |
| MediaPipe | `02_mediapipe_processed/` | `02_mediapipe_v2/` |
| 同期 | 約 3 フレームずれ | 概ね 0±2 フレーム |

v1 処理結果の退避先: `_backup_v1_outputs_20260716_233457/`

関連ドキュメント:
- [`docs/SYNC_ISSUE_REPORT.md`](SYNC_ISSUE_REPORT.md) — ずれの原因分析
- [`docs/UNITY_VIDEO_CAPTURE_PROMPT.md`](UNITY_VIDEO_CAPTURE_PROMPT.md) — Unity 書き換え用プロンプト

---

## 実施した作業ログ

### 2026-07-16

1. **位相ずれ発見**  
   `plot_angle_timeseries.py` で R_Elbow（`CapturedFrames_4.0_1.0_0.0`）を可視化 → GT と MP が位相ずれ。相互相関で最良ラグ **−3 フレーム（≈99 ms）**。
2. **原因特定（Unity_1019 コード閲覧のみ）**  
   `FrameCapturer`（`WaitForEndOfFrame`）と `SyncedJointRecorder`（`Update` でカウント監視）のタイミング差 + JPG 同期 I/O。
3. **フォルダ整理**  
   - `01_input_videos/` 新設、動画データ移動  
   - `02_mediapipe_v2/` 新設  
   - `config.py` に `DATASET_VERSION` スイッチ追加  
   - 既存コード／v1 データは残置
4. **v2 実装**  
   - `02_mediapipe_v2/mediapipe_video_processor.py`  
   - `tools/gt_adapter.py`（Frame/frame_id 互換）  
   - `05_direction_detection` を per-camera GT 対応  
   - `run_v2_pipeline.py`（03〜07, 09 通し）

### 2026-07-16 夜〜17 未明

5. **MediaPipe 全 576 動画処理完了**（約 8 分）
6. **パイプライン通し**  
   - 03 3点角 MAE / 05 方向角 / 09 キャリブレーション → 完了  
   - 04 最大角誤差 / 06 θ検証 / 07 ダッシュボード → 追完了
7. **時系列グラフ再作成（同期確認）**  
   - 条件: `CapturedFrames_4.0_1.0_0.0`, Y=1.0, L/R Elbow・Knee  
   - 出力:  
     - v1: `09_calibration_framework/scripts/output/v1/`  
     - v2: `09_calibration_framework/scripts/output/v2/`

---

## v2 主な数値（参考・論文差し替え前）

### 同期（相互相関ラグ）同一カメラ比較

| 関節 | v1 | v2 |
|------|----|----|
| L_Elbow | （旧データで位相ずれ確認） | **0** |
| R_Elbow | **−3** | **−1** |
| L_Knee | — | **+1** |
| R_Knee | — | **+2** |

→ 一貫した −3 フレームずれは解消。残差は 0±2 フレーム程度。

### 符号付き補正（Model 4S, v2 再計算）

| split | θ 改善 | ψ 改善 |
|-------|--------|--------|
| known | ~66% | ~75% |
| unknown_Y2 | ~73% | ~76% |

（unsigned 補正は従来どおり悪化）

### 関節角 MAE（v2, 全カメラ平均の目安）

肘・膝 ~15°、腰 ~20°、肩 ~35°（詳細は `03_joint_angle_mae/joint_angle_error_statistics.csv`）

---

## 主要コマンド

```bash
# データセット切替
# config.py → DATASET_VERSION = "v1" | "v2"

# v2 パイプライン全体（MP 済みなら）
python run_v2_pipeline.py --no-dashboard

# 時系列グラフ（現在の DATASET_VERSION に応じて output/v1 or v2）
cd 09_calibration_framework
python scripts/plot_angle_timeseries.py \
  --camera CapturedFrames_4.0_1.0_0.0 --height 1.0 \
  --joints L_Elbow R_Elbow L_Knee R_Knee
```

---

## 次にやること（論文完成まで）

- [ ] v2 結果の数値を `paper/IEEJ_02`（英・日）に差し替え
- [ ] 必要なら図（MAE 比較・符号付き補正・時系列例）を v2 で再生成して `figs/` 更新
- [ ] 同期問題と動画キャプチャ化を実験手法セクションに追記
- [ ] v1/v2 時系列比較図を論文 or 補足に使うか判断
- [ ] Overleaf / 提出用 PDF の最終確認

論文メモ（タイトル・要旨・キーワード）:  
`paper/IEEJ_02/IEEJ_ja_calibration/PAPER_MEMO.md`
