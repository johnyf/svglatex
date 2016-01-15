#!/usr/bin/env python
"""Convert SVG to PDF with inkscape, with latex output.


Usage
=====

Create a "content" labeled layer and
put a text box (no `flowRect`),
with each line looking like:

```
background, layer1
background, layer2
background, layer2, layer3
+layer4
background, layer2 * 0.5, layer3 * 0.5, layer5
```


License
=======

Copyright (GPLv3) 2010-2016 by Ioannis Filippidis

Based on:  InkscapeSlide 1.0 by Alexandre Bourget
GPLv3 Copyright (c) 2008 by Alexandre Bourget
    http://pypi.python.org/pypi/InkscapeSlide/1.0
    http://projects.abourget.net/inkscapeslide/
    https://github.com/abourget/inkscapeslide


Note
====

Changes by Ioannis Filippidis:
ported to Python 3.2, handling UTF-8,
latex export, solved encoding="UTF-8" error
"""
import lxml.etree
import sys
import os
import subprocess
import re
from optparse import OptionParser  # replace with argparse
import codecs
import time
import warnings


def main():
    # HIDE DEPRECATION WARINGS ONLY IN RELEASES. SHOW THEM IN DEV. TRUNKS
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    # parse arguments
    usage = 'Usage: %prog [options] svgfilename'
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-f", "--file", dest="svgfile",
        default=False, help="Provide input SVG file name")
    parser.add_option(
        "-s", "--scene-order", dest="sceneorder",
        default=False,
        help=(
            'Define order of generated scenes for \onslide<> in .pdf_tex'
            'as a comma-separated list like --scene-order=1-2,3,4,5-5,6-8'))
    parser.add_option(
        "-w", "--width", dest="width",
        default=False, help="Define width of included PDF scenes")
    parser.add_option(
        "-i", "--imageexport", action="store_true", dest="imageexport",
        default=False, help="Use PNG files as export content")
    parser.add_option(
        "-b", "--overprint", dest="overprint",
        default=False, help="Include or not overprint environment")
    options, args = parser.parse_args()
    # no .svg file provided
    if options.svgfile:
        FILENAME = options.svgfile
    else:
        raise sys.exit("Please provide an .svg file name.")
    # file name wwith or w/o extension provided?
    if FILENAME.find(".svg") == -1:
        fname = FILENAME
        FILENAME = "%s.svg" % FILENAME
    else:
        fname = FILENAME.split(".svg")[0]
    # check .svg exists
    svg_exists = os.access(FILENAME, os.F_OK)
    if svg_exists:
        print("SVG file exists.")
        # get last modification time
        (mode, ino, dev, nlink, uid, gid,
         size, atime, svgmtime, ctime) = os.stat(FILENAME)
    else:
        # it does not exist, nothing can be done
        raise sys.exit("SVG file not found! I cannot produce PDF.")
    # load .svg
    f = codecs.open(FILENAME, "r", "utf-8")
    cnt = f.read()
    f.close()
    cnt = cnt.encode('utf-8')
    utf8_parser = lxml.etree.XMLParser(encoding='utf-8')
    doc = lxml.etree.fromstring(cnt, parser=utf8_parser)
    # Get all layers
    attr = '{http://www.inkscape.org/namespaces/inkscape}groupmode'
    layers = [
        x for x in doc.iterdescendants(tag='{http://www.w3.org/2000/svg}g')
        if x.attrib.get(attr, False) == 'layer']
    # Scan the 'content' layer
    attr = '{http://www.inkscape.org/namespaces/inkscape}label'
    content_layer = [
        x for x in layers
        if x.attrib.get(attr, False).lower() == 'content']
    if not content_layer:
        print(
            "No 'content'-labeled layer."
            "Create a 'content'-labeled layer and "
            "put a text box (no flowRect), with each line looking like:")
        s = [
            "",
            " background, layer1",
            " background, layer2",
            " background, layer2, layer3",
            " background, layer2 * 0.5, layer3",
            " +layer4 * 0.5",
            "",
            "each name being the label of another layer. Lines starting with",
            "a '+' will add to the layers of the preceding line, creating",
            "incremental display",
            "(note there must be no whitespace before '+')",
            "",
            "The opacity of a layer can be set to 50% for example by adding ",
            "'*0.5' after the layer name."]
        print('\n'.join(s))
        sys.exit(1)
    content = content_layer[0]
    # Find the text stuff, everything starting with SLIDE:
    # take all the layer names separated by ','..
    s = '{http://www.w3.org/2000/svg}text/{http://www.w3.org/2000/svg}tspan'
    preslides = [x.text for x in content.findall(s) if x.text]
    if not bool(preslides):
        print("Make sure you have a text box (with no flowRect) in the "
              "'content' layer, and rerun this program.")
        sys.exit(1)
    # print(preslides)
    # Get the initial style attribute and keep it
    orig_style = {}
    attr = '{http://www.inkscape.org/namespaces/inkscape}label'
    for l in layers:
        label = l.attrib.get(attr)
        if 'style' not in l.attrib:
            l.set('style', '')
        # Save initial values
        orig_style[label] = l.attrib['style']
    slides = list()  # Contains seq of:
    # [('layer', opacity), ('layer', opacity), ..]
    for sl in preslides:
        if sl:
            if sl.startswith('+'):
                sl = sl[1:]
                sl_layers = slides[-1].copy()
            else:
                sl_layers = {}

            for layer in sl.split(','):
                elements = layer.strip().split('*')
                name = elements[0].strip()
                opacity = None
                if len(elements) == 2:
                    opacity = float(elements[1].strip())
                sl_layers[name] = {'opacity': opacity}
            slides.append(sl_layers)

    def set_style(el, style, value):
        """Set the display: style.

        Add it if it isn't there, don't touch the rest.
        """
        if re.search(r'%s: ?[a-zA-Z0-9.]*' % style, el.attrib['style']):
            el.attrib['style'] = re.sub(
                r'(.*%s: ?)([a-zA-Z0-9.]*)(.*)' % style,
                r'\1%s\3' % value, el.attrib['style'])
        else:
            el.attrib['style'] = '%s:%s;%s' % (style, value,
                                               el.attrib['style'])
    pdfslides = []
    pdftexslides = []
    for i, slide_layers in enumerate(slides):
        for l in layers:
            attr = '{http://www.inkscape.org/namespaces/inkscape}label'
            label = l.attrib.get(attr)
            # Set display mode to original
            l.set('style', orig_style[label])

            # Don't show it by default...
            set_style(l, 'display', 'none')

            if label in slide_layers:
                set_style(l, 'display', 'inline')
                opacity = slide_layers[label]['opacity']
                if opacity:
                    set_style(l, 'opacity', str(opacity))
            # print l.attrib['style']
        svgslide = os.path.abspath(os.path.join(
            os.curdir, "%s_scene%d.svg" % (fname, i)))
        pdfslide = os.path.abspath(os.path.join(
            os.curdir, "%s_scene%d.pdf" % (fname, i)))
        pdftexslide = "%s_scene%d.pdf_tex" % (fname, i)
        # Use the correct extension if using images
        if options.imageexport:
            pdfslide = os.path.abspath(os.path.join(
                os.curdir, ".inkscapeslide_%s.p%05d.png" % (fname, i)))
        # check .pdf exists
        pdf_exists = os.access(pdfslide, os.F_OK)
        if pdf_exists:
            print("PDF file exists.")
            # get last modification time
            (mode, ino, dev, nlink, uid, gid,
             size, atime, pdfmtime, ctime) = os.stat(pdfslide)
            print(
                "\n------------------------\n"
                "last mod dates?\n\tSVG: %s\n\tPDF: %s\n"
                % (time.ctime(svgmtime), time.ctime(pdfmtime)))
            flag = 1
        else:
            # it does not exist,
            # last modification check omitted, first export performed
            print("PDF file not found. I wiil produce a new one.")
            flag = 0
        # compare last modification times only if both .svg and .pdf exist
        if flag == 0 or svgmtime > pdfmtime:
            print("Updating...\n------------------------\n")
            # Write the XML to file, "filename.svg"
            f = open(svgslide, 'wb')
            f.write(lxml.etree.tostring(
                doc, encoding='UTF-8', xml_declaration=True))
            f.close()
            # Determine whether to export pdf's or images
            # (e.g. inkscape -A versus inkscape -e)
            cmd = "inkscape -z -D --export-latex -A {pdf} {svg}".format(
                pdf=pdfslide, svg=svgslide)
            if options.imageexport:
                cmd = "inkscape -d 180 -e %s %s" % (pdfslide, svgslide)

            # Using subprocess to hide stdout
            subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE).communicate()
            # p = subprocess.call(args)
            os.unlink(svgslide)  # delete auxiliary .svg files
            print("Generated scene %d." % (i + 1))
        else:
            print("No update needed.\n------------------------\n")
        pdfslides.append(pdfslide)
        pdftexslides.append(pdftexslide)
    # create .pdf_tex file to \input{} the generated .pdf_tex scene files
    # which in turn \includehraphics{} the generated .pdf files
    pdf_tex = "%s.pdf_tex" % fname
    # scene order given?
    if options.sceneorder:
        scene_order = options.sceneorder
        scene_order = scene_order.split(",")
    else:
        print("Please provide a scene order.")
        print("No .pdf_tex file created.")
        sys.exit(1)
    # pdf width given?
    if options.width:
        texcode = "\\def"
        texcode = texcode + "\\tempsvgwidth{" + options.width + "}"
    else:
        print("No width defined for included PDF scenes.")
        texcode = "\\global\\let\\svgwidth\\undefined"
    if options.overprint:
        texcode = texcode + "\n\\begin{overprint}"
    else:
        texcode = texcode + "\n"
    # same number of scenes produces as defined in scene order provided?
    if len(scene_order) != len(pdftexslides):
        print("Number of scenes generated is different than "
              "defined in scene order.")
        print("No .pdf_tex file created.")
        sys.exit(1)
    # \overprint{} environment with \onslide<> and \input{}
    for i in range(len(scene_order)):
        if options.width:
            texcode = texcode + "\n\t\\onslide<" + scene_order[i] + ">\
                \n\t\t\\def\\svgwidth{\\tempsvgwidth}\
                \n\t\t\\input{" + pdftexslides[i] + "}"
        else:
            texcode = texcode + "\n\t\\onslide<" + scene_order[i] + ">\
                \\global\\let\\svgwidth\\undefined\
                \n\t\t\\input{" + pdftexslides[i] + "}"
    if options.overprint:
        texcode = texcode + "\n\\end{overprint}"
    else:
        texcode = texcode + "\n"
    # Write the LaTeX to file, "filename.pdf_tex"
    f = open(pdf_tex, 'wb')
    f.write(bytes(texcode, 'UTF-8'))
    f.close()


'''
    # Joining multiple .pdf slides to single .pdf presentation

    joinedpdf = False
    outputFilename = "%s.pdf" % FILENAME.split(".svg")[0]
    outputDir = os.path.dirname(outputFilename)
    print("Output file %s" % outputFilename)

     if options.imageexport:
         # Use ImageMagick to combine the PNG files into a PDF
         if not os.system('which convert > /dev/null'):
             print("Using 'convert' to join PNG's")
             pngPath = os.path.join(outputDir, ".inkscapeslide_*.png")
             proc = subprocess.Popen(
                 "convert %s -resample 180 %s" % (pngPath, outputFilename),
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
             # See if the command succeeded
             stdout_value, stderr_value = proc.communicate()
             if proc.returncode:
                 print("\nERROR: convert command failed:")
                 print(stderr_value)
             else:
                 joinedpdf = True
         else:
             print("Please install ImageMagick"
                   " to provide the 'convert' utility")
     else:
         # Join PDFs
         has_pyPdf = False
         try:
             import pyPdf
             has_pyPdf = True
         except:
             pass

         if has_pyPdf:
             print("Using 'pyPdf' to join PDFs")
             output = pyPdf.PdfFileWriter()
             inputfiles = []
             for slide in pdfslides:
                 inputstream = file(slide, "rb")
                 inputfiles.append(inputstream)
                 input = pyPdf.PdfFileReader(inputstream)
                 output.addPage(input.getPage(0))
             outputStream = file(outputFilename, "wb")
             output.write(outputStream)
             outputStream.close()
             for f in inputfiles:
                 f.close()
             joinedpdf = True

         # Verify pdfjoin exists in PATH
         elif not os.system('which pdfjoin > /dev/null'):
             # In the end, run: pdfjoin wireframes.p*.pdf -o Wireframes.pdf
             print("Using 'pdfsam' to join PDFs")
             os.system(
                 "pdfjoin --outfile %s.pdf %s" % (FILENAME.split(".svg")[0],
                 " ".join(pdfslides)))
             joinedpdf = True

         # Verify pdftk exists in PATH
         elif not os.system('which pdftk > /dev/null'):
             # run: pdftk in1.pdf in2.pdf cat output Wireframes.pdf
             print("Using 'pdftk' to join PDFs")
             os.system("pdftk %s cat output %s.pdf" % (" ".join(pdfslides),
                                                FILENAME.split(".svg")[0]))
             joinedpdf = True
         else:
             print(
                 "Please install pdfjam, pdftk or "
                 "install the 'pyPdf' python "
                 "package, to join PDFs.")

     Clean up
    if joinedpdf:
        for pdfslide in pdfslides:
            os.unlink(pdfslide)
'''


if __name__ == '__main__':
    main()
