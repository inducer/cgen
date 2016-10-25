#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open("README.rst", "rt") as inf:
    readme = inf.read()

setup(
        name="cgen",
        version="2016.2.2",
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

        packages=["cgen"],
        install_requires=[
            "pytools>=2015.1.2",
            "numpy>=1.6",
            ])
