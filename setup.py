import os
import sys
from setuptools import setup

command = sys.argv[-1]
if command == 'publish':
    os.system('rm -rf dist')
    os.system('python3 setup.py sdist')
    os.system('python3 setup.py bdist_wheel')
    os.system('twine upload dist/*whl dist/*gz')
    sys.exit()

with open("README.md", "rt") as fh:
    long_description = fh.read()

install_requires = [
    "configargparse",
    "flask",
    "flask-cors",
    "gunicorn",
    "jinja2",
    "openpyxl",
    "pandas",
    "requests",
    "wcmatch",
    "xlrd",
    "xlwt",
]

setup(
    name='flipbook',
    version="0.10.2",
    description="Starts a simple image server that lets you quickly flip through image files from a local directory "
                "using your web browser and optionally answering customizable questions about each one",
    install_requires=install_requires,
    entry_points = {
        'console_scripts': [
            'flipbook = flipbook:main',
        ],
    },
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=["flipbook"],
    py_modules=["compare_form_response_tables"],
    include_package_data=True,
    package_data={'': ['*/*.png', '*/*.html']},
    python_requires=">=3.7",
    license="MIT",
    keywords='curation, NGS, sequencing, STRs, REviewer, read visualization, machine learning',
    url='https://github.com/broadinstitute/flipbook',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
