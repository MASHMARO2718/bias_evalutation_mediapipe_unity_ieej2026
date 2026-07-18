# UV pseudo-world correction summary (GT-free, PDF spec)

- cameras: 2
- rows: 2028
- window: 7
- K_sigma: 3.0
- sigma_estimator: MAD
- empty: 0
- global_replace_rate: 0.2347

## GT error (all evaluated frames)
- mean err before: 0.7669 m
- mean err after:  0.7638 m

## GT error (replaced frames only)
- n: 373
- mean err before: 0.7928 m
- mean err after:  0.7786 m

## Error decomposition (before correction, all evaluated frames)
- LoS (camera depth) component:  0.4833 m
- perpendicular component:       0.5063 m
- dynamic (bias-removed) error:  0.5588 m

## Dynamic error (static per-camera bias removed) — the filter's actual target
- all frames:      0.5588 -> 0.5519 m
- replaced frames: 0.5829 -> 0.5523 m

## By joint

         joint   n  replace_rate  mean_err_before  mean_err_after  mean_los_before  mean_perp_before  mean_dyn_before  mean_dyn_after  dyn_improvement_pct  improvement_pct
    LEFT_ANKLE 169      0.272189         0.970914        0.968967         0.731254          0.456317         0.644058        0.634617             1.465908         0.200596
    LEFT_ELBOW 169      0.195266         0.689808        0.689157         0.601134          0.311666         0.522446        0.517453             0.955645         0.094400
      LEFT_HIP 169      0.284024              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
     LEFT_KNEE 169      0.236686         0.752819        0.752665         0.576920          0.414529         0.584178        0.580755             0.585895         0.020462
 LEFT_SHOULDER 169      0.284024         0.676236        0.673994         0.532150          0.348919         0.501860        0.495188             1.329348         0.331556
    LEFT_WRIST 169      0.201183         0.664334        0.660746         0.536804          0.358241         0.557632        0.551880             1.031447         0.540111
   RIGHT_ANKLE 169      0.218935         0.832049        0.826062         0.351986          0.720942         0.630277        0.618854             1.812316         0.719521
   RIGHT_ELBOW 169      0.159763         0.822768        0.818440         0.449340          0.612437         0.528016        0.521218             1.287531         0.526078
     RIGHT_HIP 169      0.325444              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
    RIGHT_KNEE 169      0.201183         0.687610        0.684674         0.231281          0.626610         0.569621        0.562576             1.236792         0.426857
RIGHT_SHOULDER 169      0.218935         0.705990        0.699901         0.302516          0.593576         0.493181        0.485370             1.583701         0.862546
   RIGHT_WRIST 169      0.218935         0.866943        0.863609         0.519779          0.620125         0.556537        0.550663             1.055528         0.384651

- elapsed_sec: 1.5

Plots: C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026\02_mediapipe_v2\uv_pseudo_world_correction\results_mad_cam\plots
