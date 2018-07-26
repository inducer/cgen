#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open("README.rst", "rt") as inf:
    readme = inf.read()

ver_dic = {}
with open("cgen/version.py") as version_file:
    version_file_contents = version_file.read()

exec(compile(version_file_contents, "cgen/version.py", 'exec'), ver_dic)

setup(
        name="cgen",
        version=ver_dic["VERSION_TEXT"],
        description="C/C++ source generation from an AST",
        long_description=readme,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Intended Audience :: Other Audience',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Programming Language :: Python',
            'Topic :: Scientific/Engineering',
            'Topic :: Software Development :: Libraries',
            'Topic :: Utilities',
            ],

        author="Andreas Kloeckner",
        author_email="inform@tiker.net",
        license="MIT",
        url="http://documen.tician.de/cgen/",

        packages=[
            "cgen",
            "cgen.preprocessor"
        ],
        install_requires=[
            "pytools>=2015.1.2",
            "numpy>=1.6",
            ])
