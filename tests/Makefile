all:
	-rm img/beautiful.pdf
	-rm img/beautiful.pdf_tex
	xelatex \
	    --interaction=nonstopmode \
	    --shell-escape \
	    svglatex_test.tex
	# clean to ensure independence
	-rm img/beautiful.pdf
	-rm img/beautiful.pdf_tex
	xelatex \
	    --interaction=nonstopmode \
	    --shell-escape \
	    svglatex_integration_test.tex


clean:
	-rm *.pdf_tex
