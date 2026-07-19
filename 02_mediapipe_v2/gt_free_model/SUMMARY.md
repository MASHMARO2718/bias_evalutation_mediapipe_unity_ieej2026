# GT-free model validation summary

- calibration camera: (3.0, 1.0, 0.0)
- validation camera:  (3.2, 1.1, 0.4)
- pipeline: UV pseudo-world (2D torso scale 0.582 m)
  -> moving median w=7 + 4.0xMAD spike replace (direction-agnostic, replace rate 0.050)
  -> Kalman RTS smoother (Q/R learned on calibration GT)
  -> 3-point 3D angles (rigid-transform invariant)
  -> cheat-sheet bias, linearly interpolated over subject travel position z(t) (gait-phase locked index)

## GT-free travel estimate at validation
- z error: mean 0.033 m / max 0.107 m
- (calibration z-fit residual: 0.032 m)

## Validation angle MAE [deg]

  angle  mae_raw_deg  mae_kalman_deg  mae_corrected_deg  improve_vs_raw_pct
 L_KNEE    15.326309       16.141331           8.273582           46.017129
 R_KNEE    13.342603       16.132503           7.714043           42.184871
L_ELBOW    40.933123       42.022239           8.922461           78.202345
R_ELBOW    16.084504       15.085680           4.604489           71.373136

## Notes
- GT used at inference: none (only for this evaluation).
- Validation GT is the world-space trajectory copied from camera 4.0_1.0_0.0
  (GT is camera-independent within 3 mm; the additional capture has no own GT).
- Cheat sheet learned entirely at the calibration camera.
