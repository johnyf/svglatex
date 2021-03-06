#!/usr/bin/env python
"""Export SVG to PDF + LaTeX."""
#
# Based on:
# https://github.com/johnbartholomew/svg2latex/blob/
# b77623b617b9b92c131a8eafe09ec1b1abed93f2/svg2latex.py
#
# BSD 3-Clause License
#
# Copyright 2017-2020 by California Institute of Technology
# Copyright (c) 2017, John Bartholomew
# Copyright 2017-2020 by Ioannis Filippidis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#    Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#    Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import argparse
import collections
import math
import os
import pprint
import re
import subprocess
import sys
import shutil
import tempfile

# import cairosvg
import lxml.etree as etree


_FONT_MAP = {
    'CMU Serif': 'rm',
    'CMU Sans Serif': 'sf',
    'CMU Typewriter Text': 'tt',
    'Calibri': 'rm'}
_FONT_SIZE_MAP = {
    '9px': r'\scriptsize',
    '10px': r'\footnotesize',
    '11px': r'\small',
    '12px': r'\normalsize',
    '13px': r'\large'}
# 72 big-points (PostScript points) (72 bp) per inch
PT_PER_INCH = 72.0  # pt / in
# 96 SVG "User Units" (96 px) per inch
# https://wiki.inkscape.org/wiki/index.php/Units_In_Inkscape
DPI = 96.0  # px / in
SVG_UNITS_TO_BIG_POINTS = PT_PER_INCH / DPI  # pt / px
# initial fragment of `*.pdf_tex` file
_PICTURE_PREAMBLE = r'''% Picture generated by svglatex
\makeatletter
\providecommand\color[2][]{%
  \errmessage{(svglatex) Color is used for the text in Inkscape,
    but the package 'color.sty' is not loaded}%
  \renewcommand\color[2][]{}}%
\providecommand\transparent[1]{%
  \errmessage{
    (svglatex) Transparency is used for the text in Inkscape,
    but the package 'transparent.sty' is not loaded}%
  \renewcommand\transparent[1]{}}%
\setlength{\unitlength}{\svgwidth}%
\global\let\svgwidth\undefined%
\makeatother
'''
# alignments
_ALIGN_LEFT = 0
_ALIGN_CENTER = 1
_ALIGN_RIGHT = 2
# weights
_WEIGHT_NORMAL = 500
_WEIGHT_BOLD = 700
# styles
_STYLE_NORMAL = 0
_STYLE_ITALIC = 1
_STYLE_OBLIQUE = 2
# namespaces
_INKSVG_NAMESPACES = {
    'dc': r'http://purl.org/dc/elements/1.1/',
    'cc': r'http://creativecommons.org/ns#',
    'rdf': r'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'svg': r'http://www.w3.org/2000/svg',
    'xlink': r'http://www.w3.org/1999/xlink',
    'sodipodi': (r'http://sodipodi.sourceforge.net/'
                 r'DTD/sodipodi-0.dtd'),
    'inkscape': r'http://www.inkscape.org/namespaces/inkscape'}
# transform re
_RX_TRANSFORM = re.compile('^\s*(\w+)\(([0-9,\s\.-]*)\)\s*')
# bounding box
_BBox = collections.namedtuple('BBox', ['x', 'y', 'width', 'height'])


def _parse_args():
    """Return arguments parsed from the command line."""
    p = argparse.ArgumentParser()
    p.add_argument('fname', type=str, help='svg file name')
    args = p.parse_args()
    return args


def convert(svg_fname):
    """Convert SVG `svg_fname` to a PDF and a LaTeX file.

    The PDF file includes graphics from the SVG `svg_fname`.
    The LaTeX file includes text from the SVG `svg_fname`.
    The LaTeX file has extension `.pdf_tex`.

    @type svg_fname: `str`
    """
    fname, ext = os.path.splitext(svg_fname)
    assert ext == '.svg', ext
    tex_path = '{fname}.pdf_tex'.format(fname=fname)
    pdf_path = '{fname}.pdf'.format(fname=fname)
    # convert
    xml, text_ids, ignore_ids, labels = _split_text_graphics(svg_fname)
    pdf_bboxes = _generate_pdf_from_svg_using_inkscape(xml, pdf_path)
    pdf_bbox = _pdf_bounding_box(pdf_bboxes)
    svg_bboxes = _svg_bounding_boxes(svg_fname)
    svg_bbox = _svg_bounding_box(
        svg_bboxes, text_ids, ignore_ids, pdf_bbox)
    tex = _TeXPicture(svg_bbox, pdf_bbox, pdf_path, labels)
    pdf_tex_contents = tex.dumps()
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(pdf_tex_contents)


def _split_text_graphics(svg_fname):
    """Return XML for graphics SVG and text labels.

    @type svg_fname: `str`
    """
    doc = etree.parse(svg_fname)
    _print_svg_units(doc)
    ignore_ids = set()
    for defs in doc.xpath(
            '//svg:defs',
            namespaces=_INKSVG_NAMESPACES):
        for u in defs.xpath(
                '//svg:path',
                namespaces=_INKSVG_NAMESPACES):
            name = u.attrib['id']
            ignore_ids.add(name)
    # extract text and remove it from svg
    text_ids = set()
    labels = list()
    scaling = _scaling_assumed(doc)
    text = doc.xpath(
        '//svg:text',
        namespaces=_INKSVG_NAMESPACES)
    for u in text:
        ids = _interpret_svg_text(u, labels, scaling)
        text_ids.update(ids)
        parent = u.getparent()
        parent.remove(u)
    return doc, text_ids, ignore_ids, labels


def _print_svg_units(doc):
    """Print `doc` width and height in units.

    @type doc: `lxml.etree._ElementTree`
    """
    w = _mm_to_svg_units(doc.getroot().attrib['width'])
    h = _mm_to_svg_units(doc.getroot().attrib['height'])
    print('width = {w:0.2f} px, height = {h:0.2f} px'.format(
        w=w, h=h))
    w_inch = w / DPI
    h_inch = h / DPI
    print('width = {w:0.2f} in, height = {h:0.2f} in'.format(
        w=w_inch, h=h_inch))
    w_bp = w * SVG_UNITS_TO_BIG_POINTS
    h_bp = h * SVG_UNITS_TO_BIG_POINTS
    print('width = {w:0.2f} bp, height = {h:0.2f} bp'.format(
        w=w_bp, h=h_bp))


def _mm_to_svg_units(x):
    """Return SVG units from `x`.

    @param x: `str` that may contain `"mm"`
    """
    if 'in' in x:
        s = x[:-2]
        return float(s) * DPI
    elif 'mm' in x:
        s = x[:-2]
        return float(s) / 25.4 * DPI
    elif 'cm' in x:
        s = x[:-2]
        return float(s) / 2.54 * DPI
    elif 'pt' in x:
        s = x[:-2]
        return float(s) / SVG_UNITS_TO_BIG_POINTS
    elif 'pc' in x:
        raise NotImplementedError('pc units')
    elif 'px' in x:
        return float(x[:-2])
    else:
        return float(x)


def _scaling_assumed(doc):
    """Return scaling factor.

    Assume that 1 unit is equal to 1 viewBox unit.
    """
    root = doc.getroot()
    viewbox = root.attrib.get('viewBox')
    width = root.attrib['width']
    if viewbox is not None:
        if ',' in viewbox:
            viewbox = viewbox.split(',')
        else:
            viewbox = viewbox.split(' ')
    print('viewbox:' + str(viewbox))
    if viewbox is None:
        scaling = 1.0
        return scaling
    # assume same scaling in x and y axes
    viewbox_width = float(viewbox[2])
    if 'in' in width:
        print('in found')
        in_width = float(width[:-2])
        # px / viewbox units
        scaling = (
            DPI  # px / in
            * in_width / viewbox_width)  # * in / viewbox units
    elif 'mm' in width:
        print('mm found')
        mm_width = float(width[:-2])
        # px / viewbox units
        scaling = (
            DPI / 25.4  # (px / in) * (in / mm) = (px / mm)
            * mm_width / viewbox_width)  # * mm / viewbox units
    elif 'cm' in width:
        print('cm found')
        cm_width = float(width[:-2])
        # px / viewbox units
        scaling = (
            DPI / 2.54  # (px / in) * (in / cm) = (px / cm)
            * cm_width / viewbox_width)  # * cm / viewbox units
    elif 'pt' in width:
        print('pt found')
        pt_width = float(width[:-2])
        # px / viewbox units
        scaling = (
            1.0 / SVG_UNITS_TO_BIG_POINTS  # px / pt
            * pt_width / viewbox_width)  # * pt / viewbox units
    elif 'pc' in width:
        raise NotImplementedError('pc units')
    elif 'px' in width:
        print('px found')
        px_width = float(width[:-2])
        scaling = px_width / viewbox_width
    else:  # no unit identifier
        scaling = float(width) / viewbox_width
    return scaling


def _interpret_svg_text(text_element, labels, scaling):
    """Return text IDs and augment `labels`.

    @type text_element: `lxml.etree._Element`
    @type labels: `list`
    @return: text IDs
    @rtype: `set`
    """
    assert text_element.tag.endswith('text'), text_element.tag
    if 'style' in text_element.attrib:
        style = _split_svg_style(
            text_element.attrib['style'])
    else:
        style = dict()
    text_ids = set()
    if 'id' in text_element.attrib:
        name = text_element.attrib['id']
        text_ids.add(name)
    all_text = list()
    xys = list()
    # has `tspan` ?
    tspans = text_element.xpath(
        'svg:tspan',
        namespaces=_INKSVG_NAMESPACES)
    if not tspans:
        tspans = [text_element]
    for tspan in tspans:
        all_text.append(tspan.text)
        tex_label = _make_tex_label(tspan)
        _scale_texlabel(tex_label, scaling)
        xys.append(tex_label.pos)
        # name = tspan.attrib['id']
        # text_ids.add(name)
        # style
        span_style = _update_tspan_style(style, tspan)
        _set_fill(tex_label, span_style)
        _set_font_weight(tex_label, span_style)
        _set_font_style(tex_label, span_style)
        _set_text_anchor(tex_label, span_style)
        _set_font_family(tex_label, span_style)
        _set_font_size(tex_label, span_style)
    all_text = [s for s in all_text if s is not None]
    tex_label.text = ' '.join(all_text)
    tex_label.pos = xys[0]
    labels.append(tex_label)
    return text_ids


def _make_tex_label(tspan):
    """Return a `_TeXLabel` from `tspan`."""
    # position and angle
    pos, angle = _get_tspan_pos_angle(tspan)
    tex_label = _TeXLabel(pos, '')
    tex_label.angle = angle
    return tex_label


def _get_tspan_pos_angle(tspan):
    """Compute position and orientation of `tspan`."""
    xform = _compute_svg_transform(tspan)
    pos = (float(tspan.attrib['x']), float(tspan.attrib['y']))
    pos = xform.apply(pos)
    angle = - round(xform.get_rotation(), 3)
    return pos, angle


def _update_tspan_style(style, tspan):
    """Return style of `style` updated using `tspan`."""
    span_style = style.copy()
    if 'style' in tspan.attrib:
        st = _split_svg_style(tspan.attrib['style'])
        span_style.update(st)
    return span_style


def _set_fill(tex_label, span_style):
    """Assign `tex_label.color` using `span_style`."""
    if 'fill' not in span_style:
        return
    tex_label.color = _parse_svg_color(span_style['fill'])


def _set_font_weight(tex_label, span_style):
    """Assign `tex_label.fontweight` using `span_style`."""
    if 'font-weight' not in span_style:
        return
    weight = span_style['font-weight']
    if weight == 'bold':
        tex_label.fontweight = _WEIGHT_BOLD
    elif weight == 'normal':
        tex_label.fontweight = _WEIGHT_NORMAL
    else:
        tex_label.fontweight = int(weight)


def _set_font_style(tex_label, span_style):
    """Assign `tex_label.fontstyle` using `span_style`."""
    if 'font-style' not in span_style:
        return
    fstyle = span_style['font-style']
    if fstyle == 'normal':
        tex_label.fontstyle = _STYLE_NORMAL
    elif fstyle == 'italic':
        tex_label.fontstyle = _STYLE_ITALIC
    elif fstyle == 'oblique':
        tex_label.fontstyle = _STYLE_OBLIQUE


def _set_text_anchor(tex_label, span_style):
    """Assign `tex_label.align` using `span_style`."""
    if 'text-anchor' not in span_style:
        return
    anchor = span_style['text-anchor']
    if anchor == 'start':
        tex_label.align = _ALIGN_LEFT
    elif anchor == 'end':
        tex_label.align = _ALIGN_RIGHT
    elif anchor == 'middle':
        tex_label.align = _ALIGN_CENTER


def _set_font_family(tex_label, span_style):
    """Assign `tex_label.fontfamily` using `span_style`."""
    if 'font-family' not in span_style:
        return
    ff = span_style['font-family']
    if ff in _FONT_MAP:
        tex_label.fontfamily = _FONT_MAP[ff]
    else:
        print('Could not match font-family', ff)


def _set_font_size(tex_label, span_style):
    """Assign `tex_label.fontsize` using `span_style`."""
    if 'font-size' not in span_style:
        return
    fs = span_style['font-size']
    if fs in _FONT_SIZE_MAP:
        tex_label.fontsize = _FONT_SIZE_MAP[fs]
    else:
        print('Could not match font-size', fs)


def _scale_texlabel(tex_label, scaling):
    x, y = tex_label.pos
    x = x * scaling
    y = y * scaling
    tex_label.pos = (x, y)


def _split_svg_style(style):
    """Return `dict` from parsing `style`."""
    parts = [x.strip() for x in style.split(';')]
    parts = [x.partition(':') for x in parts if x != '']
    st = dict()
    for p in parts:
        st[p[0].strip()] = p[2].strip()
    return st


def _compute_svg_transform(el):
    """Return transformation of element `el`.

    @type el: `lxml.etree._Element`
    @rtype: `_AffineTransform`
    """
    xform = _AffineTransform()
    while el is not None:
        if 'transform' in el.attrib:
            t = _parse_svg_transform(el.attrib['transform'])
            xform = t * xform
        el = el.getparent()
    return xform


def _parse_svg_transform(attribute):
    t = _AffineTransform()
    while attribute:
        tx, end = _parse_single_svg_transform(attribute)
        attribute = attribute[end:]
        t = tx * t
    return t


def _parse_single_svg_transform(attribute):
    """Return transformation from `attribute`.

    @type attribute: `str`
    @rtype: `_AffineTransform`
    """
    m = _RX_TRANSFORM.match(attribute)
    assert m is not None, 'bad transform (' + attribute + ')'
    func = m.group(1)
    if ',' in m.group(2):
        args = [float(x.strip()) for x in m.group(2).split(',')]
    else:
        args = [float(x.strip()) for x in m.group(2).split(' ')]
    if func == 'matrix':
        tform = _make_matrix_transform(args)
    elif func == 'translate':
        tform = _make_translation_transform(args)
    elif func == 'scale':
        tform = _make_scaling_transform(args)
    elif func == 'rotate':
        tform = _make_rotation_transform(args)
    else:
        raise Exception(
            'unsupported transform attribute ({a})'.format(
                a=attribute))
    return tform, m.end()


def _make_matrix_transform(args):
    """Return matrix transformation from `args`.

    @type args: `list` of `float`
    @rtype: `_AffineTransform`
    """
    assert len(args) == 6, args
    xform = _AffineTransform()
    xform.matrix(*args)
    return xform


def _make_translation_transform(args):
    """Return translation from `args`.

    @type args: `list` of `float`
    @rtype: `_AffineTransform`
    """
    assert len(args) in (1, 2), args
    tx = args[0]
    ty = args[1] if len(args) > 1 else 0.0
    xform = _AffineTransform()
    xform.translate(tx, ty)
    return xform


def _make_scaling_transform(args):
    """Return scaling from `args`.

    @type args: `list` of `float`
    @rtype: `_AffineTransform`
    """
    assert len(args) in (1, 2), args
    sx = args[0]
    sy = args[1] if len(args) > 1 else sx
    xform = _AffineTransform()
    xform.scale(sx, sy)
    return xform


def _make_rotation_transform(args):
    """Return rotation from `args`.

    @type args: `list` of `float`
    @rtype: `_AffineTransform`
    """
    assert len(args) in (1, 3), args
    if len(args) == 1:
        args = args + [0, 0]  # cx, cy
    xform = _AffineTransform()
    xform.rotate_degrees(*args)
    print('WARNING: text rotation (not tested)')
    return xform


def _parse_svg_color(color):
    """Return RGB integers from Inkscape color.

    @type color: `str`
    @rtype: `tuple` (triplet)
    """
    if color[0] != '#':
        raise Exception('only hash-code colors are supported!')
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    return (red, green, blue)


def _generate_pdf_from_svg_using_inkscape(svg_data, pdfpath):
    """Export drawing area of SVG `svg_data` to PDF.

    This functions uses `inkscape` for both the
    conversion to PDF, and for computing bounding boxes.

    @type svg_data: `lxml.etree._ElementTree`
    @type pdfpath: `str`
    @return: bounding boxes
    @rtype: `dict`
    """
    inkscape = which_inkscape()
    path = os.path.realpath(pdfpath)
    args = [inkscape,
            '--without-gui',
            '--export-area-drawing',
            '--export-ignore-filters',
            '--export-dpi={dpi}'.format(dpi=DPI),
            '--export-pdf={path}'.format(path=path)]
    with tempfile.NamedTemporaryFile(
            suffix='.svg', delete=True) as tmpsvg:
        svg_data.write(tmpsvg, encoding='utf-8',
                      xml_declaration=True)
        tmpsvg.flush()
        bboxes = _svg_bounding_boxes(tmpsvg.name)
        # shutil.copyfile(tmpsvg.name, 'foo_bare.svg')
        tmp_path = os.path.realpath(tmpsvg.name)
        args.append('--file={s}'.format(s=tmp_path))
        with subprocess.Popen(args) as proc:
            proc.wait()
            if proc.returncode != 0:
                raise Exception((
                    '`{inkscape}` conversion of SVG '
                    'to PDF failed with return code '
                    '{rcode}'
                    ).format(
                        inkscape=inkscape,
                        rcode=proc.returncode))
    return bboxes


def _generate_pdf_from_svg_using_cairo(svg_data, pdfpath):
    """Export SVG `svg_data` to PDF.

    This function uses `cairosvg` for the conversion to PDF,
    and `inkscape` to compute the bounding boxes.

    @type svg_data: `lxml.etree._ElementTree`
    @type pdfpath: `str`
    @return: bounding boxes
    @rtype: `dict`
    """
    with tempfile.NamedTemporaryFile(
            suffix='.svg', delete=True) as tmpsvg:
        svg_data.write(tmpsvg, encoding='utf-8',
                      xml_declaration=True)
        tmpsvg.flush()
        bboxes = _svg_bounding_boxes(tmpsvg.name)
        # shutil.copyfile(tmpsvg.name, 'foo_bare.svg')
        cairosvg.svg2pdf(
            file_obj=tmpsvg,
            write_to=pdfpath)
    return bboxes


def _pdf_bounding_box(pdf_bboxes):
    """Return PDF bounding box.

    @type pdf_bboxes: `dict`
    @rtype: `_BBox`
    """
    # Drawing area coordinates within SVG
    for k, d in pdf_bboxes.items():
        if k.startswith('svg'):
            break
    xmin, xmax, ymin, ymax = _corners(d)
    pdf_bbox = _BBox(
        x=xmin,
        y=ymin,
        width=xmax - xmin,
        height=ymax - ymin)
    return pdf_bbox


def _svg_bounding_box(
        svg_bboxes, text_ids, ignore_ids, pdf_bbox):
    """Return initial SVG bounding box.

    @type svg_bboxes: `dict`
    @type text_ids: `set`
    @type ignore_ids: `set`
    @type pdf_bbox: `_BBox`
    @rtype: `_BBox`
    """
    xs = set()
    ys = set()
    # pprint.pprint(svg_bboxes)
    for name in text_ids:
        d = svg_bboxes.get(name)
        if name in ignore_ids or d is None:
            continue
        x, _, y, _ = _corners(d)
        xs.add(x)
        ys.add(y)
    # overall bounding box
    xmin = pdf_bbox.x
    ymin = pdf_bbox.y
    xmax = xmin + pdf_bbox.width
    ymax = ymin + pdf_bbox.height
    xs.add(xmin)
    xs.add(xmax)
    ys.add(ymin)
    ys.add(ymax)
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)
    svg_bbox = _BBox(
        x=x_min,
        y=y_min,
        width=x_max - x_min,
        height=y_max - y_min)
    return svg_bbox


def _svg_bounding_boxes(svgfile):
    """Parses the output from inkscape `--query-all`.

    This function calls `inkscape`.

    @type svgfile: `str`
    @rtype: `dict`
    """
    inkscape = which_inkscape()
    path = os.path.realpath(svgfile)
    args = [
        inkscape,
        '--without-gui',
        '--query-all',
        '--file={s}'.format(s=path)]
    with subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            universal_newlines=True) as proc:
        lines = proc.stdout.readlines()
        proc.wait()
        if proc.returncode != 0:
            raise Exception((
                '`{inkscape}` exited with '
                'return code {rcode}'
                ).format(
                    inkscape=inkscape,
                    rcode=proc.returncode))
    bboxes = dict()
    for line in lines:
        name, x, y, w, h = _parse_bbox_string(line)
        bboxes[name] = dict(x=x, y=y, w=w, h=h)
    return bboxes


def which_inkscape():
    """Return absolute path to `inkscape`.

    Assume that `inkscape` is in the `$PATH`.
    Useful on OS X, where calling `inkscape` from the command line does not
    work properly, unless an absolute path is used.

    In the future, using another approach for conversion (e.g., a future
    version of `cairosvg`) will make this function obsolete.
    """
    s = shutil.which('inkscape')
    inkscape_abspath = os.path.realpath(s)
    return inkscape_abspath


def _parse_bbox_string(line):
    """Return `x, y, w, h` from bounding box string.

    @type line: `str`
    @return: quintuple
    @rtype: `tuple`
    """
    name, *rest = line.split(',')
    x, y, w, h = [float(x) for x in rest]
    return name, x, y, w, h


def _corners(d):
    """Return corner coordinates.

    @param d: `dict` with keys
        `'x', 'y', 'w', 'h'`
    @return: quadruple
    @rtype: `tuple`
    """
    x = d['x']
    y = d['y']
    w = d['w']
    h = d['h']
    xmax = x + w
    ymax = y + h
    return x, xmax, y, ymax


class _AffineTransform(object):
    """Affine transformation."""

    def __init__(self, t=None, m=None):
        self.t = (0.0, 0.0) if t is None else t
        self.m = (1.0, 0.0, 0.0, 1.0) if m is None else m

    def clone(self):
        nt = _AffineTransform()
        nt.t = self.t
        nt.m = self.m
        return nt

    def translate(self, tx, ty):
        """Create translation."""
        self.matrix(1.0, 0.0, 0.0, 1.0, tx, ty)

    def rotate_degrees(self, angle, cx=0.0, cy=0.0):
        """Create rotation."""
        angle = math.radians(angle)
        sin, cos = math.sin(angle), math.cos(angle)
        if cx != 0.0 or cy != 0.0:
            self.translate(cx, cy)
            self.matrix(cos, sin, -sin, cos, 0.0, 0.0)
            self.translate(-cx, -cy)
        else:
            self.matrix(cos, sin, -sin, cos, 0.0, 0.0)

    def scale(self, sx, sy=None):
        """Create scaling."""
        if sy is None:
            sy = sx
        self.matrix(sx, 0.0, 0.0, sy)

    def matrix(self, a, b, c, d, e=0.0, f=0.0):
        """Create matrix transformation."""
        sa, sb, sc, sd = self.m
        se, sf = self.t

        ma = sa * a + sc * b
        mb = sb * a + sd * b
        mc = sa * c + sc * d
        md = sb * c + sd * d
        me = sa * e + sc * f + se
        mf = sb * e + sd * f + sf
        self.m = (ma, mb, mc, md)
        self.t = (me, mf)

    def apply(self, x, y=None):
        """Transform position `x, y`."""
        if y is None:
            x, y = x
        xx = self.t[0] + self.m[0] * x + self.m[2] * y
        yy = self.t[1] + self.m[1] * x + self.m[3] * y
        return (xx, yy)

    def __str__(self):
        """Return `str` representation."""
        return '[{},{},{}  ;  {},{},{}]'.format(
            self.m[0], self.m[2], self.t[0],
            self.m[1], self.m[3], self.t[1])

    def __mul__(a, b):
        """Compose transformations."""
        a11, a21, a12, a22 = a.m
        a13, a23 = a.t
        b11, b21, b12, b22 = b.m
        b13, b23 = b.t

        # cIJ = aI1*b1J + aI2*b2J + aI3*b3J
        c11 = a11 * b11 + a12 * b21
        c12 = a11 * b12 + a12 * b22
        c13 = a11 * b13 + a12 * b23 + a13
        c21 = a21 * b11 + a22 * b21
        c22 = a21 * b12 + a22 * b22
        c23 = a21 * b13 + a22 * b23 + a23
        return _AffineTransform((c13, c23), (c11, c21, c12, c22))

    def get_rotation(self):
        """Return angle in degrees."""
        m11, m21, m12, m22 = self.m
        len1 = math.sqrt(m11 * m11 + m21 * m21)
        len2 = math.sqrt(m12 * m12 + m22 * m22)
        # TODO check that len1 and len2 are close to 1
        # TODO check that the matrix is orthogonal
        # TODO do a real matrix decomposition here!
        return math.degrees(math.atan2(m21, m11))


class _TeXLabel(object):
    """LaTeX label."""

    def __init__(self, pos, text):
        self.text = text
        self.color = (0, 0, 0)
        self.pos = pos
        self.angle = 0.0
        self.align = _ALIGN_LEFT
        self.fontsize = None
        self.fontfamily = 'rm'
        self.fontweight = _WEIGHT_NORMAL
        self.fontstyle = _STYLE_NORMAL
        self.scale = 1.0

    def texcode(self):
        """Return LaTeX code."""
        color = self._color_tex()
        font = '\\' + self.fontfamily + 'family'
        font += self._font_weight_tex()
        font += self._font_style_tex()
        font += self._font_size_tex()
        align = self._alignment_tex()
        text = self._text()
        texcode = (
            font + color + align +
            r'{\smash{' + text + '}}')
        if self.angle != 0.0:
            texcode = (
                '\\rotatebox{{{angle}}}{{{texcode}}}'
                ).format(
                    angle=self.angle,
                    texcode=texcode)
        return texcode

    def _color_tex(self):
        """Return LaTeX code for text color."""
        r, g, b = self.color
        if r != 0 or g != 0 or b != 0:
            color = '\\color[RGB]{{{r},{g},{b}}}'.format(
                r=r, g=g, b=b)
        else:
            color = ''
        return color

    def _font_weight_tex(self):
        """Return LaTeX code for text weight."""
        if self.fontweight >= _WEIGHT_BOLD:
            return r'\bfseries'
        else:
            return ''

    def _font_style_tex(self):
        """Return LaTeX code for font style."""
        if self.fontstyle == _STYLE_ITALIC:
            return r'\itshape'
        elif self.fontstyle == _STYLE_OBLIQUE:
            return r'\slshape'
        else:
            return ''

    def _font_size_tex(self):
        """Return LaTeX code for font size."""
        if self.fontsize is not None:
            return self.fontsize
        else:
            return ''

    def _alignment_tex(self):
        """Return LaTeX code for text alignment."""
        if self.align == _ALIGN_LEFT:
            return r'\makebox(0,0)[bl]'
        elif self.align == _ALIGN_CENTER:
            return r'\makebox(0,0)[b]'
        elif self.align == _ALIGN_RIGHT:
            return r'\makebox(0,0)[br]'
        else:
            raise ValueError(align)

    def _text(self):
        """Return text."""
        if self.text is None:
            return ''
        else:
            return self.text


class _TeXPicture(object):
    """LaTeX `\picture` environment."""

    def __init__(
            self, svg_bbox, pdf_bbox,
            fname=None, labels=None):
        self.svg_bbox = svg_bbox
        self.pdf_bbox = pdf_bbox
        self.background_graphics = fname
        if labels is None:
            labels = list()
        self.labels = labels

    def dumps(self):
        """Return `str` representation."""
        unit = self.svg_bbox.width
        xmin = self.svg_bbox.x
        ymin = self.svg_bbox.y
        w = self.svg_bbox.width
        h = self.svg_bbox.height
        c = list()
        if self.background_graphics is not None:
            x = self.pdf_bbox.x - xmin
            # the SVG coordinate system origin is at the top left corner
            # whereas the `picture` origin is at the lower left corner
            y = (h + ymin) - (self.pdf_bbox.height + self.pdf_bbox.y)
            x, y = _round(x, y, unit=unit)
            scale = self.pdf_bbox.width / unit
            s = (
                '\\put({x}, {y}){{'
                '\\includegraphics[width={scale}\\unitlength]{{{img}}}'
                '}}%').format(
                    scale=scale,
                    x=x, y=y,
                    img=self.background_graphics)
            c.append(s)
        for label in self.labels:
            x, y = label.pos
            # y=0 top in SVG, bottom in `\picture`
            x = x - xmin
            y = (h + ymin) - y
            x, y = _round(x, y, unit=unit)
            s = '\\put({x}, {y}){{{text}}}%'.format(
                x=x, y=y,
                text=label.texcode())
            c.append(s)
        width, height = _round(w, h, unit=unit)
        assert width == 1, width
        s = (
            '\\begingroup%\n' +
            _PICTURE_PREAMBLE +
            ('\\begin{{picture}}'
             '({width}, {height})%\n').format(
                width=width,
                height=height) +
            '\n'.join(c) + '\n' +
            '\\end{picture}%\n'
            '\\endgroup%\n')
        return s

    def add_label(self, label):
        """Append a label."""
        self.labels.append(label)


def _round(*args, unit=1):
    """Return `args` normalized by `unit` and rounded."""
    return tuple(round(x / unit, 3) for x in args)


if __name__ == '__main__':
    # respond to call from a command line
    args = _parse_args()
    convert(args.fname)
