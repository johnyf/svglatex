all:
	-rm img/beautiful.pdf
	-rm img/beautiful.pdf_tex
	xelatex --interaction=nonstopmode --shell-escape inkscape2tex_test.tex
	# clean to ensure independence
	-rm img/beautiful.pdf
	-rm img/beautiful.pdf_tex
	xelatex --interaction=nonstopmode --shell-escape inkscape2tex_integration_test.tex
