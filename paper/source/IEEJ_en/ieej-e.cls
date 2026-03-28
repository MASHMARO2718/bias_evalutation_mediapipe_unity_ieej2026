%%
%%% ieej-e.cls (LaTeX2e)
%%   for the Transactions of The Institute of Electrical Engineers of Japan
%%    by Motoaki Sato (ULS and Company), 2002-2022. 
%%     E-mail: teppei@uls.co.jp, http://www.uls.co.jp/
\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\ProvidesClass{ieej-e}
%% based on article.cls [2001/04/21 v1.4e Standard LaTeX document class]
%% based on ieej.cls [2005/03/03 v2.2 for Transactions of IEEJ]
%%[2002/10/01 v1.0 for Transactions of IEEJ (English)]
%%[2002/11/27 v1.0a for Transactions of IEEJ (English)]
%%[2003/01/14 v1.1 for Transactions of IEEJ (English)]
%%[2005/03/03 v1.2 for Transactions of IEEJ (English)]
%%[2005/05/20 v1.3 for Transactions of IEEJ (English)]
%%[2011/03/15 v2.0 for Transactions of IEEJ (English)]
%%[2016/11/07 v2.1 for Transactions of IEEJ (English)]
  [2022/04/06 v3.0 for Transactions of IEEJ (English)]

\def\ieej@warning{\ClassWarningNoLine{ieej-e}}

\newdimen\@JQ
 \@JQ=0.7392507pt
\newdimen\@Q
 \@Q=0.71144pt
\newdimen\@ZW
 \@ZW=3.25mm
\let\inhibitglue\relax

\newif\if@letter \@letterfalse
\DeclareOption{letter}{\@lettertrue}
\newif\if@english \@englishtrue %% \@englishfalse
\DeclareOption{english}{\@englishtrue}
%\newif\if@comment \@commentfalse
%\DeclareOption{comment}{\@commenttrue}
%\newif\if@feature \@featurefalse
%\DeclareOption{feature}{\@featuretrue\@commenttrue}

%\newif\if@ExSum \@ExSumfalse
%\DeclareOption{ExtendedSummary}{\@ExSumtrue}

\newif\if@Proof \@Prooffalse
\DeclareOption{Proof}{\@Prooftrue}

\newcommand\@ptsize{}
\newif\if@restonecol
%\newif\if@titlepage
%\@titlepagefalse
\if@compatibility\else
\DeclareOption{a4paper}
   {\setlength\paperheight {297mm}%
    \setlength\paperwidth  {210mm}}
\fi
\if@compatibility
  \renewcommand\@ptsize{0}
\else
\DeclareOption{10pt}{\renewcommand\@ptsize{0}}
\fi
\DeclareOption{11pt}{\renewcommand\@ptsize{1}}
\DeclareOption{12pt}{\renewcommand\@ptsize{2}}
\if@compatibility\else
\DeclareOption{oneside}{\@twosidefalse \@mparswitchfalse}
\fi
\DeclareOption{twoside}{\@twosidetrue  \@mparswitchtrue}
\DeclareOption{draft}{\setlength\overfullrule{5pt}}
\if@compatibility\else
\DeclareOption{final}{\setlength\overfullrule{0pt}}
\fi
\if@compatibility\else
\DeclareOption{onecolumn}{\@twocolumnfalse}
\fi
\DeclareOption{twocolumn}{\@twocolumntrue}
%\DeclareOption{leqno}{\input{leqno.clo}}
%\DeclareOption{fleqn}{\input{fleqn.clo}}
\DeclareOption{openbib}{%
  \AtEndOfPackage{%
   \renewcommand\@openbib@code{%
      \advance\leftmargin\bibindent
      \itemindent -\bibindent
      \listparindent \itemindent
      \parsep \z@
      }%
   \renewcommand\newblock{\par}}%
}
\ExecuteOptions{a4paper,10pt,twoside,twocolumn,fleqn,final}
\ProcessOptions

% \input{size1\@ptsize.clo}
% based on \ProvidesFile{size10.clo}
%   [2001/04/21 v1.4e Standard LaTeX file (size option)]
%%% normalsize -->10pt 13Q 16.6H
\renewcommand\normalsize{%
   \@setfontsize\normalsize\@xpt{16.6\@Q}%
   \abovedisplayskip 8\p@ \@plus1.5\p@ \@minus4\p@
   \abovedisplayshortskip \z@ \@plus2.5\p@
   \belowdisplayshortskip 5\p@ \@plus2.5\p@ \@minus2.5\p@
   \belowdisplayskip \abovedisplayskip
   \let\@listi\@listI}
\normalsize
\@ifundefined{Cvs}{\newdimen\Cvs}{}
\Cvs\baselineskip

%%% small-->9pt 12Q 14H
\newcommand\small{%
   \@setfontsize\small\@ixpt{14\@Q}%
   \abovedisplayskip 8\p@ \@plus2.5\p@ \@minus3\p@
   \abovedisplayshortskip \z@ \@plus1.5\p@
   \belowdisplayshortskip 3\p@ \@plus1.5\p@ \@minus1.5\p@
   \def\@listi{\leftmargin\leftmargini
               \topsep 4\p@ \@plus2\p@ \@minus2\p@
               \parsep 2\p@ \@plus\p@ \@minus\p@
               \itemsep \parsep}%
   \belowdisplayskip \abovedisplayskip
}
%%% footnotesize-->7pt 10Q 13H
\newcommand\footnotesize{%
   \@setfontsize\footnotesize\@viipt{13\@Q}%
   \abovedisplayskip 5\p@ \@plus1.5\p@ \@minus3\p@
   \abovedisplayshortskip \z@ \@plus\p@
   \belowdisplayshortskip 2.5\p@ \@plus\p@ \@minus1.5\p@
   \def\@listi{\leftmargin\leftmargini
               \topsep 3\p@ \@plus\p@ \@minus\p@
               \parsep 2\p@ \@plus\p@ \@minus\p@
               \itemsep \parsep}%
   \belowdisplayskip \abovedisplayskip
}
%%% Small-->8pt 11Q 13H
\newcommand{\Small}{\@setfontsize\Small\@viiipt{13\@Q}}

\newcommand\scriptsize{\@setfontsize\scriptsize\@viipt\@viiipt}
\newcommand\tiny{\@setfontsize\tiny\@vpt\@vipt}
\newcommand{\large}{\@setfontsize\large\@xipt{23\@Q}}
\newcommand{\Large}{\@setfontsize\Large\@xiipt{23\@Q}}
\newcommand{\LARGE}{\@setfontsize\LARGE\@xivpt{27\@Q}}
\newcommand{\huge}{\@setfontsize\huge\@xviipt{31\@Q}}
\newcommand{\Huge}{\@setfontsize\Huge\@xxpt{30}}

%\if@twocolumn
\setlength\parindent{\@ZW}
%\else
% \setlength\parindent{15\p@}
%\fi
\setlength\smallskipamount{3\p@ \@plus 1\p@ \@minus 1\p@}
\setlength\medskipamount{6\p@ \@plus 2\p@ \@minus 2\p@}
\setlength\bigskipamount{12\p@ \@plus 4\p@ \@minus 4\p@}

\setlength\topskip   {10\p@}% 1\Cht 

%%\if@ExSum
%% \setlength\headheight{\z@}
%% \setlength\headsep   {\z@}
%% \setlength\footskip{\z@}
%%\else
 \setlength\headheight{6mm}
 \setlength\headsep   {2.5mm}% 3.5mm
 \setlength\footskip{9mm}
%%\fi

\if@compatibility
 \setlength\maxdepth{4\p@}
\else
 \setlength\maxdepth{.5\topskip}
\fi

%%\if@ExSum
%% \textwidth  169mm
%%\else
 \textwidth  178.75mm %% 13Qx26x2+13Qx3=676+39=715H (178.75mm)
%%\fi
%\if@compatibility\else
% \@settopoint\textwidth
%\fi

%%\if@ExSum
%% \baselineskip16\@Q
%% \textheight 55\baselineskip
%% \advance \textheight \topskip
%% \advance \textheight .35mm %% limit .33mm
%%\else
 \textheight 59\baselineskip
 \addtolength\textheight{\topskip}
 \addtolength\textheight{.15mm}%% limit .08mm
%%\fi
%\if@compatibility\else
% \@settopoint\textheight
%\fi

\if@twocolumn
 \setlength\marginparsep {10\p@}
\else
  \setlength\marginparsep{11\p@}
\fi
\setlength\marginparpush{5\p@}

\topmargin\paperheight
\advance \topmargin -\textheight
\advance \topmargin -\headheight
\advance \topmargin -\headsep
\advance \topmargin -\footskip
\divide \topmargin \tw@
\advance \topmargin -1in
%\@settopoint\topmargin
\oddsidemargin\paperwidth
\advance \oddsidemargin -\textwidth
\divide \oddsidemargin \tw@
\advance \oddsidemargin -1in
%\@settopoint\oddsidemargin
\evensidemargin\oddsidemargin
%\@settopoint\evensidemargin

\setlength\footnotesep{2.275mm}%%??
\skip\footins .75\baselineskip \@plus 4\p@ \@minus 2\p@
\floatsep 1\baselineskip \@plus 1.5mm \@minus 2mm
\textfloatsep 1.5\baselineskip \@plus 2mm \@minus 2mm
\intextsep 1.5\baselineskip \@plus 1.5mm \@minus 2mm
\dblfloatsep 1\baselineskip \@plus 1.5mm \@minus 2mm
\dbltextfloatsep 1.5\baselineskip \@plus 2mm \@minus 2mm

\setlength\@fptop{0\p@ \@plus 1fil}
\setlength\@fpsep{8\p@ \@plus 2fil}
\setlength\@fpbot{0\p@ \@plus 1fil}
\setlength\@dblfptop{0\p@ \@plus 1fil}
\setlength\@dblfpsep{8\p@ \@plus 2fil}
\setlength\@dblfpbot{0\p@ \@plus 1fil}
\setlength\partopsep{\z@}
\def\@listi{\leftmargin\leftmargini
            \parsep 4\p@ \@plus2\p@ \@minus\p@
            \topsep 8\p@ \@plus2\p@ \@minus4\p@
            \itemsep4\p@ \@plus2\p@ \@minus\p@}
\let\@listI\@listi
\@listi
\def\@listii {\leftmargin\leftmarginii
              \labelwidth\leftmarginii
              \advance\labelwidth-\labelsep
              \topsep    4\p@ \@plus2\p@ \@minus\p@
              \parsep    2\p@ \@plus\p@  \@minus\p@
              \itemsep   \parsep}
\def\@listiii{\leftmargin\leftmarginiii
              \labelwidth\leftmarginiii
              \advance\labelwidth-\labelsep
              \topsep    2\p@ \@plus\p@\@minus\p@
              \parsep    \z@
              \partopsep \p@ \@plus\z@ \@minus\p@
              \itemsep   \topsep}
\def\@listiv {\leftmargin\leftmarginiv
              \labelwidth\leftmarginiv
              \advance\labelwidth-\labelsep}
\def\@listv  {\leftmargin\leftmarginv
              \labelwidth\leftmarginv
              \advance\labelwidth-\labelsep}
\def\@listvi {\leftmargin\leftmarginvi
              \labelwidth\leftmarginvi
              \advance\labelwidth-\labelsep}

\setlength\lineskip{1\p@}
\setlength\normallineskip{1\p@}
\renewcommand\baselinestretch{}
\setlength\parskip{\z@}% 
\@lowpenalty   51
\@medpenalty  151
\@highpenalty 301
\setcounter{topnumber}{5}
\setcounter{bottomnumber}{5}
\setcounter{totalnumber}{10}
\setcounter{dbltopnumber}{5}
\renewcommand{\topfraction}{.95}
\renewcommand{\bottomfraction}{.95}
\renewcommand{\textfraction}{.05}
\renewcommand{\floatpagefraction}{.05}
\renewcommand{\dbltopfraction}{.95}
\renewcommand{\dblfloatpagefraction}{.05}

\if@Proof
 \def\@RH{\rlap{\smash{\raisebox{-1\headsep}%
  {\rule{0.01mm}{10mm}\rule{10mm}{0.01mm}}}}}
 \def\@LH{\llap{\smash{\raisebox{-1\headsep}%
  {\rule{10mm}{0.01mm}\rule{0.01mm}{10mm}}}}}
 \def\@RB{\rlap{\smash{\raisebox{1\footskip}%
  {\rule[-10mm]{0.01mm}{10mm}\rule{10mm}{0.01mm}}}}}
 \def\@LB{\llap{\smash{\raisebox{1\footskip}%
  {\rule{10mm}{0.01mm}\rule[-10mm]{0.01mm}{10mm}}}}}
\else
 \let\@RH\relax \let\@LH\relax \let\@RB\relax \let\@LB\relax 
\fi

\def\nombre@font{\small\sffamily}
\def\foot@font{\Small\sffamily}% \gtfamily

\def\ps@ieej{\let\@mkboth\@gobbletwo
 \def\@oddfoot{\@LB
  \rlap{\Small\normalfont
   \textcopyright\ 
   \f@YEAR\ The Institute of Electrical Engineers of Japan.}\hfil
  {\nombre@font \thepage}\hfil
  \@RB}%
 \let\@evenfoot\@oddfoot
 \def\@evenhead{\@LH
  \hbox to \z@{\hbox to \textwidth{\leaders\hrule height.12mm\hfil}\hss}%
  \ieej@info\hfil
  \@RH}%
 \def\@oddhead{\@LH
  \hbox to \z@{\hbox to \textwidth{\leaders\hrule height.12mm\hfil}\hss}%
  \ieej@info\hfil
  \@RH}%
}

\def\ieej@info{%
 \smash{{%
  \renewcommand{\small}{\@setfontsize\small\@ixpt{16\@Q}}%
  \small
  \raise2mm\hbox{%
  \tabcolsep\z@
  \begin{tabular}[b]{l}
   IEEJ Transactions on \csname Einfo@\@FIELD\endcsname\\[-.5mm]
   Vol.\@VOL\ No.\@NO\ pp.\the\c@page--\pageref{LastPage}\hskip5.5mm
    DOI: 10.1541/ieej\csname DOIinfo@\@FIELD\endcsname.\@VOL.\the\c@page
  \end{tabular}%
  }}}%
}

\def\Einfo@A{Fundamentals and Materials}
\def\Einfo@B{Power and Energy}
\def\Einfo@C{Electronics, Information and Systems}
\def\Einfo@D{Industry Applications}
\def\Einfo@E{Sensors and Micromachines}
\def\Einfo@X{xx}
\def\DOIinfo@A{fms}
\def\DOIinfo@B{pes}
\def\DOIinfo@C{eiss}
\def\DOIinfo@D{ias}
\def\DOIinfo@E{smas}
\def\DOIinfo@X{xxs}

\def\ps@IEEJ{\let\@mkboth\@gobbletwo
 \def\@evenfoot{\@LB
  \hfil{\nombre@font \thepage}\hfil
  \llap{\foot@font 
   IEEJ Trans.\ \e@FIELD, Vol.\@VOL, No.\@NO, \f@YEAR\hskip3.25mm
  }%
  \@RB}%
 \let\@oddfoot\@evenfoot
 \def\@evenhead{\@LH
  \hbox to \z@{\hbox to \textwidth{\leaders\hrule height.12mm\hfil}\hss}%
  \hfil\smash{\raise 3mm\hbox{\small \head@title}}\hfil
  \@RH}%
 \def\@oddhead{\@LH
  \hbox to \z@{\hbox to \textwidth{\leaders\hrule height.12mm\hfil}\hss}%
  \hfil\smash{\raise 3mm\hbox{\small \head@title}}\hfil
  \@RH}%
}

%\if@ExSum
%%%\def\pp#1{\gdef\@pp{#1}}
%%%\def\@pp{}
%
%\def\ps@exsum{\let\@mkboth\@gobbletwo
% \def\@oddfoot{\@LB
%  \hfil{\nombre@font --\,\thepage\,--}\hfil
%  \@RB}%
% \let\@evenfoot\@oddfoot
% \def\@oddhead{\@LH
%  \hbox to \z@{\hbox to \textwidth{%
%   \leaders\hrule \@height-3.4mm \@depth 3.52mm\hfil}\hss}%
%  \smash{\raise -1.4mm\hbox{\Large Extended Summary}}\hfil
%  %\ifx\@pp\empty\else
%  % \smash{\raise -1.4mm\hbox{\small XXX pp.\@pp}}%
%  %\fi
%  \@RH}%
% \let\@evenhead\@oddhead
%}
%\fi

\def\jtitle{\@ifnextchar[% ]
 {\d@jtitle}{\s@jtitle}}

\def\m@headlength#1{%
 \setbox\@tempboxa\hbox{\def\\{\unskip\space\ignorespaces}\small #1}%
  \ifdim \wd\@tempboxa > 174mm
   \ieej@warning{Title for header is too wide, make it shorter}\fi
}

\def\ieejhead@etal{\ \textit{et al.}}

\def\output@head@author{%
 ({\@header@author
   \ifnum\@totalnumber=\@ne\else
    \ieejhead@etal
   \fi})%
}

\def\d@jtitle[#1]#2{%
 \gdef\head@title{\def\\{\unskip\space\ignorespaces}%
  #1\unskip\ \output@head@author}%
 \m@headlength{#1\unskip\ \output@head@author}%
 \gdef\@jtitle{#2}}

\def\s@jtitle#1{%
 \gdef\head@title{\def\\{\unskip\space\ignorespaces}%
  #1\unskip\ \output@head@author}%
 \m@headlength{#1\unskip\ \output@head@author}%
 \gdef\@jtitle{#1}}

\def\@jtitle{}
\def\head@title{}

%%\def\etitle#1{\gdef\@etitle{#1}}
%%\def\@etitle{}

\def\jsubtitle#1{\gdef\@jsubtitle{#1}}
\def\@jsubtitle{}

%%\def\esubtitle#1{\gdef\@esubtitle{#1}}
%%\def\@esubtitle{}

\if@english
 \let\title\jtitle
 \let\subtitle\jsubtitle
\fi

\newtoks\@authorlist
\newcount\@authorcnt
\newcount\@alcnt
\newcount\p@alcnt
 \p@alcnt=12\relax
\newcount\@totalnumber
\newbox\@tempboxb
\newbox\@tempboxc
\newbox\@tempboxd

\def\authorlist#1{%
 \if@english\let\authorentry\Eauthorentry\fi
  \@authorlist={#1}\the\@authorlist
}

\def\get@al#1{%
 \def\@noaffi{none}\def\@tempaffi{#1}%
 \ifx\@noaffi\@tempaffi\else
  \@for\get@label:=#1\do{%
   \@ifundefined{al@\get@label}%
    {%
     \global\advance \@alcnt \@ne
     \expandafter\xdef\csname al@\get@label\endcsname{\the\@alcnt}%
     \global\advance \@tempcnta \@ne
     \protected@xdef\plural@affi{\plural@affi
      \ifnum\@tempcnta=\@ne
       $^{\@fnsymbol{\csname al@\get@label\endcsname}}$%
      \else
       $^{,\@fnsymbol{\csname al@\get@label\endcsname}}$%
      \fi
     }%
    }%
    {%
     \global\advance \@tempcnta \@ne
     \protected@xdef\plural@affi{\plural@affi
      \ifnum\@tempcnta=\@ne
       $^{\@fnsymbol{\csname al@\get@label\endcsname}}$%
      \else
       $^{,\@fnsymbol{\csname al@\get@label\endcsname}}$%
      \fi
     }%
    }%
  }%
 \fi
}

\def\plural@affi{}

\def\Eauthorentry{\@ifnextchar[%% ]
 {\E@Eae}{\NE@Eae}}
\def\NE@Eae#1#2#3{\@ifnextchar[%% ]
  {\NE@EaeP{#1}{#2}{#3}}%   no Email with present aff.
  {\NE@EaeNP{#1}{#2}{#3}}}% no Email without present aff.
\def\E@Eae[#1]#2#3#4{\@ifnextchar[%% ]
  {\E@EaeP[#1]{#2}{#3}{#4}}%    Email with present aff.
  {\E@EaeNP[#1]{#2}{#3}{#4}}}%  Email without present aff.

\def\NE@EaeNP#1#2#3{%
 \@tempcnta\z@
 \advance \@authorcnt \@ne
 %% author label
 \get@al{#3}%
 \def\al@none{0}%
 %% author's name in English
 \@temptokena{#1}%
 \expandafter\protected@xdef\csname @Eauthorname\number\@authorcnt\endcsname{%
  \the\@temptokena\nobreak\plural@affi}%
 %% membership
 \expandafter\xdef\csname @authmbrship\number\@authorcnt\endcsname{%
  \csname #2@member\endcsname}%
 \global\@totalnumber\@authorcnt
 \def\plural@affi{}%
 %% authorname in header
 \ifnum\@authorcnt=\@ne
  \header@author{#1}%
 \fi
}

\def\NE@EaeP#1#2#3[#4]{%
 \@tempcnta\z@
 \advance \@authorcnt \@ne
 %% author label
 \get@al{#3}%
 \def\al@none{0}%
 \@ifundefined{p@al@#4}%
  {\global\advance \p@alcnt \@ne
   \expandafter\xdef\csname p@al@#4\endcsname{\the\p@alcnt}}%
  {\relax}%
 %% author's name in English
 \@temptokena{#1}%
 \expandafter\protected@xdef\csname @Eauthorname\number\@authorcnt\endcsname{%
  \the\@temptokena\nobreak\plural@affi
  $^{\@fnsymbol{\csname p@al@#4\endcsname}}$}%
 %% membership
 \expandafter\xdef\csname @authmbrship\number\@authorcnt\endcsname{%
  \csname #2@member\endcsname}%
 \global\@totalnumber\@authorcnt
 \def\plural@affi{}%
 %% authorname in header
 \ifnum\@authorcnt=\@ne
  \header@author{#1}%
 \fi
}

\def\E@EaeNP[#1]#2#3#4{%
 \@tempcnta\z@
 \advance \@authorcnt \@ne
 %% author label
 \get@al{#4}%
 \def\al@none{0}%
 %% author's name in English
 \def\@tempa{#1}%
 \ifx\@tempa\empty
  \let\ss@mailaddress\relax
 \else
  \stepcounter{enumii}%
  \ft@mailaddress{\hbox to \z@{\hss % (
   \theenumii)\hskip.25\@ZW}Correspondence to: #1}%
 \fi
 \@temptokena{#2}%
 \expandafter\protected@xdef\csname @Eauthorname\number\@authorcnt\endcsname{%
  \the\@temptokena\nobreak\plural@affi
  \nobreak \ss@mailaddress}%
 %% membership
 \expandafter\xdef\csname @authmbrship\number\@authorcnt\endcsname{%
  \csname #3@member\endcsname}%
 \global\@totalnumber\@authorcnt
 \def\plural@affi{}%
 %% authorname in header
 \ifnum\@authorcnt=\@ne
  \header@author{#2}%
 \fi
}

\def\E@EaeP[#1]#2#3#4[#5]{%
 \@tempcnta\z@
 \advance \@authorcnt \@ne
 %% author label
 \get@al{#4}%
 \def\al@none{0}%
 \@ifundefined{p@al@#5}%
  {\global\advance \p@alcnt \@ne
   \expandafter\xdef\csname p@al@#5\endcsname{\the\p@alcnt}}%
  {\relax}%
 %% author's name in English
 \def\@tempa{#1}%
 \ifx\@tempa\empty
  \let\ss@mailaddress\relax
 \else
  \stepcounter{enumii}%
  \ft@mailaddress{\hbox to \z@{\hss % (
   \theenumii)\hskip.25\@ZW}Correspondence to: #1}%
 \fi
 \@temptokena{#2}%
 \expandafter\protected@xdef\csname @Eauthorname\number\@authorcnt\endcsname{%
  \the\@temptokena\nobreak\plural@affi
  $^{\@fnsymbol{\csname p@al@#5\endcsname}}$%
  \nobreak\ss@mailaddress}%
 %% membership
 \expandafter\xdef\csname @authmbrship\number\@authorcnt\endcsname{%
  \csname #3@member\endcsname}%
 \global\@totalnumber\@authorcnt
 \def\plural@affi{}%
 %% authorname in header
 \ifnum\@authorcnt=\@ne
  \header@author{#2}%
 \fi
}

\def\ft@mailaddress#1{%
 \protected@xdef\@mailaddress{%
  \@mailaddress
  \protect\footnotetext[0]{#1}}%
}
\def\@mailaddress{}

\def\ss@mailaddress{%
 \protect\@textsuperscript{%(
  \normalfont\theenumii)}%
}

\def\header@author#1{\gdef\@header@author{#1}}
\def\@header@author{}

\def\authoralign#1{\gdef\@authoralign{#1}}
\authoralign{2}

%% [english], [letter,english]
\def\@outputauthorlist{%
 \def\m@member{Member}%
 \def\n@member{Non-member}%
 \def\a@member{Associate Member}%
 \def\l@member{Life Member}%
 \def\s@member{Student Member}%
 \def\h@member{Honorary Member}%
 \def\S@member{Senior Member}%
 \def\f@member{Fellow}%
 \@authorcnt\z@
 \loop\ifnum \@authorcnt < \@totalnumber
  \advance \@authorcnt \@ne
  \protected@xdef\align@author{\align@author
   {\authorname@font
    \csname @Eauthorname\number\@authorcnt\endcsname\hskip.75em}%
     & \csname @authmbrship\number\@authorcnt\endcsname
    \ifnum\@authoralign=\@ne
     \cr
    \else
     \ifodd\@authorcnt
      \ifnum\@authorcnt=\@totalnumber\cr \else \unskip, & \fi
     \else
      \cr
     \fi
    \fi
  }%
 \repeat
 \align@author
}
\def\align@author{}

\newcount\chk@alcnt
\newcount\chk@p@alcnt

\def\affiliate[#1]#2{%
 \advance \chk@alcnt \@ne
 \@ifundefined{al@#1}%
  {\expandafter\def\csname al@#1\endcsname{1}%
   \ieej@warning{Check the label "#1", it does not correspond to
     ^^J\space\space any labels in \string\authorentry\space command}%
  }{}%
 \bgroup
  \def\\{\hfil\protect\break}%
  \protected@xdef\@affiliate{\@affiliate
   \protect\footnotetext[\csname al@#1\endcsname]{#2}}%
 \egroup
}
\def\@affiliate{}

\def\paffiliate[#1]#2{%
 \advance \chk@p@alcnt \@ne
 \@ifundefined{p@al@#1}%
  {\expandafter\def\csname p@al@#1\endcsname{1}%
   \ieej@warning{Check the label "#1", it does not correspond to
    ^^J\space\space any labels in \string\authorentry\space command}
  }{}%
 \bgroup
  \def\\{\hfil\protect\break}%
  \protected@xdef\p@affiliate{\p@affiliate
   \protect\footnotetext[\csname p@al@#1\endcsname]{#2}}%
 \egroup
}
\def\p@affiliate{}

\def\NoteOnArticle#1{%
 \protected@xdef\@NoteOnArticle{%
  \@NoteOnArticle
  \protect\footnotetext[0]{#1}}% \protect\vspace{\baselineskip}
}
\def\@NoteOnArticle{}

\def\NoteIntConf#1{%
 \protected@xdef\@NoteIntConf{%
  \@NoteIntConf
  \protect\footnotetext[0]{#1}}% \protect\vspace{\baselineskip}
}
\def\@NoteIntConf{}

\newbox\@abstractbox
\newbox\e@keywordbox
\def\abstract{\global\setbox\@abstractbox=\hbox\bgroup
 \begin{minipage}[t]{165.75mm}%
  \normalsize\normalfont\parindent\@ZW\ignorespaces}
\def\endabstract{\end{minipage}\egroup}

\def\ekeyword{\global\setbox\e@keywordbox=\hbox\bgroup
 \begin{minipage}[t]{165.75mm}%
  \small{\bfseries Keywords:\ }\ignorespaces}
\def\endekeyword{\end{minipage}\egroup}

\if@english 
 \let\keyword\ekeyword
 \let\endkeyword\endekeyword
\fi

\newdimen\belowtitlesep
\belowtitlesep\z@

\def\maketitle{\par
 \ifnum \chk@alcnt < \@alcnt
  \ieej@warning{information of \string\affiliate\space is not specified}%
 \fi
 \advance \p@alcnt -12\relax
 \ifnum \chk@p@alcnt < \p@alcnt
  \ieej@warning{information of \string\paffiliate\space is not specified}%
 \fi
  \begingroup
   \long\def\@makefntext##1{\small
     \ifnum \p@alcnt > \@alcnt
      \ifnum \p@alcnt>\thr@@
       \@tempdima=6.875mm  %% 2.5zw
      \else
       \ifnum \p@alcnt=\thr@@
        \@tempdima=5.5mm   %% 2zw
       \else
        \@tempdima=4.125mm %% 1.5zw
       \fi
      \fi
     \else
      \ifnum \@alcnt>\thr@@
       \@tempdima=6.875mm  %% 2.5zw
      \else
       \ifnum \@alcnt=\thr@@
        \@tempdima=5.5mm   %% 2zw
       \else
        \@tempdima=4.125mm %% 1.5zw
       \fi
      \fi
     \fi
     \leftskip\@tempdima
     \leavevmode
     \hbox to \z@{\hss $^{\@thefnmark}$\hskip.6875mm}##1%
   }%
   \if@letter \let\@maketitle\@makelettertitle \fi
   \if@english \let\@maketitle\@makeenglishtitle \fi
   \twocolumn[\@maketitle]%
   \thispagestyle{ieej}%
   \@NoteOnArticle
   \@NoteIntConf
   \@mailaddress
   \@affiliate
   \p@affiliate
  \endgroup
 \global\let\maketitle\relax
 %%\global\let\@maketitle\relax
 %%\global\let\@makelettertitle\relax
 \global\let\@makeenglishtitle\relax
 \global\let\@jtitle\relax
 %%\global\let\@etitle\relax
 \global\let\@authorlist\relax
 \global\let\affiliate\relax
 \global\let\paffiliate\relax
 %%\global\let\@outputJauthorlist\relax
 %%\global\let\@outputEauthorlist\relax
 \global\let\@outputauthorlist\relax
 \@authorcnt\z@
 \loop\ifnum \@authorcnt < \@totalnumber
  \advance \@authorcnt \@ne
   \global\expandafter\let\csname @authmbrship\number\@authorcnt\endcsname
    \relax
   \global\expandafter\let\csname @Eauthorname\number\@authorcnt\endcsname
    \relax
 \repeat
 \def\@fnsymbol##1{\ensuremath{\ifcase##1\or
  \dagger\or {\dagger}{\dagger}\or
  {\dagger}{\dagger}{\dagger}\or {\dagger}{\dagger}{\dagger}{\dagger}\or
  \dagger 5\or
  \dagger 6\or 
  \dagger 7\or \dagger 8\or \dagger 9\else\@ctrerr\fi}}%
 \setcounter{footnote}{0}%
}

\if@letter
 \def\mbrship@font{\small}
 \if@english
  %\font\authorname@font=cmr10 at 10.95pt
  \DeclareRobustCommand\authorname@font{%
   \fontsize{10.95}{\f@baselineskip}\selectfont}
 \fi
\else
 \def\mbrship@font{\normalsize}
 \if@english
  %\font\authorname@font=cmr10 at 14.4pt
  \DeclareRobustCommand\authorname@font{%
   \fontsize{14.4}{\f@baselineskip}\selectfont}
 \fi
\fi

%% [english] and [letter,english]
\def\@makeenglishtitle{%
 \setbox\@tempboxa\hbox{%
  \begin{minipage}{\textwidth}
   \hfill\vbox to 8.5mm{\hrule height .4mm
    \hbox to 18mm{%
     \vrule width .4mm height 7.5mm
      \hss\raise2.25mm\hbox{\LARGE\bfseries\if@letter Letter\else Paper\fi}\hss
     \vrule width .4mm height 7.5mm}%
   \hrule height .4mm}\hspace*{\@ZW}%
   \vskip3mm
   {\huge\centering
    \@jtitle\par
   }%
   \ifx\@jsubtitle\empty\else
    \vskip2mm
    {\LARGE\centering
     \@jsubtitle\par
    }%
   \fi
   \vskip24\@Q
   {%
    \baselineskip23\@Q
    \hfil\vbox{%
     \tabskip\z@
     %\halign{%
     %  ##\hfil & \hskip1em ##\hfil\cr
     % \@outputauthorlist
     %}%
     \halign{%
       ##\hfil & ##\hfil
	& \hskip1.5em ##\hfil & ##\hfil\cr
      \@outputauthorlist
     }%
    }\par
   }%
   \vskip\baselineskip
   {\small
    \@acceptance\par
   }%
   \vskip24\@Q
   \ifvoid\@abstractbox\else
    \hfil\box\@abstractbox\par
    \vskip4\@Q
    \vskip\baselineskip
   \fi
   \ifvoid\e@keywordbox\else
    \hfil\box\e@keywordbox
   \fi
  \end{minipage}%
 }%
  \@tempdima\ht\@tempboxa
  \advance \@tempdima \dp\@tempboxa
  \divide \@tempdima \Cvs
  \@tempcnta=\@tempdima
  \advance \@tempcnta \tw@
  {\newpage\null
   \boxmaxdepth\z@
   \lineskiplimit\z@
   \lineskip\z@
   \parindent\z@
   \vbox to \@tempcnta\Cvs{%
    \leavevmode\box\@tempboxa
   \vss}%
  }\par
  \vspace{\belowtitlesep}%
}

%% [ExtendedSummary]
%\def\makeExSumtitle{\par
% \begingroup
%  \twocolumn[\@makeExSumtitle]
%  \thispagestyle{exsum}
% \endgroup
% \pagestyle{exsum}
% \global\let\makeExSumtitle\relax
% \global\let\@makeExSumtitle\relax
%}
%
%\if@ExSum
% \let\maketitle\makeExSumtitle
%\fi
%
%\def\@makeExSumtitle{%
% \setbox\@tempboxa\hbox{%
%  \begin{minipage}{\textwidth}
%   \vskip6.5mm
%  {\huge\centering
%   \@jtitle\par
%  }%
%  \ifx\@jsubtitle\empty\else
%   \vskip2mm
%   {\Large\centering
%    \@jsubtitle\par
%   }%
%  \fi
%  \vskip1.5\baselineskip
%  {\def\arraystretch{1.8}%
%   \hfil
%   \begin{tabular}{@{}l@{}}
%    \@outputExSum@authorlist
%   \end{tabular}
%  }%
%   \vskip2\baselineskip
%   \ifvoid\e@keywordbox\else
%    \hfil\box\e@keywordbox
%   \fi
%  \end{minipage}%
% }%
%  \small\baselineskip16\@Q
%  \@tempdima \ht\@tempboxa
%  \advance \@tempdima \dp\@tempboxa
%  \@tempdimb \@tempdima
%  \@tempdimc \@tempdima
%  \divide \@tempdimc \baselineskip
%  \@tempcnta=\@tempdimc
%  \@tempdimc \@tempcnta\baselineskip
%  \advance \@tempdimb -\@tempdimc
%  \ifdim \@tempdimb > .5\baselineskip
%   \advance \@tempcnta \tw@
%  \else
%   \advance \@tempcnta \@ne
%  \fi
%  {\newpage\null
%   \boxmaxdepth\z@
%   \lineskiplimit\z@
%   \lineskip\z@
%   \parindent\z@
%   \vbox to \@tempcnta\baselineskip{%
%    \leavevmode\box\@tempboxa
%   \vss}%
%  }\par
%  \vspace{\belowtitlesep}%
%}

%\if@ExSum
%\def\ExSum@shortstack{\@ifnextchar[\@ExSum@shortstack{\@ieej@shortstack[c]}}
%\def\@ExSum@shortstack[#1]{%
%  \leavevmode
%  \vtop\bgroup
%    \let\mb@l\hss\let\mb@r\hss
%    \expandafter\let\csname mb@#1\endcsname\relax
%    \let\\\@stackcr
%    \@ishortstack}
%
%\def\NE@EaeNP#1#2#3{%
% \@tempcnta\z@
% \advance \@authorcnt \@ne
% %% author's name in English
% \@temptokena{#1}%
% \expandafter\protected@xdef\csname @Eauthorname\number\@authorcnt\endcsname{%
%  {\noexpand\authorname@font
%   \the\@temptokena\hskip1em
%   \csname #2@member\endcsname\hskip1em}%
%   \noexpand\small
%   (\noexpand\ExSum@shortstack[l]{%
%    \ignorespaces\csname ExSumAffi@#3\endcsname\unskip)}}%
% \global\@totalnumber\@authorcnt
%}
%
%\def\authorname@font{\fontsize{12}{\f@baselineskip}\selectfont}
%
%\def\affiliate[#1]#2{%
% \expandafter\gdef\csname ExSumAffi@#1\endcsname{#2}%
%}
%\fi

%\def\@outputExSum@authorlist{%
% \gdef\m@member{Member}%
% \gdef\n@member{Non-member}%
% \gdef\a@member{Associate Member}%
% \gdef\l@member{Life Member}%
% \gdef\s@member{Student Member}%
% \gdef\h@member{Honorary Member}%
% \gdef\S@member{Senior Member}%
% \gdef\f@member{Fellow}%
% \@authorcnt\z@
% \process@ExSum@authorlist
%}
%
%\def\process@ExSum@authorlist{%
% \global\advance \@authorcnt \@ne
% \csname @Eauthorname\number\@authorcnt\endcsname\\
% \ifnum\@authorcnt < \@totalnumber \expandafter\process@ExSum@authorlist\fi
%}

\def\FIELD#1{\def\@tempx{#1}%
 \ifx \@tempx\empty
  \gdef\@FIELD{X}%
  \gdef\e@FIELD{XX}%
 \else
  \gdef\@FIELD{#1}%
  \if#1A\gdef\e@FIELD{FM}\else
   \if#1B\gdef\e@FIELD{PE}\else
    \if#1C\gdef\e@FIELD{EIS}\else
     \if#1D\gdef\e@FIELD{IA}\else
      \if#1E\gdef\e@FIELD{SM}\else
       \gdef\e@FIELD{#1}%
       \fi
      \fi
     \fi
    \fi
   \fi
 \fi
}

\def\NO#1{%
 \def\@tempa{#1}%
 \ifx\@tempa\empty
  \gdef\@NO{xx}%
 \else
  \edef\@tempb{\zap@space#1 \@empty}%
  \afterassignment\remove@to@nnil
  \count@ 0\@tempb\relax\@nnil
  \ifnum\count@=\z@
   \gdef\@NO{xx}%
  \else
   \gdef\@NO{\zap@space#1 \@empty}%
  \fi
 \fi
}

\def\YEAR#1{%
 \def\@tempa{#1}%
 \ifx\@tempa\empty
  \gdef\f@YEAR{202x}%
 \else
  \edef\@tempb{\zap@space#1 \@empty}%
  \afterassignment\remove@to@nnil
  \count@ 0\@tempb\relax\@nnil
  \ifnum\count@=\z@
   \xdef\f@YEAR{202x}%
  \else
   \xdef\f@YEAR{\@tempb}%
   \@tempcnta=#1\relax
   \advance \@tempcnta -1880\relax
   \xdef\@VOL{\the\@tempcnta}%
  \fi
 \fi
}

\def\@FIELD{X}
\def\e@FIELD{XX}
\def\@VOL{xxx}
\def\@NO{xx}
\def\f@YEAR{xxxx}

\setcounter{secnumdepth}{3}
%\newcounter {part}
\newcounter {section}
\newcounter {subsection}[section]
\newcounter {subsubsection}[subsection]
\newcounter {paragraph}[subsubsection]
\newcounter {subparagraph}[paragraph]
%\renewcommand \thepart {\@Roman\c@part}
\renewcommand \thesection {\@arabic\c@section}
\renewcommand\thesubsection   {\thesection.\@arabic\c@subsection}
\renewcommand\thesubsubsection{\thesubsection.\@arabic\c@subsubsection}
\renewcommand\theparagraph    {\@arabic\c@paragraph}% \thesubsubsection.
\renewcommand\thesubparagraph {\@arabic\c@subparagraph}% \theparagraph.

\def\@afterheading{%
 \global\@nobreaktrue
 \everypar{%
  \if@nobreak
   \global\@nobreakfalse
   \clubpenalty \z@
    \if@afterindent
    \else
     {\setbox\z@=\lastbox}%
    \fi
  \else
   \clubpenalty\@clubpenalty
   \everypar{}%
  \fi}%
}

%% \@startsection{NAME}{LEVEL}{INDENT}{BEFORESKIP}{AFTERSKIP}{STYLE}
\def\@startsection#1#2#3#4#5#6{\if@noskipsec \leavevmode \fi
   \par \@tempskipa #4\relax
   \@afterindenttrue
   \ifdim \@tempskipa <\z@ \@tempskipa -\@tempskipa \@afterindentfalse\fi
   \if@nobreak
    \everypar{}%
   \else
    %\addpenalty\@secpenalty
    \vskip-\prevdepth \prevdepth\z@ \vskip\Cvs
    \advance\@tempskipa-\Cvs
    \vspace*{\@tempskipa}
    %\addvspace\@tempskipa
   \fi
 \@ifstar{\@ssect{#3}{#4}{#5}{#6}}{\@dblarg{\@sect{#1}{#2}{#3}{#4}{#5}{#6}}}}

\def\sectionnum@font{\sffamily\fontsize{14\@Q}{\z@}\selectfont}
\def\subsectionnum@font{\sffamily\normalsize}
\def\dotafter@section{.}

%% \@sect{NAME}{LEVEL}{INDENT}{BEFORESKIP}{AFTERSKIP}{STYLE}[ARG1]{ARG2}
%% \ifdim \@tempskipa>\z@ --> \ifdim \@tempskipa<\z@
\def\@sect#1#2#3#4#5#6[#7]#8{%
 \ifnum #2>\c@secnumdepth
  \let\@svsec\@empty
 \else
  \refstepcounter{#1}%
  %\protected@edef\@svsec{\@seccntformat{#1}\relax}%
  \ifnum#2=\@ne
   \if@letter
    \protected@edef\@svsec{%
     {\csname sub#1num@font\endcsname\csname the#1\endcsname
      \csname dotafter@#1\endcsname\hskip\@ZW}}%
   \else
    \protected@edef\@svsec{%
     {\csname #1num@font\endcsname\csname the#1\endcsname
      \csname dotafter@#1\endcsname\hskip3.5mm}}%
   \fi
  \else
   \protected@edef\@svsec{%
    {\noexpand\subsectionnum@font % \noexpand\gtfamily
     \csname the#1\endcsname\hskip\@ZW}}%
  \fi
 \fi
  \@tempskipa #5\relax
  \ifdim \@tempskipa<\z@
   \def\@svsechd{#6{\hskip #3\relax \@svsec\inhibitglue #8}}%
  \else
   \begingroup
    #6{%
      \@hangfrom{\hskip #3\relax\@svsec}\interlinepenalty\@M
       \inhibitglue #8\@@par
      }%
   \endgroup
  \fi
  \@xsect{#5}}

%% \@ssect{INDENT}{BEFORESKIP}{AFTERSKIP}{STYLE}{ARG} ==
%% \ifdim \@tempskipa>\z@ --> \ifdim \@tempskipa<\z@
\def\@ssect#1#2#3#4#5{%
  \@tempskipa #3\relax
  \ifdim \@tempskipa<\z@
   \def\@svsechd{#4{\hskip #1\relax #5}}%
  \else
   \begingroup
    #4{%
     \@hangfrom{\hskip #1}\interlinepenalty \@M #5\@@par
    }%
   \endgroup
  \fi
 \@xsect{#3}}

%% \ifdim \@tempskipa>\z@ --> \ifdim \@tempskipa<\z@
\def\@xsect#1{%
  \@tempskipa #1\relax
  \ifdim \@tempskipa<\z@
    \@nobreakfalse
    \global\@noskipsectrue
    \everypar{%
      \if@noskipsec
        \global\@noskipsecfalse
       {\setbox\z@\lastbox}%
        \clubpenalty\@M
        \begingroup \@svsechd \endgroup
        \unskip
        \@tempskipa #1\relax
        \hskip -\@tempskipa
        \pagebreak[2]%
      \else
        \clubpenalty \@clubpenalty
        \everypar{}%
      \fi}%
  \else
    \par \nobreak
    \vskip \@tempskipa
    \@afterheading
  \fi
  \ignorespaces}

%%\def\@seccntformat#1{\csname the#1\endcsname\hskip1zw}

%%\DeclareFixedFont{\KFsec}{JY1}{gt}{m}{n}{14\@JQ}
\def\sec@font{\bfseries\fontsize{10.95}{\Cvs}\selectfont}% \KFsec

\if@letter
 \newcommand{\section}{\@startsection{section}{1}{\@ZW}% 1zw
   {\z@ \@plus .2ex \@minus .1ex}%
   {\z@ \@plus .2ex \@minus .1ex}%
   {\reset@font\normalsize\bfseries\mathversion{bold}}}
\else
 \newcommand{\section}{\@startsection{section}{1}{3.5mm}% 1zw
   {.5\Cvs \@plus .5ex \@minus .1ex}%
   {.5\Cvs \@plus .5ex \@minus .1ex}%
   {\reset@font\sec@font\mathversion{bold}}}
\fi
\newcommand{\subsection}{\@startsection{subsection}{2}{\@ZW}% 1zw
  {\z@ \@plus .2ex \@minus .1ex}%
  {-2\@ZW}% -2zw
  {\reset@font\normalsize\bfseries\mathversion{bold}}}
\newcommand{\subsubsection}{\@startsection{subsubsection}{3}{\@ZW}% 1zw
  {\z@ \@plus .2ex \@minus .1ex}%
  {-2\@ZW}% -2zw
  {\reset@font\normalsize\bfseries\mathversion{bold}}}
\newcommand{\paragraph}{\@startsection{paragraph}{4}{\@ZW}% 1zw
   {\z@ \@plus .2ex \@minus .1ex}%
   {-2\@ZW}% -2zw
   {\reset@font\normalsize}}
\newcommand{\subparagraph}{\@startsection{subparagraph}{5}{\@ZW}% 1zw
   {\z@ \@plus .2ex \@minus .1ex}%
   {-2\@ZW}% -2zw
   {\reset@font\normalsize}}

\newcommand{\appendix}{\par %}{
 \section*{\centering Appendix}
 \renewcommand{\section}{\@startsection{section}{1}{\@ZW}% 1zw
   {\z@ \@plus .2ex \@minus .1ex}%
   {\z@ \@plus .2ex \@minus .1ex}%
   {\reset@font\normalsize\bfseries}}%
 \setcounter{section}{0}
 \setcounter{subsection}{0}
 \setcounter{equation}{0}
 \setcounter{figure}{0}
 \setcounter{table}{0}
 \if@english
  \def\theequation{A\arabic{equation}}%
 \fi
  \def\fnum@efigure{app.\,Fig.\,\thefigure.}%
  \def\fnum@etable{app.\,Table~\thetable.}%
}

\if@twocolumn
  \setlength\leftmargini  {2\@ZW}% 2em
\else
  \setlength\leftmargini  {2\@ZW}% 2.5em
\fi
\leftmargin  \leftmargini
\setlength\leftmarginii  {2\@ZW}% 2.2em
\setlength\leftmarginiii {2\@ZW}% 1.87em
\setlength\leftmarginiv  {2\@ZW}% 1.7em
\if@twocolumn
  \setlength\leftmarginv  {\@ZW}% .5em
  \setlength\leftmarginvi {\@ZW}% .5em
\else
  \setlength\leftmarginv  {\@ZW}% 1em
  \setlength\leftmarginvi {\@ZW}% 1em
\fi
\setlength  \labelsep  {\@ZW}% .5em
\setlength  \labelwidth{\leftmargini}
\addtolength\labelwidth{-\labelsep}
\@beginparpenalty\z@ % -\@lowpenalty
\@endparpenalty\z@ %   -\@lowpenalty
\@itempenalty\z@ %     -\@lowpenalty

\renewcommand\theenumi{\@arabic\c@enumi}
\renewcommand\theenumii{\@alph\c@enumii}
\renewcommand\theenumiii{\@roman\c@enumiii}
\renewcommand\theenumiv{\@Alph\c@enumiv}
%\newcommand\labelenumi{\theenumi.}
\newcommand\labelenumi{(\,\theenumi\,)}
%\newcommand\labelenumii{(\theenumii)}
\newcommand\labelenumii{(\,\theenumii\,)}
\newcommand\labelenumiii{\theenumiii.}
\newcommand\labelenumiv{\theenumiv.}
\renewcommand\p@enumii{\theenumi}
\renewcommand\p@enumiii{\theenumi(\theenumii)}
\renewcommand\p@enumiv{\p@enumiii\theenumiii}

\renewenvironment{enumerate}
  {\ifnum \@enumdepth >3\relax\@toodeep\else
   \advance\@enumdepth\@ne
   \edef\@enumctr{enum\romannumeral\the\@enumdepth}%
   \list{\csname label\@enumctr\endcsname}{%
         \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
	 \leftmargin3\@ZW
	 \labelwidth2\@ZW
	 \labelsep1\@ZW
	 \itemindent1\@ZW
	 \listparindent1\@ZW
         \clubpenalty-200\relax
         \usecounter{\@enumctr}%
         \def\makelabel##1{\hss\llap{##1}}}%
   \fi}{\endlist}

\newcommand{\labelitemi}{\leavevmode
 \hbox to \@ZW{\hss\textbullet\hss}}
\newcommand{\labelitemii}{\leavevmode
 \hbox to \@ZW{\hss $\circ$\hss}}% \textendash
\newcommand{\labelitemiii}{\leavevmode
 \hbox to \@ZW{\hss $\star$\hss}}% \textasteriskcentered
\newcommand{\labelitemiv}{\leavevmode
 \hbox to \@ZW{\hss \textasteriskcentered\hss}}% \textperiodcentered

\renewenvironment{itemize}
  {\ifnum \@itemdepth >3\relax\@toodeep\else
   \advance\@itemdepth\@ne
   \edef\@itemitem{labelitem\romannumeral\the\@itemdepth}%
   \expandafter
   \list{\csname \@itemitem\endcsname}{%
	 \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
	 \leftmargin2\@ZW
	 \labelwidth1\@ZW
	 \labelsep\z@ %% \itemindent
	 \listparindent1\@ZW
	 \clubpenalty-200
         \def\makelabel##1{\leavevmode\hbox to \@ZW{\hss ##1\hss}}%
   }%
   \fi}{\endlist}

\newenvironment{description}
               {\list{}{\labelwidth\z@ \itemindent-\leftmargin
                        \let\makelabel\descriptionlabel}}
               {\endlist}
\newcommand*\descriptionlabel[1]{\hspace\labelsep
                                \normalfont\bfseries #1}

%%\def\descriptionlabel#1{%
%%  \setbox0\hbox{\bfseries #1}%
%%  \dimen0=\wd0 \dimen1=1zw
%%  \divide \dimen0 \dimen1
%%  \multiply \dimen0 \dimen1
%%  \ifdim\dimen0<\wd0 \advance \dimen0 \dimen1\fi
%%  \hbox to \dimen0{\box0 \hfil}\hfil}

%%\def\description{\list{}{%
%%  \leftmargin1zw
%%  \labelwidth\leftmargin
%%  \labelsep1zw
%%  \listparindent1zw
%%  \advance \labelwidth -\labelsep
%%  \let\makelabel\descriptionlabel
%%  \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@}}
%%\let\enddescription\endlist

\newskip\@hlskip
\@hlskip=.5\baselineskip \@plus 1mm \@minus .5mm

%\newenvironment{verse}
%               {\let\\\@centercr
%                \list{}{\itemsep      \z@
%                        \itemindent   -1.5em%
%                        \listparindent\itemindent
%                        \rightmargin  \leftmargin
%                        \advance\leftmargin 1.5em}%
%                \item\relax}
%               {\endlist}
%\newenvironment{quotation}
%               {\list{}{\listparindent 1.5em%
%                        \itemindent    \listparindent
%                        \rightmargin   \leftmargin
%                        \parsep        \z@ \@plus\p@}%
%                \item\relax}
%               {\endlist}
%\newenvironment{quote}
%               {\list{}{\rightmargin\leftmargin}%
%                \item\relax}
%               {\endlist}

\newenvironment{verse}
  {\let\\\@centercr
   \list{}{\itemsep\z@
           \topsep\@hlskip\parsep\z@\partopsep\z@
           \itemindent -1\@ZW
           \listparindent\itemindent
           \rightmargin\leftmargin \advance\leftmargin 1\@ZW}%
           \item\relax}{\endlist}

\newenvironment{quotation}
  {\list{}{\listparindent \@ZW
           \itemindent\listparindent
           \rightmargin\leftmargin
           \topsep\@hlskip\parsep\z@\partopsep\z@
           }%
           \item\relax}{\endlist}

\newenvironment{quote}
  {\list{}{%
           \topsep\@hlskip\parsep\z@\partopsep\z@
           \rightmargin\leftmargin}%
           \item\relax}{\endlist}

\gdef\tabbing{\lineskip \z@skip\let\>\@rtab\let\<\@ltab\let\=\@settab
     \let\+\@tabplus\let\-\@tabminus\let\`\@tabrj\let\'\@tablab
     \let\\=\@tabcr
     \@hightab\@firsttab
     \global\@nxttabmar\@firsttab
     \dimen\@firsttab\@totalleftmargin
     \global\@tabpush\z@ \global\@rjfieldfalse
     \topsep\@hlskip \parsep\z@\partopsep\z@
     \trivlist \item\relax
     \if@minipage\else\vskip\parskip\fi
     \setbox\@tabfbox\hbox{%
       \rlap{\hskip\@totalleftmargin\indent\the\everypar}}%
     \def\@itemfudge{\box\@tabfbox}%
     \@startline\ignorespaces}

\newdimen\verbatimleftmargin
  \verbatimleftmargin\z@
\newdimen\verbatimbaselineskip
  \verbatimbaselineskip\baselineskip
\def\verbatimsize{\normalsize}

\def\@verbatim{%
 \topsep\z@ % \@hlskip
 \partopsep\z@\parsep\z@\itemsep\z@
 \trivlist \item\relax
  \if@minipage\else
   \vskip\baselineskip
   \vskip-\verbatimbaselineskip
   %\vskip\parskip
  \fi
  \leftskip\@totalleftmargin
  \if@minipage\else
   \advance \leftskip by \verbatimleftmargin
  \fi
  \rightskip\z@skip
  \parindent\z@\parfillskip\@flushglue\parskip\z@skip
  \@@par
  \@tempswafalse
  \def\par{%
    \if@tempswa
      \leavevmode \null \@@par\penalty\interlinepenalty
    \else
      \@tempswatrue
      \ifhmode\@@par\penalty\interlinepenalty\fi
    \fi}%
  \let\do\@makeother \dospecials
  \obeylines 
   \verbatimsize \baselineskip\verbatimbaselineskip
   \verbatim@font \@noligs
  \everypar \expandafter{\the\everypar \unpenalty}%
}
%\def\verbatim@font{\normalfont\ttfamily}

\setlength\arraycolsep{5\p@}
\setlength\tabcolsep{.5\@ZW}
\setlength\arrayrulewidth{.12mm}
\setlength\doublerulesep{2\p@}
\setlength\tabbingsep{\labelsep}
\skip\@mpfootins = \skip\footins
\setlength\fboxsep{.5\@ZW}
\setlength\fboxrule{.1mm}
\renewcommand \theequation {\@arabic\c@equation}

\newcounter{figure}
\renewcommand{\thefigure}{\@arabic\c@figure}
\def\fps@figure{tbp}
\def\ftype@figure{1}
\def\ext@figure{lof}
\def\fnum@figure{\figurename~\thefigure}
\def\fnum@efigure{Fig.\,\thefigure.}
\newenvironment{figure}
               {\@floatenv\capwidth72mm\ecapwidth72mm
                \abovecaptionskip1mm\belowcaptionskip\z@\@float{figure}}
               {\end@float}
\newenvironment{figure*}
               {\@floatenv\capwidth.8\textwidth\ecapwidth.8\textwidth
                \abovecaptionskip1mm\belowcaptionskip\z@\@dblfloat{figure}}
               {\end@dblfloat}
\newcounter{table}
\renewcommand{\thetable}{\@arabic\c@table}
\def\fps@table{tbp}
\def\ftype@table{2}
\def\ext@table{lot}
\def\fnum@table{\tablename~\thetable}
\def\fnum@etable{Table~\thetable.}
\newenvironment{table}
               {\@floatenv\capwidth72mm\ecapwidth72mm
                \abovecaptionskip\z@\belowcaptionskip1.5mm\@float{table}}
               {\end@float}
\newenvironment{table*}
               {\@floatenv\capwidth.8\textwidth\ecapwidth.8\textwidth
                \abovecaptionskip\z@\belowcaptionskip1.5mm\@dblfloat{table}}
               {\end@dblfloat}

\def\@floatboxreset {%
        \reset@font
        \footnotesize\tabcolsep1.25mm
        \@setminipage
}

\def\@floatenv{\let\center\Center}

\def\Center{\topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
 \trivlist \centering\item\relax}
\def\endCenter{\endtrivlist}

\long\def\@caption#1[#2]#3{\par
 \begingroup
  \@parboxrestore
  \if@minipage
   \@setminipage
  \fi
   \normalsize
   \@makecaption{\csname fnum@#1\endcsname}{\ignorespaces #3}\par
 \endgroup}

\newdimen\abovecaptionskip
\newdimen\belowcaptionskip
\newdimen\capwidth
\newdimen\ecapwidth

%%\long\def\@makecaption#1#2{%
%% \vskip\abovecaptionskip
%%  \belowcaptionskip1mm
%%  \def\capnum@font{\normalfont\sffamily}%
%%  \let\cap@font\relax
%% \setbox\@tempboxa\hbox{\cap@font
%%  \shortstack[c]{{\capnum@font #1}\hskip\@ZW #2}}%
%% \@tempdima\ht\@tempboxa \advance \@tempdima \dp\@tempboxa
%% \ifdim \@tempdima > \baselineskip
%%  \hfil\parbox[t]{\capwidth}{\centering\baselineskip4mm\cap@font
%%   {\capnum@font #1}\hskip\@ZW #2}%
%% \else
%%  \ifdim \wd\@tempboxa > \capwidth
%%   \hfil\parbox[t]{\capwidth}{\centering\baselineskip4mm\cap@font
%%    {\capnum@font #1}\hskip\@ZW #2}%
%%  \else
%%   \hbox to\hsize{\hfil\box\@tempboxa\hfil}%
%%  \fi
%% \fi
%% \vskip\belowcaptionskip
%%}

\long\def\@makecaption#1#2{%
 \vskip\abovecaptionskip
 \small
 \setbox\@tempboxa\hbox{#1\hskip1em #2}%
 \ifdim \wd\@tempboxa > \capwidth
  \hfil\parbox[t]{\capwidth}{\unhbox\@tempboxa\strut}%
 \else
  \hbox to \hsize{\hfil\box\@tempboxa\hfil}%
 \fi
 \vskip\belowcaptionskip
}

%\long\def\ecaption#1{%
% \if@english
%  \refstepcounter\@captype 
%  \vskip\abovecaptionskip
% \fi
% \bgroup
%  \small
%  \setbox\@tempboxa\hbox{\csname fnum@e\@captype\endcsname\hskip1em #1}%
%  \ifdim \wd\@tempboxa > \ecapwidth
%   \hfil\parbox[t]{\ecapwidth}{\unhbox\@tempboxa\strut}%
%  \else
%   \hbox to\hsize{\hfil\box\@tempboxa\hfil}%
%  \fi
%  \vspace{\belowcaptionskip}
% \egroup
%}

%\if@english
% \let\caption\ecaption
% \let\capwidth\ecapwidth
%\fi

\DeclareOldFontCommand{\rm}{\normalfont\rmfamily}{\mathrm}
\DeclareOldFontCommand{\sf}{\normalfont\sffamily}{\mathsf}
\DeclareOldFontCommand{\tt}{\normalfont\ttfamily}{\mathtt}
\DeclareOldFontCommand{\bf}{\normalfont\bfseries}{\mathbf}
\DeclareOldFontCommand{\it}{\normalfont\itshape}{\mathit}
\DeclareOldFontCommand{\sl}{\normalfont\slshape}{\@nomath\sl}
\DeclareOldFontCommand{\sc}{\normalfont\scshape}{\@nomath\sc}
\DeclareRobustCommand*\cal{\@fontswitch\relax\mathcal}
\DeclareRobustCommand*\mit{\@fontswitch\relax\mathnormal}

\newdimen\bibindent
\setlength\bibindent{1.5em}

\newenvironment{thebibliography}[1]{%
 \raggedbottom
 \vskip-\prevdepth\prevdepth\z@
 \vskip7\@Q
  \if@letter
  \else
   \vskip\baselineskip
  \fi
  \pagebreak[2]%
  \vbox to 10mm{%
   \vskip.5\baselineskip
   \hbox to \hsize{%
    \if@letter \normalsize\bfseries \else
     \sec@font\fi
    \hss\refname\hss}%
   \vss
   \hrule height .12mm
   \nopagebreak[4]%
   \vskip.5\baselineskip
  }\par
 \nopagebreak[4]%
 \footnotesize\baselineskip13\@Q
  \list{(\hfil\@arabic\c@enumiv\hfil)}%
   {\@ZW=2.5mm
    \leftmargin 4\@ZW
    \labelwidth 2\@ZW
    \labelsep 1\@ZW
    \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
    \usecounter{enumiv}%
    \let\p@enumiv\@empty
    \renewcommand\theenumiv{\@arabic\c@enumiv}%
 }%
 \sloppy
 \clubpenalty-100
 \@clubpenalty\clubpenalty
 \widowpenalty-100
 \sfcode`\.\@m}
  {\def\@noitemerr
    {\@latex@warning{Empty `thebibliography' environment}}%
   \endlist}

\newcommand\newblock{\hskip .11em\@plus.33em\@minus.07em}
\let\@openbib@code\@empty

\renewcommand\footnoterule{%
  \kern-3\p@
  \hrule\@width \columnwidth
  \kern2.6\p@}
%\newcommand\@makefntext[1]{%
%    \parindent 1em%
%    \noindent
%    \hb@xt@1.8em{\hss\@makefnmark}#1}

\@addtoreset{footnote}{page}
\def\@makefnmark{\hbox{\@textsuperscript{\normalfont\@thefnmark}}}

\newcommand\@makefntext[1]{\small
 \ifnum\c@footnote=\thr@@
  \@tempdima5.5mm
 \else
  \ifnum\c@footnote=4\relax
   \@tempdima6.875mm
  \else
   \@tempdima4.125mm
  \fi
 \fi
 \parindent\@tempdima
 \noindent\hbox to \@tempdima{\hss\@makefnmark\hskip.6875mm}#1}

\def\thefootnote{\fnsymbol{footnote}}
\def\@fnsymbol#1{%\ensuremath{
 \ifcase#1\or *\or **\or 
  ***\or ****\or *5\or *6\or *7\or *8\or *9\or *10\or *11\or *12\or
  \dagger\or \dagger\dagger\or \dagger\dagger\dagger\or
  \dagger\dagger\dagger\dagger
  \else
   \@ctrerr\fi}%}

\def\@eqnnum{{\normalfont \normalcolor (\theequation)\hspace*{\@ZW}}}

\def\@begintheorem#1#2{%
 \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
  \trivlist\item[\hskip \labelsep{\bfseries #1\ #2}]}
\def\@opargbegintheorem#1#2#3{%
 \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
  \trivlist\item[\hskip \labelsep{\bfseries #1\ #2\ (#3)}]}

%\newcommand\contentsname{Contents}
%\newcommand\listfigurename{List of Figures}
%\newcommand\listtablename{List of Tables}
\newcommand\refname{References}
%\newcommand\indexname{Index}
\newcommand\figurename{Figure}
\newcommand\tablename{Table}
%\newcommand\partname{Part}
\newcommand\appendixname{Appendix}
\newcommand\abstractname{Abstract}
\def\today{\ifcase\month\or
  January\or February\or March\or April\or May\or June\or
  July\or August\or September\or October\or November\or December\fi
  \space\number\day, \number\year}
\setlength\columnsep{8mm}
\setlength\columnseprule{0\p@}

%% from "citesort.sty", with a little customized
%\newcount\@minsofar
%\newcount\@min
%\newcount\@cite@temp
%\def\@citex[#1]#2{%
%\if@filesw \immediate \write \@auxout {\string \citation {#2}}\fi
%\@tempcntb\m@ne \let\@h@ld\relax \def\@citea{}%
%\@min\m@ne
%\@cite{%
%  \@for \@citeb:=#2\do {\@ifundefined {b@\@citeb}%
%    {\@h@ld\@citea\@tempcntb\m@ne{\bfseries ?}%
%    \@warning {Citation `\@citeb ' on page \thepage \space undefined}}%
%{\@minsofar\z@ \@for \@scan@cites:=#2\do {%
%  \@ifundefined{b@\@scan@cites}%
%    {\@cite@temp\m@ne}
%    {\@cite@temp\number\csname b@\@scan@cites \endcsname \relax}%
%\ifnum\@cite@temp > \@min% select the next one to list
%    \ifnum\@minsofar = \z@
%      \@minsofar\number\@cite@temp
%      \edef\@scan@copy{\@scan@cites}\else
%    \ifnum\@cite@temp < \@minsofar
%      \@minsofar\number\@cite@temp
%      \edef\@scan@copy{\@scan@cites}\fi\fi\fi}\@tempcnta\@min
%  \ifnum\@minsofar > \z@ % some more
%    \advance\@tempcnta\@ne
%    \@min\@minsofar
%    \ifnum\@tempcnta=\@minsofar %   Number follows previous--hold on to it
%      \ifx\@h@ld\relax
%        \edef \@h@ld{\@citea\csname b@\@scan@copy\endcsname}%
%      \else
%%%     \edef\@h@ld{\ifmmode{)...(}\else)...(\fi
%%%      \csname b@\@scan@copy\endcsname}%
%       \edef\@h@ld{\ifmmode{){\sim}(}\else)${\sim}$(\fi
%        \csname b@\@scan@copy\endcsname}%
%      \fi
%    \else \@h@ld\@citea\csname b@\@scan@copy\endcsname
%          \let\@h@ld\relax
%  \fi % no more
%\fi}%
%\def\@citea{)\penalty\@highpenalty\,(}}\@h@ld}{#1}}
%%% end of citesort.sty
%
%%% from "cite.sty", with a little customized
%\def\@cite#1#2{\leavevmode\unskip
%  \ifnum\lastpenalty=\z@\penalty\@highpenalty\fi% highpenalty before
%  \,$^{\mbox{\tiny ({\multiply\@highpenalty 3 #1% % triple-highpenalties within
%      \if@tempswa,\penalty\@highpenalty\ #2\fi % and before note.
%    })}}$\spacefactor\@m}
%%% end of cite.sty
%
%\let\org@cite\@cite
%\def\cite{\@ifnextchar[% ]
% {\@tempswatrue\let\@cite\org@cite\@citex}
% {\@tempswafalse\let\@cite\org@cite\@citex[]}}
%\def\Cite{\@ifnextchar[% ]
% {\@tempswatrue\let\@cite\@Cite\@citex}
% {\@tempswafalse\let\@cite\@Cite\@citex[]}}
%
%\def\@Cite#1#2{\leavevmode\unskip
%  \ifnum\lastpenalty=\z@\penalty\@highpenalty\fi% highpenalty before
%  \,({\multiply\@highpenalty 3 #1%             % triple-highpenalties within
%      \if@tempswa,\penalty\@highpenalty\ #2\fi % and before note.
%    })\spacefactor\@m}

\def\acknowledgment{\par
 \addpenalty{-\@highpenalty}%
 {\normalfont\bfseries Acknowledgment}\par
 \nopagebreak
}

\def\@acceptance{\par
 \ifx \@received\empty\else
  \noindent\hfil
  (\@received\@revised)\par
 \fi
}

\def\received#1#2#3{\def\@temp@m{#2}\ifx \@temp@m\empty\def\@temp@m{0}\fi
 \def\@recmonth{%
  \ifcase\@temp@m xxx\or January\or February\or March\or April\or 
   May\or June\or July\or August\or September\or October\or 
   November\or December\fi}
    \gdef\@received{Manuscript received \@recmonth\space #3\unskip, 
    #1\unskip\nobreak}}
\def\revised#1#2#3{%
 \def\@revmonth{\def\@temp@m{#2}\ifx \@temp@m\empty\def\@temp@m{0}\fi
  \ifcase\@temp@m xxx\or January\or February\or March\or April\or 
   May\or June\or July\or August\or September\or October\or 
   November\or December\fi}
    \gdef\@revised{, revised \@revmonth\space #3\unskip, #1\unskip}}

\def\@received{}
\def\@revised{}

\newenvironment{biography}{%
 \vskip2\baselineskip
 \Small\normalbaselineskip14\@Q\baselineskip14\@Q
 }{\par}

\def\eprofile{\@ifstar{\n@eprofile}{\@eprofile}}

\def\profile@font{\sffamily}% \bfseries
\newcount\c@profile

\long\def\@eprofile#1#2#3{%
 \advance \c@profile \@ne
 \if #1m \def\p@membership{(Member)}\else
  \if #1s \def\p@membership{(Student Member)}\else
   \if #1n \def\p@membership{(Non-member)}\else
    \if #1a \def\p@membership{(Associate Member)}\else
     \if #1l \def\p@membership{(Life Member)}\else
      \if #1h \def\p@membership{(Honorary Member)}\else
       \if #1S \def\p@membership{(Senior Member)}\else
        \if #1f \def\p@membership{(Fellow)}\else
  \def\p@membership{}%
  \ieej@warning{Check the 1st. argument of \string\profile{#1}{#2}..}%
 \fi\fi\fi\fi\fi\fi\fi\fi
 \parindent\z@
 \setbox\@tempboxa\hbox{\parbox[t]{\hsize}{\parshape=11 \z@ \hsize
  24.75mm 59.73mm 24.75mm 59.73mm 24.75mm 59.73mm 24.75mm 59.73mm 
  24.75mm 59.73mm 24.75mm 59.73mm
  24.75mm 59.73mm 24.75mm 59.73mm 24.75mm 59.73mm \z@ \hsize
  \hskip2.75mm{\bfseries #2}\hskip2.75mm\p@membership\hskip2.75mm #3}}%
 \@tempdima\ht\@tempboxa \advance \@tempdima \dp\@tempboxa
 \output@profile
}

\long\def\n@eprofile#1#2#3{%
 \if #1m \def\p@membership{(Member)}\else
  \if #1s \def\p@membership{(Student Member)}\else
   \if #1n \def\p@membership{(Non-member)}\else
    \if #1a \def\p@membership{(Associate Member)}\else
     \if #1l \def\p@membership{(Life Member)}\else
      \if #1h \def\p@membership{(Honorary Member)}\else
       \if #1S \def\p@membership{(Senior Member)}\else
        \if #1f \def\p@membership{(Fellow)}\else
  \def\p@membership{}%
  \ieej@warning{Check the 1st. argument of \string\profile{#1}{#2}..}%
 \fi\fi\fi\fi\fi\fi\fi\fi
  \parindent2.75mm
  {\bfseries #2}\hskip2.75mm\p@membership\hskip2.75mm #3
  \vskip2\baselineskip
}

\if@english
 \let\profile\eprofile
\fi

\def\output@profile{%
  \ifdim \@tempdima < \if@english 9\else 8\fi\baselineskip
   \vtop to 35.25mm{%
    \leavevmode\smash{\rlap{\profile@box}}%
     \hbox to \hsize{\hss\box\@tempboxa\hss}\vss
    }%
  \else
   \leavevmode\smash{\rlap{\profile@box}}%
    \hbox to \hsize{\hss\box\@tempboxa\hss}%
  \fi
  \vskip2\baselineskip
}

\def\profile@box{%
 \IfFileExists{a\the\c@profile.\ieej@in@ext}%
  {\lower30.5mm\hbox{%
    \resizebox{22mm}{28mm}{\includegraphics{a\the\c@profile.\ieej@in@ext}}}%
  }%
  {\l@p@box}%
}

\def\l@p@box{%
 \lower30.5mm
 \vbox to 28mm{\hrule height .1mm
  \hbox to 22mm{%
   \vrule width .1mm height 27.8mm
    \hss
   \vrule width .1mm height 27.8mm}%
 \hrule height .1mm}%
}

%%% </borrowed from dotseqn.sty by Donald Arseneau>
%%\ProvidesPackage{dotseqn}
%%  [1995/03/22  v1.1 \space Dots leading to equation numbers]
\newcommand\EqnDots{\leaders\hbox{%
 $\m@th \mkern1.5mu\cdot\mkern1.5mu$}\hfill}
\@ifundefined{mathindent}{\newdimen\mathindent \mathindent\leftmargini}{}
\renewcommand{\[}{\relax \ifmmode\@badmath \else
 \begin{trivlist}%
  \@beginparpenalty\predisplaypenalty \@endparpenalty\postdisplaypenalty
  \item[]\leavevmode \hbox to\linewidth\bgroup $\m@th\displaystyle %$
  \hskip\mathindent\bgroup
 \fi}
\renewcommand{\]}{\relax\ifmmode \egroup $\hfil% $
    \egroup \end{trivlist}%
  \else \@badmath \fi}
\renewenvironment{equation}%
 {\@beginparpenalty\predisplaypenalty \@endparpenalty\postdisplaypenalty
     \refstepcounter{equation}\trivlist \item[]\leavevmode
       \hbox to\linewidth\bgroup $\m@th% $
         \displaystyle \hskip\mathindent}%
 {$\EqnDots % $   Replace `\hfil' with dotted leaders `\EqnDots'.
     \displaywidth\linewidth\hbox{\@eqnnum}\egroup \endtrivlist}
\renewenvironment{eqnarray}{%
   \stepcounter{equation}%
   \def\@currentlabel{\p@equation\theequation}%
   \global\@eqnswtrue \m@th \global\@eqcnt\z@  \tabskip\mathindent
   \let\\\@eqncr \setlength\abovedisplayskip\topsep
   \ifvmode \addtolength\abovedisplayskip\partopsep \fi
   \addtolength\abovedisplayskip\parskip
   \setlength\belowdisplayskip\abovedisplayskip
   \setlength\belowdisplayshortskip\abovedisplayskip
   \setlength\abovedisplayshortskip\abovedisplayskip
   $$\everycr{}\halign to\linewidth% $$
   \bgroup
     \hskip\@centering
     $\displaystyle\tabskip\z@skip{##}$\@eqnsel&%
     \global\@eqcnt\@ne \hfil${\DEQ@acs##\DEQ@acs}$\hfil&%
     \global\@eqcnt\tw@ $\displaystyle{##}$\hskip\@centering\cr%
 }% end of "\begin" part
 {\@@eqncr
   \noalign{% vertical skip up to overlay phantom line
      \penalty\@M \vskip-\prevdepth
      \edef\@tempa{\omit\span\omit\span\omit   % span three columns
        \vrule\@depth\the\prevdepth \@width\z@ % strut of proper depth
        \kern-\mathindent \kern\linewidth}%    % full line width
      \nointerlineskip \expandafter % use saved |\@tempa| outside group
   }\@tempa\cr
   \egroup
   \global\advance\c@equation\m@ne$$% $$
   \global\@ignoretrue
 }

%% from latex.ltx
%\def\@@eqncr{\let\reserved@a\relax
%    \ifcase\@eqcnt \def\reserved@a{& & &}\or \def\reserved@a{& &}%
%     \or \def\reserved@a{&}\else
%       \let\reserved@a\@empty
%       \@latex@error{Too many columns in eqnarray environment}\@ehc\fi
%     \reserved@a \if@eqnsw\@eqnnum\stepcounter{equation}\fi
%     \global\@eqnswtrue\global\@eqcnt\z@\cr}
%%

\def\@@eqncr{\let\reserved@a\@empty
   \ifcase\@eqcnt \def\reserved@a{& &}\or \def\reserved@a{&}\fi
   \reserved@a
   \if@eqnsw \egroup $\EqnDots \@eqnnum $\bgroup \stepcounter{equation}%
   \fi \global\@eqnswtrue\global\@eqcnt\z@\cr}
\def\DEQ@acs{\hskip\tw@\arraycolsep}
\DeclareOption{leftjust}{\let\@eqnsel\hfil}
\DeclareOption{nocolsep}{\let\DEQ@acs\null}
\ExecuteOptions{nocolsep}% {leftjust}% 
\ProcessOptions
%% </borrowed from dotseqn.sty>

\def\FRAC#1#2{\leavevmode\kern-.1em
  \raise.5ex\hbox{\the\scriptfont0 #1}\kern-.1em
  /\kern-.15em\lower.25ex\hbox{\the\scriptfont0 #2}}
\def\RN#1{\uppercase\expandafter{\romannumeral#1}}
\def\onelineskip{\vskip\baselineskip}
\def\halflineskip{\vskip.5\baselineskip}
\def\MARU#1{\raisebox{0.1em}%
 {{\normalfont\ooalign{\hfil\lower.168ex\hbox{#1}\hfil\crcr\mathhexbox20D}}}}
%%\def\kintou#1#2{\leavevmode\hbox to #1{%
%% \kanjiskip\z@ plus 1fill minus 1fill\xkanjiskip\kanjiskip #2\hfil}%
%%}
\def\ddash{\leavevmode\hbox{---\kern0pt ---}}
%%\def\ruby#1#2{\leavevmode \setbox0=\hbox{#1}\setbox1=\hbox{\tiny#2}%
%% \ifdim\wd0>\wd1 \dimen0=\wd0 \else \dimen0=\wd1 \fi
%% \hbox{\kanjiskip=\fill
%%  \vbox{\smash{\hbox to \dimen0{\tiny \hfil#2\hfil}}%
%%   \nointerlineskip \hbox to \dimen0{\hfil#1\hfil}}}}
\def\QED{{\unskip\nobreak\hfil\penalty50
 \hskip1\@ZW\hbox{}\nobreak\hfil \hbox{$\Box$\hskip1\@ZW}
 \parfillskip\z@ \finalhyphendemerits\z@\par}}

\def\sloppy{\tolerance9999\hbadness9999\hfuzz.5\p@ \vfuzz.5\p@}

\hbadness4000
\vbadness10001
\tolerance4000\pretolerance\m@ne
\clubpenalty\z@
\widowpenalty\z@
\displaywidowpenalty\z@
\interdisplaylinepenalty\z@ % 100 
\predisplaypenalty\z@       % 1000

\pagestyle{IEEJ}
\pagenumbering{arabic}
\raggedbottom
\if@twocolumn
  \twocolumn
  \sloppy
  \flushbottom
\else
  \onecolumn
\fi
\if@twoside
  \@mparswitchtrue
\else
  \@mparswitchfalse
\fi

%\AtEndDocument{%
% \clearpage
% \addtocounter{page}{-1}%
% \immediate\write\@auxout
%  {\string\newlabel{ieej@lastpage}{{}{\thepage}}}%
% %%\addtocounter{page}{1}%
%}

\AtBeginDocument{%
 \displaywidowpenalty\z@
 \interdisplaylinepenalty\z@
 \predisplaypenalty\z@
 \postdisplaypenalty\z@
 %%
 \RequirePackage{lastpage}%
 %\@ifundefined{cmex@opt}{%
 % \DeclareFontFamily{OMX}{cmex}{}{}%
 % \DeclareFontShape{OMX}{cmex}{m}{n}{%
 %  <->    cmex10
 % }{}%
 %}{%
 % \ifnum\cmex@opt=7\relax
 %  \DeclareFontFamily{OMX}{cmex}{}{}%
 %  \DeclareFontShape{OMX}{cmex}{m}{n}{%
 %   <->    cmex10
 %  }{}%
 % \fi
 %}%
 %%
 %% graphicx
 \@ifpackageloaded{graphics}{}{\RequirePackage{graphicx}}%
 %% cite.sty +\Cite
 \@ifpackageloaded{cite}{%
  %% Superscript cite
  %\renewcommand\citeleft{(}% -> void when superscript opt
  %\renewcommand\citeright{)}% -> void when superscript opt
  %%\providecommand\citepunct{,\penalty\citepunctpenalty%
  %%      \hskip.13emplus.1emminus.1em\relax}%
  \renewcommand\citepunct{\,\penalty\citepunctpenalty}%
  \renewcommand\citeform[1]{(#1)}%
  %\renewcommand\citedash{\sim}%
  \renewcommand\citedash{--}%
  %\def\@citess#1{\mbox{$\m@th^{\hbox{\OverciteFont{#1}}}$}}%
  %% \Cite is same as \citen
  \DeclareRobustCommand{\Cite}{%
   \renewcommand\citeleft{}%
   \renewcommand\citeright{}%
   \@ifnextchar[%]
    {\@tempswatrue\@citex}{\@tempswafalse\@citex[]}}%
 }{}%
 %% amsmath-2018-12-01.sty
 \@ifpackageloaded{amsmath}{%
   \@mathmargin\mathindent
   \multlinegap\@ZW
   \def\maketag@@@#1{\hbox{\m@th\normalfont #1}\hskip3.25mm}%
   \renewcommand{\eqref}[1]{\textup{\tagform@{\ref{#1}}\unskip}}%
   \def\make@display@tag{%
    \if@eqnsw
        \incr@eqnum %%\print@eqnum
        \EqnDots\tagform@\theequation
    \else
        \iftag@
            \df@tag
            \global\let\df@tag\@empty
        \fi
    \fi
    \ifmeasuring@
    \else
      \ifx\df@label\@empty\else
        \@xp\ltx@label\@xp{\df@label}%
        \global\let\df@label\@empty
      \fi
    \fi
   }%
   \renewenvironment{equation}%
    {\@beginparpenalty\predisplaypenalty \@endparpenalty\postdisplaypenalty
        \refstepcounter{equation}\trivlist \item[]\leavevmode
          \hbox to\linewidth\bgroup $\m@th% $
            \displaystyle \hskip\mathindent}%
    {$\EqnDots % $   Replace `\hfil' with dotted leaders `\EqnDots'.
        \displaywidth\linewidth\hbox{\@eqnnum}\egroup \endtrivlist}%
  }{}%
 %\if@ExSum
 % \small
 % \baselineskip16\@Q
 %\fi
 %% for txfonts
 %\def\tmp@rmdefault{txr}%
 %\ifx\rmdefault\tmp@rmdefault
 % \DeclareFontShape{JY1}{txtt}{bx}{n}{<->ssub*gt/m/n}{}%
 % \DeclareFontShape{JT1}{txtt}{bx}{n}{<->ssub*gt/m/n}{}%
 %\fi
 %% eps/pdf
 \@ifundefined{ver@dvips.def}{\def\ieej@in@ext{pdf}}{\def\ieej@in@ext{eps}}%
 %% newtxtext, nfssext-cfr and superiors redefine \@makefnmark.
 \@ifundefined{sustyle}{}{%
  \def\@makefnmark{\hbox{\kern\z@
   \@textsuperscript{\normalfont\@thefnmark}\kern\z@}}%
 }%
}

\endinput
