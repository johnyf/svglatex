#!/usr/bin/env python
"""Convert inkscape SVG files to TeX input.

- SVG to PDF or EPS with inkscape, optionally with LaTeX output.
- DOT to SVG

Skips conversion if PDF file found newer than SVG source.
Requires `inkscape` in path.
"""
# Copyright 2010-2017 by Ioannis Filippidis
# All rights reserved. Licensed under BSD-2.
#
import argparse
import shlex
import os
import time
import subprocess
import fnmatch


def locate(pattern, root=os.curdir):
    """Locate all files matching supplied filename pattern under `root`."""
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
        raise Exception('SVG file not found! Cannot produce PDF or EPS.')
    flag = 0
    # check .pdf exists
    if out_type == 'latex-pdf' or out_type == 'pdf':
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
    if out_type == 'latex-eps' or out_type == 'eps':
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
        print('No update needed, PDF or EPS newer than SVG.')
        return
    print('Exporting from SVG...\n')
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
    r = subprocess.call(args)
    assert r == 0, 'inkscape failed'


def main():
    """Start from here."""
    args = parse_args()
    f = '{name}.svg'.format(name=args.input_file)
    out_type = args.method
    if './img/' in f:
        files = [f]
    else:
        files = locate(f, './img')
    svg = None
    for svg in files:
        print('Will convert SVG file "{f}" to {t}'.format(
            f=svg, t=out_type))
        export_from_svg(svg, out_type)
    if svg is None:
        raise Exception(
            'SVG file "{f}" not found! '
            'Cannot export to PDF.'.format(f=f))


def parse_args():
    """Parse command-line arguments using."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--input-file', type=str,
        help=(
            'Name (w/o extension) of SVG file. '
            'Either file name to search for under `./img`, '
            'or path that starts with `./img`.'))
    choices = [
        'latex-pdf', 'pdf',
        'latex-eps', 'eps']
    parser.add_argument(
        '-m', '--method', type=str, choices=choices,
        help=(
            'Export to this file type. '
            'The prefix "latex" produces also a file `*.pdf_tex` '
            'that contains the text from the SVG. '
            'The command `\includesvgpdf` passes `pdf`, '
            'and `\includesvg` passes `latex-pdf`.'))
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()
