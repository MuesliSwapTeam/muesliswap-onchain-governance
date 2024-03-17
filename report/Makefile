# Makefile for compiling LaTeX documents

# Variables
DOC=main
DOC2=audit
PDF=$(DOC).pdf
PDF2=$(DOC2).pdf
TEX=$(wildcard *.tex)
BIB=$(wildcard *.bib)

# Main target
all: $(PDF) $(PDF2)

# Compile PDF
$(PDF): $(TEX) $(BIB)
	pdflatex $(DOC)
	biber $(DOC)
	pdflatex $(DOC)
	pdflatex $(DOC)

$(PDF2): $(TEX) $(BIB)
	pdflatex $(DOC2)
	biber $(DOC2)
	pdflatex $(DOC2)
	pdflatex $(DOC2)


# Clean auxiliary files
clean:
	rm -f $(DOC).aux $(DOC).bbl $(DOC).blg $(DOC).log $(DOC).out $(DOC).toc $(DOC).bcf $(DOC).run.xml
	rm -f $(DOC2).aux $(DOC2).bbl $(DOC2).blg $(DOC2).log $(DOC2).out $(DOC2).toc $(DOC2).bcf $(DOC2).run.xml

# Clean all files including PDF
distclean: clean
	rm -f $(PDF)
	rm -f $(PDF2)

# Phony targets
.PHONY: all clean distclean
