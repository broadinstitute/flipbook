import os
import sys
import setuptools

command = sys.argv[-1]
if command == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    install_requires = [r.strip() for r in fh.readlines()]

setuptools.setup(
    name='reviewer2',
    version="0.1",
    description="Starts a simple image server that lets you quickly flip through image files from a local directory "
                "using your web browser and optionally answering customizable questions about each one",
    install_requires=install_requires,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=["reviewer2"],
    package_data={'': ['favicon.png']},
    python_requires=">=3.6",
    license="MIT",
    keywords='curation, NGS, sequencing, STRs, REviewer, read visualization, machine learning',
    url='https://github.com/bw2/reviewer2',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
