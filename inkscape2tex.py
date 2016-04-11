#!/usr/bin/env python
"""Convert inkscape SVG files to TeX input.

Can be used to convert:

  1. DOT to SVG
  2. SVG to PDF or EPS with inkscape,
     optionally with LaTeX output

Requires `inkscape` in path.

Usage
=====

  1. `inkscape2tex.py filename -latex`

     checks if filename.svg is in a directory tree below ./img
     for all matches it tries to find filename.pdf in the same path
     if there is not a pdf it generates a pdf from the svg using inkscape.
     if there is a pdf, it checks the modification dates.
     if the pdf was last modified after the svg then it does nothing.
     if the pdf was last modified before the svg then
     it generates the pdf again
     and overwrites the old pdf.
     Using the -latex option exports a .pdf_tex latex file
     containing the svg's text and a
     .pdf which is imported in latex by the code within .pdf_tex.
     In your document you should input the .pdf_tex,
     which is done automatically
     by the command: \includesvg[]{} provided in latex.

  2. `inkscape.py filename -pdf`
     the same as above, except only a pdf is created from the svg.
     The latex command achieving this is \includesvgpdf[]{}

  3. `inkscape.py ./img/dir/myother/fig -pdf`
     no search. The specified file is used. Rest is the same.

  4. Other options
     `-latex-pdf, -latex-eps`

Notes
=====

  1. filename can contain python regular expressions.
     this comes handy for auto conversion of entire directory tries
     mostly when batch processing and not from within latex.

  2. Caution: the assumptions made are that
     i. you either provide a filename without extension which is an svg
        or if a path precedes it, it is a relative path starting with ./img
     ii. you want to extract to pdf (and not eps)


License
=======

Copyright (BSD-2) 2010-2016 by Ioannis Filippidis
"""
import sys
import shlex
import os
import time
import subprocess
import fnmatch
import getopt


def locate(pattern, root=os.curdir):
    """Locate all files matching supplied filename pattern in and
    below supplied root directory.

    locate() is used in case of exporting only to a .pdf (w/o latex export)
    Only in that case \includegraphics{} is still able to find the .pdf
    without a path.
    If latex export is used, then the produced .pdf_tex should be used
    with an \input{} command in latex and a relative path is mandatory for
    the \input{} command to work.
    """
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def export_from_svg(svg, out_type):
    """Export .SVG-> .PDF | .EPS."""
    svg = svg.replace('\\', '/')
    pdf = svg
    pdf = pdf.replace('.svg', '.pdf')
    eps = svg
    eps = eps.replace('.svg', '.eps')
    # check .svg exists
    svg_exists = os.access(svg, os.F_OK)
    if svg_exists:
        print('SVG file exists.')
        # get last modification time
        (mode, ino, dev, nlink, uid, gid,
         size, atime, svgmtime, ctime) = os.stat(svg)
    else:
        # it does not exist, nothing can be done
        raise sys.exit('SVG file not found! Cannot produce PDF or EPS.')
    flag = 0
    # check .pdf exists
    if (out_type == 'latex-pdf') or (out_type == 'pdf'):
        pdf_exists = os.access(pdf, os.F_OK)
        if pdf_exists:
            print('PDF file exists.')
            # get last modification time
            (mode, ino, dev, nlink, uid, gid,
             size, atime, pdfmtime, ctime) = os.stat(pdf)
            print('\n last mod dates?\n\tSVG: %s\n\tPDF: %s\n'
                  % (time.ctime(svgmtime), time.ctime(pdfmtime)))
            # compare last modification dates
            if (svgmtime < pdfmtime):
                flag = 1
        else:
            # it does not exist, last modification check omitted,
            # first export performed
            print('PDF file not found. New one to be created...')
    # check .eps exists
    if (out_type == 'latex-eps') or (out_type == 'eps'):
        eps_exists = os.access(eps, os.F_OK)
        if eps_exists:
            print('EPS file exists.')
            # get last modification time
            (mode, ino, dev, nlink, uid, gid,
             size, atime, epsmtime, ctime) = os.stat(eps)
            print('\n last mod dates?\n\tSVG: %s\n\tEPS: %s\n'
                  % (time.ctime(svgmtime), time.ctime(epsmtime)))
            # compare last modification dates
            if (svgmtime < epsmtime):
                flag = 1
        else:
            # it does not exist, last modification check omitted,
            # first export performed
            print('EPS file not found. New one to be created...')
    # export SVG-> PDF | EPS, if SVG newer
    if flag != 0:
        print('No update needed:\n\t PDF | EPS newer than SVG.')
        return
    print('Exporting: .DOT-> .SVG ...\n')
    assert out_type in ('latex-pdf', 'pdf', 'latex-eps', 'eps'), (
        'No output option passed.'
        'Available options: latex-pdf, latex-eps, pdf, eps')
    # inkscape need be called with an absolute path on OS X
    # http://wiki.inkscape.org/wiki/index.php/MacOS_X
    symlink_relpath = 'bin/inkscape'
    home = os.path.expanduser('~')
    symlink_abspath = os.path.join(home, symlink_relpath)
    inkscape_abspath = os.path.realpath(symlink_abspath)
    args = ['{inkscape_abspath} -z -D --file={svg}'.format(
        inkscape_abspath=inkscape_abspath, svg=svg)]
    if 'pdf' in out_type:
        args.append('--export-pdf={pdf}'.format(pdf=pdf))
    if 'eps' in out_type:
        args.append('--export-eps={eps}'.format(eps=eps))
    if 'latex' in out_type:
        args.append('--export-latex')
    args = shlex.split(' '.join(args))
    subprocess.call(args)
    print('Success: .SVG-> .PDF | .EPS.')


def export_from_dot(dot):
    """Export .DOT-> .SVG."""
    dot = dot.replace('\\', '/')
    svg = dot
    svg = svg.replace('dot', '.svg')
    # check .dot exists
    dot_exists = os.access(dot, os.F_OK)
    if dot_exists:
        print('DOT file exists.')
        # get last modification time
        (mode, ino, dev, nlink, uid, gid,
         size, atime, dotmtime, ctime) = os.stat(dot)
    else:
        # it does not exist, nothing can be done
        raise sys.exit('.DOT file not found! Cannot produce .SVG.')
    flag = 0
    # check .svg exists
    svg_exists = os.access(svg, os.F_OK)
    if svg_exists:
        print('SVG file exists.')
        # get last modification time
        (mode, ino, dev, nlink, uid, gid,
         size, atime, svgmtime, ctime) = os.stat(svg)
        print('\n last mod dates?\n\tDOT: %s\n\tSVG: %s\n'
              % (time.ctime(dotmtime), time.ctime(svgmtime)))
        # compare last modification dates
        if (dotmtime < svgmtime):
            flag = 1  # not modification needed
    else:
        # it does not exist, last modification check omitted,
        # first export performed
        print('.SVG file not found. New one to be created...')
    # export if needed
    if flag == 0:
        print('Exporting: .DOT-> .SVG ...\n')
        args = shlex.split('dot ' + dot + ' -Tsvg -o ' + svg)
        subprocess.call(args)
        print('Success: .DOT-> .SVG')
    else:
        print('No update needed:\n\t .SVG newer than .DOT.')


def help_text():
    raise Exception(
        'Input missing.\n'
        'Usage:\n'
        '\t inkscape2tex.py --input-file filename --method type\n'
        '\t inkscape2tex.py -i filename -m type\n'
        'where:\n\t filename = name (w/o extension) of SVG file under ./img'
        '\n\t type = file-type to export to, available:'
        '\n\t\t latex-pdf\n\t\t pdf'
        '\n\t\t latex-eps\n\t\t eps'
        '\n\t\t dot-svg-latex-pdf')


def main(argv):
    print(
        '\n------------------\n'
        'inkscape2tex'
        '\n------------------\n')
    try:
        opts, args = getopt.getopt(
            argv, 'hi:m:', ["help", "input-file=", "method="])
    except getopt.GetoptError:
        help_text()
        sys.exit(2)
    if len(opts) == 0:
        help_text()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help_text()
            sys.exit()
        elif opt in ('-i', '--input-file'):
            filename = arg
        elif opt in ('-m', '--method'):
            out_type = arg
    # dot file ?
    flag = 1
    if out_type == 'dot-svg-latex-pdf':
        # need to search for .DOT, or relative path given ?
        if './img/' in filename:
            dot_file = filename + '.dot'
            export_from_dot(dot_file)
            flag = 0
        else:
            file_generator = locate(dot_file, './img')
            for cur_dot_file in file_generator:
                print('Found .dot file named: ' +
                      cur_dot_file + ', to export to .SVG')
                export_from_dot(cur_dot_file)
                flag = 0
        # switch to exporting SVG-> LaTeX - PDF
        out_type = 'latex-pdf'
        if flag == 1:
            raise sys.exit('.DOT file not found! Cannot export to .SVG.')
            sys.exit(1)
        print('\n---------\n')
    # need to search fir .SVG, or relative path given ?
    flag = 1
    svg_file = filename + '.svg'
    if './img/' in filename:
        export_from_svg(svg_file, out_type)
        flag = 0
    else:
        file_generator = locate(svg_file, './img')
        for cur_svg_file in file_generator:
            print('Found .SVG file named: ' +
                  cur_svg_file + ' to export to ' + out_type)
            export_from_svg(cur_svg_file, out_type)
            flag = 0
    if flag == 1:
        raise sys.exit('.SVG file not found! Cannot export to .PDF.')
    print('\n------------------\n')


if __name__ == '__main__':
    main(sys.argv[1:])
