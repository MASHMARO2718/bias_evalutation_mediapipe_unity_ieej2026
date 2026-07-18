# Error · MC analysis summary (Plan B approx)

- cameras_processed: 498
- rows: 215210
- missing_gt: 0
- empty_result: 78
- elapsed_sec: 49.8

## Overall by joint (mean |cos φ|; closer to 0 ⇒ more orthogonal to camera ray)

         joint     n  mean_cos_phi  mean_abs_cos_phi  mean_error_norm  frac_abs_cos_lt_0_3
     LEFT_KNEE 21521      0.059011          0.482739         0.330414             0.314205
    LEFT_ANKLE 21521      0.087295          0.489479         0.542243             0.310952
   RIGHT_ANKLE 21521      0.056325          0.492782         0.567264             0.318061
    RIGHT_KNEE 21521      0.059047          0.496122         0.339082             0.296222
RIGHT_SHOULDER 21521     -0.009490          0.525499         0.278839             0.280284
 LEFT_SHOULDER 21521      0.007433          0.526773         0.291519             0.282097
   RIGHT_ELBOW 21521      0.136357          0.579270         0.401671             0.247293
    LEFT_ELBOW 21521      0.123819          0.589600         0.389232             0.230008
    LEFT_WRIST 21521      0.076110          0.596988         0.444403             0.221086
   RIGHT_WRIST 21521      0.136217          0.607824         0.479477             0.209934

## Global
- mean |cos φ|: 0.5387
- median |cos φ|: 0.5539
- fraction |cos φ| < 0.3: 0.271

See docs/05_CAMERA_JOINT_ERROR_MC_ANALYSIS.md for interpretation and caveats.
