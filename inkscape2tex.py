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


def export_from_svg(svg, out_type):
    """Convert SVG file to PDF or EPS."""
    svg = svg.replace('\\', '/')
    if 'pdf' in out_type:
        out = svg.replace('.svg', '.pdf')
    elif 'eps' in out_type:
        out = svg.replace('.svg', '.eps')
    else:
        raise ValueError(out_type)
    if not os.access(svg, os.F_OK):
        raise FileNotFoundError(
            'No SVG file "{f}"'.format(f=svg))
    t_svg = os.stat(svg)[8]
    if os.access(out, os.F_OK):
        print('Output "{f}" file exists.'.format(f=out))
        t_out = os.stat(out)[8]
        print((
            'last modification dates:\n'
            '    SVG: {t_svg}\n'
            '    OUTPUT: {t_out}').format(
                t_svg=t_svg, t_out=t_out))
    else:
        t_out = -1
    if t_svg < t_out:
        print('No update needed, PDF or EPS newer than SVG.')
        return
    print('File not found or old. Converting from SVG...')
    # inkscape need be called with an absolute path on OS X
    # http://wiki.inkscape.org/wiki/index.php/MacOS_X
    symlink_relpath = 'bin/inkscape'
    home = os.path.expanduser('~')
    symlink_abspath = os.path.join(home, symlink_relpath)
    inkscape_abspath = os.path.realpath(symlink_abspath)
    args = ['{inkscape_abspath} -z -D --file={svg}'.format(
        inkscape_abspath=inkscape_abspath, svg=svg)]
    if 'pdf' in out_type:
        args.append('--export-pdf={pdf}'.format(pdf=out))
    if 'eps' in out_type:
        args.append('--export-eps={eps}'.format(eps=out))
    if 'latex' in out_type:
        args.append('--export-latex')
    args = shlex.split(' '.join(args))
    r = subprocess.call(args)
    if r != 0:
        raise Exception(
            'conversion from "{svg}" to "{out}" failed'.format(
                svg=svg, out=out))


def locate(pattern, root=os.curdir):
    """Locate all files matching supplied filename pattern under `root`."""
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


if __name__ == '__main__':
    main()
