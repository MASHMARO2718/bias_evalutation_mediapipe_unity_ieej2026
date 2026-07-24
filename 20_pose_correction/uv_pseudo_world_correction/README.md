# uv_pseudo_world_correction — 出力ディレクトリ

UV 擬似ワールド補正(GT フリー時系列フィルタ)の実行結果。
アルゴリズム・検証の詳細は [`docs/07_UV_PSEUDO_WORLD_CORRECTION.md`](../../docs/07_UV_PSEUDO_WORLD_CORRECTION.md) を参照。

## ディレクトリ

| ディレクトリ | 構成 | 位置づけ |
|---|---|---|
| `results_std_k3/` | 初期仕様(移動標準偏差, K=3) | PDF 仕様どおりの基準実行。自己マスキング問題あり |
| `results_mad_k5/` | **推奨**(移動 MAD, K=5) | 介入半減・σ比が異常度スコアとして機能 |

命名規則: `results_<σ推定>_<K>[_2d]`。`--outdir` で指定して実行する。

## 各ディレクトリの中身

| ファイル | 内容 |
|---|---|
| `SUMMARY.md` | 実行条件と全体統計(誤差分解込み) |
| `uvpw_frame_joint.csv` | フレーム×関節の全記録(P, P_corr, r, ε, 置換フラグ, GT誤差) |
| `uvpw_by_camera_joint.csv` / `uvpw_by_joint.csv` | 集計 |
| `uvpw_camera_meta.csv` | カメラ毎メタ(D̂, スケール, 位置合わせ残差など) |
| `plots/` | 置換率・誤差前後比較・時系列例 |
| `plots/hip_center_error_scale_fix.png` | スケール修正検証(V字消滅、results_mad_k5 のみ) |

## 再実行

```bash
# 推奨構成
python 20_pose_correction/run_uv_pseudo_world_correction.py \
    --torso-2d --robust-sigma --k-sigma 5 --outdir results_mad_k5_2d

# 初期仕様の再現
python 20_pose_correction/run_uv_pseudo_world_correction.py --outdir results_std_k3
```
