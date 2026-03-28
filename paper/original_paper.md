\documentclass[twocolumn]{article}

% パッケージの読み込み
\usepackage{xeCJK}
\setCJKmainfont{Noto Serif CJK JP}
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

% 長い単語の改行を許可
\sloppy

% タイトル情報
\title{Unity環境を用いたMediaPipe姿勢推定の精度評価}
\author{%
  非会員\quad 平良\ 文磨$^{*a)}$ \qquad
  正員\quad 加藤\ 司$^{*b)}$ \qquad
  非会員\quad 安富祖\ 仁$^{*c)}$\footnotemark[1]
}
\date{}

\begin{document}

\maketitle
\begingroup
\renewcommand{\thefootnote}{}
\footnotetext[1]{$^{*a)}$ 沖縄県立開邦高等学校，$^{*b)}$ 琉球大学大学院教育学研究科，$^{*c)}$ 株式会社lollol}
\endgroup

\section*{概要}
本研究では、Unity環境で取得したGround Truthを用いてMediaPipeの姿勢推定精度を定量評価した。MediaPipeの精度に関する先行研究は多くが正面視点や限定的なカメラ配置に留まり、実用場面で重要となる多様な視点からの評価は十分でない。

505台のマルチビューカメラから107フレームの歩行データを収集し、12関節について合計259,356観測を得た。関節角度誤差（MAE）と方向角誤差（$\Delta\theta$・$\Delta\psi$）の二種類を評価し、関節間の相関分析を行った。その結果、座標系（Y軸の向き）を統一することで肘の方向角誤差が大きく改善すること、腰の奥行き誤差が左右で強い負の相関（r = -0.84）を示すこと、誤差が体系的なパターンを持つことを明らかにした。これらの知見は、MediaPipeの実用上の適用範囲と限界の把握に有用である。
\vspace{-0.8em}
\section{はじめに}
姿勢推定技術は、スポーツ分析、リハビリテーション、人間工学など幅広い分野で応用されている。特にMediaPipeは、Googleが開発した機械学習ベースの姿勢推定フレームワークであり、リアルタイム処理が可能な点で注目されている。

しかし、MediaPipeの推定精度に関する定量的な評価は限定的であり、特に三次元空間における関節角度の誤差については十分に検証されていない。Bazarevskyら\cite{blazepose}はBlazePoseの精度を報告しているが、視点による精度変化の体系的評価は少ない。実用場面ではカメラ配置は環境に依存するため、様々な視点からの精度特性を把握することが重要である。

本研究では、Unity環境でGround Truth (GT) データを取得し、MediaPipeの推定結果と比較することで、その精度と限界を明らかにする。多様なカメラ配置下での関節角度誤差と方向角誤差を定量化し、誤差の原因と改善の方向性を考察する。

\section{実験方法}

\subsection{実験環境}
Unity(バージョン6000.0.60f1)を用いて、Y-Botアバターによる歩行シミュレーション環境を構築した。アバターは座標(0, 0, -3)から(0, 0, 3)まで直線歩行するモーションを実行した。

\begin{figure}[t]
\centering
\includegraphics[width=0.30\textwidth]{Images/camera_layout.png}
\caption{Camera layout (505 positions, layered). The arrow in the center indicates the avatar's walking direction (from (0,0,-3) to (0,0,3), positive Z-axis).}
\end{figure}

カメラは3次元グリッド状に配置し、異なる高さ4層（Y = 0.5, 1.0, 1.5, 2.0）と水平位置（X, Z = -6〜6の範囲）を網羅した。各層では13×13グリッドから中心の5×5を除いた領域を用い、カメラ数は$4(13^2-5^2)=576$箇所で計算される。実際には505位置のデータを収集し、各位置から107フレームの撮影を行った。撮影解像度は1280×720ピクセルとした。これにより、合計259,356観測（107フレーム×505カメラ×12関節の一部）のデータを解析した。本実験環境は、同一のGT・画像データを用いてYOLO-Pose等の他の姿勢推定手法の評価にも適用可能である。

\begin{figure}[!t]
  \centering
  \includegraphics[width=0.44\textwidth]{Images/Unity実験環境.png}
  \vspace{0.3em}
  \includegraphics[width=0.44\textwidth]{Images/frame_0018.jpg}
  \caption{Unity実験環境（上）と歩行シーンの様子（下）。}
\end{figure}

\subsection{キャプチャシステム}

Unity上でTrigger Zone Capture Systemを構築し、\texttt{CaptureSystemManager}（キャラクター生成・アニメーション再生・フレームキャプチャ・関節データ記録）と\texttt{AutoCaptureManager}（CSVから読み込んだ505カメラ位置での自動撮影）により、単一キャラクターの動作を複数視点・複数フレームで記録した。

\subsection{データ収集}
UnityからはHumanBodyBones APIを用いて、各フレームにおける関節座標(GT)をCSV形式で出力した。MediaPipeのPose Landmarkerを用いて、保存された画像から33ランドマークの3次元座標を抽出した。可視度が0.5未満のランドマークは解析から除外した。

\subsection{角度計算と誤差評価}

本研究では、\textbf{二種類の角度誤差}を報告する。(1) \textbf{関節角度誤差（Joint Angle MAE）}：3点がなす屈曲角の誤差（0°～180°）。関節の曲がり具合の精度を表す。(2) \textbf{方向角誤差（Direction Detection Error, $\Delta\theta$・$\Delta\psi$）}：腰を基準とした関節の方向角の誤差（$-180°$～$+180°$）。体の向き・方向検出の精度を表す。これらは異なる物理量であり、表・図のキャプションで区別する。図\ref{fig:concept_metrics}に二種類の評価指標の概念図を示す。

\subsubsection{関節角度誤差（Joint Angle MAE）}
3点（関節の前後）を用いて関節角度を計算した。肘は「上腕-肘-前腕」、膝は「大腿-膝-下腿」の3点から、頂点における2ベクトルのなす角を算出した。各フレームにおけるGTとMediaPipeの角度差の絶対値を全フレームで平均し、MAE（平均絶対誤差）を評価指標とした。

\subsubsection{方向角誤差（Direction Detection Error, $\Delta\theta$, $\Delta\psi$）}
この定義は、MediaPipeのBlazePoseが3Dワールド座標の原点を腰中心として出力する仕様\cite{blazepose}に準拠している。腰（左右腰関節の中点）を原点とする相対座標において、各関節の方向角を定義する。XY平面の角度を$\theta = \mathrm{arctan2}(y, x)$、XZ平面の角度を$\psi = \mathrm{arctan2}(z, x)$とし、GTとMediaPipeの角度差を$-180°$～$+180°$に正規化したものを$\Delta\theta$、$\Delta\psi$とする。なお、Unityのワールド座標はY軸上向き正、MediaPipeのpose\_landmarksは画像座標系でY軸下向き正である。この向きの差は$\theta = \mathrm{arctan2}(y, x)$に影響するため、比較前にMediaPipeの相対座標においてYを反転し、両座標系を統一した。関節間の相関分析（表2・表3）および考察で示す方向角誤差は、本方式に基づく。

\begin{figure}[!t]
\centering
\includegraphics[width=0.48\linewidth]{Images/角度の概念図.png}
\caption{Concept of two evaluation metrics. Left: joint angle (MAE)—flexion angle of three points (0--180°). Right: direction angle ($\Delta\theta$, $\Delta\psi$)—direction angle with hip as origin (-180°--+180°). The figure is a simplified model for visual explanation; the actual analysis uses MediaPipe's 33 landmarks~\cite{blazepose}.}
\label{fig:concept_metrics}
\end{figure}

\section{実験結果}

\subsection{関節角度の誤差}
8関節（左右肩・肘・腰・膝）のMAEを表1に示す。方向角誤差のカメラ位置別分布の例として、肘の$\Delta\theta$を図\ref{fig:elbow_heatmaps}に、腰の$\Delta\psi$を図\ref{fig:hip_psi_heatmap}に示す。いずれも誤差はカメラ視点によって大きく変動する。

\begin{table}[t]
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

\begin{figure}[t]
  \centering
  \includegraphics[width=0.75\linewidth]{Images/Graph/heatmapsY=0.5,1.5/heatmap_L_Elbow_Y0_5.jpg}
  \caption{Heatmap of elbow joint direction angle error $\Delta\theta$ (Y=0.5, left elbow; right elbow shows similar pattern).}
  \label{fig:elbow_heatmaps}
\end{figure}

図\ref{fig:hip_psi_heatmap}に腰の$\Delta\psi$ヒートマップを示す。左右腰はr = -0.84の負の相関のため絶対値で類似パターンとなる。

\begin{figure}[t]
  \centering
  \includegraphics[width=0.75\linewidth]{Images/Graph/heatmap_HIP_phi/heatmap_LEFT_HIP_psi_Y0_5.jpg}
  \caption{Heatmap of hip joint direction angle error $\Delta\psi$ (Y=0.5, left hip; right hip shows similar pattern).}
  \label{fig:hip_psi_heatmap}
\end{figure}

\subsection{関節間誤差の相関分析}

Pearson相関係数により関節間の誤差相関を分析した。表2に$\Delta\theta$、表3に$\Delta\psi$の高相関ペア（|r| > 0.7）を示す。

\begin{table}[htbp]
\centering
\caption{High-correlation pairs in XY plane ($\Delta\theta$).}
\label{tab:correlation_theta}
\small
\begin{tabular}{llr}
\toprule
Joint 1 & Joint 2 & Correlation \\
\midrule
LEFT\_ELBOW & RIGHT\_ELBOW & -0.862 \\
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
LEFT\_HIP & RIGHT\_HIP & -0.840 \\
RIGHT\_ELBOW & RIGHT\_SHOULDER & 0.770 \\
RIGHT\_ELBOW & RIGHT\_WRIST & 0.769 \\
LEFT\_ELBOW & LEFT\_SHOULDER & 0.768 \\
RIGHT\_SHOULDER & RIGHT\_WRIST & 0.726 \\
LEFT\_ELBOW & LEFT\_WRIST & 0.722 \\
RIGHT\_ELBOW & RIGHT\_HIP & 0.721 \\
LEFT\_HIP & RIGHT\_ELBOW & -0.705 \\
\bottomrule
\end{tabular}
\end{table}

XY平面では左右肘が強い負の相関（r = -0.862）、同側の肘-肩・足首-膝で正の相関を確認した。XZ平面では腰の強い負の相関（r = -0.84）、上肢の肩-肘-手首の連動（r = 0.72--0.77）が顕著である。これらの相関パターンは誤差の伝播やモデルアーキテクチャの制約を反映していると考えられる。図\ref{fig:correlation_heatmaps}に相関行列を示す。

\begin{figure*}[t]
  \centering
  \begin{minipage}{0.49\textwidth}
    \centering
    \includegraphics[width=\linewidth]{correlation_analysis/heatmap_theta.png}
    \par\medskip
    (a) $\Delta\theta$（XY平面）
  \end{minipage}\hfill
  \begin{minipage}{0.49\textwidth}
    \centering
    \includegraphics[width=\linewidth]{correlation_analysis/heatmap_psi.png}
    \par\medskip
    (b) $\Delta\psi$（XZ平面）
  \end{minipage}
  \caption{Correlation matrix of inter-joint errors. (a) $\Delta\theta$ (Table 2), (b) $\Delta\psi$ (Table 3).}
  \label{fig:correlation_heatmaps}
\end{figure*}

\section{考察}

\subsection{誤差の原因}

\subsubsection{体系的バイアスの原因}

MediaPipeのBlazePoseは、各ランドマークをヒートマップと回帰により推定し、3Dワールド座標の原点を腰中心として出力する\cite{blazepose}。このアーキテクチャでは骨長の一貫性や骨盤の剛体性といった解剖学的制約は明示的に組み込まれていない。座標系を統一した上での解析では、肘の方向角誤差$|\Delta\theta|$平均は約58°であった。この誤差には、学習データにおける腕の姿勢の偏りや単眼カメラの奥行き推定限界などが寄与していると考えられる。MediaPipeを含む多くの姿勢推定モデルは、Human3.6MやCOCOなどの公開データセットで学習されているが、これらのデータセットでは日常的な姿勢、特に立位や歩行における腕が体側に垂れ下がった姿勢が大半を占めている。左右の肘で誤差の符号が反転している点は、学習時にデータ拡張として左右反転が用いられたことを示唆する。標準偏差が23--25°程度と比較的小さいことから、この残存誤差はある程度予測可能であり、後処理による補正の余地がある。

\subsubsection{左右対称な奥行き誤差の原因}

腰関節においては、$|\Delta\psi|$平均が約90°と大きく、LEFT\_HIPとRIGHT\_HIPの奥行き方向（ψ）の誤差が強い負の相関（r = -0.8402）を示した。これは、一方の腰が前方に推定されると他方が後方に推定される、すなわち片方の大腿骨（腰）が前に出るともう片方は後ろに出るという奥行き方向の逆相関であり、骨盤全体が回転しているように誤認識されることを意味する。図\ref{fig:hip_psi_heatmap}の左右腰の$\Delta\psi$ヒートマップがほぼ同じパターンを示すのは、絶対値でプロットしているためであり、同一観測で$\Delta\psi_{\text{左}} \approx -\Delta\psi_{\text{右}}$となる負の相関と整合的である。

MediaPipeの骨格モデルでは、骨盤は左右の腰関節（23, 24）を結ぶ直線として表現される。複数部位（仙骨・寛骨など）に分解した剛体構造ではなく、両腰を結ぶ線分のみであるため、3Dリフティング時に両腰の奥行きに剛体制約がかからない。その結果、2D画像上のわずかな水平位置差を、片方を手前に・もう片方を奥に配置する自由度として解釈しやすく、「片方が手前ならもう片方が奥」という対称的な誤差パターンを生じさせやすいと考えられる。

単眼カメラによる奥行き推定の原理的限界に加え、骨格モデルが骨盤を直線で表現するため剛体制約がなく、2D画像上のわずかな水平位置差を骨盤回転として過剰解釈しやすい。骨盤の剛体性を制約として組み込むモデル改良が必要である。

\subsubsection{高変動誤差の原因}

肩・足首の$\Delta\theta$は座標系統一後は約10--12°に改善したが、$\Delta\psi$は肩で約93°、足首・手首で88--100°と大きい。2D検出の不安定性（衣服・オクルージョン）と奥行き推定の限界に起因すると考えられる。

\subsubsection{上肢における連動誤差}

上肢（肩、肘、手首）の$\Delta\psi$が高い正の相関（r = 0.72--0.77）を示すのは、階層的推定による誤差伝播または上肢を剛体として扱う制約によるものと考えられる。

\subsubsection{カメラ視点依存性}

フレームごとの最良カメラで$|\Delta\theta|$が約6°から約16°までばらつく。学習データの視点分布の偏りにより、斜め・俯瞰などの少ない視点では汎化が低下すると考えられる。

\subsection{改善のためのモデル設計の方向性}

本知見に基づき、誤差低減のためのモデル設計の方向性を述べる。(1) \textbf{ランドマークトポロジーの変更}：骨盤を直線ではなく複数部位に分解した剛体構造で表現し、左右腰の奥行きに剛体制約を課すモデルは、腰の左右対称誤差を直接抑制できる可能性がある。(2) \textbf{剛体制約の組み込み}：グラフニューラルネットワーク等において、骨盤・上肢等の解剖学的剛体性を正則化や制約として組み込む手法が有効と考えられる。(3) \textbf{出力形式の再設計}：Unity Humanoid等のアニメーション用途に一対一対応する関節構造で出力するモデルは、座標変換の複雑さを減らし統合を容易にする。(4) \textbf{後処理と学習の併用}：座標系の統一（本論文で実施したY反転など）は後処理で対応可能だが、残存誤差には多視点データの拡充やファインチューニングが有効である。これらの方向性の検証は今後の課題とする。

\section{まとめ}

Unity環境のGTを用いてMediaPipeの姿勢推定精度を定量評価した。505カメラ・107フレーム・259,356観測から、関節角度MAE（肩約40°、肘約18°、腰約30°、膝約17--19°）と方向角誤差（座標系統一後、肘$\Delta\theta$約58°、腰$\Delta\psi$でr=-0.84の負の相関、上肢の連動）を報告した。誤差は体系的なパターンを持ち、実用上の限界把握に有用である。今後の課題として、多様な条件下での評価拡張および肘・腰の補正やツール開発を検討する。

\section*{謝辞}
本研究は，国立研究開発法人科学技術振興機構（JST）の次世代人材育成事業（グローバルサイエンスキャンパス事業）からの支援を受けて実施しました。

\begin{thebibliography}{9}
\bibitem{mediapipe}
Google. MediaPipe Pose. \url{https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker}

\bibitem{blazepose}
V.~Bazarevsky et~al. BlazePose: On-device real-time body pose tracking. \textit{arXiv preprint arXiv:2006.10204}, 2020.

\bibitem{unity}
Unity Technologies. HumanBodyBones. \textit{Unity Documentation}, 2024. \url{https://docs.unity3d.com/ScriptReference/HumanBodyBones.html}
\end{thebibliography}

\end{document}