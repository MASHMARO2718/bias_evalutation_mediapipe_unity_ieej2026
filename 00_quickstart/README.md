# 初見ユーザー向け クイックスタート

このフォルダは、初めて使う方向けの最小手順です。

---

## 3ステップで開始

### 1. 依存パッケージのインストール

プロジェクトルートで実行:

```bash
pip install -r requirements.txt
```

### 2. データ処理

**パターンA: 画像から全自動（MediaPipe〜論文検証＋ダッシュボード）**

`01_input_photos/` に次の形式で画像を置き、以下を実行:

```
01_input_photos/
  CapturedFrames_-1.0_0.5_-3.0/
    frame_0001.jpg
    frame_0002.jpg
    ...
  CapturedFrames_1.0_1.5_2.0/
    ...
```

```bash
python run.py
```

→ MediaPipe → MAE → 方向角分析 → 論文検証 → ダッシュボード起動まで自動実行。

**パターンB: 02 が既にある場合**

```bash
python run.py --no-mediapipe
```

→ ステップ1〜5 を実行し、最後にダッシュボードを起動。`--no-dashboard` でダッシュボード起動をスキップ。

**パターンC: 方向角パイプラインのみ＋ダッシュボード（約1分、`run.py --dashboard`）**

```bash
python run.py --dashboard
```

### 3. 可視化ダッシュボード

```bash
python 07_dashboard/app.py
```

ブラウザで **http://127.0.0.1:8050/** を開く。

---

以上で完了です。
