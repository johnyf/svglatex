"""Installation script."""
from setuptools import setup
from pkg_resources import parse_version

# inline:
# import git


name = 'svglatex'
description = (
    'Include Inkscape graphics in LaTeX.')
long_description = (
    'svglatex is a package for including SVG graphics in LaTeX documents '
    'via Inkscape. A script converts an SVG file to a PDF file that '
    'contains only graphics, and a text file that includes LaTeX code '
    'for typesetting the text of the SVG file. So the script '
    'separates text from graphics, and overlays the text, typeset with LaTeX, '
    'on the PDF.'
    'More details can be found in the README at: '
    'https://github.com/johnyf/svglatex')
url = 'https://github.com/johnyf/{name}'.format(name=name)
VERSION_FILE = '{name}/_version.py'.format(name=name)
MAJOR = 0
MINOR = 0
MICRO = 2
VERSION = '{major}.{minor}.{micro}'.format(
    major=MAJOR, minor=MINOR, micro=MICRO)
VERSION_TEXT = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n")

install_requires = [
    'humanize >= 2.6.0',
    'lxml >= 3.7.2',
    ]
tests_require = [
    ]
classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Topic :: Multimedia :: Graphics :: Graphics Conversion',
    'Topic :: Scientific/Engineering :: Visualization',
    'Topic :: Text Processing :: Markup :: LaTeX',
    ]


def git_version(version):
    """Return version with local version identifier."""
    import git
    repo = git.Repo('.git')
    repo.git.status()
    # assert versions are increasing
    latest_tag = repo.git.describe(
        match='v[0-9]*', tags=True, abbrev=0)
    assert parse_version(latest_tag) <= parse_version(version), (
        latest_tag, version)
    sha = repo.head.commit.hexsha
    if repo.is_dirty():
        return '{v}.dev0+{sha}.dirty'.format(
            v=version, sha=sha)
    # commit is clean
    # is it release of `version` ?
    try:
        tag = repo.git.describe(
            match='v[0-9]*', exact_match=True,
            tags=True, dirty=True)
    except git.GitCommandError:
        return '{v}.dev0+{sha}'.format(
            v=version, sha=sha)
    assert tag == 'v' + version, (tag, version)
    return version


def run_setup():
    """Get version from `git`, install."""
    # version
    try:
        version = git_version(VERSION)
    except AssertionError:
        raise
    except:
        print('No git info: Assume release.')
        version = VERSION
    s = VERSION_TEXT.format(version=version)
    with open(VERSION_FILE, 'w') as f:
        f.write(s)
    setup(
        name=name,
        version=version,
        description=description,
        long_description=long_description,
        author='Ioannis Filippidis',
        author_email='jfilippidis@gmail.com',
        url=url,
        license='BSD',
        install_requires=install_requires,
        tests_require=tests_require,
        packages=[name],
        package_dir={name: name},
        include_package_data=True,
        entry_points={
            'console_scripts': ['svglatex = svglatex.interface:main']},
        classifiers=classifiers,
        keywords=[
            'svg', 'latex', 'pdf', 'inkscape',
            'figure', 'graphics'])


if __name__ == '__main__':
    run_setup()
