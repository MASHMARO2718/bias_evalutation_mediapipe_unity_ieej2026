# MA noise rejection summary

- cameras: 484
- rows: 215020
- window: 7
- K_sigma: 3.0
- missing_gt: 0
- empty: 92
- global_reject_rate: 0.2821
- mean_|eps|: 0.2188
- mean_|eps|_keep: 0.2169
- mean_|E|: 0.4064
- mean_|E_corr|: 0.4035
- elapsed_sec: 57.5

## Reject rate by joint

         joint     n  reject_rate  mean_eps_norm  mean_E_norm  mean_E_corr_norm
    LEFT_WRIST 21502     0.311087       0.220559     0.444418          0.439071
   RIGHT_WRIST 21502     0.303925       0.283762     0.479381          0.476345
    RIGHT_KNEE 21502     0.295182       0.208555     0.339040          0.335891
   RIGHT_ELBOW 21502     0.294205       0.250679     0.401587          0.399818
    LEFT_ELBOW 21502     0.278114       0.220265     0.389199          0.387354
RIGHT_SHOULDER 21502     0.271463       0.111489     0.278829          0.277694
 LEFT_SHOULDER 21502     0.270859       0.115000     0.291484          0.290581
     LEFT_KNEE 21502     0.269696       0.202869     0.330370          0.327629
   RIGHT_ANKLE 21502     0.266952       0.287325     0.567167          0.562927
    LEFT_ANKLE 21502     0.259092       0.287299     0.542276          0.537567

Plots: C:\projects\MOTIONTRACK\bias_evaluation_,mediapipe_unity_ieej2026\02_mediapipe_v2\ma_noise_rejection\results\plots
See docs/06_MOVING_AVERAGE_NOISE_REJECTION.md
