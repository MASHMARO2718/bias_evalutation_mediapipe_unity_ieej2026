# 同期ずれ問題レポート — GT と撮影フレームのタイミング不一致

**発見日**: 2026-07-16  
**発見者**: 解析中に時系列グラフの位相ずれを目視確認  
**影響範囲**: 全評価データ（IEEJ_01・IEEJ_02 双方）  

---

## 概要

Unity GT（`synced_joint_positions.csv`）と MediaPipe が処理した画像フレームの間に、
**約 3 フレーム（≈ 99 ms）の時刻ずれ**が存在することを発見した。

これは「補正が正しく機能しているか」を確認するためにフレームごとの角度時系列グラフを
可視化したことで発覚した（`09_calibration_framework/scripts/plot_angle_timeseries.py`）。

---

## 発見のきっかけ

`CapturedFrames_4.0_1.0_0.0`（方位角 90°, 側面ビュー）における R_Elbow の角度時系列グラフで、
GT 曲線（緑）と MediaPipe 曲線（赤）が **同じ形をしているにもかかわらず位相がずれている**
ことが目視で明らかになった。

```
GT（緑）  :  ↑──╮╭──↑──╮╭──↑
MP（赤）  :    ↑──╮╭──↑──╮╭──↑
                  ↑
                  約3フレーム遅れ
```

---

## 定量的な測定

**手法**: R_Elbow の GT/MP 角度時系列に対して相互相関（cross-correlation）を計算し、
ラグが最大となる点を求めた。

```
使用カメラ : CapturedFrames_4.0_1.0_0.0 (Y=1.0, azimuth=90°)
関節       : R_Elbow
共通フレーム: 105 フレーム
GT サンプリング: 30.3 fps（Time ステップ = 0.033 s）

測定結果
─────────────────────────────────────
最良ラグ: −3 フレーム
（MP が GT より 3 フレーム先行している）
時間換算: 3 × (1/30.3) ≈ 99 ms
─────────────────────────────────────
```

---

## 根本原因：個別フレーム静止画キャプチャ方式の設計上の問題

### コードレベルで特定した原因（Unity_1019 プロジェクト）

**`FrameCapturer.cs`（画像保存）の処理順：**
```csharp
// WaitForEndOfFrame() → CaptureFrame() で画像保存 + capturedFrameCount++
yield return new WaitForEndOfFrame();
CaptureFrame();  // File.WriteAllBytes() でメインスレッドをブロック
```

**`SyncedJointRecorder.cs`（GT 記録）の処理順：**
```csharp
// Update() で FrameCapturer のカウントが増えたか検知 → RecordFrame()
private void Update()
{
    if (frameCapturer.GetCapturedFrameCount() > lastCapturedFrameCount)
        RecordFrame(i);  // ← この時点では Animator がすでに次フレームに進んでいる
}
```

**フレーム単位のずれの発生メカニズム：**
```
フレーム N:
  ① Update()  → capturedFrameCount = N-1 → GT 記録なし
  ② WaitForEndOfFrame() → 画像保存（フレーム N の姿勢）, count = N

フレーム N+1:
  ① Update()  → count が N に増加 → RecordFrame() 呼び出し
               しかしこの時点で Animator はフレーム N+1 に進んでいる
               → フレーム N+1 の骨格座標が記録される！

結果: 画像＝フレーム N の姿勢、GT＝フレーム N+1 の姿勢 → 最低 1 フレームずれ
さらに File.WriteAllBytes() のメインスレッドブロックが累積して実測 3 フレームずれ
```

**問題点:**
- `Update()` と `WaitForEndOfFrame()` の実行順の違いにより 1 フレームずれが構造的に発生
- `File.WriteAllBytes()` が同期 I/O でメインスレッドをブロックし、遅延が累積する

### MediaPipe 側の設定

`static_image_mode=True` で各フレームを独立に処理しているため、MediaPipe 自体による
タイムラグは発生しない。ずれはすべて **Unity キャプチャ側** に起因する。

---

## 現行データへの影響

| 項目 | 影響 |
|------|------|
| Joint Angle MAE の評価 | 約 3 フレームずれた姿勢同士の角度差を計算している |
| 局所線形 R² の計算 | GT との誤差がずれているため、R² の絶対値が過小評価の可能性あり |
| 論文 IEEJ_01 の数値 | 同様のデータ収集方法 → 同じ影響を受けている |

**ただし** 方向角誤差の相関分析（`delta_theta_deg`, `delta_psi_deg`）は
「どの視点でどの方向に誤差が大きいか」という空間的な傾向を見るものであり、
数フレームのずれはこの構造的な傾向には大きく影響しないと考えられる。

---

## 暫定的な対処法（現行データ）

フレームシフト補正を適用することで近似的に同期させることが可能：

```python
# GT を 3 フレーム後ろにシフト（= MP と同時刻の姿勢に対応させる）
gt_aligned = gt.assign(frame_id=gt["frame_id"] + LAG)  # LAG = 3
```

ただしこれは暫定措置であり、**根本的な解決にはなっていない**。

---

## 推奨される解決策：動画キャプチャ方式への移行

### 要件

1. **フレーム番号の完全同期**  
   GT 記録と画像/動画フレームが同一の `Time.frameCount` に紐づく

2. **Unity Recorder を使用した動画エクスポート**  
   Unity の公式 Recorder Package（`com.unity.recorder`）を使い、
   アニメーション再生と同期したビデオを出力する

3. **GT CSV にタイムスタンプを付与**  
   各行に `frame_id`（= `Time.frameCount`）と `time_sec`（= `Time.time`）を記録し、
   動画のフレーム番号と 1:1 で対応させる

### 期待される効果

- 同期ずれがゼロになり、評価精度が向上
- 動画フォーマットなので視点ごとのファイル管理が簡潔になる
- MediaPipe の `static_image_mode=False`（動画モード）も利用可能になり、
  より安定したランドマーク検出が期待できる

---

## 関連ファイル

| ファイル | 説明 |
|---------|------|
| `09_calibration_framework/scripts/plot_angle_timeseries.py` | 位相ずれを発見した可視化スクリプト |
| `09_calibration_framework/scripts/output/angle_timeseries_R_Elbow_*.png` | 位相ずれが視覚的に確認できるグラフ |
| `paper/IEEJ_01/source/IEEJ_en/main.tex` §3.2 | 旧キャプチャ方式の記述 |
| `docs/04_UNITY_VIDEO_CAPTURE_PROMPT.md` | Unity コード書き換えエージェントへのプロンプト |

---

## 次のアクション

- [x] Unity プロジェクトの `FrameCapturer` / `SyncedJointRecorder` を動画キャプチャ方式に書き換え  
      → 完了（2026-07-16）。新データは `01_input_videos/`
- [x] 新方式でデータを再収集し、同期確認  
      → v2 時系列でラグ **0±2 フレーム**（旧 −3）。比較図: `09_calibration_framework/scripts/output/v1` vs `v2`
- [x] 再収集データで MAE・方向角・校正パイプラインを再実行（03〜07, 09）
- [ ] IEEJ_02 論文の数値・図を v2 結果に更新する  
      → 進捗全体: [`docs/00_PROGRESS.md`](00_PROGRESS.md)
