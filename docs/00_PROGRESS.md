# プロジェクト進捗メモ

**最終更新**: 2026-07-19  
**目標**: IEEJ_02 論文の完成（同期修正済み v2 データでの再評価結果を反映）

---

## 現状サマリ

| 項目 | 状態 |
|------|------|
| 同期ずれの発見・文書化 | 完了（v1 で約 −3 フレーム） |
| Unity 動画キャプチャ化 | 完了（別エージェント／Unity_1019） |
| v2 生データ配置 | 完了 `1_input/`（576 カメラ） |
| MediaPipe v2 | 完了 `2_pose/`（576 CSV） |
| パイプライン 03〜07, 09 | 完了（v2 データで再実行） |
| 位相ずれ再確認（時系列グラフ） | 完了（v1/v2 比較可能） |
| IEEJ_02 への数値差し替え | **未着手** |

---

## データセット構成（2026-07-16 整理）

`config.py` の `DATASET_VERSION` で切り替え（現在 `"v2"`）。

| | v1（旧） | v2（新） |
|--|---------|---------|
| 収集 | 2025-12 JPG 連写 | 2026-07 動画キャプチャ |
| 入力 | `9_legacy_v1/input_photos/` | `1_input/`（video.mp4 + gt_joints.csv） |
| MediaPipe | `9_legacy_v1/mediapipe_processed/` | `2_pose/` |
| 同期 | 約 3 フレームずれ | 概ね 0±2 フレーム |

v1 処理結果の退避先: `_backup_v1_outputs_20260716_233457/`

関連ドキュメント:
- [`docs/03_SYNC_ISSUE_REPORT.md`](03_SYNC_ISSUE_REPORT.md) — ずれの原因分析
- [`docs/04_UNITY_VIDEO_CAPTURE_PROMPT.md`](04_UNITY_VIDEO_CAPTURE_PROMPT.md) — Unity 書き換え用プロンプト

---

## 実施した作業ログ

### 2026-07-16

1. **位相ずれ発見**  
   `plot_angle_timeseries.py` で R_Elbow（`CapturedFrames_4.0_1.0_0.0`）を可視化 → GT と MP が位相ずれ。相互相関で最良ラグ **−3 フレーム（≈99 ms）**。
2. **原因特定（Unity_1019 コード閲覧のみ）**  
   `FrameCapturer`（`WaitForEndOfFrame`）と `SyncedJointRecorder`（`Update` でカウント監視）のタイミング差 + JPG 同期 I/O。
3. **フォルダ整理**  
   - `1_input/` 新設、動画データ移動  
   - `2_pose/` 新設  
   - `config.py` に `DATASET_VERSION` スイッチ追加  
   - 既存コード／v1 データは残置
4. **v2 実装**  
   - `2_pose/mediapipe_video_processor.py`  
   - `tools/gt_adapter.py`（Frame/frame_id 互換）  
   - `5_direction` を per-camera GT 対応  
   - `run_v2_pipeline.py`（03〜07, 09 通し）

### 2026-07-16 夜〜17 未明

5. **MediaPipe 全 576 動画処理完了**（約 8 分）
6. **パイプライン通し**  
   - 03 3点角 MAE / 05 方向角 / 09 キャリブレーション → 完了  
   - 04 最大角誤差 / 06 θ検証 / 07 ダッシュボード → 追完了
7. **時系列グラフ再作成（同期確認）**  
   - 条件: `CapturedFrames_4.0_1.0_0.0`, Y=1.0, L/R Elbow・Knee  
   - 出力:  
     - v1: `7_correction/scripts/output/v1/`  
     - v2: `7_correction/scripts/output/v2/`

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

肘・膝 ~15°、腰 ~20°、肩 ~35°（詳細は `3_joint_angle_mae/joint_angle_error_statistics.csv`）

### 2026-07-18〜19（UV 擬似ワールド補正 — 詳細は [`07_UV_PSEUDO_WORLD_CORRECTION.md`](07_UV_PSEUDO_WORLD_CORRECTION.md)）

1. **GT フリー時系列補正の実装**（`2_pose/run_uv_pseudo_world_correction.py`）
   UV 大域位置から擬似ワールドを構成 → 進行方向直交成分を移動平均+3σ で置換。
   全 576 カメラで実行（484 処理 / 92 は遠方で MP 検出なし）。
2. **前提「誤差は奥行きに乗る」を定量確認**: 補正ベクトルの 87% が視線方向。
3. **自己マスキング発見 → MAD 化**: 移動標準偏差はスパイク自身で閾値が膨らみ
   本物のグリッチと境界ノイズが分離不能（比率とも 1.14）。移動 MAD で分離
   （グリッチ 16.6 vs 通常 1.9）。推奨構成 `--robust-sigma --k-sigma 5`。
4. **腰軌跡 V 字誤差の原因特定とスケール較正**: MP z が体幹長を 54% 水増し
   + 事前値の定義不一致 → 2D 体幹長+実効定数 0.582 m（`--torso-2d`）で
   腰軌跡誤差 0.581 → **0.067 m**（真横 3 m）。
5. **膝の奥行き誤差の構造分解**: ビン定数バイアス + ARIMA(2,0,2) の滑らか波
   + 白色ノイズ ±0.1 m に完全分解。bin+ARIMA 減算で |e_X| **82〜90%減**、
   膝角度 MAE 26〜43% 改善。鏡映（深度左右曖昧性）が bin バイアスの符号を
   反転させる問題を発見（配備の前提条件として文書化）。
6. **副産物**: 関節マッピング監査で肩の GT 対応誤り
   （`LeftShoulder`=鎖骨 → 正しくは `LeftUpperArm`）を発見。
   `5_direction/scripts/data_loader.py:90` にも同じ誤りがあり、
   **論文数値に波及するため修正は要判断**。
7. docs/ を時系列番号付きにリネーム（本ファイル含む）、README・参照を一括更新。
8. **GT フリーモデルの再構築と別カメラ検証**（詳細は
   [`08_GT_FREE_CHEATSHEET_MODEL.md`](08_GT_FREE_CHEATSHEET_MODEL.md)）
   推論時 GT ゼロのパイプライン（UV 擬似ワールド → 中央値+4×MAD →
   カルマン RTS → 3 点角 → 進行位置索引のバイアス表を線形補間で減算）を
   `2_pose/run_gt_free_model.py` に実装。(3.0,1.0,0.0) で較正した
   カンニングペーパーを別動画 (3.2,1.1,0.4) に適用し、角度 MAE
   膝 42〜46% / 肘 71〜78% 改善（完全 out-of-sample）。
   **系統誤差は視方位ロックでなく歩行位相ロック**という知見を獲得。
9. 歩行位相ロック誤差の詳細解説を
   [`09_GAIT_PHASE_LOCKED_ERROR.md`](09_GAIT_PHASE_LOCKED_ERROR.md) に文書化。
   改訂版アブストラクト＋キーワード候補 10 個は docs/08 §7、README に
   主要結果ハイライトとドキュメント索引を新設。
10. 位相明示型モデル（ヒルベルト位相＋テンプレート照合で位相と左右を同時確定）
    の設計提案を [`10_PHASE_EXPLICIT_MODEL_PROPOSAL.md`](10_PHASE_EXPLICIT_MODEL_PROPOSAL.md)
    に文書化し、同日 **実装・検証完了**（`run_phase_explicit_model.py`、同 §7）。
    結果: 位相のみ索引は不十分（誤差に大きな非周期成分）。アンカー破壊テスト
    （冒頭25フレーム切り落とし+振り直し）で docs/08 現行方式は膝が raw より
    悪化するまで崩壊する一方、**方位ベース絶対 z 索引（z-bearing）が全関節
    最良で生存**（膝 8.2〜11.2° / 肘 5.9〜7.2°）。テンプレート照合による
    左右スワップ判定も動作確認。配備推奨は z-bearing 主・2 階建て将来拡張。
11. **構成刷新版の論文下書き（案B）を作成**: `paper/IEEJ_02/IEEJ_ja_gtfree/`
    （main.tex 全文・PAPER_MEMO.md・図 5 枚）。docs/07〜10 の成果を
    「はじめに→関連研究→提案手法→実験設定→結果→考察→むすび」の
    7 節構成に本文化。既存稿 `IEEJ_ja_calibration/` は無変更。
12. **world landmarks 単独補正の実証**（詳細は
    [`11_WORLD_LANDMARK_MODEL.md`](11_WORLD_LANDMARK_MODEL.md)）:
    UV 擬似ワールドを使わず pose_world_landmarks だけで補正パイプラインを
    構成・検証。world raw は UV raw より大幅に高品質（L_ELBOW 40.9→14.3° 等）で、
    ゆっくり成分が GHUM フィットで消えるため**位相のみの索引が成立**。
    W-phase が全関節で UV 系最良を更新（膝 5.8〜8.7° / 肘 3.1〜7.7°）し、
    推論時入力は「MP world 出力+較正表」のみ（カメラ情報・画像座標・
    フレーム原点すべて不要）。論文下書き §3 は world 中心への再構成が必要。
13. **論文下書きを第 2 稿に全面改稿**（`paper/IEEJ_02/IEEJ_ja_gtfree/`）:
    主軸を「world landmarks + 位相索引」に変更し、UV 系の結果は
    「発見の過程（位相ロック同定・アンカー問題）」として §5.1–5.2 に整理。
    全表・図に座標系（画像系/world）を明記して数値の混同を排除。
    アブストラクト（和英）・キーワード・PAPER_MEMO（200字要旨・50語）も
    最終結果（膝 5.8〜8.7° / 肘 3.1〜7.7°、推論時入力は推定器出力+較正表のみ）
    ベースに更新。フォーマット規定（`IEEJ_format_instruction`）に準拠させ、
    実験目的の節・全体フロー図（段抜き）を追加、専門語を平易化。
14. **CANDAR 投稿版（英文）を作成**: `paper/IEEJ_02/CANDAR_gtfree/`
    （IEEEtran conference・US-letter 2 段組 + IEEEtran.bst + refs.bib 22 件）。
    内容は和文版と同一。CANDAR 規定（is-candar.org/paper_format）に合わせ
    **ブラインド査読対応**（著者情報を匿名化、自己引用を三人称に修正）、
    図を 6→4 点に削減し本文も圧縮。ページ数（Regular 5〜7）は要確認。

### 2026-07-24（フォルダ再編・可視性向上）

15. **入口スクリプトの新設**: 補正モデルのライン（docs/07〜11）を通す唯一の
    入口 `run_world_phase_correction.py` を新設。既定は最終形（world landmarks
    + 歩行位相索引 = W-phase）だけを再現し、`--history` で過程の実験を再現、
    `--check` で入力の有無を確認。README・quickstart・本メモを「補正モデル本線 /
    576 カメラ調査 / v1」の 3 ライン案内に組み替え。空だった `08_dev/` は削除。
16. **役割別フォルダ再編**（番号衝突の解消と可視性向上）。旧→新の対応:

    | 旧 | 新 |
    |----|----|
    | `01_input_videos` | `1_input` |
    | `02_mediapipe_v2` | `2_pose`（姿勢抽出＋補正モデル） |
    | `03_joint_angle_mae` | `3_joint_angle_mae` |
    | `04_max_angle_error` | `4_max_angle_error` |
    | `05_direction_detection` | `5_direction` |
    | `06_theta_verification` | `6_theta_check` |
    | `09_calibration_framework` | `7_correction` |
    | `07_dashboard` | `8_dashboard` |
    | `01_input_photos` | `9_legacy_v1/input_photos` |
    | `02_mediapipe_processed` | `9_legacy_v1/mediapipe_processed` |

    参照 506 箇所を一括更新、`data_storage` へのジャンクション 17 本を新パスに
    貼り直し、`.gitignore` / `config.py` を更新。両入口（補正本線 `--step 1`、
    調査ライン `--step 1`）の再実行で動作確認済み（EXIT 0、論文数値を再現）。

---

## 主要コマンド

```bash
# データセット切替
# config.py → DATASET_VERSION = "v1" | "v2"

# 補正モデル本線（論文の最終結果 W-phase・動画 2 本）
python run_world_phase_correction.py --check   # 入力確認
python run_world_phase_correction.py           # 最終形を再現
python run_world_phase_correction.py --history # 過程の実験（docs/07, 08, 10）

# 576 カメラ調査ライン全体（MP 済みなら）
python run_v2_pipeline.py --no-dashboard

# 時系列グラフ（現在の DATASET_VERSION に応じて output/v1 or v2）
cd 7_correction
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
