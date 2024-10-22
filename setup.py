"""Installation script."""
import setuptools

# inline:
# import git


NAME = 'svglatex'
DESCRIPTION = (
    'Include Inkscape graphics in LaTeX.')
LONG_DESCRIPTION = (
    'svglatex is a package for including SVG graphics in LaTeX documents '
    'via Inkscape. A script converts an SVG file to a PDF file that '
    'contains only graphics, and a text file that includes LaTeX code '
    'for typesetting the text of the SVG file. So the script '
    'separates text from graphics, and overlays the text, typeset with LaTeX, '
    'on the PDF.'
    'More details can be found in the README at: '
    'https://github.com/johnyf/svglatex')
url = f'https://github.com/johnyf/{NAME}'
PROJECT_URLS = {
    'Bug Tracker':
        'https://github.com/johnyf/svglatex/issues'}
VERSION_FILE = f'{NAME}/_version.py'
VERSION = '0.0.3'
VERSION_TEXT = (
    '# This file was generated from setup.py\n'
    "version = '{version}'\n")

INSTALL_REQUIRES = [
    'lxml >= 3.7.2',
    ]
CLASSIFIERS = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3 :: Only',
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
        match='v[0-9]*',
        tags=True,
        abbrev=0)
    latest_version = _parse_version(latest_tag[1:])
    given_version = _parse_version(version)
    if latest_version > given_version:
        raise ValueError((latest_tag, version))
    sha = repo.head.commit.hexsha
    if repo.is_dirty():
        return f'{version}.dev0+{sha}.dirty'
    # commit is clean
    # is it release of `version` ?
    try:
        tag = repo.git.describe(
            match='v[0-9]*',
            exact_match=True,
            tags=True,
            dirty=True)
    except git.GitCommandError:
        return f'{version}.dev0+{sha}'
    if tag != 'v' + version:
        raise ValueError((tag, version))
    return version


def _parse_version(
        version:
            str
        ) -> tuple[
            int, int, int]:
    """Return numeric version."""
    numerals = version.split('.')
    if len(numerals) != 3:
        raise ValueError(numerals)
    return tuple(map(int, numerals))


def run_setup():
    """Get version from `git`, install."""
    # version
    try:
        version = git_version(VERSION)
    except ValueError:
        raise
    except:
        print('No git info: Assume release.')
        version = VERSION
    s = VERSION_TEXT.format(version=version)
    with open(VERSION_FILE, 'w') as fd:
        fd.write(s)
    setuptools.setup(
        name=NAME,
        version=version,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        author='Ioannis Filippidis',
        author_email='jfilippidis@gmail.com',
        url=url,
        project_urls=PROJECT_URLS,
        license='BSD',
        python_requires='>=3.8',
        install_requires=INSTALL_REQUIRES,
        packages=[NAME],
        package_dir={NAME: NAME},
        include_package_data=True,
        entry_points={
            'console_scripts': [
                'svglatex = svglatex.interface:main']},
        classifiers=CLASSIFIERS,
        keywords=[
            'svg', 'latex', 'pdf', 'inkscape',
            'figure', 'graphics'])


if __name__ == '__main__':
    run_setup()
