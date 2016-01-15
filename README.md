These are two Python scripts for using SVG graphics
created with [Inkscape](https://inkscape.org)
in a [LaTeX](https://en.wikipedia.org/wiki/LaTeX) document:

- `inkscape2tex.py` converts SVG files to PDF or EPS,
  optionally typesetting text with an [export option of Inkscape](https://www.ctan.org/tex-archive/info/svg-inkscape?lang=en).

- `inkscape2scenes.py` converts a layered SVG file to
  multiple images, named by layer, for incremental graphics
  animation in a [Beamer](https://en.wikipedia.org/wiki/Beamer_%28LaTeX%29) slide.

These scripts are invoked by the latex commands defined in
[`mycommands.sty`](https://github.com/johnyf/latex_packages/blob/master/mycommands.sty), part of `latex_packages`.
