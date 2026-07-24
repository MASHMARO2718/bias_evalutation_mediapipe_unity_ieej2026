# 提案書2

# 局所線形性に基づく MediaPipe Pose のパラメトリック補正フレームワーク

## 1. 研究背景

MediaPipe Pose は、単眼RGB画像から人体ランドマークを高速に推定できる姿勢推定手法であり、スポーツ解析、リハビリテーション、教育、XR、ヒューマンコンピュータインタラクションなど幅広い応用可能性を持つ。

一方で、前段階の研究では、Unity シミュレーション環境における Ground Truth と MediaPipe Pose の推定結果を比較し、MediaPipe の3次元推定には複数の系統的バイアスが存在することが確認された。具体的には、座標系の不一致、骨盤深度方向の反相関、上肢関節間の誤差連動、カメラ視点依存の誤差増大が観測されている。

これらの結果は、MediaPipe Pose の出力をそのまま高精度な3次元計測値として扱うことの危険性を示している。一方で、誤差が視点や関節に依存して構造的に分布しているならば、後処理による補正が可能である可能性もある。

本研究では、ニューラルネットワークのようなブラックボックス型の補正ではなく、説明可能性を重視したパラメトリック補正を採用する。特に、MediaPipe の誤差がカメラ視点空間において局所的には線形近似可能であるという仮定に基づき、視点空間を複数の bin に分割し、各 bin 内で局所線形補正モデルを構築する。

---

## 2. 研究目的

本研究の目的は、MediaPipe Pose の視点依存誤差に対して、局所線形性に基づくパラメトリック補正フレームワークを構築し、その補正可能性と限界を明らかにすることである。

より具体的には、以下を目的とする。

1. MediaPipe Pose の誤差が、視点空間の局所領域において線形近似可能かを検証する。
2. 視点空間の bin 分割をハイパーパラメータとして扱い、最適な分割方法を探索する。
3. 各 bin 内で線形補正モデルを構築し、補正前後の誤差を比較する。
4. 補正後にも残る残差を解析し、MediaPipe Pose の後処理補正における限界を明らかにする。
5. 現実的な応用において必要とされる関節角度精度と比較し、補正後の MediaPipe Pose がどの程度実用可能かを評価する。

本研究の中心的な問いは、次のように定義する。

> MediaPipe Pose の3D推定誤差は、局所線形性という説明可能な仮定のもとで、どこまで補正可能か。

---

## 3. 本研究の基本方針

本研究では、ニューラルネットワークを用いない。

その理由は、単にモデルを軽量化するためではなく、研究の主目的が「誤差を最小化すること」だけではなく、「誤差構造を説明し、補正可能な誤差と補正困難な誤差を分離すること」にあるためである。

ニューラルネットワークを用いた残差補正は、数値的な精度を向上させる可能性がある。しかし、カメラ視点、関節、補正量の関係が不透明になりやすく、どの条件でなぜ補正が成功したのか、または失敗したのかを説明しにくい。

本研究では、Explainable AI の観点から、以下の方針を採用する。

* ブラックボックス型の補正モデルは用いない。
* 補正式の構造を明示的に定義する。
* 補正パラメータはデータから自動推定する。
* bin 分割をハイパーパラメータとして扱う。
* 局所線形性の成立度を定量評価する。
* 補正後残差を MediaPipe の構造的限界として分析する。

---

## 4. 研究仮説

本研究では、以下の仮説を置く。

### 仮説1：視点依存誤差は局所的には線形近似可能である

MediaPipe Pose の誤差は、カメラ高さ、方位角、距離、仰角などの視点パラメータに依存して変化する。ただし、視点空間全体では非線形であっても、十分に小さい局所領域では線形モデルで近似可能であると考える。

### 仮説2：bin 分割の粒度には最適値が存在する

bin を粗くしすぎると、局所線形性が成立しにくくなり、補正精度が低下する。一方で、bin を細かくしすぎると、各 bin 内のデータ数が不足し、過学習や汎化性能の低下が生じる。

したがって、補正性能と汎化性能のバランスを取る最適な bin 分割が存在すると考える。

### 仮説3：局所線形補正後にも残る残差は MediaPipe の構造的限界を反映する

局所線形性という比較的緩い仮定のもとで補正してもなお残る誤差は、単純な視点依存バイアスでは説明できない。これは、単眼3D推定の深度曖昧性、MediaPipe の学習済み人体事前分布、剛体制約の欠如などに由来する構造的限界を示唆すると考える。

---

## 5. 提案する補正フレームワーク

本研究で提案する補正フレームワークは、以下の段階から構成される。

```text
Input
 ├─ MediaPipe output
 ├─ Unity Ground Truth
 ├─ Camera geometry
 └─ Joint metadata

↓

Coordinate Unification
 └─ y ← -y

↓

Error Computation
 ├─ joint angle error
 ├─ Δθ error
 ├─ Δψ error
 └─ optional 3D position error

↓

View-space Binning
 ├─ height bin
 ├─ azimuth bin
 ├─ distance bin
 └─ elevation bin

↓

Local Linear Calibration
 ├─ fit linear model in each bin
 ├─ estimate correction parameters
 └─ evaluate local linearity

↓

Hyperparameter Optimization
 ├─ grid search
 ├─ optional genetic algorithm
 └─ select optimal bin configuration

↓

Correction Application
 ├─ apply local linear correction
 └─ generate corrected pose metrics

↓

Residual Error Analysis
 ├─ remaining error map
 ├─ failure mode classification
 └─ limitation analysis
```

---

## 6. 入力と出力

### 6.1 Calibration Phase

Calibration Phase では、補正モデルのパラメータを推定する。この段階では Unity Ground Truth が必要である。

#### 入力

* Unity Ground Truth

  * GT joint coordinates
  * GT joint angles
  * GT direction angles
* MediaPipe output

  * estimated joint coordinates
  * estimated joint angles
  * estimated direction angles
  * visibility / confidence
* Camera geometry

  * camera X
  * camera Y
  * camera Z
  * camera distance
  * camera azimuth
  * camera elevation
* Metadata

  * joint name
  * frame ID
  * camera ID
  * bin ID

#### 出力

* bin ごとの局所線形補正係数
* bin ごとの線形近似精度
* bin ごとの残差分布
* 最適 bin 分割設定
* 補正モデル設定ファイル

---

### 6.2 Inference / Correction Phase

Inference Phase では、Calibration Phase で得られた補正パラメータを用いて、新しい MediaPipe 出力を補正する。この段階では Unity Ground Truth は不要である。

#### 入力

* 新しい MediaPipe output
* camera geometry
* joint name
* 事前に推定された補正パラメータ

#### 出力

* corrected joint angle
* corrected θ
* corrected ψ
* corrected pose metrics
* 補正信頼度
* 該当 bin の局所線形性スコア

---

## 7. 局所線形補正モデル

各データ点に対して、MediaPipe の誤差を次のように定義する。

$$

e = x^{mp} - x^{gt}

$$

ここで、$x$ は補正対象であり、以下のいずれかを用いる。

* joint angle
* $\theta$
* $\psi$
* 3D coordinate component

本研究では、まず joint angle、$\theta$、$\psi$ を主要な補正対象とする。3D座標そのものは、MediaPipe world landmark のスケール解釈や座標系の影響を受けやすいため、補助的な対象として扱う。

各 bin $B_k$ において、誤差 $e$ を線形モデルで近似する。

$$

\hat{e}_{j,k}
=
\mathbf{x}^{T}\beta_{j,k}

$$

ここで、

* $j$：関節ID
* $k$：bin ID
* $\mathbf{x}$：特徴量ベクトル
* $\beta_{j,k}$：関節 $j$、bin $k$ における線形補正係数
* $\hat{e}_{j,k}$：予測された誤差

特徴量ベクトルは次のように定義する。

$$

\mathbf{x}
=
[1,\;Y,\;D,\;\sin\phi,\;\cos\phi,\;\epsilon,\;x^{mp}]

$$

ここで、

* $Y$：カメラ高さ
* $D$：カメラ距離
* $\phi$：方位角
* $\epsilon$：仰角
* $x^{mp}$：MediaPipe の出力値

補正後の値は次のように得る。

$$

x^{corr}
=
x^{mp} - \hat{e}_{j,k}

$$

---

## 8. View-space Binning Strategy

### 8.1 bin 分割の目的

bin 分割の目的は、視点空間全体の複雑な誤差分布を、局所的に線形近似可能な領域へ分割することである。

bin は単なる LUT の区分ではなく、局所線形モデルを適用するための領域である。

---

### 8.2 bin 分割対象

本研究では、以下の視点パラメータを bin 分割対象とする。

* camera height
* camera azimuth
* camera distance
* camera elevation

### 8.3 bin 分割候補

例として、以下の候補を探索する。

| Parameter               | Candidate values  |
| ----------------------- | ----------------- |
| azimuth bins            | 4, 8, 12, 16      |
| height bins             | 2, 4              |
| distance bins           | 1, 2, 3, 4        |
| elevation bins          | 1, 2, 3           |
| minimum samples per bin | 50, 100, 200, 500 |

bin を細かくしすぎると局所性は高まるが、データ数が減少する。逆に、bin を粗くしすぎるとデータ数は増えるが、局所線形性が崩れる。そのため、bin 分割は最適化すべきハイパーパラメータとして扱う。

---

## 9. bin 分割のハイパーパラメータ最適化

### 9.1 Grid Search

まず、Grid Search によって bin 分割候補を網羅的に評価する。

探索対象は以下である。

```text
azimuth_bin_count
height_bin_count
distance_bin_count
elevation_bin_count
minimum_samples_per_bin
regularization_strength
```

各設定について、以下を評価する。

* calibration error
* validation error
* generalization gap
* local linearity score
* number of valid bins
* number of low-sample bins

---

### 9.2 Genetic Algorithm による拡張

Grid Search の後、必要に応じて Genetic Algorithm による局所探索を行う。

Genetic Algorithm では、bin 数だけでなく、bin 境界そのものを探索対象にできる。

探索対象の例は以下である。

* azimuth boundary positions
* distance boundary positions
* elevation boundary positions
* minimum sample threshold
* regularization strength

ただし、研究の主実験では Grid Search を中心とし、Genetic Algorithm は追加実験または発展実験として扱う。

---

## 10. 最適化の目的関数

bin 分割の良し悪しは、単純な補正後誤差だけでは評価しない。細かすぎる bin 分割は calibration set では高精度になりやすいが、test set では汎化性能が低下する可能性があるためである。

そこで、次のような総合スコアを用いる。

$$

Score
=
E_{val}
+ \lambda_1 G
+ \lambda_2 K
+ \lambda_3 N_{small}

$$

ここで、

* $E_{val}$：validation set における補正後誤差
* $G$：generalization gap
* $K$：bin 数
* $N_{small}$：サンプル数が閾値未満の bin 数
* $\lambda_1, \lambda_2, \lambda_3$：重み係数

generalization gap は次のように定義する。

$$

G
=
E_{val} - E_{calib}

$$

この目的関数により、補正精度が高く、過学習が少なく、bin が過度に細かすぎない分割を選択する。

---

## 11. 局所線形性の評価

各 bin 内で線形近似がどれだけ成立しているかを評価する。

### 11.1 決定係数

$$

R^2
=
1 - \frac{
\sum_i (e_i - \hat{e}_i)^2
}{
\sum_i (e_i - \bar{e})^2
}

$$

$R^2$ が高いほど、bin 内で線形モデルが誤差分布をよく説明できていることを示す。

### 11.2 Local RMSE

$$

RMSE_{local}
=
\sqrt{
\frac{1}{N}
\sum_i
(e_i - \hat{e}_i)^2
}

$$

### 11.3 Local MAE

$$

MAE_{local}
=
\frac{1}{N}
\sum_i
|e_i - \hat{e}_i|

$$

### 11.4 bin 安定性

bin 内のサンプル数を確認する。

$$

n_k \geq n_{min}

$$

サンプル数が少ない bin は信頼性が低いため、補正対象から除外するか、近傍 bin と統合する。

---

## 12. 補正信頼度

各補正結果には、信頼度を付与する。

信頼度は以下の要素から計算する。

* bin 内サンプル数
* bin 内の $R^2$
* bias / residual の標準偏差
* MediaPipe visibility
* validation error
* generalization gap

補正式は以下のように拡張できる。

$$

x^{corr}
=
x^{mp} - w_{j,k}\hat{e}_{j,k}

$$

ここで、

* $w_{j,k}$：補正信頼度または補正強度
* $0 \leq w_{j,k} \leq 1$

信頼度が低い bin では補正を弱めることで、過補正を抑制する。

---

## 13. データ分割

### 13.1 Camera Split

カメラ位置を基準に分割する。

```text
Calibration set: 70% cameras
Validation set: 15% cameras
Test set: 15% cameras
```

この分割により、未知カメラ位置に対する汎化性能を評価する。

---

### 13.2 Height Hold-out

特定の高さを完全に評価用として残す。

```text
Training:
Y = 0.5, 1.0, 1.5

Testing:
Y = 2.0
```

この分割により、未知高さ、特に上方視点に対する補正限界を評価する。

---

### 13.3 Motion Hold-out

将来的な拡張として、動作単位で分割する。

```text
Training:
walking

Testing:
running
sitting
jumping
```

この評価により、補正モデルが特定動作に過剰適合していないかを確認する。

---

## 14. 評価指標

### 14.1 Joint Angle MAE

$$

MAE_{\alpha}
=
\frac{1}{N}
\sum_{i=1}^{N}
|\alpha^{corr}_i - \alpha^{gt}_i|

$$

### 14.2 Direction Angle Error

$$

\theta = \arctan2(y, x)

$$

$$

\psi = \arctan2(z, x)

$$

$$

\Delta \theta = \theta^{corr} - \theta^{gt}

$$

$$

\Delta \psi = \psi^{corr} - \psi^{gt}

$$

### 14.3 Improvement Rate

$$

Improvement
=
\frac{
E_{raw} - E_{corr}
}{
E_{raw}
}
\times 100

$$

### 14.4 Generalization Drop

$$

\Delta_{generalization}
=
Improvement_{known} - Improvement_{unknown}

$$

### 14.5 Viewpoint Gap

$$

Gap
=
\frac{
E_{worst}
}{
E_{best}
}

$$

### 14.6 Residual Error

$$

r_i
=
e_i - \hat{e}_i

$$

補正後の残差 $r_i$ を解析することで、局所線形モデルでは説明できない誤差成分を評価する。

---

## 15. 実用要求精度との比較

本研究では、補正後誤差が数学的に減少したかだけでなく、実用上意味のある精度に達しているかも評価する。

そのため、技術者または現場経験者に対して、用途別に必要な精度を確認する。

確認項目は以下である。

1. 姿勢推定を現場で利用する場合、関節角度誤差は何度以内なら許容できるか。
2. 用途によって許容誤差は変わるか。

   * リハビリ
   * スポーツ解析
   * 教育用途
   * 安全監視
   * 研究用途
3. 肩、肘、股関節、膝など、関節ごとに要求精度は異なるか。
4. 2D解析と3D解析で要求精度はどの程度異なるか。
5. フレーム間の揺れ、すなわち temporal jitter はどの程度まで許容されるか。
6. 実用上、絶対角度と相対変化量のどちらが重要か。
7. MediaPipe のような単眼推定を補助情報として使う場合、どこまで信頼できるか。

この調査により、補正後の誤差を「実用上許容可能か」という観点から評価できる。

---

## 16. 期待される結果

本研究では、以下の結果が期待される。

### 16.1 補正により改善が期待される要素

* 視点依存の平均的な関節角度誤差
* 特定関節における方向角バイアス
* 高さ依存の誤差
* 方位角依存の誤差
* known-view 条件での補正精度

### 16.2 補正後も残ると予想される要素

* 単眼3D推定に由来する深度曖昧性
* 骨盤深度反相関
* 上肢関節間の誤差連動
* unknown-view 条件での補正効果低下
* MediaPipe 内部の人体事前分布に由来する誤差
* 遮蔽や低 visibility 条件での推定破綻

---

## 17. 本研究の意義

本研究の意義は、単に MediaPipe Pose の誤差を小さくすることではない。

本研究では、局所線形性という説明可能な仮定のもとで補正を行い、その補正可能限界を定量化する。これにより、MediaPipe Pose の誤差のうち、視点依存の滑らかなバイアスとして補正可能な部分と、単眼深度推定や学習済み事前分布に由来して補正困難な部分を分離できる。

この結果は、MediaPipe Pose を実用環境で用いる際に、どの条件であれば補助的に利用可能か、どの条件では高精度3D計測として扱うべきでないかを判断するための基準となる。

---

## 18. 論文での主張

本研究では、以下の主張を目指す。

### 主張1

MediaPipe Pose の視点依存誤差は、カメラ視点空間において構造的に分布している。

### 主張2

視点空間を適切に bin 分割することで、各局所領域において線形補正モデルを構築できる。

### 主張3

bin 分割をハイパーパラメータとして最適化することで、補正精度と汎化性能のバランスを取ることができる。

### 主張4

最適化された局所線形補正後にも残る誤差は、MediaPipe Pose の単眼深度曖昧性、人体事前分布、剛体制約欠如に由来する構造的限界を示唆する。

### 主張5

MediaPipe Pose は、補正なしで高精度な3D計測器として用いるべきではないが、視点条件を限定し、説明可能な補正を行うことで、補助的な姿勢解析手法としての有用性を高められる。

---

## 19. 想定タイトル

### 英語タイトル

**A Local-Linearity-Based Parametric Calibration Framework for MediaPipe Pose**

または、

**Exploring the Limits of Local Linear Calibration for MediaPipe Pose Estimation**

### 日本語タイトル

**局所線形性に基づく MediaPipe Pose のパラメトリック補正フレームワーク**

または、

**局所線形補正による MediaPipe Pose 推定限界の評価**

---

## 20. 想定結論

本研究では、MediaPipe Pose の視点依存誤差に対して、局所線形性に基づくパラメトリック補正フレームワークを提案した。視点空間を bin に分割し、各 bin 内で線形補正モデルを構築することで、MediaPipe Pose の系統的誤差を一定程度低減できることが期待される。

一方で、最適化された局所線形補正を適用しても残る誤差は、単純な視点依存バイアスでは説明できず、単眼3D推定の深度曖昧性、学習済み人体事前分布、剛体制約の欠如に由来する構造的限界を示す可能性がある。

したがって、本研究は MediaPipe Pose の補正精度向上だけでなく、説明可能な補正仮定のもとでの限界評価を通じて、MediaPipe Pose を実用的な補助計測手法として利用するための条件と限界を明らかにするものである。
