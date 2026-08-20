#!/usr/bin/env python3
"""
関節定義ミスマッチ監査:
腰相対フレームで MP と GT を毎フレーム相似変換 (Kabsch + scale) で整合させ、
軸規約・スケールの影響を除去した上で、各 MP ランドマークに最も近い GT ボーン
候補をデータドリブンに判定する。

Kabsch のフィットは「定義が確実な」コア関節のみ (Unity Humanoid では
LowerArm=肘, LowerLeg=膝 の位置) で行い、評価対象の候補には依存させない。
"""
import sys
import re
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "2_pose"))
sys.path.insert(0, str(REPO))

from run_error_mc_analysis import (
    MP_BASE, INPUT_DIR, parse_camera, extract_mp_coords, hip_center,
    flip_mp_y, to_relative,
)
from tools.gt_adapter import find_gt_csv_for_camera, load_gt_csv

# Kabsch フィット用コア対応（Unity Humanoid で位置が確実なもの）
CORE = {
    "LEFT_ELBOW": "LeftLowerArm",
    "RIGHT_ELBOW": "RightLowerArm",
    "LEFT_KNEE": "LeftLowerLeg",
    "RIGHT_KNEE": "RightLowerLeg",
    "LEFT_WRIST": "LeftHand",
    "RIGHT_WRIST": "RightHand",
}

# 監査対象: MP ランドマーク → GT ボーン候補（"A+B" は中点）
CANDIDATES = {
    "LEFT_SHOULDER":  ["LeftShoulder", "LeftUpperArm", "LeftShoulder+LeftUpperArm"],
    "RIGHT_SHOULDER": ["RightShoulder", "RightUpperArm", "RightShoulder+RightUpperArm"],
    "LEFT_ELBOW":     ["LeftLowerArm", "LeftUpperArm", "LeftUpperArm+LeftLowerArm"],
    "RIGHT_ELBOW":    ["RightLowerArm", "RightUpperArm", "RightUpperArm+RightLowerArm"],
    "LEFT_WRIST":     ["LeftHand", "LeftLowerArm", "LeftLowerArm+LeftHand"],
    "RIGHT_WRIST":    ["RightHand", "RightLowerArm", "RightLowerArm+RightHand"],
    "LEFT_HIP":       ["LeftUpperLeg", "Hips", "Hips+LeftUpperLeg"],
    "RIGHT_HIP":      ["RightUpperLeg", "Hips", "Hips+RightUpperLeg"],
    "LEFT_KNEE":      ["LeftLowerLeg", "LeftUpperLeg", "LeftUpperLeg+LeftLowerLeg"],
    "RIGHT_KNEE":     ["RightLowerLeg", "RightUpperLeg", "RightUpperLeg+RightLowerLeg"],
    "LEFT_ANKLE":     ["LeftFoot", "LeftToes", "LeftFoot+LeftToes", "LeftLowerLeg+LeftFoot"],
    "RIGHT_ANKLE":    ["RightFoot", "RightToes", "RightFoot+RightToes", "RightLowerLeg+RightFoot"],
}

ALL_GT_BONES = sorted({b for cands in CANDIDATES.values() for c in cands for b in c.split("+")})


def gt_point(row, bone):
    """GT 行からボーン位置（"A+B" は中点）。"""
    pts = []
    for b in bone.split("+"):
        cols = (f"{b}_X", f"{b}_Y", f"{b}_Z")
        if any(c not in row.index for c in cols):
            return None
        try:
            pts.append(np.array([float(row[cols[0]]), float(row[cols[1]]),
                                 float(row[cols[2]])], dtype=np.float64))
        except (TypeError, ValueError):
            return None
        if np.any(~np.isfinite(pts[-1])):
            return None
    return np.mean(pts, axis=0)


def similarity_fit(A, B):
    """A (n,3) → B (n,3) の相似変換 (s, R)。反射許容。中心化済み前提。"""
    H = A.T @ B
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    varA = np.sum(A ** 2)
    s = np.sum(S) / varA if varA > 1e-12 else 1.0
    # 反射が最適なら反射込み（det は記録）
    return s, R


def main():
    # 方位・高さのバランスを取って 32 カメラをサンプル
    csvs = sorted(MP_BASE.glob("Y=*/CapturedFrames_*.csv"))
    rng = np.random.default_rng(0)
    sample = [csvs[i] for i in rng.choice(len(csvs), size=min(32, len(csvs)), replace=False)]

    dist_sum = {(lm, c): [] for lm, cands in CANDIDATES.items() for c in cands}
    core_resid = {lm: [] for lm in CORE}
    dets = []
    n_frames_used = 0

    for mp_path in sample:
        folder = mp_path.stem
        if parse_camera(folder) is None:
            continue
        gt_path = find_gt_csv_for_camera(folder, INPUT_DIR)
        if gt_path is None:
            continue
        mp_df = pd.read_csv(mp_path)
        gt_df = load_gt_csv(gt_path)
        gt_by_frame = {int(r["Frame"]): r for _, r in gt_df.iterrows()}

        for fid in sorted(mp_df["frame_id"].dropna().astype(int).unique()):
            if fid not in gt_by_frame:
                continue
            grow = gt_by_frame[fid]
            mp_abs = extract_mp_coords(mp_df, fid)
            Hmp = hip_center(mp_abs)
            if Hmp is None:
                continue
            mp_rel = flip_mp_y(to_relative(mp_abs, Hmp))

            gt_hips = gt_point(grow, "Hips")
            if gt_hips is None:
                continue

            # コア対応で相似変換をフィット
            A, B = [], []
            for mp_lm, gt_bone in CORE.items():
                if mp_lm not in mp_rel:
                    continue
                g = gt_point(grow, gt_bone)
                if g is None:
                    continue
                A.append(mp_rel[mp_lm])
                B.append(g - gt_hips)
            if len(A) < 4:
                continue
            A = np.stack(A); B = np.stack(B)
            cA, cB = A.mean(axis=0), B.mean(axis=0)
            s, R = similarity_fit(A - cA, B - cB)
            dets.append(float(np.linalg.det(R)))
            n_frames_used += 1

            def to_gt(v):
                return s * (R @ (v - cA)) + cB

            # コア残差（フィット品質）
            for i, (mp_lm, gt_bone) in enumerate(
                [(k, v) for k, v in CORE.items() if k in mp_rel
                 and gt_point(grow, v) is not None][: len(A)]
            ):
                core_resid[mp_lm].append(float(np.linalg.norm(to_gt(A[i]) - B[i] - cB * 0)))

            # 候補距離
            for mp_lm, cands in CANDIDATES.items():
                if mp_lm not in mp_rel:
                    continue
                m = to_gt(mp_rel[mp_lm])
                for c in cands:
                    g = gt_point(grow, c)
                    if g is None:
                        continue
                    dist_sum[(mp_lm, c)].append(float(np.linalg.norm(m - (g - gt_hips))))

    print(f"frames used: {n_frames_used}, cameras: {len(sample)}")
    print(f"det(R) mean: {np.mean(dets):.3f}  (−1 なら反射込み整合)")
    print()
    rows = []
    for (lm, c), ds in dist_sum.items():
        if ds:
            rows.append({"mp_landmark": lm, "gt_candidate": c,
                         "mean_dist_m": np.mean(ds), "median_dist_m": np.median(ds),
                         "n": len(ds)})
    out = pd.DataFrame(rows).sort_values(["mp_landmark", "mean_dist_m"])
    pd.set_option("display.width", 150)
    for lm in CANDIDATES:
        sub = out[out["mp_landmark"] == lm]
        if sub.empty:
            continue
        best = sub.iloc[0]
        print(f"--- {lm}  (best: {best['gt_candidate']}  {best['mean_dist_m']:.3f} m)")
        for _, r in sub.iterrows():
            print(f"    {r['gt_candidate']:<35s} mean={r['mean_dist_m']:.3f}  med={r['median_dist_m']:.3f}")
    out.to_csv(Path(__file__).parent / "joint_mapping_audit.csv", index=False)


if __name__ == "__main__":
    main()
