# UV pseudo-world correction summary (GT-free, PDF spec)

- cameras: 484
- rows: 258024
- window: 7
- K_sigma: 5.0
- sigma_estimator: MAD
- empty: 92
- global_replace_rate: 0.0880

## GT error (all evaluated frames)
- mean err before: 0.7511 m
- mean err after:  0.7496 m

## GT error (replaced frames only)
- n: 17618
- mean err before: 0.7855 m
- mean err after:  0.7669 m

## Error decomposition (before correction, all evaluated frames)
- LoS (camera depth) component:  0.4731 m
- perpendicular component:       0.4973 m
- dynamic (bias-removed) error:  0.5838 m

## Dynamic error (static per-camera bias removed) — the filter's actual target
- all frames:      0.5838 -> 0.5808 m
- replaced frames: 0.6327 -> 0.5979 m

## By joint

         joint     n  replace_rate  mean_err_before  mean_err_after  mean_los_before  mean_perp_before  mean_dyn_before  mean_dyn_after  dyn_improvement_pct  improvement_pct
    LEFT_ANKLE 21502      0.075807         0.922792        0.921220         0.516134          0.675805         0.677878        0.673015             0.717405         0.170312
    LEFT_ELBOW 21502      0.088038         0.695455        0.693751         0.481597          0.415709         0.547537        0.545417             0.387230         0.244936
      LEFT_HIP 21502      0.119384              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
     LEFT_KNEE 21502      0.079946         0.703480        0.702352         0.422392          0.487844         0.577027        0.574536             0.431732         0.160346
 LEFT_SHOULDER 21502      0.083760         0.694195        0.692601         0.470127          0.429140         0.525179        0.523049             0.405570         0.229714
    LEFT_WRIST 21502      0.089294         0.716841        0.715116         0.480009          0.448129         0.579319        0.576621             0.465678         0.240598
   RIGHT_ANKLE 21502      0.075574         0.935556        0.932721         0.507817          0.703136         0.689479        0.683903             0.808713         0.302983
   RIGHT_ELBOW 21502      0.081341         0.703103        0.702142         0.483418          0.419090         0.548801        0.546796             0.365445         0.136683
     RIGHT_HIP 21502      0.117710              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
    RIGHT_KNEE 21502      0.079807         0.712396        0.710955         0.412778          0.505485         0.589320        0.586733             0.438948         0.202280
RIGHT_SHOULDER 21502      0.080086         0.694540        0.693488         0.453500          0.443427         0.530877        0.528970             0.359185         0.151468
   RIGHT_WRIST 21502      0.085713         0.733045        0.731792         0.503430          0.445735         0.572381        0.569368             0.526287         0.170804

- elapsed_sec: 81.6

Plots: C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026\02_mediapipe_v2\uv_pseudo_world_correction\results_mad_k5\plots
