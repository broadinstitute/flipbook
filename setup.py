import os
import sys
from setuptools import setup

# NOTE: This package must be installed with pip, and not with python3 setup.py install
# in order for static files to work on the webpage
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
    "configargparse>=1.5.5",
    "flask-cors>=4.0.0",
    "gunicorn>=21.2.0",
    "jinja2>=3.1.2",
    "openpyxl>=3.1.1",
    "pandas>=2.0.3",
    "requests>=2.31.0",
    "wcmatch>=8.4.1",
    "xlrd>=2.0.1",
    "xlwt>=1.3.0",

    # NOTE: there is a "KeyError: 'WERKZEUG_SERVER_FD'" in the latest versions of Werkzeug
    # when starting the server, so use a previous version of flask and Werkzeug
    "flask==2.1",
    "Werkzeug==2.0.0",
]

setup(
    name='flipbook',
    version="0.12",
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
    package_data={'': [
        'static/*/*.*',
        'static/*/*/*.*',
        'static/*/*/*/*.*',
        'static/*/*/*/*/*.*',
        'static/*/*/*/*/*/*.*',
        'templates/*.*',
    ]},
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
