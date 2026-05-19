# MediaPipe Pose 補正モデル提案書

**読み方（推奨）** — 章は **§1→§18 の番号順**でも通るが、次の順のほうが内容の依存がつながりやすい。**査読・成功条件・評価の厳しさ**を先に掴む読者向け: §1〜§3 のあと **§17**（論文強化）→ §4（Phase A/B）→ §8（分割）→ §9（指標）→ 必要に応じ §6（モデル詳細）。**入出力・式・パラメータの図**: **§4.10**（PNG 埋め込み。Mermaid 原文は `03_MediaPipe Pose 補正アーキテクチャ図.md`）。**実装寄り**: §4 → §5 → §6 → §7 → §11。**論文の文章・主張だけ**: §18（要約）→ §14〜§16 → §17。**全体の骨格だけ先に**: §5（Stage 一覧）を読んでから §4（入出力・テーブル詳細）に入ると、長い §4 に入る前に地図ができる。

## 1. 研究背景
MediaPipe Pose は単眼 RGB 画像から人体ランドマークを高速推定できる実用的な手法だが、3 次元座標や関節方向を定量的に扱う場合には系統誤差が残る。Unity シミュレーション環境で MediaPipe Pose と Ground Truth を比較した先行研究では、座標系不一致、骨盤深度方向の反相関、上肢関節間の誤差連動、カメラ視点依存の誤差増大など、複数のバイアスが確認されている。本提案では、ニューラルネットワークを使わず、パラメトリックな後処理補正モデルでこれらの誤差を補正し、有効性と限界を評価する。

## 2. 研究目的
本研究の目的は、MediaPipe Pose の 3 次元推定誤差に対し、明示的な補正式と幾何学的制約に基づく補正モデルを構築し、系統的バイアスの低減効果、視点・関節情報を用いた補正の有効性、骨盤剛体制約や運動連鎖制約による構造的誤差の抑制、単眼 3D 推定の本質的限界を明らかにすることである。

## 3. 基本方針
- 補正式の構造は人間が設計し、パラメータ値はデータから自動推定する。
- マジックナンバー調整は行わず、Ground Truth と MediaPipe 出力の差分から補正パラメータを推定する。
- 補正用データと評価用データを分離し、未知視点への汎化性能を評価する。
- 補正で改善した誤差と補正後も残る誤差を明確に区別する。
- **運用と研究を分ける。バイアス値は事前に集めた calibration dataset（§4）から推定し、本番の補正適用は GT なしの新規 MediaPipe 出力に対してのみ行う。**
- **査読耐性のため、「補正が成功した」と言える条件（主要指標・解剖学的妥当性・既知／未知視点）を実験前に固定する（§17）。**

## 4. キャリブレーションと推論（二段階パイプライン）
補正に使うバイアス値は **過去に用意した calibration dataset** から作る。最終的な運用では **GT なしの新しい MediaPipe 出力** にだけ補正をかける。流れは **Phase A（キャリブレーション）** と **Phase B（推論／補正適用）** の二段階に分けて記述する必要がある。ここでいう「過去のデータ」は雑なログではなく、**バイアス推定のために設計・分割されたデータ集合** を指す。

### 4.1 Phase A：Calibration phase（補正パラメータを作る段階）
**Unity GT が必須**。入力は Unity GT（関節座標、関節角度、方向角 $\theta,\psi$）、MediaPipe 出力（推定座標・角度・$\theta,\psi$、visibility/confidence）、カメラ情報（$X,Y,Z$、distance、azimuth、elevation）、メタデータ（joint name、frame index、camera ID 等）。各サンプルで $\text{error} = \text{MediaPipe output} - \text{Unity GT}$ を計算し、条件（例: joint × camera height bin × azimuth bin × metric 種別）ごとに標本を集約して平均誤差・必要なら中央値・標準偏差・件数 $n$ を求める。例: `left_elbow`, $Y=2.0\,\mathrm{m}$, `front-left` ビンにおける角度の平均誤差が $+12.4^\circ$ なら、その値が **ルックアップテーブル用の補正パラメータ** になる。線形パラメトリック補正の場合は同じ error を目的変数に最小二乗で $\beta$ を推定し、閾値類（$\tau$ 等）は GT 分布から推定する（§7）。

### 4.2 Phase B：Correction / inference phase（新しいデータを補正する段階）
**Unity GT は使わない**。入力は新しい画像から得た MediaPipe 出力、カメラ情報、**事前に Phase A で求めた補正テーブル（または $\beta,\tau$ 等）**、および joint 識別子。現在フレームの条件（例: `joint=left_elbow`, `height_bin=2.0`, `view=front-left`, `metric=angle`）をキーにテーブルからバイアスを取り出し、**キャリブレーション時と同じ符号規約** で $\text{corrected} = \text{MediaPipe} - \text{bias}$ を適用する（例: MediaPipe $82.0^\circ$, bias $+12.4^\circ$ → corrected $69.6^\circ$）。連続モデルなら特徴量から $\hat{e}$ を算出して減算する。**MPJPE** は真の GT が無い場面では定義できない。MPJPE は **評価実験**（テスト集合に GT があるとき）に限り算出する。実運用の推論では「MPJPE-like 内部指標」を別定義で出すかどうかは任意だが、本仕様では評価指標としての MPJPE と混同しない。

### 4.3 Phase A / B の入出力（整理）
**Calibration 入力**: Unity Ground Truth（座標・角度・$\theta,\psi$）、MediaPipe 出力（座標・角度・$\theta,\psi$・信頼度）、カメラ（位置・距離・方位角・仰角）、メタデータ（joint、frame ID、camera ID）。**Calibration 出力**: Bias parameters / correction table（下記のような行集合、または回帰係数・閾値）。**Correction 入力**: 新規 MediaPipe 出力、カメラ情報、precomputed bias table。**Correction 出力**: corrected pose（補正済み座標・角度・$\theta,\psi$ 等）。テーブルの具体例:

```text
joint        height   azimuth_bin   metric      bias
left_elbow   2.0      front-left    angle      +12.4°
left_elbow   2.0      front-left    Δθ         -8.1°
left_hip     1.0      right         Δψ         +21.7°
right_hip    1.0      right         Δψ         -20.9°
```

### 4.4 何を補正するか（三種と推奨順）
**次論文で安全な主張にするなら「まず角度空間で補正する」と先に決める**。3D 座標・joint angle・$\theta,\psi$・MPJPE を同時に主張の中心に置くと評価が分散し、査読で「何を成功と言っているのか」がぼやける。**第1主対象**: joint angle。**第2主対象**: $\Delta\theta,\Delta\psi$（または $\theta,\psi$ 本体）。**第3対象**: 3D 座標（world landmark のスケール・座標系・奥行き解釈が不安定なため後段推奨）。MPJPE は **GT がある評価実験での検証指標** とし、補正の主出力とは切り分ける（§9.3、§17）。**A. 関節角度**: $\alpha^{\mathrm{corr}} = \alpha^{\mathrm{mp}} - b_\alpha[\mathrm{joint},\mathrm{view},\ldots]$。実装・論文記述が最も容易。**B. 方向角**: $\theta^{\mathrm{corr}} = \theta^{\mathrm{mp}} - b_\theta[\cdot]$、$\psi^{\mathrm{corr}} = \psi^{\mathrm{mp}} - b_\psi[\cdot]$。先行研究の $\Delta\theta,\Delta\psi$ を直接テーブル化してもよい。視点依存バイアスや骨盤深度（左右 hip の $\Delta\psi$ の反相関など）の分析に向く。**C. 3D 座標**: $\mathbf{p}^{\mathrm{corr}} = \mathbf{p}^{\mathrm{mp}} - \mathbf{b}_p[\cdot]$。スケール・座標系の解釈が難しく破綻しやすい。**推奨段階順**: (1) 関節角度、(2) $\theta,\psi$（または $\Delta\theta,\Delta\psi$）、(3) 必要なら座標。剛体・連鎖制約（§6 Model 6–7）は座標域で効くため、バイアス減算と併用する場合は座標系・符号・適用順を仕様で固定する。

### 4.5 補正テーブル（CSV）のイメージ
推論時に読み込むファイル例（列は研究で拡張可）:

```csv
joint,height_bin,azimuth_bin,metric,bias_mean,bias_median,bias_std,n
left_elbow,2.0,front_left,angle,12.4,11.9,5.3,842
left_elbow,2.0,front_left,theta,-8.1,-7.7,4.8,842
left_elbow,2.0,front_left,psi,3.2,2.9,7.1,842
left_hip,1.0,right,psi,21.7,20.4,10.2,801
right_hip,1.0,right,psi,-20.9,-19.8,9.9,801
```

キー（joint, height_bin, azimuth_bin, metric）で `bias_mean` を参照し `corrected = raw - bias_mean` とする（符号はキャリブレーション定義と一致させる）。

### 4.6 Calibration dataset の候補
**候補1：前論文の Unity データをそのまま使う** — メリット: 既存、505 カメラ規模、MediaPipe バイアス論拠と接続しやすい。デメリット: 歩行単一、Y-Bot のみ、環境が単純。次論文の第一段階として十分。**候補2：同一母集団を calibration / test に分割** — 例: 70% cameras で bias table、30% cameras で評価。「同じデータで補正して同じデータだけ見た」批判を避けるうえで最重要。**候補3：新しい動作・アバター・カメラ配置で外部評価** — 研究レベルが上がる。効果が落ちるならそれ自体が **後処理補正の限界** のエビデンスになる。

### 4.7 推奨研究デザイン（クリーンな流れ）
1. 前論文データを **70% / 30% camera split** 等で分割する。2. Calibration set で $b[\mathrm{joint},\mathrm{height\_bin},\mathrm{azimuth\_bin},\mathrm{metric}] = \mathrm{mean}(\mathrm{MediaPipe}-\mathrm{GT})$（または線形／制約付き推定）。3. Test set の MediaPipe に同キーで補正を適用: $\text{corrected}=\text{MediaPipe}-b[\cdot]$。4. Test の GT と比較し $\text{raw\_error}=|\text{MediaPipe}-\text{GT}|$、$\text{corrected\_error}=|\text{corrected}-\text{GT}|$、$\text{improvement}=(\text{raw\_error}-\text{corrected\_error})/\text{raw\_error}$ を見る。5. **未知視点**（例: $Y\in\{0.5,1.0,1.5\}$ のみで表を作り $Y=2.0$ で評価）で汎化が崩れるかを見ると、「既知視点では補正可能だが未知視点では限界がある」と主張しやすい。

### 4.8 本研究で最終的に得るもの
**得るもの1**: 補正済み MediaPipe 出力（角度、$\theta,\psi$、任意で座標）。**得るもの2**: **バイアスマップ**（どの関節がどの視点でどの方向にどれだけズレるかの可視化・表）。**得るもの3**: **補正可能性の定量評価**（何が減り何が残るか）。**得るもの4**: MediaPipe の限界の証拠（視点依存バイアスは減らせるが単眼深度曖昧性は残る、骨盤・上肢の構造誤差は完全には消えない等）。補正モデルの正体は次の一文で言い切れる: **GT 付きデータから「この条件では MediaPipe は平均してここまでズレる」という表（または連続モデル）を作り、新規 MediaPipe に対してその条件のズレを引いて補正済み出力を得る**。推論時の入出力は $\text{Input: MediaPipe}+\text{camera}$、$\text{Model: precomputed bias table}$、$\text{Output: corrected MediaPipe}$。テーブル作成時だけ $\text{MediaPipe}+\text{GT}+\text{camera}$ が要る。

### 4.9 論文用の定型文（英日）
> The proposed correction framework consists of two stages: a calibration stage and an inference stage. In the calibration stage, Unity ground-truth joint values and MediaPipe outputs are compared under known camera conditions to estimate viewpoint- and joint-dependent bias parameters. In the inference stage, these precomputed parameters are applied to new MediaPipe outputs using only the camera parameters and joint identity. Therefore, ground truth is required only during calibration, not during correction.

> 提案する補正フレームワークは、キャリブレーション段階と推論段階の二段階から構成される。キャリブレーション段階では、既知のカメラ条件下で Unity Ground Truth と MediaPipe 出力を比較し、関節および視点に依存するバイアスパラメータを推定する。推論段階では、推定済みの補正パラメータを用いて、新しい MediaPipe 出力を補正する。このため、Ground Truth は補正パラメータの推定時にのみ必要であり、補正適用時には不要である。

### 4.10 アーキテクチャ図（MediaPipe 入力・特徴量・式・推定パラメータ・出力）
手作業のハイパラ調整は行わず、**数値はすべて Phase A の calibration データから推定**する（任意で §17 の **λ（補正強度）・w（信頼度重み）** を validation で決める）。

#### 図1: Phase A（キャリブレーション）と Phase B（推論）のデータ流れ

![図1 Phase A/B のデータ流れ・入出力・推定パラメータ](03-fig1-phase-ab.png)

#### 図2: 推論パイプライン（Stage 0–3）と主要な式

![図2 推論側 Stage 0–3](03-fig2-inference-stages.png)

**ソース・再生成**: Mermaid 原文は **`03_MediaPipe Pose 補正アーキテクチャ図.md`**。画像は **`03-fig1-phase-ab.png` / `03-fig2-inference-stages.png`**（拡大用は `.svg`）を同フォルダに置く。

#### 推定パラメータの「数」とチューニングの意味
| パラメータ | 何を表すか | 個数の目安 | 推定方法（手動調整なし） |
| --- | --- | --- | --- |
| **b**（view-bin 等） | キーごとの平均バイアス | キー数 × metric 数（例: 関節×高さビン×方位ビン×角度） | **mean** または **median**（§7.2） |
| **β**（線形） | 視点連続依存の係数 | 6（切片＋5特徴）／関節・metric ごとに別セット可 | **最小二乗**（§7.3） |
| **τ** | 左右 hip 深度差の許容幅 | スカラー（または左右別） | GT の **P95** や **μ+2σ**（§7.4） |
| **L_bone, r_gt** | 骨長・骨長比の参照 | チェーン辺ごと | GT 上の代表値または統計 |
| **λ** | 補正を掛ける強度 0〜1 | スカラー（または metric 別） | **任意**: validation で決定（§17.7）。既定 1 |
| **w** | 信頼度（n, bias_std から） | キーごと 0〜1 | **任意**: テーブル信頼度（§17.6）。既定 1 |

**出力（Phase B）**: 補正後の **関節角・θ/ψ（または Δθ/Δψ）・（任意）3D 座標**。**MPJPE** は GT がある評価セットでのみ計算可能（§9.3）。

## 5. 補正モデル全体構成（処理ステージの概観）
**フェーズとの対応**: Phase A では主に **誤差の集計とパラメータ推定**、Phase B では **事前推定パラメータの適用と（任意で）幾何制約** を行う。オフライン評価ではテスト GT がある場合のみ再度誤差指標を計算する。  
**Stage 0**: 座標系統一（y 軸反転）— A/B 両方で同一規則を適用。  
**Stage 1**: 誤差計算（関節角度誤差、方向角誤差、MPJPE など）— **主に Phase A**、および **評価実験時**（テスト GT あり）。  
**Stage 2**: パラメトリックバイアス補正（関節別・高さ別・視点ビン・線形補正）— Phase A で推定、Phase B で適用。  
**Stage 3**: 解剖学的制約補正（骨盤剛体、左右 hip 深度一貫性、運動連鎖一貫性）— 閾値・比率等は Phase A で GT から推定し、Phase B ではその値で実行。  
**出力（Phase B）**: 補正後の座標・角度。研究評価では分析指標も併記。

## 6. 補正モデル仕様
### 6.1 Model 0: Raw MediaPipe
**概要**: 補正を行わず MediaPipe Pose の出力をそのまま用い、全モデルのベースラインとする。  
**出力例**: 生の関節座標・角度、生の方向角誤差、MPJPE。

### 6.2 Model 1: Coordinate Unified Model
**概要**: Unity と MediaPipe の座標系差を補正するため、MediaPipe 側 y 座標を反転する。  
**補正式**: 

$$

y' = -y

$$

### 6.3 Model 2: Joint-wise Constant Bias Correction
**概要**: 関節ごとの平均誤差を推定し、視点情報を使わず関節固有バイアスを補正する。  
**補正式**: 

$$

x^{corr}_j = x^{mp}_j - b_j

$$

（ここで $b_j$ は $e_j = x^{mp}_j - x^{gt}_j$ の平均）

### 6.4 Model 3: Height-wise Bias Correction
**概要**: 関節とカメラ高さごとに平均誤差を推定し、高さ依存バイアスを補正する。  
**補正式**: 

$$

x^{corr}_{j,h} = x^{mp}_{j,h} - b_{j,h}

$$

### 6.5 Model 4: View-bin Bias Correction
**概要**: カメラ視点を離散ビン（例: front, left, back）に分割し、関節・高さ・方位角ビンごとの平均誤差で補正する。  
**補正式**: 

$$

x^{corr}_{j,h,a} = x^{mp}_{j,h,a} - b_{j,h,a}

$$
  
**使用する視点情報**: camera height, camera azimuth, camera distance, camera elevation。  
**方位角ビン例**: front, front-left, left, back-left, back, back-right, right, front-right。  
**誤差定義**: 

$$

e_{j,h,a} = x^{mp}_{j,h,a} - x^{gt}_{j,h,a}

$$
  
**補正パラメータ**: 

$$

b_{j,h,a} = \mathrm{mean}(e_{j,h,a})

$$
  
**目的**: カメラ位置に依存して変化する空間的バイアスを補正する。  
**特徴**: ヒートマップ上の視点依存誤差を直接扱え、実装も比較的単純で、本研究の中心モデル候補である。

### 6.6 Model 5: Linear Parametric Correction
**概要**: 誤差をカメラ視点パラメータの連続関数として近似し、離散ビンではなく連続視点変化に対応する。  
**入力特徴量**: $1$, camera\_y, camera\_distance, $\sin(\text{azimuth})$, $\cos(\text{azimuth})$, elevation。  
**誤差モデル**: 

$$

\hat{e} = \beta_0 + \beta_1 Y + \beta_2 D + \beta_3 \sin\phi + \beta_4 \cos\phi + \beta_5 \epsilon

$$
  
ここで $Y$ はカメラ高さ、$D$ はカメラ距離、$\phi$ は方位角、$\epsilon$ は仰角、$\beta$ は推定する補正パラメータである。  
**補正式**: 

$$

x^{corr} = x^{mp} - \hat{e}

$$
  
**パラメータ推定**: 最小二乗法で 

$$

\min_{\beta} \sum_i (e_i - \hat{e}_i)^2

$$

 を最小化する。  
**特徴**: 解釈しやすく、数学的に明確で、View-bin Bias Correction との比較対象として有効である。

### 6.7 Model 6: Pelvis Rigidity Correction（骨盤剛体制約）
**背景と目的**: 単眼 3D 推定では左右 hip の深度誤差に強い反相関が現れ、実際には存在しない骨盤回転が推定されることがあるため、左右 hip の深度差を物理的に妥当な範囲へ制限する。  
**制約**: 

$$

|z_{Lhip} - z_{Rhip}| < \tau

$$
  
**中点計算**: 

$$

z_{mid} = \frac{z_{Lhip} + z_{Rhip}}{2}

$$
  
**深度差**: 

$$

\Delta z = z_{Lhip} - z_{Rhip}

$$
  
**クリップ後深度差**: 

$$

\Delta z' = \mathrm{clip}(\Delta z, -\tau, \tau)

$$
  
**補正後座標**: 

$$

z'_{Lhip} = z_{mid} + \frac{1}{2}\Delta z', \quad z'_{Rhip} = z_{mid} - \frac{1}{2}\Delta z'

$$
  
**閾値決定**: $\tau$ は手動で決めず、GT データの 95% 範囲や平均 $\pm 2$ 標準偏差から自動推定する（例: 

$$

\tau = P_{95}(|z^{gt}_{Lhip} - z^{gt}_{Rhip}|)

$$

）。  
**ポイント**: 物理的に不自然な骨盤回転を抑制し、MediaPipe の深度推定限界を定量化し、関節構造の一貫性を担保する。

### 6.8 Model 7: Kinematic Chain Consistency Correction
**概要**: 肩・肘・手首、股関節・膝・足首の運動連鎖を考慮し、各関節を独立補正せず、近位から遠位まで構造的一貫性を保つ。  
**対象チェーン**: left shoulder → left elbow → left wrist、right shoulder → right elbow → right wrist、left hip → left knee → left ankle、right hip → right knee → right ankle。  
**制約例**: 骨長制約 

$$

|p_{child} - p_{parent}| \approx L_{bone}

$$

、骨長比制約 

$$

\frac{L_{upper}}{L_{lower}} \approx r_{gt}

$$

、急激な局所補正抑制 

$$

|p^{corr}_j - p^{mp}_j| < \lambda

$$

。  
**ポイント**: 上肢関節間の誤差連動を補正し、関節単位ではなく人体構造単位で補正し、過剰補正による不自然姿勢を抑える。

## 7. パラメータ推定法
### 7.1 基本原則
人間が設計するものは、補正式の構造、入力特徴量、ビン分割、導入する幾何学的制約、評価指標であり、データから推定するものは、補正値、回帰係数、制約閾値、平均誤差、中央値誤差、残差分布である。

### 7.2 平均誤差推定
**使用モデル**: Joint-wise Constant Bias Correction、Height-wise Bias Correction、View-bin Bias Correction。  
**補正パラメータ**: 

$$

b = \mathrm{mean}(x^{mp} - x^{gt})

$$
  
**補正式**: 

$$

x^{corr} = x^{mp} - b

$$
  
**外れ値に強い代替**: 

$$

b = \mathrm{median}(x^{mp} - x^{gt})

$$
  
**目的**: 条件別の平均的系統誤差を除去する。

### 7.3 最小二乗推定
**使用モデル**: Linear Parametric Correction。  
**行列表現**: 

$$

\mathbf{e} = X\beta + \epsilon

$$

（ここで $\mathbf{e}$ は誤差ベクトル、$X$ は特徴量行列、$\beta$ は回帰係数、$\epsilon$ は残差）  
**目的関数**: 

$$

\min_{\beta} |\mathbf{e} - X\beta|^2

$$
  
**解**: 

$$

\beta = (X^T X)^{-1}X^T\mathbf{e}

$$

（実装では逆行列を直接計算せず、最小二乗ソルバーを用いる）。

### 7.4 制約閾値推定
**使用モデル**: Pelvis Rigidity Correction、Kinematic Chain Consistency Correction。  
**推定方法**: GT データの自然変動範囲から閾値を求める。  
例: 

$$

\tau = P_{95}(|z^{gt}_{Lhip} - z^{gt}_{Rhip}|)

$$

 または 

$$

\tau = \mu_{gt} + 2\sigma_{gt}

$$

（ここで $\mu_{gt}$ は GT 上の平均値、$\sigma_{gt}$ は GT 上の標準偏差）。  
**目的**: 手動閾値設定を避け、データに基づいて制約範囲を設定する。

## 8. データ分割と評価戦略
### 8.1 基本方針
補正パラメータ推定用データと性能評価用データは必ず分離する。同一データで推定と評価を行うと、訓練条件への過剰適合が起こり得る。

### 8.2 分割案 A: Camera Split
**概要**: カメラ位置を基準に分割（70% cameras → calibration set、30% cameras → test set）。  
**目的**: 未知カメラ位置への汎化性能を評価する。  
**長所**: 最も基本的で、視点汎化を評価しやすい。

### 8.3 分割案 B: Height Hold-out
**概要**: 一部のカメラ高さを評価専用として保持（例: Training: $Y=0.5, 1.0, 1.5$、Testing: $Y=2.0$）。  
**目的**: 未知高さ、特に上方視点での限界を評価する。  
**長所**: 視点依存補正の汎化限界を明確化でき、「既知視点では有効・未知視点では限定的」という主張を検証しやすい。

### 8.4 分割案 C: Motion Hold-out
**概要**: 将来的に複数動作を用意し、動作単位で分割する（例: Training: walking、Testing: running/sitting/jumping）。  
**目的**: 補正モデルの動作依存性を検証する。  
**長所**: より強い外的妥当性を評価でき、次段階の研究拡張に有効である。

## 9. 評価指標
### 9.1 Joint Angle MAE
**定義**: 

$$

MAE_{\alpha} = \frac{1}{N} \sum_{i=1}^{N} |\alpha^{mp}_i - \alpha^{gt}_i|

$$
  
**目的**: 関節角度の平均絶対誤差を評価する。

### 9.2 Direction Angle Error
**定義**: 

$$

\theta = \arctan2(y, x), \quad \psi = \arctan2(z, x)

$$
  
**誤差**: 

$$

\Delta \theta = \theta^{mp} - \theta^{gt}, \quad \Delta \psi = \psi^{mp} - \psi^{gt}

$$
  
**評価量**: 

$$

|\Delta \theta|, \quad |\Delta \psi|

$$
  
**目的**: 関節方向バイアスを評価する。

### 9.3 MPJPE
**定義**: 

$$

MPJPE = \frac{1}{N} \sum_{i=1}^{N} |p^{mp}_i - p^{gt}_i|

$$
  
**目的**: 3 次元位置誤差を評価する。**注意**: GT 必須。実運用推論（§4 Phase B）では計算不能。

### 9.4 Hip Correlation
**定義**: 左右 hip の 

$$

\Delta \psi

$$

 の相関係数を評価する。  

$$

r = \frac{\sum_{i=1}^{N}(x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^{N}(x_i - \bar{x})^2}\sqrt{\sum_{i=1}^{N}(y_i - \bar{y})^2}}

$$
  
**目的**: 骨盤深度方向の反相関バイアスが補正後に弱まるかを確認する。

### 9.5 Upper-limb Correlation
**対象**: shoulder-elbow、elbow-wrist、shoulder-wrist。  
**目的**: 上肢関節間の誤差連動が補正後に弱まるかを確認する。

### 9.6 Viewpoint Gap
**定義**: 最良視点と最悪視点の誤差差を評価し、

$$

Gap = \frac{E_{worst}}{E_{best}}

$$

 とする。  
**目的**: 補正により視点依存性がどこまで緩和されたかを評価する。

### 9.7 Improvement Rate
**定義**: 

$$

\text{Improvement} = \frac{E_{raw} - E_{corr}}{E_{raw}} \times 100

$$
  
**目的**: 補正前後の改善率を比較する。

### 9.8 Generalization Drop
**定義**: 

$$

\Delta_{generalization} = \text{Improvement}_{known} - \text{Improvement}_{unknown}

$$
  
**目的**: 既知視点と未知視点での補正効果差を評価する。

## 10. 推奨実験構成
### 10.1 比較するモデル
| Model | 内容 | 目的 |
| --- | --- | --- |
| Model 0 | Raw MediaPipe | ベースライン |
| Model 1 | Coordinate Unified | 座標系不一致の除去 |
| Model 2 | Joint-wise Bias | 関節固有バイアスの補正 |
| Model 3 | Height-wise Bias | 高さ依存バイアスの補正 |
| Model 4 | View-bin Bias | 視点依存バイアスの補正 |
| Model 5 | Linear Parametric | 連続視点パラメータ補正 |
| Model 6 | Pelvis Rigidity | 骨盤深度反相関の抑制 |
| Model 7 | Kinematic Chain | 関節連鎖の構造補正 |

### 10.2 推奨する最終構成
Raw MediaPipe → Coordinate Unification → View-bin Bias Correction → Pelvis Rigidity Correction → Corrected Pose。  
**理由**: 座標系補正は必須であり、View-bin Bias Correction は視点依存誤差を直接扱え、Pelvis Rigidity Correction は骨盤深度方向の構造的誤差に対応でき、ニューラルネットワークを使わず高い解釈可能性を維持できるため。

## 11. 実装手順
**用語**: 以下の Phase 1–4 は **実装・評価の工程** を指す。§4 の **Phase A/B（キャリブレーション／推論）** とは別概念だが、実装では「まず A でテーブル生成 → B 相当のパイプラインをテストデータに適用 → 評価」と対応づける。
### Phase 1: 基本補正
**実装内容**: Raw MediaPipe 出力読み込み、Unity GT 読み込み、座標系統一、joint angle・$\Delta \theta$・$\Delta \psi$・MPJPE 計算、Joint-wise Bias Correction、Height-wise Bias Correction。  
**目的**: 基本的補正効果の確認。

### Phase 2: 視点依存補正
**実装内容**: camera azimuth・camera distance・camera elevation 計算、方位角ビン作成、View-bin Bias Correction、Linear Parametric Correction。  
**目的**: 視点依存バイアス補正。

### Phase 3: 構造補正
**実装内容**: 左右 hip 深度差計算、GT 分布に基づく閾値推定、Pelvis Rigidity Correction、骨長比計算、Kinematic Chain Consistency Correction。  
**目的**: 人体構造に反する推定の抑制。

### Phase 4: 評価
**実装内容**: 補正前後の MAE、$|\Delta \theta|$、$|\Delta \psi|$、MPJPE、hip 相関係数、upper-limb 相関係数、viewpoint gap、既知視点と未知視点の改善率を比較する。加えて **anatomical validity**（骨長のフレーム間変動、左右 hip 深度関係、関節可動域逸脱）、**時系列の揺れ**（フレーム間角度差の平均・標準偏差、簡易 jitter）、**方位角ビン粒度の感度**（例: 4 / 8 / 16 bin で calibration と test の乖離を比較）、**失敗ケースの収集**（低 visibility、体幹近接の腕、横向き・背面、$Y=2.0$ で改善しない例など）を行う（§17）。  
**目的**: 補正可能誤差と補正困難誤差の分離、および「精度は上がったが姿勢が壊れた」パターンの排除・限界の明示。

## 12. 期待される結果
### 12.1 補正で改善が期待される誤差
- 座標系不一致由来の角度誤差
- 関節ごとの平均バイアス
- カメラ高さ依存の平均誤差
- 方位角依存の平均誤差
- 骨盤の過剰な深度差

### 12.2 補正後も残ると予想される誤差
- 単眼 3D 推定に由来する深度曖昧性
- 遮蔽による推定破綻
- 未知視点への補正効果低下
- 未知動作への補正効果低下
- MediaPipe 内部の学習済み人体事前分布由来の誤差
- 剛体制約だけでは解決できない上肢連動誤差

## 13. 成功条件
### 13.1 補正モデルとしての成功条件（事前定義）
**実験設計の前に**、§17.1 に沿って「何が改善すれば成功か」を書き下ろす。指標の一例として、以下のうち **複数** を改善し、かつ §17.3 の解剖学的妥当性が悪化していないこと（少なくとも主要チェックで悪化なし）を満たすとする: Joint Angle MAE 低下、$|\Delta \theta|$・$|\Delta \psi|$ 低下、（評価集合に GT がある場合）MPJPE 低下、hip 負相関の弱化、upper-limb 過剰相関の弱化、viewpoint gap の縮小、時系列 jitter の悪化が許容範囲内（§17.8）。**単一指標だけの改善**や **calibration set だけの改善**は成功とみなさない（§8、§17.4–17.5）。

### 13.2 研究としての成功条件
パラメトリック補正により系統的バイアスを一定程度低減でき、**補正で改善する誤差と補正しても残る誤差を分離**でき、既知視点では有効・未知視点では効果限定的であることを示し、後処理補正のみでは単眼 3D 推定の本質的限界を完全解決できないことを示せる。**成功例だけでなく失敗モードと実用ゾーン（§17.9–17.10）を提示できること**が、単なる精度改善実験との差別化になる。

## 14. 論文での主張
### 14.1 主張 1: 補正可能なバイアス
MediaPipe Pose の誤差の一部は関節・視点・高さ依存の系統バイアスであり、Unity Ground Truth を用いたパラメトリック補正で低減可能である。

### 14.2 主張 2: 構造的制約の有効性
左右 hip 深度差や骨長比への幾何学的制約導入により、人体構造に反する推定結果を一定程度抑制できる。

### 14.3 主張 3: 後処理補正の限界
補正後も単眼 3D 推定の深度曖昧性、未知視点への汎化不足、学習済み人体事前分布由来の誤差は残存する。

### 14.4 主張 4: MediaPipe の位置づけ
MediaPipe Pose は補正なしで高精度 3D 計測器として使うべきではない一方、視点条件を限定し補正モデルを導入すれば補助的姿勢解析手法としての有用性を高められる。

## 15. 想定される結論文
### 英語
Parametric post-hoc correction reduces systematic viewpoint-dependent bias in MediaPipe Pose, but cannot fully eliminate residual depth ambiguity or anatomically inconsistent errors. This indicates that calibration improves estimator usability, while structural limitations remain without explicit rigidity constraints or multi-view information.

### 日本語
パラメトリックな後処理補正により、MediaPipe Pose の視点依存バイアスは一定程度低減できるが、単眼深度曖昧性や解剖学的一貫性を欠く誤差は完全には除去できない。したがって、キャリブレーションは推定器の実用性を高める一方、明示的な剛体制約や多視点情報なしでは構造的限界が残る。

## 16. 研究タイトル案
### 英語タイトル案
- A Parametric Calibration Framework for MediaPipe Pose（フレームワーク全体を主張する場合）
- Parametric Post-hoc Correction of MediaPipe Pose under Multi-view Unity Ground Truth
- Correctable and Irreducible Biases in MediaPipe Pose: A Parametric Calibration Study
- Limits of Viewpoint-aware Calibration for MediaPipe Pose Estimation
- Evaluating the Limits of Parametric Bias Correction for MediaPipe Pose
- Viewpoint-dependent Calibration and Residual Bias Analysis of MediaPipe Pose

### 日本語タイトル案
- MediaPipe Pose のためのパラメトリック・キャリブレーション・フレームワーク
- Unity Ground Truth に基づく MediaPipe Pose のパラメトリック後処理補正
- MediaPipe Pose における補正可能バイアスと不可避バイアスの分離
- 視点依存補正に基づく MediaPipe Pose 後処理の限界評価
- MediaPipe Pose の系統的誤差に対するパラメトリック補正モデルの構築
- 多視点 Unity 環境を用いた MediaPipe Pose 補正可能性の評価

## 17. 論文として強化する設計（成功条件の先決・妥当性・限界の明示）
単なる「誤差が下がった」では弱い。**「補正が本当に成功した」と言える条件を実験前に決める**こと、**補正できない誤差を同時に示す**ことが、MediaPipe の 3D 推定の**構造的限界を解析した研究**としての体裁を与える。以下は査読で突っ込まれやすい点への先回りである（§4・§8・§9 と整合）。

### 17.1 成功条件を先に書く
事前登録レベルまで厳密でなくてよいが、提案段階で文書化する: **主指標**（例: joint angle MAE を第1、$|\Delta\theta|,|\Delta\psi|$ を第2）、**副指標**（MPJPE、相関、viewpoint gap）、**否定すべき結果**（例: unknown-view で改善ゼロでも「限界の証拠」として価値がある）、**解剖学的チェック**（§17.3）、**時系列**（§17.8）。「成功＝すべての指標がベスト」ではなく、**主張と一致するパターンを定義**する。

### 17.2 補正対象の絞り込み（評価のぼやけ防止）
§4.4 と同じ結論を論文戦略として固定する: **第1主対象は joint angle**、**第2は $\Delta\theta,\Delta\psi$**、3D 座標は主張の中心から外すか後段。**MPJPE は評価指標**として残し、補正パイプラインの主出力と混同しない。全部同時に「補正した」と言い始めると、査読で分解を求められる。

### 17.3 解剖学的妥当性（anatomical validity）
誤差だけ下がっても、**人体として不自然**なら実用・論文ともに弱い。GT 誤差とは独立に、補正後シーケンスで次を監視する: **bone length のフレーム間変動**（腕が伸び縮みする）、**左右 hip の深度関係**（骨盤剛体の破綻）、**関節可動域逸脱**（肘が過伸展など）、**時間的なガタつき**（§17.8 と併用）。先行研究で顕在な骨盤反相関・上肢連動は、**補正後に「構造的に自然か」**で語れると強い。

### 17.4 View-bin の細かさと「覚えただけ」問題
View-bin は便利だが、ビンを細かくしすぎると **calibration 条件の誤差を暗記**しているだけと見なされるリスクがある。**方位角ビン数の感度分析**（例: 4 / 8 / 16）を行い、**calibration では改善するが test では改善しない**パターンを報告できると、**過学習の限界**を肯定的エビデンスにできる。

### 17.5 Known-view と Unknown-view の二系統評価
**Known-view test**: 補正テーブルに近いカメラ分布での改善（「条件が似ているときどれだけ効くか」）。**Unknown-view test**: テーブルに含まれない高さ・方位角・距離（§8 の hold-out と対応）。後者で性能が落ちるなら、**後処理補正は既知条件では有効だが未知視点には限界がある**と主張できる。院論文・査読向けに近い。

### 17.6 補正値の信頼度（bias_std、$n$、重み $w$）
テーブルは `bias_mean` だけでなく **`bias_std`、`n`（必要なら信頼区間）** を保持する。**$n$ が小さい**、**`bias_std` が大きい**ビンは信頼が低い。推論時に 

$$

\text{corrected} = \text{raw} - w \cdot \text{bias}

$$

 とし、$w$ を $n$ と分散から作る **reliability score**（例: 件数が十分で分散が小さいほど $w\to 1$）にすると実用的で、論文でも「不確実なセルで補正を弱める」と説明しやすい。

### 17.7 過補正抑制（補正強度 $\lambda$）
平均バイアスを丸ごと引くと条件によっては振り過ぎる。

$$

\text{corrected} = \text{raw} - \lambda \cdot \text{bias}

$$

 とし、$\lambda\in[0,1]$ を **validation split**（calibration 内のホールドアウト）で決めると丁寧。最初の実装では $\lambda=1$ 固定でもよいが、提案書・論文では **過補正抑制オプション** として記載する価値がある。

### 17.8 時系列の揺れ（フレーム独立補正の副作用）
補正がフレーム独立だと、**平均誤差は下がるがフレーム間角度がガタガタ**になり得る。簡易指標: 

$$

\text{jitter} = \mathrm{mean}_t(|\alpha_t-\alpha_{t-1}|)

$$

 または同差分の標準偏差、**速度の滑らかさ**（低通過との比較は任意）。報告時は raw と corrected を並べる。

### 17.9 実用条件のゾーニング
補正は万能ではない。**Safe zone**（例: near-frontal、$Y\in[1.0,1.5]$、高 visibility）、**Caution zone**（例: 側面、$Y=2.0$、低 visibility）、**Not recommended**（真上に近い、強遮蔽、学習外動作）のように表形式で示すと、**安全 critical 計測にそのまま使えない**という先行主張と整合する。

### 17.10 失敗例の収集と「フレームワーク」としての位置づけ
成功例だけでは弱い。**補正後も hip 反相関が残る**、**$Y=2.0$ で効かない**、**visibility が低い**、**腕が体幹に近い**、**横向き・背面** などを図示し、**補正の限界を明らかにした**と主張する。単なるテーブルではなく、**Calibration dataset → Bias estimation → Reliability scoring → Correction application → Residual / failure analysis** まで含めて **parametric calibration framework** と呼ぶと、タイトル・貢献の言い方が強くなる（§16）。

### 17.11 優先度（実装・執筆の順）
1. 補正主対象を joint angle / $\Delta\theta,\Delta\psi$ に絞る。2. calibration / test の明確分離。3. known-view / unknown-view の二系統。4. ビン粒度の感度（過学習の可視化）。5. `bias_std` と $n$ による信頼度。6. $\lambda$ による過補正抑制（任意だが記載価値大）。7. anatomical validity。8. 時系列 jitter。9. 失敗モードとゾーニング。10. **framework** として記述。**核**: 補正成功だけを狙わず、**補正可能な誤差と不可避な誤差を分ける**。

## 18. 最終要約
本研究では、MediaPipe Pose の 3D 推定誤差に対して、ニューラルネットワークを用いないパラメトリック後処理補正モデルを構築する。補正モデルは座標系統一、関節別バイアス補正、高さ別バイアス補正、視点ビン補正、線形パラメトリック補正、骨盤剛体制約、運動連鎖制約から構成される。補正パラメータは **calibration dataset** 上で Unity Ground Truth と MediaPipe 出力の差分から自動推定し（§4 Phase A）、本番では **GT なし** の新規出力に対してのみ適用する（§4 Phase B）。評価では補正前後の Joint Angle MAE、$|\Delta \theta|$、$|\Delta \psi|$、MPJPE、hip 相関、upper-limb 相関、viewpoint gap に加え、**解剖学的妥当性・時系列安定性・既知／未知視点・失敗モード**（§17）を明示し、補正可能な系統バイアスと後処理では除去困難な本質的限界を分離して、MediaPipe を補助的な 3D 姿勢推定手法として利用するための条件と限界を明らかにする。
