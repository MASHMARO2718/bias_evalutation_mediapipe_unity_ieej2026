# UV pseudo-world correction summary (GT-free, PDF spec)

- cameras: 484
- rows: 258024
- window: 7
- K_sigma: 3.0
- empty: 92
- global_replace_rate: 0.1931

## GT error (all evaluated frames)
- mean err before: 0.7511 m
- mean err after:  0.7478 m

## GT error (replaced frames only)
- n: 38176
- mean err before: 0.7737 m
- mean err after:  0.7550 m

## Error decomposition (before correction, all evaluated frames)
- LoS (camera depth) component:  0.4731 m
- perpendicular component:       0.4973 m
- dynamic (bias-removed) error:  0.5838 m

## Dynamic error (static per-camera bias removed) — the filter's actual target
- all frames:      0.5838 -> 0.5776 m
- replaced frames: 0.6207 -> 0.5868 m

## By joint

         joint     n  replace_rate  mean_err_before  mean_err_after  mean_los_before  mean_perp_before  mean_dyn_before  mean_dyn_after  dyn_improvement_pct  improvement_pct
    LEFT_ANKLE 21502      0.166310         0.922792        0.918245         0.516134          0.675805         0.677878        0.666636             1.658349         0.492713
    LEFT_ELBOW 21502      0.185936         0.695455        0.692364         0.481597          0.415709         0.547537        0.543043             0.820809         0.444474
      LEFT_HIP 21502      0.272812              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
     LEFT_KNEE 21502      0.176216         0.703480        0.701081         0.422392          0.487844         0.577027        0.571666             0.929129         0.341030
 LEFT_SHOULDER 21502      0.180634         0.694195        0.691258         0.470127          0.429140         0.525179        0.520976             0.800418         0.423182
    LEFT_WRIST 21502      0.188308         0.716841        0.712898         0.480009          0.448129         0.579319        0.573726             0.965393         0.549937
   RIGHT_ANKLE 21502      0.161799         0.935556        0.929871         0.507817          0.703136         0.689479        0.677925             1.675776         0.607610
   RIGHT_ELBOW 21502      0.179937         0.703103        0.700675         0.483418          0.419090         0.548801        0.544562             0.772457         0.345338
     RIGHT_HIP 21502      0.269463              NaN             NaN              NaN               NaN              NaN             NaN                  NaN              NaN
    RIGHT_KNEE 21502      0.172961         0.712396        0.709694         0.412778          0.505485         0.589320        0.584196             0.869436         0.379200
RIGHT_SHOULDER 21502      0.177518         0.694540        0.691941         0.453500          0.443427         0.530877        0.526533             0.818211         0.374272
   RIGHT_WRIST 21502      0.185843         0.733045        0.730196         0.503430          0.445735         0.572381        0.566582             1.013089         0.388583

- elapsed_sec: 83.0

Plots: C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026\02_mediapipe_v2\uv_pseudo_world_correction\results\plots
