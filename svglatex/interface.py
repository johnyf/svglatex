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
import datetime
import fnmatch
import logging
import os
import shlex
import subprocess
import time

import humanize

from svglatex import converter


log = logging.getLogger(__name__)


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
        log.info('Will convert SVG file "{f}" to {t}'.format(
            f=svg, t=out_type))
        convert_if_svg_newer(svg, out_type)
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
        'latex-pdf', 'pdf']
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


def convert_if_svg_newer(svg, out_type):
    """Convert SVG file to PDF or EPS."""
    base, ext = os.path.splitext(svg)
    assert ext == '.svg', ext
    if 'pdf' in out_type:
        out = base + '.pdf'
    elif 'eps' in out_type:
        out = base + '.eps'
    else:
        raise ValueError(out_type)
    if not os.access(svg, os.F_OK):
        raise FileNotFoundError(
            'No SVG file "{f}"'.format(f=svg))
    fresh = is_newer(out, svg)
    if out_type == 'latex-pdf':
        pdf_tex = base + '.pdf_tex'
        fresh &= is_newer(pdf_tex, svg)
    if fresh:
        log.info('No update needed, target newer than SVG.')
        return
    log.info('File not found or old. Converting from SVG...')
    convert_svg(svg, out, out_type)


def is_newer(target, source):
    """Return `True` if `target` newer than `source` file."""
    assert os.path.isfile(source), source
    if not os.path.isfile(target):
        return False
    t_src = os.stat(source)[8]
    t_tgt = os.stat(target)[8]
    _print_dates(source, target, t_src, t_tgt)
    return t_src < t_tgt


def _print_dates(source, target, t_src, t_tgt):
    s = _format_time(t_src)
    t = _format_time(t_tgt)
    log.info((
        'last modification dates:\n'
        '    Source ({source}): {s}\n'
        '    Target ({target}): {t}').format(
            source=source, target=target,
            s=s, t=t))


def _format_time(t):
    """Return time readable by humans."""
    return humanize.naturaltime(
        datetime.datetime.fromtimestamp(t))


def convert_svg(svg, out, out_type):
    """Convert from SVG to output format."""
    assert out_type in ('latex-pdf', 'pdf'), out_type
    if out_type == 'latex-pdf':
        converter.convert(svg)
    elif out_type == 'pdf':
        inkscape = converter.which_inkscape()
        svg_path = os.path.realpath(svg)
        out_path = os.path.realpath(out)
        args = [
            inkscape,
            '--without-gui',
            '--export-area-drawing',
            '--export-ignore-filters',
            '--export-dpi={dpi}'.format(dpi=96),
            '--export-pdf={out}'.format(out=out_path),
            svg_path]
        r = subprocess.call(args)
        if r != 0:
            raise Exception('Conversion error')


def convert_svg_using_inkscape(svg, out, out_type):
    """Convert from SVG to output format."""
    # inkscape need be called with an absolute path on OS X
    # http://wiki.inkscape.org/wiki/index.php/MacOS_X
    symlink_relpath = 'bin/inkscape'
    home = os.path.expanduser('~')
    symlink_abspath = os.path.join(home, symlink_relpath)
    inkscape_abspath = os.path.realpath(symlink_abspath)
    svg_abspath = os.path.realpath(svg)
    args = ['{inkscape_abspath} -z -D --file={svg}'.format(
        inkscape_abspath=inkscape_abspath, svg=svg_abspath)]
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
