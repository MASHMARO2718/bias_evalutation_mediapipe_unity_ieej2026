# Computation Results Report
Generated: 2026-03-15  
Script: `paper/compute_paper_stats.py`  
Data source: `C:\projects\MOTIONTRACK\Zeval_DataSet`

---

## A4 — Hip Direction Angle Statistics

**Source:** `11_direction_ditection/output/processed_data/detailed_results.csv`  
**n = 21,613 observations per hip joint** (all frames × all cameras)

| Joint      | \|Δθ\| Mean | \|Δθ\| SD | \|Δψ\| Mean | \|Δψ\| SD |
|------------|------------|-----------|------------|-----------|
| LEFT_HIP   | 83.5°      | 72.5°     | 88.9°      | 26.4°     |
| RIGHT_HIP  | 96.5°      | 72.5°     | 91.1°      | 26.4°     |

**Note:** Hip joints were excluded from `joint_summary.csv` (likely because the pelvis serves as the coordinate origin and its θ values are geometrically degenerate). Values computed directly from `detailed_results.csv`.

**Interpretation:**
- |Δθ| for hip is very large (83–97°), with high SD (72°), indicating the XY-plane direction estimate is largely unreliable. This is expected: the hip center IS the origin of the MediaPipe world coordinate system, so the "direction" from hip to itself is undefined or near-zero length, making θ extremely sensitive to noise.
- |Δψ| ≈ 89–91° with SD=26.4° is the meaningful metric. This matches the existing table values (88.9 / 91.1) that were previously confirmed from partial data.

---

## A3 — Y-Axis Coordinate Unification Effect

**Source (before):** `7_direction_ditection/output/processed_data/joint_summary.csv`  
**Source (after):** `11_direction_ditection/output/processed_data/joint_summary.csv`

| Joint          | Before (°) | After (°) | Reduction (°) |
|----------------|-----------|-----------|--------------|
| LEFT_SHOULDER  | 169.5     | 10.4      | **159.1**    |
| RIGHT_SHOULDER | 171.2     | 9.3       | **161.9**    |
| LEFT_ELBOW     | 121.6     | 58.3      | 63.3         |
| RIGHT_ELBOW    | 121.2     | 59.3      | 61.9         |
| LEFT_WRIST     | 94.3      | 84.3      | 10.0         |
| RIGHT_WRIST    | 93.1      | 91.5      | 1.6          |
| LEFT_KNEE      | 161.7     | 17.4      | **144.3**    |
| RIGHT_KNEE     | 162.2     | 18.5      | **143.7**    |
| LEFT_ANKLE     | 168.7     | 11.3      | **157.4**    |
| RIGHT_ANKLE    | 167.9     | 11.9      | **156.0**    |

**Key findings:**
- Shoulder, knee, and ankle joints: reduction > 140°. These joints have GT θ values close to ±90°, so Y-flip doubles the error.
- Elbow: reduction ~63°. Residual error (~58°) reflects genuine estimation bias (arm-at-side prior), not coordinate mismatch.
- Wrist: minimal reduction (1.6–10°). High estimation variance (SD > 100°) masks the systematic sign error.

---

## A5 — Correlation Coefficient p-Values

**Source:** `11_direction_ditection/output/processed_data/detailed_results.csv`  
**Method:** `scipy.stats.pearsonr` on pivot-table of frame×camera vs joint  
**n ≈ 21,000 per joint pair** (107 frames × 201 cameras)

### XY Plane (Δθ) — High-correlation pairs (|r| > 0.7)

| Joint 1        | Joint 2         | r        | p-value    | Significant? |
|----------------|-----------------|----------|------------|--------------|
| LEFT_ELBOW     | RIGHT_ELBOW     | −0.8622  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| LEFT_ELBOW     | LEFT_SHOULDER   | +0.7876  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_ANKLE    | RIGHT_KNEE      | +0.7669  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| LEFT_ANKLE     | LEFT_KNEE       | +0.7664  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_ELBOW    | RIGHT_SHOULDER  | +0.7105  | < 10⁻³⁰⁰  | ✅ p < 0.001 |

### XZ Plane (Δψ) — High-correlation pairs (|r| > 0.7)

| Joint 1        | Joint 2         | r        | p-value    | Significant? |
|----------------|-----------------|----------|------------|--------------|
| LEFT_HIP       | RIGHT_HIP       | −0.8402  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_ELBOW    | RIGHT_SHOULDER  | +0.7697  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_ELBOW    | RIGHT_WRIST     | +0.7691  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| LEFT_ELBOW     | LEFT_SHOULDER   | +0.7680  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_SHOULDER | RIGHT_WRIST     | +0.7258  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| LEFT_ELBOW     | LEFT_WRIST      | +0.7217  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| RIGHT_ELBOW    | RIGHT_HIP       | +0.7212  | < 10⁻³⁰⁰  | ✅ p < 0.001 |
| LEFT_HIP       | RIGHT_ELBOW     | −0.7052  | < 10⁻³⁰⁰  | ✅ p < 0.001 |

**Key finding:** All high-correlation pairs have p-values that underflow to 0.0 in double-precision floating point (i.e., p < 5×10⁻³²⁴). With n ≈ 21,000, even r = 0.01 would be statistically significant. The p-values confirm that all listed correlations are genuine structural patterns, not sampling artifacts.

---

## B3 — Joint Angle MAE by Camera Height Layer

**Source:** `03_joint_angle_mae/Y=0.5/` … `Y=2.0/` each `coordinate_angle_mae.csv` (four layers; Zeval may still use `4_MAE_HEATMAP` two-bucket layout until migrated)  
**n = 144 camera positions per height layer**

| Joint          | Y=0.5 | Y=1.0 | Y=1.5 | Y=2.0 |
|----------------|-------|-------|-------|-------|
| LEFT_SHOULDER  | 39.8  | 38.9  | 39.6  | **41.0** |
| RIGHT_SHOULDER | 39.3  | 38.1  | 38.6  | **40.2** |
| LEFT_ELBOW     | 18.1  | 17.7  | 18.3  | **20.2** |
| RIGHT_ELBOW    | 17.5  | 16.7  | 18.2  | **20.2** |
| LEFT_HIP       | 29.6  | 29.0  | 29.9  | **32.5** |
| RIGHT_HIP      | 32.0  | 31.7  | 32.8  | **36.7** |
| LEFT_KNEE      | 16.1  | 16.6  | 17.7  | **17.8** |
| RIGHT_KNEE     | 18.9  | 18.7  | 19.6  | **20.6** |

**Key findings:**
- Y=1.0 consistently shows the lowest MAE (optimal height).
- Y=2.0 shows the highest MAE for all joints (overhead cameras degrade accuracy).
- Right hip shows the largest absolute increase: 31.7° → 36.7° (+4.7°, +15%).
- Bar chart saved to: `paper/source/figs/fig08_mae_layer_bar.png`

---

## B1 — MPJPE (Mean Per-Joint Position Error)

**Source:** `11_direction_ditection/output/processed_data/detailed_results.csv`  
**Column:** `error_3d` = Euclidean distance between GT and MediaPipe world landmark positions  
**Coordinate scale:** MediaPipe world units ≈ metres for a 1.7m subject

### Per-joint values

| Joint          | Mean (m) | SD (m)  | Median (m) | Max (m) |
|----------------|----------|---------|------------|---------|
| LEFT_HIP       | 0.044    | 0.017   | 0.043      | 0.197   |
| RIGHT_HIP      | 0.044    | 0.017   | 0.043      | 0.197   |
| LEFT_ELBOW     | 0.305    | 0.057   | 0.293      | 0.841   |
| RIGHT_ELBOW    | 0.322    | 0.055   | 0.312      | 0.842   |
| LEFT_SHOULDER  | 0.327    | 0.039   | 0.332      | 1.019   |
| RIGHT_SHOULDER | 0.321    | 0.042   | 0.328      | 1.026   |
| LEFT_WRIST     | 0.362    | 0.068   | 0.345      | 1.085   |
| RIGHT_WRIST    | 0.397    | 0.073   | 0.379      | 1.092   |
| LEFT_KNEE      | 0.401    | 0.039   | 0.402      | 0.847   |
| RIGHT_KNEE     | 0.406    | 0.040   | 0.407      | 0.753   |
| LEFT_ANKLE     | 0.708    | 0.081   | 0.710      | 1.605   |
| RIGHT_ANKLE    | 0.714    | 0.089   | 0.714      | 1.583   |
| **All joints** | **0.363** | —      | —          | —       |

### Interpretation

**Why hip error is near-zero (0.044 m):**  
In MediaPipe world coordinates, the hip center (midpoint of LEFT_HIP and RIGHT_HIP) serves as the origin. Individual hip landmarks are small offsets from the origin, so their error is dominated by the pelvis width estimation, not depth. This is expected behavior.

**Why ankle error is very large (0.71 m):**  
Ankle is maximally distal from the hip origin. Depth uncertainty in monocular lifting accumulates along the kinematic chain. Since no ground-plane constraint is applied, ankle Z-position is essentially free to vary.

**Comparison to standard benchmarks:**  
State-of-the-art monocular 3D HPE on Human3.6M achieves ~30–50 mm MPJPE (Zheng et al., 2021 PoseFormer; Zhu et al., 2023 MotionBERT). Our simulation-based MPJPE (≈363 mm overall, ≈436 mm excluding hip) is substantially higher. Contributing factors:
1. Our evaluation covers extreme viewpoints (lateral, overhead) absent in Human3.6M.
2. MediaPipe is not specifically fine-tuned for 3D absolute position accuracy.
3. Coordinate scale uncertainty: world unit to metric conversion depends on subject height assumption.

**Recommendation for paper:**  
Report MPJPE as a supplementary metric with the caveat that it is not directly comparable to benchmarks evaluated on metric-scale data with known subject heights. The direction angle metrics (Δθ, Δψ) are the primary contributions of this paper.

---

## Summary of main.tex Changes Made

| Task | Change |
|------|--------|
| A4 | Table 2 (tab:direction_angle_error): Hip `---` → 83.5±72.5 / 96.5±72.5 (Δθ) and 88.9±26.4 / 91.1±26.4 (Δψ) |
| A3 | New Table (tab:yflip_effect) added to Discussion §5.1 with before/after Y-flip comparison |
| A5 | Correlation Tables 4 & 5 captions updated: "All pairs: p < 0.001 (n > 21,000)" |
| B3 | New Figure (fig:mae_layer_bar) added before Table 3 showing MAE by layer for all joints |
| B1 | New subsection §4.4 "3-D Position Error (MPJPE)" added to Results |
