# MediaPipe Pose 補正アーキテクチャ図（Mermaid）

仕様書 `01_MediaPipe Pose 補正モデル・アーキテクチャ仕様.md` の §4.10 に対応する図のソース。Obsidian / VS Code（Mermaid 拡張）でプレビュー可能。

## 画像出力（生成済みファイル）

同フォルダにレンダリング済み画像を置いている。

| 内容 | PNG | SVG |
| --- | --- | --- |
| 図1 Phase A/B データ流れ | `03-fig1-phase-ab.png` | `03-fig1-phase-ab.svg` |
| 図2 推論 Stage 0–3 | `03-fig2-inference-stages.png` | `03-fig2-inference-stages.svg` |

## 図1: Phase A（キャリブレーション）と Phase B（推論）のデータ流れ

```mermaid
flowchart TB
  subgraph MPIN["MediaPipe 測定値（両フェーズで入力）"]
    M1["ランドマーク座標 p_mp（3D/world 等）"]
    M2["関節角 α_mp"]
    M3["方向角 θ_mp · ψ_mp（または Δθ, Δψ）"]
    M4["visibility · confidence"]
  end

  subgraph FEAT["特徴量（カメラ＋メタから算出。ビン／回帰のキー）"]
    C1["カメラ: X, Y, Z, distance D, azimuth φ, elevation ε"]
    C2["離散キー: height_bin, azimuth_bin（例: 8方向）"]
    C3["線形モデル用ベクトル x = 1,Y,D,sinφ,cosφ,ε"]
    C4["メタ: joint_id, frame_id, camera_id"]
  end

  subgraph PA["Phase A · GT 必須"]
    GT["Unity GT: p_gt, α_gt, θ_gt, ψ_gt"]
    E["誤差 e = 測定 - GT（角度・方向角・座標など metric ごと）"]
    TBL["テーブル推定: b = mean(e)  median  std  n（キー: joint×bin×metric）"]
    LS["線形: beta = argmin sum_i (e_i - x_i^T beta)^2（§6.6）"]
    TAU["τ: 骨盤深度差の GT 分布から P95 等（§6.7）"]
    AUX["補助: 骨長 L_bone, 比 r_gt, 連鎖用 λ_max（§6.8）"]
    STORE["出力: bias table · β · τ · 補助定数（ファイル化）"]
  end

  subgraph PB["Phase B · GT なし"]
    LOOKUP["キー照合: b[joint,height_bin,az_bin,metric] または e_hat = x^T beta"]
    S0["Stage0: y_corr = -y_mp（座標系統一）"]
    S2["Stage2: x_corr = x_mp - lambda*w*b  または  x_mp - lambda*w*e_hat（§17）"]
    S3["Stage3: 骨盤 clip τ · 連鎖制約（任意）"]
    OUT["出力: 補正済み α,θ,ψ,p  ＋ 評価時のみ誤差指標"]
  end

  MPIN --> PA
  FEAT --> PA
  GT --> E
  MPIN --> E
  FEAT --> E
  E --> TBL
  E --> LS
  GT --> TAU
  GT --> AUX
  TBL --> STORE
  LS --> STORE
  TAU --> STORE
  AUX --> STORE

  MPIN --> PB
  FEAT --> PB
  STORE --> LOOKUP
  LOOKUP --> S0
  S0 --> S2
  S2 --> S3
  S3 --> OUT
```

## 図2: 処理ステージと主要な式（推論側）

```mermaid
flowchart LR
  subgraph STAGES["推論パイプライン（§5 Stage 0–3）"]
    direction TB
    N0["Stage0 座標統一: y_corr = -y_mp"]
    N1["Stage2 バイアス: v_corr = v_mp - bias_hat"]
    N2["v は α, θ, ψ, または座標成分"]
    N3["bias_hat = テーブル b  または  x^T beta"]
    N4["Stage3 骨盤: dz_clip = clip(dz,-tau,tau) 再配分 z_L,z_R"]
    N5["Stage3 連鎖: 骨長・比・局所上限 λ_max（任意）"]
  end
  N0 --> N1
  N1 --> N4
  N4 --> N5
```
