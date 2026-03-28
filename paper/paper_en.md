\documentclass[twocolumn]{article}

% Package loading
\usepackage{graphicx}
\usepackage{geometry}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{float}
\usepackage{url}
\usepackage{titlesec}
\geometry{top=24mm,bottom=24mm,left=19mm,right=19mm}
\setlength{\parskip}{0.15em}
\setlength{\floatsep}{6pt}
\setlength{\textfloatsep}{8pt}
\titlespacing*{\section}{0pt}{2ex plus 0.5ex minus 0.2ex}{1.2ex plus 0.2ex}
\titlespacing*{\subsection}{0pt}{1.8ex plus 0.5ex minus 0.2ex}{0.9ex plus 0.2ex}
\titlespacing*{\subsubsection}{0pt}{1.5ex plus 0.3ex minus 0.2ex}{0.6ex plus 0.2ex}

% Allow line breaks for long words
\sloppy

% Title information
\title{Accuracy Evaluation of MediaPipe Pose Estimation Using a Unity Environment}
\author{%
  Non-member\quad Fumimaro Taira$^{*a)}$ \qquad
  Member\quad Tsukasa Kato$^{*b)}$ \qquad
  Non-member\quad Jin Afuso$^{*c)}$\footnotemark[1]
}
\date{}

\begin{document}

\maketitle
\begingroup
\renewcommand{\thefootnote}{}
\footnotetext[1]{$^{*a)}$ Okinawa Prefectural Kaiko High School, $^{*b)}$ Graduate School of Education, University of the Ryukyus, $^{*c)}$ lollol Inc.}
\endgroup

\section*{Abstract}
This study quantitatively evaluates the pose estimation accuracy of MediaPipe using Ground Truth obtained in a Unity environment. Prior work on MediaPipe accuracy has largely been limited to frontal views or restricted camera layouts; evaluation from diverse viewpoints, which is important in practical settings, has been insufficient.

We collected walking data from 505 multi-view cameras over 107 frames and obtained 259,356 observations for 12 joints. We evaluated two types of error: joint angle error (MAE) and direction angle error ($\Delta\theta$ and $\Delta\psi$), and performed correlation analysis between joints. The results show that unifying the coordinate system (Y-axis orientation) substantially improves elbow direction angle error; that left and right hip depth error exhibit a strong negative correlation (r = $-0.84$); and that errors follow systematic patterns. These findings are useful for understanding the practical scope and limitations of MediaPipe.
\vspace{-0.8em}
\section{Introduction}
Pose estimation is used in sports analysis, rehabilitation, ergonomics, and many other fields. MediaPipe, in particular, is a machine-learning-based pose estimation framework developed by Google and is notable for enabling real-time processing.

Quantitative evaluation of MediaPipe's estimation accuracy, however, has been limited, and error in joint angles in 3D space has not been thoroughly validated. Bazarevsky et al.\cite{blazepose} report BlazePose accuracy, but systematic evaluation of how accuracy varies with viewpoint is scarce. In practice, camera placement depends on the environment, so it is important to characterize accuracy from various viewpoints.

In this study, we obtain Ground Truth (GT) in a Unity environment and compare it with MediaPipe estimates to clarify its accuracy and limitations. We quantify joint angle error and direction angle error under diverse camera layouts and discuss causes of error and directions for improvement.

\section{Experimental Method}

\subsection{Experimental Environment}
Using Unity (version 6000.0.60f1), we built a walking simulation with a Y-Bot avatar. The avatar performed a straight walking motion from coordinates (0, 0, $-3$) to (0, 0, 3).

\begin{figure}[!t]
\centering
\includegraphics[width=0.30\textwidth]{Images/camera_layout.png}
\caption{Camera layout (505 positions, layered). The arrow in the center indicates the avatar's walking direction (from (0,0,-3) to (0,0,3), positive Z-axis).}
\end{figure}

Cameras were placed on a 3D grid covering four height layers (Y = 0.5, 1.0, 1.5, 2.0) and horizontal positions (X, Z in the range $-6$ to 6). For each layer we used a $13\times13$ grid with the central $5\times5$ removed, giving $4(13^2-5^2)=576$ camera positions in total. We collected data at 505 positions and captured 107 frames from each. The capture resolution was 1280$\times$720 pixels. This yielded 259,356 observations in total (107 frames $\times$ 505 cameras $\times$ 12 joints, in part) for analysis. The same GT and image data can be used to evaluate other pose estimation methods such as YOLO-Pose.

\begin{figure}[!t]
  \centering
  \includegraphics[width=0.44\textwidth]{Images/Unity実験環境.png}
  \vspace{0.3em}
  \includegraphics[width=0.44\textwidth]{Images/frame_0018.jpg}
  \caption{Unity experiment environment (top) and a sample walking scene (bottom).}
\end{figure}

\subsection{Capture System}

On Unity we implemented a Trigger Zone Capture System. Using \texttt{CaptureSystemManager} (character generation, animation playback, frame capture, joint data recording) and \texttt{AutoCaptureManager} (automatic capture at 505 camera positions read from CSV), we recorded a single character's motion from multiple viewpoints and frames.

\subsection{Data Collection}
From Unity we exported joint coordinates (GT) per frame in CSV format using the HumanBodyBones API. We used MediaPipe's Pose Landmarker to extract 3D coordinates of 33 landmarks from the saved images. Landmarks with visibility below 0.5 were excluded from analysis.

\subsection{Angle Computation and Error Evaluation}

We report \textbf{two types of angle error}. (1) \textbf{Joint angle error (Joint Angle MAE)}: error in the flexion angle formed by three points (0°--180°). It reflects accuracy of how much the joint is bent. (2) \textbf{Direction angle error (Direction Detection Error, $\Delta\theta$ and $\Delta\psi$)}: error in the joint's direction angle with respect to the hip (from $-180°$ to $+180°$). It reflects accuracy of body orientation and direction detection. These are different physical quantities and are distinguished in table and figure captions. Figure~\ref{fig:concept_metrics} illustrates the two evaluation metrics.

\subsubsection{Joint Angle Error (Joint Angle MAE)}
Joint angles were computed from three points (before and after the joint). For the elbow we used upper arm--elbow--forearm; for the knee we used thigh--knee--lower leg. The angle at the vertex between the two vectors was computed. The absolute difference between GT and MediaPipe angles in each frame was averaged over all frames, and MAE (mean absolute error) was used as the evaluation metric.

\subsubsection{Direction Angle Error (Direction Detection Error, $\Delta\theta$, $\Delta\psi$)}
This definition follows the BlazePose specification~\cite{blazepose}, which outputs 3D world coordinates with the hip center as the origin. In a coordinate system with the hip (midpoint of left and right hip joints) as the origin, we define the direction angle of each joint. The angle in the XY plane is $\theta = \mathrm{arctan2}(y, x)$; the angle in the XZ plane is $\psi = \mathrm{arctan2}(z, x)$. The difference between GT and MediaPipe angles, normalized to the range $-180°$--$+180°$, gives $\Delta\theta$ and $\Delta\psi$. Note that Unity's world coordinates use Y-axis up as positive, while MediaPipe's pose\_landmarks use an image coordinate system with Y-axis down. This difference affects $\theta = \mathrm{arctan2}(y, x)$, so before comparison we flipped Y in MediaPipe's relative coordinates to align both coordinate systems. The inter-joint correlation analysis (Tables~2 and~3) and the direction angle errors discussed below are based on this procedure.

\begin{figure}[!t]
\centering
\includegraphics[width=0.48\linewidth]{Images/角度の概念図.png}
\caption{Concept of two evaluation metrics. Left: joint angle (MAE)—flexion angle of three points (0--180°). Right: direction angle ($\Delta\theta$, $\Delta\psi$)—direction angle with hip as origin (-180°--+180°). The figure is a simplified model for visual explanation; the actual analysis uses MediaPipe's 33 landmarks~\cite{blazepose}.}
\label{fig:concept_metrics}
\end{figure}

\section{Experimental Results}

\subsection{Joint Angle Error}
Table~1 gives the MAE for eight joints (left/right shoulder, elbow, hip, knee). As examples of camera-position-wise distribution of direction angle error, Figure~\ref{fig:elbow_heatmaps} shows elbow $\Delta\theta$ and Figure~\ref{fig:hip_psi_heatmap} shows hip $\Delta\psi$. In both cases, error varies considerably with camera viewpoint.

\begin{table}[!t]
\centering
\caption{Statistics of joint angle error (Joint angle MAE, deg).}
\label{tab:joint_angle_error}
\begin{tabular}{llll}
\toprule
Joint & MAE (deg) & Median (deg) & Max (deg) \\
\midrule
Left shoulder & 39.8 & 39.2 & 70.1 \\
Right shoulder & 39.0 & 40.0 & 58.2 \\
Left elbow & 18.6 & 15.9 & 56.9 \\
Right elbow & 18.2 & 13.6 & 46.2 \\
Left hip & 30.2 & 29.4 & 66.0 \\
Right hip & 33.3 & 32.2 & 81.7 \\
Left knee & 17.0 & 16.6 & 43.4 \\
Right knee & 19.5 & 19.4 & 62.3 \\
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[!t]
  \centering
  \includegraphics[width=0.75\linewidth]{Images/Graph/heatmapsY=0.5,1.5/heatmap_L_Elbow_Y0_5.jpg}
  \caption{Heatmap of elbow joint direction angle error $\Delta\theta$ (Y=0.5, left elbow; right elbow shows similar pattern).}
  \label{fig:elbow_heatmaps}
\end{figure}

Figure~\ref{fig:hip_psi_heatmap} shows the hip $\Delta\psi$ heatmap. Left and right hip show similar patterns in absolute value because of their negative correlation (r = $-0.84$).

\begin{figure}[!t]
  \centering
  \includegraphics[width=0.75\linewidth]{Images/Graph/heatmap_HIP_phi/heatmap_LEFT_HIP_psi_Y0_5.jpg}
  \caption{Heatmap of hip joint direction angle error $\Delta\psi$ (Y=0.5, left hip; right hip shows similar pattern).}
  \label{fig:hip_psi_heatmap}
\end{figure}

\subsection{Correlation Analysis of Inter-Joint Error}

We analyzed error correlation between joints using Pearson correlation coefficients. Table~2 lists high-correlation pairs ($|r| > 0.7$) for $\Delta\theta$; Table~3 does so for $\Delta\psi$.

\begin{table}[htbp]
\centering
\caption{High-correlation pairs in XY plane ($\Delta\theta$).}
\label{tab:correlation_theta}
\small
\begin{tabular}{llr}
\toprule
Joint 1 & Joint 2 & Correlation \\
\midrule
LEFT\_ELBOW & RIGHT\_ELBOW & $-0.862$ \\
LEFT\_ELBOW & LEFT\_SHOULDER & 0.788 \\
RIGHT\_ANKLE & RIGHT\_KNEE & 0.767 \\
LEFT\_ANKLE & LEFT\_KNEE & 0.766 \\
RIGHT\_ELBOW & RIGHT\_SHOULDER & 0.710 \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[htbp]
\centering
\caption{High-correlation pairs in XZ plane ($\Delta\psi$).}
\label{tab:correlation_psi}
\small
\begin{tabular}{llr}
\toprule
Joint 1 & Joint 2 & Correlation \\
\midrule
LEFT\_HIP & RIGHT\_HIP & $-0.840$ \\
RIGHT\_ELBOW & RIGHT\_SHOULDER & 0.770 \\
RIGHT\_ELBOW & RIGHT\_WRIST & 0.769 \\
LEFT\_ELBOW & LEFT\_SHOULDER & 0.768 \\
RIGHT\_SHOULDER & RIGHT\_WRIST & 0.726 \\
LEFT\_ELBOW & LEFT\_WRIST & 0.722 \\
RIGHT\_ELBOW & RIGHT\_HIP & 0.721 \\
LEFT\_HIP & RIGHT\_ELBOW & $-0.705$ \\
\bottomrule
\end{tabular}
\end{table}

In the XY plane we observed a strong negative correlation between left and right elbow (r = $-0.862$) and positive correlations for same-side elbow--shoulder and ankle--knee. In the XZ plane, the strong negative correlation at the hip (r = $-0.84$) and the coupled error along the upper limb (shoulder--elbow--wrist, r = 0.72--0.77) were notable. These correlation patterns are thought to reflect error propagation and constraints of the model architecture. Figure~\ref{fig:correlation_heatmaps} shows the correlation matrices.

\begin{figure*}[t]
  \centering
  \begin{minipage}{0.49\textwidth}
    \centering
    \includegraphics[width=\linewidth]{correlation_analysis/heatmap_theta.png}
    \par\medskip
    (a) $\Delta\theta$ (XY plane)
  \end{minipage}\hfill
  \begin{minipage}{0.49\textwidth}
    \centering
    \includegraphics[width=\linewidth]{correlation_analysis/heatmap_psi.png}
    \par\medskip
    (b) $\Delta\psi$ (XZ plane)
  \end{minipage}
  \caption{Correlation matrix of inter-joint errors. (a) $\Delta\theta$ (Table~2), (b) $\Delta\psi$ (Table~3).}
  \label{fig:correlation_heatmaps}
\end{figure*}

\section{Discussion}

\subsection{Causes of Error}

\subsubsection{Causes of Systematic Bias}

MediaPipe's BlazePose estimates each landmark via heatmaps and regression and outputs 3D world coordinates with the hip center as the origin~\cite{blazepose}. This architecture does not explicitly incorporate anatomical constraints such as bone length consistency or pelvic rigidity. In our analysis with a unified coordinate system, the mean elbow direction angle error $|\Delta\theta|$ was about 58°. This error is likely due in part to bias in arm poses in the training data and limitations of monocular depth estimation. Many pose estimation models including MediaPipe are trained on public datasets such as Human3.6M and COCO, where everyday poses—especially standing and walking with arms hanging at the sides—dominate. The fact that left and right elbow errors have opposite signs suggests that left-right flipping was used as data augmentation during training. The standard deviation (about 23--25°) is relatively small, so the remaining error is somewhat predictable and leaves room for correction by post-processing.

\subsubsection{Cause of Symmetric Left-Right Depth Error}

For the hip joints, the mean $|\Delta\psi|$ was about 90°, and the depth-direction ($\psi$) errors of LEFT\_HIP and RIGHT\_HIP showed a strong negative correlation (r = $-0.8402$). That is, when one hip is estimated forward, the other is estimated backward—a depth-wise anti-correlation where one femur (hip) is placed forward and the other backward—meaning the whole pelvis is misperceived as rotating. The reason the left and right hip $\Delta\psi$ heatmaps in Figure~\ref{fig:hip_psi_heatmap} look almost the same is that they are plotted in absolute value; this is consistent with the negative correlation $\Delta\psi_{\text{left}} \approx -\Delta\psi_{\text{right}}$ in each observation.

In MediaPipe's skeleton model, the pelvis is represented as the segment connecting the left and right hip joints (23, 24). It is not a rigid structure decomposed into multiple parts (e.g., sacrum, hip bone) but only the segment between the two hips, so 3D lifting does not impose a rigidity constraint on the depth of both hips. As a result, a small horizontal position difference in the 2D image can easily be interpreted as freedom to place one hip closer and the other farther, leading to a symmetric error pattern where ``if one is forward, the other is backward.''

In addition to the fundamental limits of monocular depth estimation, the skeleton model represents the pelvis as a line without rigidity, so small horizontal differences in the 2D image tend to be overinterpreted as pelvic rotation. Model improvements that incorporate pelvic rigidity as a constraint are needed.

\subsubsection{Cause of High-Variance Error}

For shoulder and ankle, $\Delta\theta$ improved to about 10--12° after coordinate unification, but $\Delta\psi$ remained large: about 93° for shoulder and 88--100° for ankle and wrist. This is thought to stem from instability in 2D detection (clothing, occlusion) and limitations of depth estimation.

\subsubsection{Coupled Error in the Upper Limb}

The high positive correlation (r = 0.72--0.77) in $\Delta\psi$ among upper-limb joints (shoulder, elbow, wrist) is thought to be due to error propagation in hierarchical estimation or to constraints that treat the upper limb as rigid.

\subsubsection{Camera Viewpoint Dependence}

When the best camera per frame is used, $|\Delta\theta|$ ranges from about 6° to about 16°. The bias in viewpoint distribution of the training data likely reduces generalization for rarer viewpoints such as oblique or top-down.

\subsection{Directions for Model Design to Reduce Error}

Based on these findings, we outline directions for model design to reduce error. (1) \textbf{Landmark topology}: A model that represents the pelvis not as a line but as a rigid structure with multiple parts and imposes a rigidity constraint on left and right hip depth could directly suppress the symmetric hip error. (2) \textbf{Incorporating rigidity constraints}: In methods such as graph neural networks, incorporating anatomical rigidity of the pelvis and upper limb as regularization or constraints is likely to be effective. (3) \textbf{Output format}: A model that outputs a joint structure in one-to-one correspondence with animation systems such as Unity Humanoid would reduce the complexity of coordinate conversion and ease integration. (4) \textbf{Combining post-processing and training}: Coordinate unification (e.g., the Y-flip used in this paper) can be handled in post-processing, but expanding multi-view data or fine-tuning is effective for the remaining error. Validation of these directions is left for future work.

\section{Conclusion}

We quantitatively evaluated MediaPipe's pose estimation accuracy using GT from a Unity environment. From 505 cameras, 107 frames, and 259,356 observations, we reported joint angle MAE (shoulder about 40°, elbow about 18°, hip about 30°, knee about 17--19°) and direction angle error (after coordinate unification: elbow $\Delta\theta$ about 58°, hip $\Delta\psi$ with r = $-0.84$ negative correlation, upper-limb coupling). The errors exhibit systematic patterns and are useful for understanding practical limitations. As future work, we plan to extend evaluation under diverse conditions and to develop correction and tools for elbow and hip.

\section*{Acknowledgments}
This work was supported by the Japan Science and Technology Agency (JST) under the Next-Generation Human Resource Development Program (Global Science Campus Initiative).

\begin{thebibliography}{9}
\bibitem{mediapipe}
Google. MediaPipe Pose. \url{https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker}

\bibitem{blazepose}
V.~Bazarevsky et~al. BlazePose: On-device real-time body pose tracking. \textit{arXiv preprint arXiv:2006.10204}, 2020.

\bibitem{unity}
Unity Technologies. HumanBodyBones. \textit{Unity Documentation}, 2024. \url{https://docs.unity3d.com/ScriptReference/HumanBodyBones.html}
\end{thebibliography}

\end{document}
