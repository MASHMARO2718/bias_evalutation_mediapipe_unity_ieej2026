# データ収集エージェントへの指示書
# (Instructions for the Data-Collection AI Agent)

---

## あなたの役割

あなたは **データ収集専門エージェント** です。
下記の各セクションに従い、実データフォルダから数値・ファイルパスを読み取り、
指定の形式で返答してください。

**書き込み禁止**: 既存ファイルを一切編集・上書きしないこと。
**読み取り専用**: Read / Glob / Shell(ls のみ) ツールを使用してください。

---

## !! 重要: 実データのルートディレクトリ !!

```
実データのルート: C:\projects\MOTIONTRACK\Zeval_DataSet\
論文作業フォルダ: C:\projects\MOTIONTRACK\Zeval_DataSet_organized\07_paper\
```

以下がフォルダ名の対応表です。必ず `Zeval_DataSet\` を参照してください。

| 論文プロンプト内の旧パス表記          | 実際の正しいパス                                         |
|---------------------------------------|----------------------------------------------------------|
| `06_direction_detection/output/`      | `Zeval_DataSet\11_direction_ditection\output\`           |
| `04_mae_heatmap/Y=0.5,1.5/`          | `Zeval_DataSet\4_MAE_HEATMAP\Y=0.5,1.5\`               |
| `04_mae_heatmap/Y=1.0.2.0/`          | `Zeval_DataSet\4_MAE_HEATMAP\Y=1.0.2.0\`               |
| `08_theta_verification/`              | `Zeval_DataSet\10_theta_verification\`                   |
| `07_paper/Images/`                    | `Zeval_DataSet\8_Paper\Images\`                          |
| `07_paper/Images/Graph/`             | `Zeval_DataSet\8_Paper\Images\Graph\`                    |
| `correlation_analysis/heatmap_*.png` | `Zeval_DataSet\8_Paper\correlation_analysis\`            |

---

## 作業の全体像

論文 `07_paper/paper_extended.tex` には `%%TODO%%` / `%%MEAN%%` / `%%SD%%` /
`%%TODO_PATH_*%%` などのプレースホルダーが埋め込まれています。
あなたの仕事は §1〜§8 の各タスクを実行し、
プレースホルダーに入れるべき **実際の数値・ファイルパス・テキスト** を返すことです。

返答形式：各セクション見出し（§番号）を明記し、表や数値のリストで出力してください。

---

## §1 — joint_summary.csv の全行読み取り（Table 2 の完成）

**目的**: `paper_extended.tex` の Table 2（Direction Angle Error）を完成させる。

**対象ファイル**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\processed_data\joint_summary.csv
```

**やること**:
1. このファイルを全行読み取る（ファイルサイズは約 1 KB なので全行読める）。
2. まずヘッダ行を確認し、列名を正確に報告する。
3. 以下の値を全12関節について抽出する（列名が異なる場合は最も近い列を使用）:
   - 関節名
   - `|Δθ|` の平均（absolute mean）
   - `|Δθ|` の標準偏差
   - `|Δψ|` の平均
   - `|Δψ|` の標準偏差
4. 対象12関節:
   `LEFT_SHOULDER`, `RIGHT_SHOULDER`,
   `LEFT_ELBOW`, `RIGHT_ELBOW`,
   `LEFT_WRIST`, `RIGHT_WRIST`,
   `LEFT_HIP`, `RIGHT_HIP`,
   `LEFT_KNEE`, `RIGHT_KNEE`,
   `LEFT_ANKLE`, `RIGHT_ANKLE`
5. 数値は小数点以下1桁（例: 58.3）で返す。

**返答形式**（LaTeX tabular 行として）:
```
【ヘッダ確認】
列名: [列1, 列2, ...]

【Table 2 データ（12行）】
Left shoulder  & [Δθ mean] & [Δθ SD] & [Δψ mean] & [Δψ SD] \\
Right shoulder & [Δθ mean] & [Δθ SD] & [Δψ mean] & [Δψ SD] \\
Left elbow     & [Δθ mean] & [Δθ SD] & [Δψ mean] & [Δψ SD] \\
... (12行すべて)
```

---

## §2 — Y層別 MAE の読み取り（Table 1 の拡張）

**目的**: カメラ高さ層別（Y=0.5,1.5 vs Y=1.0,2.0）のMAE比較データを取得する。

**対象ファイル**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\4_MAE_HEATMAP\Y=0.5,1.5\coordinate_angle_mae.csv
C:\projects\MOTIONTRACK\Zeval_DataSet\4_MAE_HEATMAP\Y=1.0.2.0\coordinate_angle_mae.csv
```

**やること**:
1. 両ファイルのヘッダ行を確認し、列名を報告する。
2. 各ファイルから以下8関節の MAE 値を抽出する:
   - Left Shoulder, Right Shoulder
   - Left Elbow, Right Elbow
   - Left Hip, Right Hip
   - Left Knee, Right Knee
3. 両Y層の値を並べた比較表を返す。
4. ファイルが大きい場合（行数が多い場合）は、先頭20行を読んで
   集計済み列（"MAE" や "mean" という列）を特定してから全体平均を返す。

**返答形式**:
```
【Y=0.5,1.5 ヘッダ】列名: [...]
【Y=1.0,2.0 ヘッダ】列名: [...]

| Joint         | MAE Y=0.5,1.5 (deg) | MAE Y=1.0,2.0 (deg) |
|---------------|---------------------|---------------------|
| Left shoulder |                     |                     |
| ...           |                     |                     |
```

---

## §3 — 相関行列 CSV の全読み取り（相関値の確認）

**目的**: 論文 Table 2/3（相関ペア）の数値を照合し、追加ペアを特定する。

**対象ファイル**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\correlation_analysis\high_correlation_pairs_theta.csv
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\correlation_analysis\high_correlation_pairs_psi.csv
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\correlation_analysis\correlation_matrix_theta.csv
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\correlation_analysis\correlation_matrix_psi.csv
```

**やること**:
1. `high_correlation_pairs_theta.csv` を全行読む。
2. `high_correlation_pairs_psi.csv` を全行読む。
3. 閾値 |r| > 0.7 の全ペアを列挙する。
4. 論文の Table 2（Δθ）・Table 3（Δψ）に載っていないペアがあれば別途明記する。
   ※ 論文掲載済みペア（Δθ）: LEFT_ELBOW/RIGHT_ELBOW(-0.862), LEFT_ELBOW/LEFT_SHOULDER(0.788),
     RIGHT_ANKLE/RIGHT_KNEE(0.767), LEFT_ANKLE/LEFT_KNEE(0.766), RIGHT_ELBOW/RIGHT_SHOULDER(0.710)
   ※ 論文掲載済みペア（Δψ）: LEFT_HIP/RIGHT_HIP(-0.840), RIGHT_ELBOW/RIGHT_SHOULDER(0.770),
     RIGHT_ELBOW/RIGHT_WRIST(0.769), LEFT_ELBOW/LEFT_SHOULDER(0.768),
     RIGHT_SHOULDER/RIGHT_WRIST(0.726), LEFT_ELBOW/LEFT_WRIST(0.722),
     RIGHT_ELBOW/RIGHT_HIP(0.721), LEFT_HIP/RIGHT_ELBOW(-0.705)
5. `correlation_matrix_theta.csv` のヘッダを確認し、含まれる関節名を列挙する。

**返答形式**:
```
【Δθ 高相関ペア（|r|>0.7）全件】
Joint1 | Joint2 | r
...

【Δψ 高相関ペア（|r|>0.7）全件】
...

【論文未掲載ペア（追加候補）】
...

【correlation_matrix_theta.csv の関節ラベル一覧】
...
```

---

## §4 — ヒートマップ画像ファイルの存在確認とパス一覧

**目的**: `paper_extended.tex` の `%%TODO_PATH_R_ELBOW%%` などのパスプレースホルダーを埋める。

### §4.1 — 方向角ヒートマップ（Δθ/Δψ 別）の確認

**対象フォルダ**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\heatmap\
```

このフォルダには以下が存在することを確認済みです:
```
heatmap_LEFT_ELBOW_theta_Y0_5.jpg    ← 左肘 Δθ（論文 Fig.4a の候補）
heatmap_RIGHT_ELBOW_theta_Y0_5.jpg   ← 右肘 Δθ（論文 Fig.4b の候補）★要確認
heatmap_LEFT_HIP_psi_Y0_5.jpg        ← 腰 Δψ（論文 Fig.5）
heatmap_RIGHT_HIP_psi_Y0_5.jpg
heatmap_LEFT_ELBOW_psi_Y0_5.jpg
heatmap_RIGHT_ELBOW_psi_Y0_5.jpg
heatmap_LEFT_HIP_theta_Y0_5.jpg
heatmap_RIGHT_HIP_theta_Y0_5.jpg
```

**やること**:
1. フォルダ内の全ファイル名を `ls` または Glob で取得し一覧を返す。
2. 現在 `8_Paper/Images/Graph/heatmapsY=0.5,1.5/` には
   `heatmap_L_Elbow_Y0_5.jpg`（左肘のみ）しかないことを確認済み。
3. 論文用に追加コピーが必要なファイルのリストを返す:
   - 右肘 Δθ ヒートマップ（Fig. 4b 用）
   - 腰 Δψ ヒートマップ（Fig. 5 用）

**返答形式**:
```
【11_direction_ditection/output/heatmap/ 内ファイル一覧】
- heatmap_LEFT_ELBOW_theta_Y0_5.jpg
- heatmap_RIGHT_ELBOW_theta_Y0_5.jpg  ← Fig.4b に使用可能
- ...（全件）

【論文 paper_extended.tex への \includegraphics パス案】
Fig.4a (左肘 Δθ): Images/Graph/heatmapsY=0.5,1.5/heatmap_L_Elbow_Y0_5.jpg  ← 既存
Fig.4b (右肘 Δθ): [コピー先の推奨パス]  ← 現在 8_Paper/Images/ に未存在
Fig.5  (腰 Δψ) : Images/Graph/heatmap_HIP_phi/heatmap_LEFT_HIP_psi_Y0_5.jpg ← 既存
```

### §4.2 — MAE ヒートマップ（Joint Angle 誤差）の確認

**対象フォルダ**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\4_MAE_HEATMAP\Y=0.5,1.5\
C:\projects\MOTIONTRACK\Zeval_DataSet\4_MAE_HEATMAP\Y=1.0.2.0\
```

このフォルダには以下の PNG 群が存在することを確認済みです:
```
Y=0.5,1.5: heatmap_l_elbow_y0.5.png, heatmap_r_elbow_y0.5.png,
           heatmap_l_hip_y0.5.png,   heatmap_r_hip_y0.5.png, ...
Y=1.0.2.0: heatmap_l_elbow_y1.0.png, heatmap_r_elbow_y1.0.png, ...
```

**やること**:
1. 両フォルダの PNG ファイル一覧を返す。
2. Y層別比較（Fig. 5 候補）として使えるペアを提案する:
   - 左肘: Y=0.5 と Y=1.5 の2枚（または Y=1.0, Y=2.0）
   - 腰:   Y=0.5 と Y=1.5 の2枚
3. これらは MAE ヒートマップ（関節角度誤差）なのか、
   方向角誤差（Δθ/Δψ）ヒートマップなのかを明確にする
   （ファイル名から判断し、必要であれば heatmap.py の内容を読んで確認）。

**返答形式**:
```
【4_MAE_HEATMAP/Y=0.5,1.5/ PNG 一覧】
- heatmap_l_elbow_y0.5.png（サイズ: 160KB）
- heatmap_r_elbow_y0.5.png（サイズ: 170KB）
- ...（全件）

【種別確認】
これらのヒートマップは: [MAE/Δθ/Δψ のどれか] を示している

【Y層別比較ペア案】
左肘: Y=0.5 → [パス] / Y=1.5 → [パス]
腰:   Y=0.5 → [パス] / Y=1.5 → [パス]
```

### §4.3 — 相関行列ヒートマップ PNG の確認（Fig. 7, 8）

**対象フォルダ**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\correlation_analysis\
C:\projects\MOTIONTRACK\Zeval_DataSet\8_Paper\correlation_analysis\
```

確認済みファイル:
```
11_direction_ditection/output/correlation_analysis/:
  heatmap_theta.png (312KB), heatmap_psi.png (323KB),
  heatmap_theta_important.png (266KB), heatmap_psi_important.png (263KB),
  heatmap_3d_norm.png, heatmap_3d_norm_important.png

8_Paper/correlation_analysis/:
  heatmap_theta.png (312KB), heatmap_psi.png (323KB)  ← 論文用コピー済み
```

**やること**:
1. `8_Paper/correlation_analysis/` 内の PNG が
   `11_direction_ditection/output/correlation_analysis/` のコピーと
   同一サイズかどうかを確認する（サイズ比較）。
2. `heatmap_theta.png`（フル版 12関節）と `heatmap_theta_important.png`（主要関節のみ）
   のどちらが論文に適しているかを判断する:
   - 腰（HIP）が含まれるか確認 → フル版を推奨（腰の相関 r=-0.84 が重要）
3. `8_Paper/correlation_analysis/` の相対パスを確認し、
   `paper_extended.tex` の `\includegraphics` パスを確定させる。

**返答形式**:
```
【相関行列ヒートマップ確認】
論文参照パス: correlation_analysis/heatmap_theta.png → [存在: YES/NO, サイズ: bytes]
論文参照パス: correlation_analysis/heatmap_psi.png   → [存在: YES/NO, サイズ: bytes]

フル版 vs 重要関節版:
  heatmap_theta.png (フル): HIP 含む → 推奨
  heatmap_theta_important.png: HIP 不含 → 論文には不適

推奨パス（paper_extended.tex 用）:
  Fig.7: correlation_analysis/heatmap_theta.png
  Fig.8: correlation_analysis/heatmap_psi.png
```

---

## §5 — カメラ視点依存性データ（Section 4.4 用）

**目的**: 「最良カメラ vs 最悪カメラ」の per-frame 誤差データを取得する。

**対象ファイル**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\processed_data\frame_camera_summary.csv
（サイズ: 約 3.9 MB）
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\processed_data\detailed_results.csv
（サイズ: 約 72 MB — 先頭20行のみ読むこと）
```

**やること（frame_camera_summary.csv から）**:
1. ヘッダ行を読み、列名を返す。
2. 先頭 30 行を読み、データ構造（フレーム×カメラ別の誤差か、フレーム別集計か）を確認する。
3. `min_delta_theta`（最良カメラ誤差）と `max_delta_theta`（最悪カメラ誤差）に
   相当する列を特定し、全フレームでの統計を返す:
   - 最良カメラ誤差の平均・最小・最大
   - 最悪カメラ誤差の平均・最小・最大

**やること（detailed_results.csv から）**:
1. 先頭 10 行のみ読む（ファイルが大きいため）。
2. 列名を返す（特に `camera_x`, `camera_z`, `delta_theta`, `delta_psi` に相当する列）。

**返答形式**:
```
【frame_camera_summary.csv ヘッダ】
列名: [列1, 列2, ...]

【最良/最悪カメラ誤差統計（|Δθ|）】
最良カメラ誤差: 平均=[X]°, 最小=[X]°, 最大=[X]°
最悪カメラ誤差: 平均=[X]°, 最小=[X]°, 最大=[X]°

【detailed_results.csv 先頭10行（列名確認）】
...
```

---

## §6 — 各関節の誤差分布データ（箱ひげ図用）

**目的**: 箱ひげ図用の分布統計を全12関節について取得する。

**対象ファイル**（存在確認済み）:
```
C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\processed_data\joint_summary.csv
```

**やること**:
1. §1 で読んだ `joint_summary.csv` に分布統計（中央値、Q1、Q3、最大値）が
   含まれているか確認する。
2. 含まれている場合: 全12関節の以下の列を抽出する:
   - |Δθ|: 平均、中央値、SD、Q1、Q3、最大値
   - |Δψ|: 同上
3. 含まれていない場合: その旨を明記し、`detailed_results.csv` の
   列構造から計算可能かどうかを判断して報告する。

**返答形式**:
```
【joint_summary.csv に分布統計が含まれるか】
YES / NO → [含まれる列名: ...]

【Δθ 分布統計（全12関節）】
| Joint         | Mean | Median | SD | Q1 | Q3 | Max |
|---------------|------|--------|----|----|----|-----|
| Left shoulder |      |        |    |    |    |     |
| ...           |      |        |    |    |    |     |

（Δψ も同様）
```

---

## §7 — 座標系統一前後の比較データ

**目的**: Y軸反転「前」と「後」の誤差を並べて Discussion §6.1 で使う。

**対象ファイル（優先順位順）**:
```
1. C:\projects\MOTIONTRACK\Zeval_DataSet\10_theta_verification\
   → README.md, MEDIAPIPE_COORDINATE_SYSTEM.md を読む
   → coordinate_fix_verification\ フォルダの内容を確認する

2. C:\projects\MOTIONTRACK\Zeval_DataSet\10_theta_verification\output\
   → 出力ファイルを確認する

3. C:\projects\MOTIONTRACK\Zeval_DataSet\11_direction_ditection\output\processed_data\joint_summary.csv
   → "before" や "without_flip" などの列が存在するか確認する
```

**やること**:
1. `10_theta_verification/README.md` を読み、
   このフォルダの目的（Y軸反転の検証）と出力ファイルを確認する。
2. `10_theta_verification/output/` 内のファイル一覧を取得する。
3. Y軸反転前後の比較数値が記録されているファイルを特定し、その数値を返す。
4. 見つからない場合:
   - `MEDIAPIPE_COORDINATE_SYSTEM.md` を読んで記述内容を要約する。
   - 「再実行が必要なスクリプトのパスと実行コマンド」を返す。

**返答形式**:
```
【10_theta_verification/output/ 内ファイル一覧】
...

【座標系統一前後の |Δθ| 比較（判明した範囲）】
データソース: [ファイルパスまたは "not found"]

| Joint         | |Δθ| Before flip | |Δθ| After flip |
|---------------|------------------|-----------------|
| Left shoulder |                  | 10.4            |
| ...           |                  |                 |

もしデータがない場合:
→ "再実行コマンド: [具体的なコマンド]"
→ MEDIAPIPE_COORDINATE_SYSTEM.md の要約: [...]
```

---

## §8 — 論文用画像の存在確認と欠損リスト

**目的**: `paper_extended.tex` が参照する画像がすべて `8_Paper/` 以下に揃っているか確認する。

**確認対象**（`8_Paper/` からの相対パス）:

| `\includegraphics` パス | 実際の絶対パス | 存在 |
|---|---|---|
| `Images/camera_layout.png` | `8_Paper\Images\camera_layout.png` | 確認済み ✓ |
| `Images/Unity実験環境.png` | `8_Paper\Images\Unity実験環境.png` | **未確認** |
| `Images/frame_0018.jpg` | `8_Paper\Images\frame_0018.jpg` | **未確認** |
| `Images/角度の概念図.png` | `8_Paper\Images\角度の概念図.png` | **未確認** |
| `Images/Graph/heatmapsY=0.5,1.5/heatmap_L_Elbow_Y0_5.jpg` | 確認済み ✓ | ✓ |
| `Images/Graph/heatmapsY=0.5,1.5/heatmap_R_Elbow_Y0_5.jpg` | **未存在**（要コピー） | ✗ |
| `Images/Graph/heatmap_HIP_phi/heatmap_LEFT_HIP_psi_Y0_5.jpg` | 確認済み ✓ | ✓ |
| `correlation_analysis/heatmap_theta.png` | 確認済み ✓ | ✓ |
| `correlation_analysis/heatmap_psi.png` | 確認済み ✓ | ✓ |

**やること**:
1. 「**未確認**」のファイル（Unity実験環境.png, frame_0018.jpg, 角度の概念図.png）を
   以下の場所で検索する:
   ```
   C:\projects\MOTIONTRACK\Zeval_DataSet\8_Paper\Images\
   C:\projects\MOTIONTRACK\Zeval_DataSet\1_Output_Photos\    ← frame画像の候補
   C:\projects\MOTIONTRACK\Zeval_DataSet\               ← 角度の概念図.pngはルートに存在
   ```
   ※ `角度の概念図.png` はルートディレクトリ `Zeval_DataSet\` に存在することを確認済み。
2. 欠損ファイルについて、コピー元パスと論文用コピー先パスを返す。
3. `heatmap_R_Elbow_Y0_5.jpg`（右肘）について:
   - コピー元: `Zeval_DataSet\11_direction_ditection\output\heatmap\heatmap_RIGHT_ELBOW_theta_Y0_5.jpg`
   - コピー先: `Zeval_DataSet\8_Paper\Images\Graph\heatmapsY=0.5,1.5\heatmap_R_Elbow_Y0_5.jpg`
   - この対応でよいかファイルの内容（種類）を確認する。

**返答形式**:
```
【画像存在確認結果】
camera_layout.png    : ✓ 存在
Unity実験環境.png   : [✓存在 / ✗ 不在 / → コピー元: パス]
frame_0018.jpg       : [✓存在 / ✗ 不在 / → 1_Output_Photos\frame_0018.jpg?]
角度の概念図.png    : [✓存在 / コピー元: Zeval_DataSet\角度の概念図.png]
heatmap_R_Elbow...  : ✗ 不在 → コピー元: 11_direction_ditection\output\heatmap\heatmap_RIGHT_ELBOW_theta_Y0_5.jpg

【NEW_PAPER_MANAGEMENT エージェントへのコピー指示リスト】
以下のファイルを 8_Paper/Images/ へコピーする必要があります:
1. コピー元: [...] → コピー先: [...]
2. ...
```

---

## 作業完了後のサマリー

上記 §1〜§8 をすべて実行したあと、以下のサマリーを最後に付けてください。

```
=== データ収集サマリー ===

完了タスク:
  §1 joint_summary.csv（Table 2）: [完了 / エラー]
  §2 Y層別 MAE 比較              : [完了 / エラー]
  §3 相関行列 高相関ペア         : [完了 / エラー]
  §4 ヒートマップパス確認        : [完了 / 一部未存在]
  §5 視点依存性データ            : [完了 / エラー]
  §6 分布統計（箱ひげ図用）      : [完了 / データ不足]
  §7 座標統一前後比較            : [完了 / 再実行必要]
  §8 論文用画像の存在確認        : [完了 / 欠損あり]

paper_extended.tex プレースホルダー充填状況:
  %%MEAN%% / %%SD%% (Table 2)   : [充填済み / 一部不明]
  %%TODO_PATH_R_ELBOW%%         : [パス確定 / 未存在]
  %%TODO_BEFORE%% (Y軸反転前)   : [数値確定 / 再実行必要]

【NEW_PAPER_MANAGEMENT エージェントへの引き継ぎ事項】
  要コピーファイル:
    1. [コピー元パス] → [コピー先パス]
    2. ...
  要再実行スクリプト:
    1. [スクリプトパスとコマンド]
  未解決プレースホルダー:
    1. %%...%% の場所と理由
```

---

## 注意事項

- `detailed_results.csv` は約 72 MB です。**先頭10〜20行のみ**読み取ること。
- 数値は論文用のため **小数点以下1桁** に丸めて返す（例: 58.3°）。
- ファイルが存在しない場合は「not found」と明記し、最も近い候補パスを代わりに返す。
- 単位はすべて **度（degrees）**。ラジアンが混在する場合は変換すること（× 180/π）。
- フォルダ名の typo に注意: `11_direction_ditection`（"detection" ではなく "ditection"）。
