"""Package that converts SVG to PDF for graphics and LaTeX for text."""
try:
    from svglatex import _version
    __version__ = _version.version
except ImportError:
    __version__ = None
