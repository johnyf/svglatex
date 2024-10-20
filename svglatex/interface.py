#!/usr/bin/env python
"""Convert inkscape SVG files to TeX input.

- SVG to PDF or EPS with inkscape, optionally with LaTeX output.
- DOT to SVG

Skips conversion if PDF file found newer than SVG source.
Requires `inkscape` in the runtime environment's PATH.
"""
# Copyright 2010-2017 by Ioannis Filippidis
# All rights reserved. Licensed under 2-clause BSD.
#
import argparse
import datetime
import fnmatch
import logging
import os
import shlex
import subprocess
import time

import svglatex.converter as _converter


log = logging.getLogger(__name__)


def main():
    """Start from here."""
    args = parse_args()
    f = f'{args.input_file}.svg'
    out_type = args.method
    if './img/' in f:
        files = [f]
    else:
        files = locate(f, './img')
    svg = None
    for svg in files:
        log.info(
            'Will convert SVG file '
            f'"{svg}" to {out_type}')
        convert_if_svg_newer(svg, out_type)
    if svg is None:
        raise Exception(
            f'SVG file "{f}" not found! '
            'Cannot export to PDF.')


def parse_args():
    """Parse command-line arguments using."""
    parser = argparse.ArgumentParser(
        description='Requires `inkscape >= 1.0.0`')
    parser.add_argument(
        '-i',
        '--input-file',
        type=str,
        help=(
            'Name (w/o extension) of SVG file. '
            'Either file name to search for under `./img`, '
            'or path that starts with `./img`.'))
    choices = [
        'latex-pdf', 'pdf']
    parser.add_argument(
        '-m',
        '--method',
        type=str,
        choices=choices,
        help=(
            'Export to this file type. '
            'The prefix "latex" produces also '
            'a file `*.pdf_tex` '
            'that contains the text from the SVG. '
            r'The command `\includesvgpdf` passes `pdf`, '
            r'and `\includesvg` passes `latex-pdf`.'))
    args = parser.parse_args()
    return args


def convert_if_svg_newer(svg, out_type):
    """Convert SVG file to PDF or EPS."""
    base, ext = os.path.splitext(svg)
    if ext != '.svg':
        raise ValueError(ext)
    if 'pdf' in out_type:
        out = f'{base}.pdf'
    elif 'eps' in out_type:
        out = f'{base}.eps'
    else:
        raise ValueError(out_type)
    if not os.access(svg, os.F_OK):
        raise FileNotFoundError(
            f'No SVG file "{svg}"')
    fresh = is_newer(out, svg)
    if out_type == 'latex-pdf':
        pdf_tex = f'{base}.pdf_tex'
        fresh &= is_newer(pdf_tex, svg)
    if fresh:
        log.info(
            'No update needed, '
            'target newer than SVG.')
        return
    log.info(
        'File not found or old. '
        'Converting from SVG...')
    convert_svg(svg, out, out_type)


def is_newer(target, source):
    """Return `True` if `target` newer than `source` file."""
    if not os.path.isfile(source):
        raise ValueError(source)
    if not os.path.isfile(target):
        return False
    t_src = os.stat(source)[8]
    t_tgt = os.stat(target)[8]
    _print_dates(source, target, t_src, t_tgt)
    return t_src < t_tgt


def _print_dates(
        source, target, t_src, t_tgt):
    s = _format_time(t_src)
    t = _format_time(t_tgt)
    log.info(
        'last modification dates:\n'
        f'    Source ({source}): {s}\n'
        f'    Target ({target}): {t}')


def _format_time(t):
    """Return time readable by humans."""
    return datetime.datetime.fromtimestamp(
        t).isoformat()


def convert_svg(svg, out, out_type):
    """Convert from SVG to output format."""
    if out_type not in ('latex-pdf', 'pdf'):
        raise ValueError(out_type)
    if out_type == 'latex-pdf':
        _converter.convert(svg)
    elif out_type == 'pdf':
        inkscape = _converter.which_inkscape()
        svg_path = os.path.realpath(svg)
        out_path = os.path.realpath(out)
        dpi = 96
        args = f'''
            {inkscape}
                --export-area-drawing
                --export-ignore-filters
                --export-dpi={dpi}
                --export-filename={out_path}
                {svg_path}
            '''
        args = shlex.split(args)
        r = subprocess.call(args)
        if r != 0:
            raise Exception(
                'Conversion error')


def convert_svg_using_inkscape(
        svg, out, out_type):
    """Convert from SVG to output format."""
    # inkscape need be called with an absolute path on OS X
    # <https://wiki.inkscape.org/wiki/index.php/MacOS_X>
    symlink_relpath = 'bin/inkscape'
    home = os.path.expanduser('~')
    symlink_abspath = os.path.join(
        home, symlink_relpath)
    inkscape_abspath = os.path.realpath(
        symlink_abspath)
    svg_abspath = os.path.realpath(svg)
    args = list()
    if 'pdf' in out_type:
        args.append(f'--export-filename={out}')
    if 'eps' in out_type:
        args.append(f'--export-filename={out}')
    if 'latex' in out_type:
        args.append('--export-latex')
    args = ' '.join(args)
    args = f'''
        {inkscape_abspath}
            --export-area-drawing
            {args}
            {svg_abspath}
        '''
    args = shlex.split(args)
    r = subprocess.call(args)
    if r != 0:
        raise Exception(
            'conversion from '
            f'"{svg}" to "{out}" failed')


def locate(
        pattern,
        root=os.curdir):
    """Locate all files matching supplied filename pattern under `root`."""
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


if __name__ == '__main__':
    main()
