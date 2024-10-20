# About

A Python package for including [SVG](
    https://en.wikipedia.org/wiki/Scalable_Vector_Graphics)
graphics in [LaTeX](https://en.wikipedia.org/wiki/LaTeX) via [Inkscape](
    https://inkscape.org).
The package includes a script that converts:

- SVG to [PDF](https://en.wikipedia.org/wiki/PDF) and LaTeX text,
  with the text overlaid in LaTeX over the graphics as PDF.
  The package first separates text from graphics, and then uses Inkscape to
  convert the SVG graphics to a PDF. The text is stored in a LaTeX file with
  extension `.pdf_tex`.

- SVG to PDF, with the text included in the PDF. The package uses Inkscape to
  convert the entire SVG to a PDF.

SVGLaTeX converts the SVG only if the PDF file is older than the SVG source.


# Requirements

- [Inkscape](https://en.wikipedia.org/wiki/Inkscape) >= 1.0.0: needs to
  be installed and the executable `inkscape` in the environment variable
  [`$PATH`](https://en.wikipedia.org/wiki/PATH_(variable)).
  The DPI setting in the package `svglatex` corresponds to
  [Inkscape version 0.92.0](https://inkscape.org/release/inkscape-0.92/)
  and higher.

  On Linux you can install `inkscape` using the operating system's package
  manager, for example `apt install inkscape` on [Debian](
      https://www.debian.org).

  On macOS you can create a symbolic link to `inkscape` and `inkscape-bin`
  as follows:

  ```shell
  ln -s \
      $HOME/Applications/Inkscape.app/Contents/Resources/bin/inkscape \
      $HOME/bin/inkscape
  ln -s \
      $HOME/Applications/Inkscape.app/Contents/Resources/bin/inkscape-bin \
      $HOME/bin/inkscape-bin
  ```

  This assumes that the file `Inkscape.app` is installed in the directory
  `/$HOME/Applications/`.
  The environment variable `$HOME` is described [here](
      https://en.wikipedia.org/wiki/Environment_variable#Examples).

  The last version supporting `inkscape < 1.0.0` was `svglatex == 0.0.2`.


# Installation

From the [Python Package Index (PyPI)](https://pypi.org) using the
package installer [`pip`](https://pip.pypa.io):

```shell
pip install svglatex
```

The Python package installs a script named `svglatex` as entry point.
This script can be invoked from the command line, for example:

```shell
svglatex -h
```


# Usage

For including SVG files in a LaTeX document,
install the Python package `svglatex`
and the LaTeX style [`svglatex.sty`](
    https://github.com/johnyf/latex_packages/blob/main/svglatex.sty),
which includes the LaTeX commands `\includesvg` and `\includesvgpdf`.
The style file `svglatex.sty` can be:

- placed in the directory `$HOME/texmf/tex/latex/local/`, and then invoking
  `texhash $HOME/texmf` registers the style with LaTeX.
  You can find the appropriate location with
  `kpsewhich -var-value=TEXMFHOME`, as discussed [here](
      https://tex.stackexchange.com/a/1138/8666).
  To confirm the LaTeX package installation invoke
  `kpsewhich svglatex.sty`
  Alternatively,

- placed in the LaTeX document directory, or

- the contents of `svglatex.sty` can be copied to
  the LaTeX document's preamble.

For convenience, the file `svglatex.sty` is in the directory `tests/`.
Examples of usage are in the test files `tests/*.tex`.
See `svglatex.sty` for documentation, in particular it needs calling LaTeX
with `--shell-escape`.


# Tests

See the file `tests/README.md`.


# License

[BSD-3](https://opensource.org/licenses/BSD-3-Clause), see file `LICENSE`.
