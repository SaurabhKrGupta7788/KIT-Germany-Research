# The `animate` LaTeX Package

© 2007--`\today` Alexander Grahn

https://gitlab.com/agrahn/animate

## Description

This package provides an interface to create portable, JavaScript driven PDF and SVG animations from sets of (vector) graphics or rasterized image files or from inline (vector) graphics, such as LaTeX-picture, PSTricks or pgf/TikZ generated pictures, or just from typeset text.

It supports the usual PDF making workflows, i. e.  pdfLaTeX, LaTeX &rArr; `dvips` &rArr; `ps2pdf` (Ghostscript)/Distiller, (Xe)LaTeX &rArr; `(x)dvipdfmx`, LuaLaTeX, and LaTeX &rArr; `dvisvgm` for SVG.

The resulting PDF with animations can be viewed in Acrobat Reader (except on mobile devices), KDE Okular, PDF-XChange, Foxit Reader, PDF.js (Firefox' built-in PDF viewer and extension for Chromium-based browsers).

Animated SVG are self-contained files that can be embedded into HTML using the `<object>` tag or opened directly in a Web browser, such as Firefox or Chromium.

Note, this file only gives a summary of usage and available package and command options. Please refer to the documentation [`animate.pdf`](http://mirrors.ctan.org/macros/latex/contrib/animate/animate.pdf) for details and examples.

*Keywords:* include portable PDF animation SVG animation animated PDF animated SVG dvisvgm html TeX4ht web animating embed animated graphics LaTeX pdfLaTeX LuaLaTeX PSTricks pgf TikZ LaTeX-picture MetaPost inline graphics vector graphics animated GIF LaTeX dvips ps2pdf dvipdfmx XeLaTeX JavaScript Acrobat Reader KDE Okular PDF-XChange Foxit Reader PDF.js Firefox Chrome Chromium

## Usage

````latex
\usepackage[<package options>]{animate}
````

- **Package options:**

````
width=<h-size>, height=<v-size>, totalheight=<v-size>,
keepaspectratio, scale=<factor>,
bb=<llx> <lly> <urx> <ury>,
viewport=<llx> <lly> <urx> <ury>,
trim=<left> <bottom> <right> <top>,
hiresbb, pagebox=..., interpolate,
type=[<file ext>],
final, draft, nomouse,
autopause, autoplay, autoresume,
controls[=all | none | ...],
controlsaligned=left[+<indent>] | center | right[+<indent>],
buttonsize=<size>,
buttonbg=<colour>, buttonfg=<colour>, buttonalpha=<opacity>,
loop, palindrome, step,
poster[=first | <num> | last | none],
alttext=none | {<alternative description>},
method=icon | widget | ocg,
dvipdfmx, dvisvgm, xetex,
export
````

- **User interface:**

````latex
\animategraphics[<options>]{<frame rate>}{<file basename>}{<first>}{<last>}

\begin{animateinline}[<options>]{<frame rate>}
    ... typeset material ...
\newframe[<frame rate>]
    ... typeset material ...
\newframe*[<frame rate>]
    ... typeset material ...
\newframe
\multiframe{<number of frames>}{[<variables>]}{
    ... repeated (parameterized) material ...
    \multiframebreak % optional !
}
\end{animateinline}
````

- **Command options:**

````
width=<h-size>, height=<v-size>, totalheight=<v-size>,
keepaspectratio, scale=<factor>,
bb=<llx> <lly> <urx> <ury>,
viewport=<llx> <lly> <urx> <ury>,
trim=<left> <bottom> <right> <top>,
hiresbb, pagebox=..., interpolate,
type=[<file ext>],
final, draft, nomouse,
autopause, autoplay, autoresume,
controls[=all | none | ...],
controlsaligned=left[+<indent>] | center | right[+<indent>],
buttonsize=<size>,
buttonbg=<colour>, buttonfg=<colour>, buttonalpha=<opacity>,
loop, palindrome, step,
measure,
poster[=first | <num> | last | none],
alttext=none | {<alternative description>},
begin={<begin text>}, end={<end text>},
timeline=<timeline file>,
method=icon | widget | ocg,
every=<number>, label=<label text>
````

## Requirements

Recent versions of
- Ghostscript or Adobe Distiller
- dvipdfmx
- dvisvgm
- PDF: Acrobat Reader, KDE Okular, PDF-XChange, Foxit Reader, PDF.js, Firefox
- SVG: Blink-based web browsers (Chromium, Chrome, Opera, ...) or Firefox

## Installation

Unzip the file
[`animate.tds.zip`](http://mirrors.ctan.org/install/macros/latex/contrib/animate.tds.zip) into the local TDS root directory which can be found by running

````bash
kpsewhich -var-value TEXMFLOCAL
````

on the command line.

After installation, update the filename database by running `texhash` on the command line.

TeXLive and MiKTeX users should run the package manager for installation.

## License

This material is subject to the [LaTeX Project Public License](http://mirrors.ctan.org/macros/latex/base/lppl.txt).
