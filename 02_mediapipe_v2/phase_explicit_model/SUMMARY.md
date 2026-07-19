# Phase-explicit / anchor-free GT-free model — results

- A z-travel: docs/08 (ref-frame anchored travel distance)
- B z-bearing: absolute z from image bearing + camera position (anchor-free)
- C phase-only: Hilbert gait phase index (anchor-free)
- D two-level: slow g(z_bearing) + phase wave h(phi_g) (anchor-free)

- gait period: calib 30 fr / val 31 fr
- template match (full): delta=6.02 rad, swap=False
- bearing-z error at validation: mean 0.129 m

## MAE [deg] — full video

  angle  raw_full  z_travel_full  z_bearing_full  phase_only_full  two_level_full
 L_KNEE     15.33           8.27           11.37            15.49           13.15
 R_KNEE     13.34           7.71            9.25            16.12           12.42
L_ELBOW     40.93           8.92            8.86            14.85           11.09
R_ELBOW     16.08           4.60            4.99             9.53            4.93

## MAE [deg] — anchor break (first 25 frames dropped, renumbered)

  angle  raw_trunc  z_travel_trunc  z_bearing_trunc  phase_only_trunc  two_level_trunc
 L_KNEE      15.55           17.09            11.20             13.67            13.15
 R_KNEE      11.11           20.53             8.19             13.14             9.66
L_ELBOW      36.43           11.30             7.16             12.51             9.19
R_ELBOW      18.52           11.58             5.93              9.83             5.63

- GT used at inference: none (evaluation only).
