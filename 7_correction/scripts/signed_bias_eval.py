"""
scripts/signed_bias_eval.py
===========================
detailed_results.csv (符号付き方向角誤差) を使った補正評価。

評価指標
--------
  平均 |Δθ|  (mean absolute delta_theta_deg): 仰角方向誤差
  平均 |Δψ|  (mean absolute delta_psi_deg) : 方位角方向誤差

補正モデル
----------
  Baseline   : 補正なし
  Model4_U   : 視点ビン (unsigned 絶対値平均 をバイアス推定値として引く)
  Model4_S   : 視点ビン (signed   平均       をバイアス推定値として引く) ← NEW
  Model2_U   : 関節別定数 (unsigned)
  Model2_S   : 関節別定数 (signed)

λ 感度分析
----------
  Model4_S で λ ∈ [0.0, 0.25, 0.50, 0.75, 1.0, 1.25, 1.50] を変えて評価。

出力
----
  7_correction/outputs/results/signed_bias_results.csv
  7_correction/outputs/results/lambda_sensitivity.csv
"""

import sys
import re
import numpy as np
import pandas as pd
from pathlib import Path

# プロジェクトルートを sys.path に追加
HERE = Path(__file__).resolve().parent.parent  # 7_correction/
sys.path.insert(0, str(HERE))

from src.config import DATA, OUTPUT, RANDOM_SEED

# ─── パス ──────────────────────────────────────────────────────────────────
DETAILED = DATA["detailed_results"]
RESULTS_DIR = OUTPUT["results"]
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── 対象関節 (detailed_results と MAE の対応) ─────────────────────────────
JOINT_MAP = {           # detailed_results "joint" 列 → MAE 列名
    "LEFT_SHOULDER":  "L_Shoulder",
    "RIGHT_SHOULDER": "R_Shoulder",
    "LEFT_ELBOW":     "L_Elbow",
    "RIGHT_ELBOW":    "R_Elbow",
    "LEFT_HIP":       "L_Hip",
    "RIGHT_HIP":      "R_Hip",
    "LEFT_KNEE":      "L_Knee",
    "RIGHT_KNEE":     "R_Knee",
}
TARGET_JOINTS = list(JOINT_MAP.keys())   # 8 関節

N_AZIMUTH   = 8
SPLIT_RATIO = {"calib": 0.70, "val": 0.15, "test": 0.15}
LAMBDAS     = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25, 1.50]


# ──────────────────────────────────────────────────────────────────────────────
def parse_camera_coords(camera_name: str):
    """CapturedFrames_X_Y_Z → (x, y, z) float"""
    m = re.search(r"CapturedFrames_([-\d.]+)_([-\d.]+)_([-\d.]+)", camera_name)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None, None, None


def compute_viewbin(az_deg: float, n_az: int = 8, y: float = 0.5) -> tuple:
    """方位角 → azimuth_bin, height_bin"""
    az_bin = int((az_deg + 180) / (360 / n_az)) % n_az
    y_map = {0.5: 0, 1.0: 1, 1.5: 2, 2.0: 3}
    h_bin = y_map.get(round(y, 1), 0)
    return h_bin, az_bin


# ──────────────────────────────────────────────────────────────────────────────
def load_and_aggregate():
    """
    detailed_results.csv を読み込み、per-camera × per-joint に集計する。
    戻り値: DataFrame (camera, joint_short, x, y, z, azimuth_deg, distance,
                        elevation_deg, height_bin, azimuth_bin,
                        signed_theta_mean, signed_psi_mean,
                        abs_theta_mean,   abs_psi_mean, n)
    """
    print("Loading detailed_results.csv ...")
    df = pd.read_csv(DETAILED)
    df = df[df["joint"].isin(TARGET_JOINTS)].copy()
    print(f"  Rows after joint filter: {len(df):,}")

    # カメラ座標を解析
    coords = df["camera"].apply(parse_camera_coords)
    df["cam_x"] = [c[0] for c in coords]
    df["cam_y"] = [c[1] for c in coords]
    df["cam_z"] = [c[2] for c in coords]
    df = df.dropna(subset=["cam_x", "cam_y", "cam_z"])

    # カメラ特徴量
    df["distance"]      = np.sqrt(df["cam_x"]**2 + df["cam_z"]**2)
    df["azimuth_deg"]   = np.degrees(np.arctan2(df["cam_x"], df["cam_z"]))
    df["elevation_deg"] = np.degrees(np.arctan2(df["cam_y"], df["distance"].clip(1e-6)))

    # ビン付与
    bins = df.apply(
        lambda r: compute_viewbin(r["azimuth_deg"], N_AZIMUTH, r["cam_y"]), axis=1
    )
    df["height_bin"]  = [b[0] for b in bins]
    df["azimuth_bin"] = [b[1] for b in bins]
    df["joint_short"] = df["joint"].map(JOINT_MAP)

    # per-camera × per-joint 集計
    agg = df.groupby(["camera", "joint_short"]).agg(
        cam_x         = ("cam_x",            "first"),
        cam_y         = ("cam_y",            "first"),
        cam_z         = ("cam_z",            "first"),
        azimuth_deg   = ("azimuth_deg",      "first"),
        distance      = ("distance",         "first"),
        elevation_deg = ("elevation_deg",    "first"),
        height_bin    = ("height_bin",       "first"),
        azimuth_bin   = ("azimuth_bin",      "first"),
        signed_theta  = ("delta_theta_deg",  "mean"),
        signed_psi    = ("delta_psi_deg",    "mean"),
        abs_theta     = ("delta_theta_deg",  lambda x: x.abs().mean()),
        abs_psi       = ("delta_psi_deg",    lambda x: x.abs().mean()),
        n             = ("delta_theta_deg",  "count"),
    ).reset_index()

    print(f"  Cameras (unique): {agg['camera'].nunique()}")
    return agg


# ──────────────────────────────────────────────────────────────────────────────
def split_cameras(cameras, seed=RANDOM_SEED):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(cameras))
    n_calib = int(len(cameras) * SPLIT_RATIO["calib"])
    n_val   = int(len(cameras) * SPLIT_RATIO["val"])
    return (
        cameras[perm[:n_calib]].tolist(),
        cameras[perm[n_calib:n_calib+n_val]].tolist(),
        cameras[perm[n_calib+n_val:]].tolist(),
    )


# ──────────────────────────────────────────────────────────────────────────────
def build_bin_tables(calib_df):
    """補正テーブルを calib セットから構築。"""
    # per-bin × per-joint
    grp = calib_df.groupby(["joint_short", "height_bin", "azimuth_bin"])

    tbl_signed = grp.agg(
        bias_signed_theta = ("signed_theta", "mean"),
        bias_signed_psi   = ("signed_psi",   "mean"),
        bias_abs_theta    = ("abs_theta",    "mean"),
        bias_abs_psi      = ("abs_psi",      "mean"),
        n                 = ("n",            "sum"),
    ).reset_index()

    # per-joint (Model 2)
    jnt = calib_df.groupby("joint_short").agg(
        bias_signed_theta_j = ("signed_theta", "mean"),
        bias_abs_theta_j    = ("abs_theta",    "mean"),
        bias_signed_psi_j   = ("signed_psi",   "mean"),
        bias_abs_psi_j      = ("abs_psi",      "mean"),
    ).reset_index()

    return tbl_signed, jnt


# ──────────────────────────────────────────────────────────────────────────────
def apply_correction(test_df, tbl_bin, tbl_joint, model: str, lam: float = 1.0):
    """
    テスト行に補正を適用し、補正後 |Δθ| を返す。
    model: 'M4S', 'M4U', 'M2S', 'M2U'
    """
    result = []
    bin_map = tbl_bin.set_index(["joint_short", "height_bin", "azimuth_bin"])
    jnt_map = tbl_joint.set_index("joint_short")

    for _, row in test_df.iterrows():
        j    = row["joint_short"]
        h, a = int(row["height_bin"]), int(row["azimuth_bin"])
        key  = (j, h, a)

        orig_theta = row["signed_theta"]
        orig_psi   = row["signed_psi"]

        if model in ("M4S", "M4U"):
            if key not in bin_map.index:
                corr_theta = orig_theta
                corr_psi   = orig_psi
            else:
                brow = bin_map.loc[key]
                if isinstance(brow, pd.DataFrame):
                    brow = brow.iloc[0]
                if model == "M4S":
                    b_theta = brow["bias_signed_theta"]
                    b_psi   = brow["bias_signed_psi"]
                else:
                    b_theta = brow["bias_abs_theta"]
                    b_psi   = brow["bias_abs_psi"]
                corr_theta = orig_theta - lam * b_theta
                corr_psi   = orig_psi   - lam * b_psi
        else:  # M2S or M2U
            if j not in jnt_map.index:
                corr_theta = orig_theta
                corr_psi   = orig_psi
            else:
                brow = jnt_map.loc[j]
                b_theta = brow["bias_signed_theta_j"] if model == "M2S" else brow["bias_abs_theta_j"]
                b_psi   = brow["bias_signed_psi_j"]   if model == "M2S" else brow["bias_abs_psi_j"]
                corr_theta = orig_theta - lam * b_theta
                corr_psi   = orig_psi   - lam * b_psi

        result.append({
            "camera":         row["camera"],
            "joint_short":    j,
            "orig_abs_theta": abs(orig_theta),
            "orig_abs_psi":   abs(orig_psi),
            "corr_abs_theta": abs(corr_theta),
            "corr_abs_psi":   abs(corr_psi),
        })

    return pd.DataFrame(result)


# ──────────────────────────────────────────────────────────────────────────────
def evaluate(corr_df):
    """mean |Δθ| および mean |Δψ| を集計。"""
    return {
        "mean_abs_theta_raw":  corr_df["orig_abs_theta"].mean(),
        "mean_abs_theta_corr": corr_df["corr_abs_theta"].mean(),
        "mean_abs_psi_raw":    corr_df["orig_abs_psi"].mean(),
        "mean_abs_psi_corr":   corr_df["corr_abs_psi"].mean(),
        "improvement_theta":   (corr_df["orig_abs_theta"].mean() - corr_df["corr_abs_theta"].mean())
                                / corr_df["orig_abs_theta"].mean() * 100,
        "improvement_psi":     (corr_df["orig_abs_psi"].mean() - corr_df["corr_abs_psi"].mean())
                                / corr_df["orig_abs_psi"].mean() * 100,
    }


# ──────────────────────────────────────────────────────────────────────────────
def main():
    agg = load_and_aggregate()

    # カメラ分割
    cameras = agg["camera"].unique()
    calib_cams, val_cams, test_cams = split_cameras(cameras)
    # Height hold-out テスト（Y=2.0m）
    test_unknown_cams = agg[agg["cam_y"].round(1) == 2.0]["camera"].unique().tolist()

    calib_df       = agg[agg["camera"].isin(calib_cams)]
    test_df        = agg[agg["camera"].isin(test_cams)]
    test_unknown_df= agg[agg["camera"].isin(test_unknown_cams)]

    print(f"\nSplit: calib={len(calib_cams)}, val={len(val_cams)}, "
          f"test={len(test_cams)}, unknown_Y2={len(test_unknown_cams)}")

    # 補正テーブル構築
    tbl_bin, tbl_jnt = build_bin_tables(calib_df)

    # ─── 各モデル評価 ───────────────────────────────────────────────────────
    rows = []
    for model_id in ["M4S", "M4U", "M2S", "M2U"]:
        for split_name, split_data in [("known", test_df), ("unknown_Y2", test_unknown_df)]:
            corr = apply_correction(split_data, tbl_bin, tbl_jnt, model=model_id, lam=1.0)
            ev   = evaluate(corr)
            rows.append({"model": model_id, "split": split_name, **ev})

    df_results = pd.DataFrame(rows)
    out_main = RESULTS_DIR / "signed_bias_results.csv"
    df_results.to_csv(out_main, index=False)
    print("\n=== Correction Results (lambda=1.0) ===")
    print(df_results.to_string(index=False))

    # ─── λ 感度分析（Model 4S, known-view test） ───────────────────────────
    lambda_rows = []
    for lam in LAMBDAS:
        corr = apply_correction(test_df, tbl_bin, tbl_jnt, model="M4S", lam=lam)
        ev   = evaluate(corr)
        lambda_rows.append({"lambda": lam, **ev})

    df_lambda = pd.DataFrame(lambda_rows)
    out_lambda = RESULTS_DIR / "lambda_sensitivity.csv"
    df_lambda.to_csv(out_lambda, index=False)
    print("\n=== Lambda Sensitivity (Model 4S, known-view) ===")
    print(df_lambda[["lambda", "mean_abs_theta_corr", "improvement_theta"]].to_string(index=False))

    # ─── 関節別結果（Model 4S, known-view） ────────────────────────────────
    corr_joint = apply_correction(test_df, tbl_bin, tbl_jnt, model="M4S", lam=1.0)
    jnt_summary = corr_joint.groupby("joint_short").agg(
        raw_theta  = ("orig_abs_theta", "mean"),
        corr_theta = ("corr_abs_theta", "mean"),
    ).assign(
        improvement = lambda d: (d["raw_theta"] - d["corr_theta"]) / d["raw_theta"] * 100
    ).reset_index()
    out_jnt = RESULTS_DIR / "signed_bias_per_joint.csv"
    jnt_summary.to_csv(out_jnt, index=False)
    print("\n=== Per-joint (Model 4S, known-view) ===")
    print(jnt_summary.to_string(index=False))

    print(f"\nSaved:\n  {out_main}\n  {out_lambda}\n  {out_jnt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
