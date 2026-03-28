"""One-off builder: extract body from legacy mains and write IEEJ main.tex files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_EN = ROOT / "main.tex"
SRC_JA = ROOT / "main_ja.tex"
OUT_EN = ROOT / "IEEJ_en" / "main.tex"
OUT_JA = ROOT / "IEEJ_ja" / "main.tex"


def deg_replace(s: str) -> str:
    # gensymb \degree{} → superscript circ (works inside $...$ as $121^{\circ}$)
    return s.replace(r"\degree{}", r"^{\circ}")


def extract_en():
    lines = SRC_EN.read_text(encoding="utf-8").splitlines()
    # Abstract: after \section*{Abstract} until \vspace before Introduction
    abs_lines = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == r"\section*{Abstract}":
            i += 1
            while i < len(lines) and not lines[i].startswith(r"\vspace"):
                abs_lines.append(lines[i])
                i += 1
            break
        i += 1
    abstract = "\n".join(abs_lines).strip()

    body = []
    in_body = False
    for i, L in enumerate(lines):
        if L.startswith(r"\section{Introduction}"):
            in_body = True
        if in_body:
            if L.startswith(r"\section*{Acknowledgments}"):
                break
            body.append(L)

    ack = []
    ack_started = False
    for i, L in enumerate(lines):
        if L.startswith(r"\section*{Acknowledgments}"):
            ack_started = True
            continue
        if ack_started:
            if L.startswith(r"\begin{thebibliography}"):
                break
            if not L.startswith("%") or L.strip() == "%":
                if L.strip() and not L.startswith("% ==="):
                    ack.append(L)

    bib = []
    bib_on = False
    for L in lines:
        if L.startswith(r"\begin{thebibliography}"):
            bib_on = True
        if bib_on:
            bib.append(L)
            if L.startswith(r"\end{thebibliography}"):
                break

    abstract = deg_replace(abstract)
    body_txt = deg_replace("\n".join(body))
    ack_txt = deg_replace("\n".join(ack)).strip()
    bib_txt = deg_replace("\n".join(bib))

    header = r"""% !TeX program = pdflatex
%% IEEJ English manuscript (ieej-e.cls). Upload this folder to Overleaf as project root.
\documentclass[english,fleqn]{ieej-e}
\usepackage[defaultsups]{newtxtext}
\usepackage[varg]{newtxmath}
\usepackage[superscript,nomove]{cite}
\usepackage{graphicx}
\usepackage{subcaption}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{dblfloatfix}
\setcounter{topnumber}{6}
\setcounter{bottomnumber}{6}
\setcounter{totalnumber}{12}
\renewcommand{\topfraction}{0.92}
\renewcommand{\bottomfraction}{0.92}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.72}
\renewcommand{\dbltopfraction}{0.95}
\renewcommand{\dblfloatpagefraction}{0.72}
\setlength{\dbltextfloatsep}{8pt plus 4pt minus 3pt}
\setlength{\dblfloatsep}{8pt plus 4pt minus 2pt}
\usepackage{url}
\usepackage[pdfencoding=auto]{hyperref}
\hypersetup{%
 setpagesize=false,
 colorlinks=true,
 urlcolor=blue,
 citecolor=black,
 linkcolor=black,
}

%% --- Journal metadata (fill before submission) ---
\FIELD{}
\YEAR{}
\NO{}
%% \received{2026}{3}{15}
%% \revised{}{}{}

\title{Bias Evaluation of MediaPipe Pose Estimation\\
       Using a Unity Simulation Environment}

\authorlist{%
 \authorentry{Fumimaro Taira}{n}{KHS}
 \authorentry{Tsukasa Kato}{m}{UEC}
 \authorentry{Jin Afuso}{n}{LOL}
}
\affiliate[KHS]{Okinawa Prefectural Kaiko High School\\ Japan}
\affiliate[UEC]{Graduate School of Education, University of the Ryukyus\\ Japan}
\affiliate[LOL]{lollol Inc.\\ Japan}

\begin{document}
\begin{abstract}
"""
    footer = r"""
\end{abstract}
\begin{keyword}
MediaPipe, BlazePose, pose estimation, bias evaluation, Unity simulation,
ground truth, joint angle error, direction angle error
\end{keyword}
\maketitle
""" + body_txt + r"""

\acknowledgment

""" + ack_txt + r"""


""" + bib_txt + r"""


\begin{biography}
\profile{n}{Fumimaro Taira}{%
Second-year student, Okinawa Prefectural Kaiko High School.
Two-stage student at Ryudai Kagaku-in under the University of the Ryukyus
SEARCH programme, affiliated with Prof.~Tsukasa Kato's laboratory;
engaged in motion-tracking research.}
\profile{m}{Tsukasa Kato}{Graduate School of Education, University of the Ryukyus.}
\profile{n}{Jin Afuso}{lollol Inc.}
\end{biography}

\end{document}
"""
    OUT_EN.write_text(header + abstract + footer, encoding="utf-8")
    print("Wrote", OUT_EN)


def extract_ja():
    lines = SRC_JA.read_text(encoding="utf-8").splitlines()
    abs_lines = []
    i = 0
    while i < len(lines):
        if "アブストラクト" in lines[i] and lines[i].startswith(r"\section*"):
            i += 1
            while i < len(lines) and not lines[i].startswith(r"\vspace"):
                abs_lines.append(lines[i])
                i += 1
            break
        i += 1
    abstract = deg_replace("\n".join(abs_lines).strip())

    body = []
    for i, L in enumerate(lines):
        if L.startswith(r"\section{はじめに}"):
            body = lines[i:]
            break
    # trim at 謝辞
    trimmed = []
    for L in body:
        if L.startswith(r"\section*{謝辞}"):
            break
        trimmed.append(L)
    body_txt = deg_replace("\n".join(trimmed))

    ack = []
    ack_started = False
    for L in lines:
        if L.startswith(r"\section*{謝辞}"):
            ack_started = True
            continue
        if ack_started:
            if L.startswith(r"\begin{thebibliography}"):
                break
            if L.strip() and not L.startswith("% ==="):
                ack.append(L)
    ack_txt = deg_replace("\n".join(ack)).strip()

    bib = []
    bib_on = False
    for L in lines:
        if L.startswith(r"\begin{thebibliography}"):
            bib_on = True
        if bib_on:
            bib.append(L)
            if L.startswith(r"\end{thebibliography}"):
                break
    bib_txt = deg_replace("\n".join(bib))

    header = r"""% !TeX program = lualatex
%% IEEJ Japanese manuscript (ieej.cls, UTF). Upload this folder to Overleaf as project root.
%% Overleaf: Menu -> Compiler -> LuaLaTeX
\documentclass[fleqn]{ieej}
\usepackage[defaultsups]{newtxtext}
\usepackage[varg]{newtxmath}
\usepackage[superscript,nomove]{cite}
\usepackage{graphicx}
\usepackage{subcaption}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{dblfloatfix}
\setcounter{topnumber}{6}
\setcounter{bottomnumber}{6}
\setcounter{totalnumber}{12}
\renewcommand{\topfraction}{0.92}
\renewcommand{\bottomfraction}{0.92}
\renewcommand{\textfraction}{0.07}
\renewcommand{\floatpagefraction}{0.72}
\renewcommand{\dbltopfraction}{0.95}
\renewcommand{\dblfloatpagefraction}{0.72}
\setlength{\dbltextfloatsep}{8pt plus 4pt minus 3pt}
\setlength{\dblfloatsep}{8pt plus 4pt minus 2pt}
\usepackage{url}
\usepackage[luatex,pdfencoding=auto]{hyperref}
\hypersetup{%
 setpagesize=false,
 colorlinks=true,
 urlcolor=blue,
 citecolor=black,
 linkcolor=black,
}

%% --- Journal metadata (fill before submission) ---
\FIELD{}
\YEAR{}
\NO{}
%% \received{2026}{3}{15}
%% \revised{}{}{}

\jtitle{Unity 環境を用いた MediaPipe 姿勢推定のバイアス評価}
\etitle{Bias Evaluation of MediaPipe Pose Estimation Using a Unity Simulation Environment}

\authorlist{%
 \authorentry{平良 文磨}{Fumimaro Taira}{n}{KHS}
 \authorentry{加藤 司}{Tsukasa Kato}{m}{UEC}
 \authorentry{安富祖 仁}{Jin Afuso}{n}{LOL}
}
\affiliate[KHS]
 {沖縄県立開邦高等学校}
 {Okinawa Prefectural Kaiko High School\\ Japan}
\affiliate[UEC]
 {琉球大学大学院教育学研究科}
 {Graduate School of Education, University of the Ryukyus\\ Japan}
\affiliate[LOL]
 {株式会社lollol}
 {lollol Inc.\\ Japan}

\begin{document}
\begin{abstract}
"""
    # Japanese template uses English abstract in \begin{abstract} often; we put Japanese text here per user content
    footer = r"""
\end{abstract}
\begin{jkeyword}
MediaPipe，BlazePose，姿勢推定，バイアス評価，Unity，シミュレーション，方向角誤差
\end{jkeyword}
\begin{ekeyword}
MediaPipe, BlazePose, pose estimation, bias evaluation, Unity simulation, direction angle error
\end{ekeyword}
\maketitle
""" + body_txt + r"""

\acknowledgment

""" + ack_txt + r"""


""" + bib_txt + r"""


\begin{biography}
\profile{n}{平良 文磨}{%
沖縄県立開邦高等学校2年に在学．琉球大学主催の琉大SEARCHプログラムに基づく
琉大カガク院の二段階生として加藤\ 司教授の研究室に所属し，
モーショントラッキング技術に関する研究に従事している．}
\profile{m}{加藤 司}{琉球大学大学院教育学研究科．}
\profile{n}{安富祖 仁}{株式会社lollol．}
\end{biography}

\end{document}
"""
    OUT_JA.write_text(header + abstract + footer, encoding="utf-8")
    print("Wrote", OUT_JA)


if __name__ == "__main__":
    extract_en()
    extract_ja()
