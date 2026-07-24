# Unity キャプチャシステム書き換えエージェントへのプロンプト

> このファイルを別のエージェントにそのまま渡してください。
> エージェントは Unity C# コードを書き換える作業を行います。

---

## タスクの概要

Unity で構築した多視点姿勢推定評価システムの **データ収集方法を「個別フレーム静止画」から「動画（MP4）」方式に変更**してください。

変更の目的は、**Ground Truth（GT）関節座標データと撮影映像フレームの時刻同期を完全に一致させる**ことです。

---

## 背景・問題の説明

### 現行システム（旧方式）

Unity の `CaptureSystemManager.cs` が以下の処理を行っていました：

1. Y-Bot ヒューマノイドアバターの歩行アニメーションを再生
2. 505 カメラ位置（4 高さ層 × 3D グリッド）を順番に切り替え
3. 各カメラ位置で 107 フレームを個別の JPEG 画像として保存  
   （`frame_0000.jpg` ～ `frame_0106.jpg`）
4. 同時に Unity の `HumanBodyBones` API で関節 3D 座標を CSV に記録  
   （`synced_joint_positions.csv`、列: `Frame, Time, LeftUpperArm_X, ..., RightHand_Z` など）

**実装クラス：**
- `CaptureSystemManager` — キャラクター生成・アニメーション再生・フレームキャプチャ・GT記録
- `AutoCaptureManager` — CSVからカメラ位置を読み込み、505箇所で自動キャプチャをトリガー

**出力ファイル構造：**
```
90_legacy_v1/input_photos/
  CapturedFrames_{X}_{Y}_{Z}/
    frame_0000.jpg
    frame_0001.jpg
    ...
    frame_0106.jpg

synced_joint_positions.csv
  Frame, Time, Hips_X, Hips_Y, Hips_Z, LeftUpperArm_X, ...
  0, 8.095, -0.103, 0.983, -3.327, ...
  1, 8.128, ...
```

### 発見した問題

`Update()` での GT 記録と `OnPostRender()`/`WaitForEndOfFrame` での画像保存の間に
**約 3 フレーム（≈ 99 ms）のタイミングずれ**が生じていることが判明しました。

```
実測: 相互相関ラグ = -3 フレーム（MP が GT より 3 フレーム先行）
```

結果として、「フレーム番号 N の GT 関節座標」と「フレーム番号 N の画像」が
実際には異なる時刻の姿勢を記録してしまい、角度誤差評価に誤差が混入します。

---

## 変更後の新しい仕様

### 基本方針

- **GT 記録と動画フレームを同一 `Time.frameCount` で確実に同期させる**
- 各カメラ位置ごとに **1 本の MP4 動画ファイル** を出力する
- GT CSV は動画と同じフレーム番号（`Time.frameCount` ベース）で記録する

### 出力ファイル構造（新方式）

```
10_input_videos/
  CapturedFrames_{X}_{Y}_{Z}/
    video.mp4            ← 解像度 1280×720, 30fps, 107フレーム
    gt_joints.csv        ← このカメラ位置の GT データ（frame_id 同期済み）

  CapturedFrames_{X}_{Y}_{Z}/
    video.mp4
    gt_joints.csv
  ...

synced_joint_positions.csv  ← 全カメラ共通のマスター GT（後処理用、旧形式と互換）
```

### `gt_joints.csv` のフォーマット

```csv
frame_id,time_sec,Hips_X,Hips_Y,Hips_Z,LeftUpperArm_X,...
0,0.000,-0.103,0.983,-3.327,...
1,0.033,...
```

- `frame_id` = 動画フレーム番号（0 始まり）
- `time_sec` = アニメーション開始からの経過秒数
- 以降の列は旧形式 `synced_joint_positions.csv` と同じ関節名

---

## 実装要件

### 1. Unity Recorder Package の使用（推奨）

Unity 公式の **Recorder Package**（`com.unity.recorder`）を使用してください。

```
Package Manager → Add by name: com.unity.recorder
バージョン: 最新安定版（4.x 以降推奨）
```

`MovieRecorderSettings` を使って MP4 を出力します：

```csharp
using UnityEditor.Recorder;
using UnityEditor.Recorder.Input;

// MovieRecorderSettings を設定して RecorderController で録画
```

> **代替案（Recorder が使えない場合）**：
> `AsyncGPUReadback.Request()` を使ったフレームバッファ読み取り + `FFmpeg` 経由の動画エンコード。
> または Unity の `NativeArray<byte>` + `ImageConversion.EncodeNativeArrayToJPG()` を使って
> フレームを列挙し、後処理で動画に結合。

### 2. GT 記録のタイミング同期

**最重要**: GT 記録は画像/フレームの書き出しと**同一フレームの同一コールバック内**で行うこと。

```csharp
// 推奨パターン: LateUpdate() の末尾で両方を確定させる
void LateUpdate()
{
    int frameId = currentRecordingFrame;  // 0始まりの連番

    // 1. GT を記録
    RecordJointPositions(frameId);

    // 2. Recorder に「このフレームを録画」のシグナルを送る
    //    （Recorder は LateUpdate 後のバックバッファを取得するため同期が保証される）
}
```

### 3. `CaptureSystemManager` の変更ポイント

#### 削除する処理
- `ScreenCapture.CaptureScreenshot()` の呼び出し
- `WaitForEndOfFrame` コルーチンでの JPEG 保存
- `Application.CaptureScreenshot()` などの旧 API

#### 追加する処理
- `RecorderController` / `MovieRecorderSettings` の初期化
- カメラ切り替えのタイミングで録画開始/停止
- `LateUpdate()` または Recorder のコールバック内での GT 記録
- `gt_joints.csv` のカメラ別書き出し

### 4. カメラ位置ごとのシーケンス（旧仕様と同じ）

```
foreach camera_position in 505_positions:
    1. カメラをその位置に移動
    2. アニメーションを先頭にリセット
    3. 録画開始（RecorderController.PrepareRecording() → StartRecording()）
    4. 107 フレーム再生（各フレームで LateUpdate() に GT 記録）
    5. 録画停止（RecorderController.StopRecording()）
    6. gt_joints.csv を CapturedFrames_{X}_{Y}_{Z}/ に保存
    7. 次のカメラへ
```

### 5. 後処理スクリプトとの互換性

既存の Python パイプラインが以下を期待しています：

- `90_legacy_v1/mediapipe_processed/mediapipe_processed_csv/Y={y}/CapturedFrames_{x}_{y}_{z}.csv`
  - 列: `frame_id, landmark, x, y, z, visibility`

新方式では動画から MediaPipe を実行して同じ形式の CSV を生成するバッチスクリプトを
別途 Python 側で作成します（Unity 側の作業ではありません）。

---

## カメラ設定（変更不要）

| 項目 | 値 |
|------|-----|
| 解像度 | 1280 × 720 px |
| フレームレート | 30 fps（`Application.targetFrameRate = 30`） |
| フォーマット | MP4（H.264） |
| カメラ数 | 505（4 高さ層: Y = 0.5, 1.0, 1.5, 2.0 m） |
| フレーム数/カメラ | 107 フレーム（歩行サイクル 1 周） |
| アバター | Y-Bot（Unity 標準 Humanoid rig, looped walk animation） |

---

## 実装時の注意事項

1. **`Time.timeScale = 1` を維持すること**  
   Recorder は実時間ベースで録画するため、`timeScale` を変えると同期が崩れる

2. **`Application.targetFrameRate = 30` と `QualitySettings.vSyncCount = 0` を設定すること**  
   フレームレートを固定し、GT とビデオの fps を一致させる

3. **録画の開始/終了は `Time.frameCount` で管理すること**  
   `Time.time` は浮動小数点の丸め誤差が蓄積するため推奨しない

4. **各カメラ位置で動画ファイル名を統一すること**  
   `CapturedFrames_{X}_{Y}_{Z}/video.mp4` の形式にする

5. **Editor 専用 API（`UnityEditor.*`）を使う場合はビルドから除外すること**  
   `#if UNITY_EDITOR` ガードを追加する

---

## 既存コードの正確な構造（Unity_1019 プロジェクト）

### ファイル構成

```
Assets/Scripts/
  Core/
    CaptureSystemManager.cs   ← 統括マネージャー。FrameCapturer と SyncedJointRecorder を連携
  Capture/
    FrameCapturer.cs          ← 画像キャプチャ担当（★ここを書き換える）
    SyncedJointRecorder.cs    ← GT 関節座標記録担当（★ここを書き換える）
    AutoCaptureManager.cs     ← 505 カメラ位置を順番に切り替えて自動撮影
    JointRecorder.cs          ← 旧 GT 記録（未使用）
    CapturePathUtility.cs     ← パス解決ユーティリティ
  Character/
    CharacterAnimationController.cs  ← Y-Bot アニメーション制御
  Triggers/
    TriggerZone.cs            ← Z=-3(撮影開始) / Z=+3(撮影終了) / Z=+5(全停止) トリガー
```

### 同期ずれの正確なメカニズム（コードレベル）

**`FrameCapturer.cs` の撮影コルーチン（現行）：**
```csharp
private IEnumerator CaptureFramesCoroutine()
{
    while (isCapturing)
    {
        yield return new WaitForEndOfFrame();  // ← フレーム末尾まで待機
        CaptureFrame();                        // ← 画像保存 + capturedFrameCount++
    }
}
```

**`SyncedJointRecorder.cs` の GT 記録タイミング（現行）：**
```csharp
private void Update()
{
    // FrameCapturer のカウントが増えたか確認
    int currentCapturedFrameCount = frameCapturer.GetCapturedFrameCount();
    if (currentCapturedFrameCount > lastCapturedFrameCount)
    {
        RecordFrame(i);  // ← GT 記録（現在フレームの骨格座標）
    }
}
```

**ずれが発生する理由：**
```
フレーム N :
  ① Update()     → capturedFrameCount はまだ N-1 → GT 記録なし
  ② Rendering
  ③ WaitForEndOfFrame() → 画像保存（= フレーム N の姿勢）、count = N

フレーム N+1 :
  ① Update()     → count が N に増えたことを検知 → RecordFrame() を呼ぶ
                    ただしこの時点では Animator はすでにフレーム N+1 に進んでいる！
                 → GT が フレーム N+1 の骨格座標で記録される

結果: 画像はフレーム N の姿勢、GT はフレーム N+1 の姿勢 → 1フレームずれ
さらに File.WriteAllBytes がメインスレッドをブロックし累積遅延 → 実測 3 フレームずれ
```

### 変更が必要なファイル（2 ファイルのみ）

書き換え対象は以下の 2 ファイルです。それ以外（`CaptureSystemManager.cs`、`AutoCaptureManager.cs`、`CharacterAnimationController.cs` 等）は**変更不要**です。

1. **`Assets/Scripts/Capture/FrameCapturer.cs`** — 動画録画方式に変更
2. **`Assets/Scripts/Capture/SyncedJointRecorder.cs`** — GT 記録を画像キャプチャと同一タイミングに修正

---

## 成果物

以下を提出してください：

1. **`CaptureSystemManager.cs`** — 動画録画方式に書き換えたもの
2. **`AutoCaptureManager.cs`** — 必要に応じて変更したもの
3. **`README_UNITY_CAPTURE.md`** — 新方式の使い方・設定手順
4. （任意）**`VideoToCsv.py`** — 動画から MediaPipe を実行して CSV を生成する Python スクリプト

---

## 補足：検証方法

書き換え後の同期確認は以下で行います：

```python
# 40_calibration_framework/scripts/plot_angle_timeseries.py を実行し
# 相互相関ラグが 0 フレームになることを確認
python scripts/plot_angle_timeseries.py --camera CapturedFrames_4.0_1.0_0.0 --joints R_Elbow

# 期待される出力:
# Best lag (GT vs MP): 0 frames  ← これを目標とする
```
