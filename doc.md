The package `svglatex` is known to work with `inkscape >= 1.0.0`.
The DPI setting in the package `svglatex` corresponds to `inkscape >= 0.92.0`,
when the DPI setting of `inkscape` changed.


## Practical hints

Sometimes we want some text to remain at the size we have drawn it,
instead of being typeset at the size of other text in LaTeX.
Using a size qualifier is one possibility, for example `{\small Foo}`.
However, the range of font sizes available within a document is limited.
Besides, in some cases it is easier to avoid back and forths for adjusting
the size of text.

Converting text to path is a simple way to achieve this objective in
a drawing program (for example Inkscape). A good candidate for such
conversions are [credit lines](
    https://en.wikipedia.org/wiki/Attribution_(copyright))
for graphics, for example pictures.

The same SVG file may contain also mathematics and other text that *does*
need to be typeset by LaTeX. Separating other cases as above lets you
focus on the text that will benefit from LaTeX.


## Design decisions

The reason for using a module to separate SVG text from SVG graphics,
instead of the LaTeX [export option of Inkscape](
    https://www.ctan.org/tex-archive/info/svg-inkscape?lang=en),
is described in [this GitHub comment](
    https://github.com/johnyf/inkscape/issues/1#issuecomment-290514835).
