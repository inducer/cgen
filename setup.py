#!/usr/bin/env python
# -*- coding: latin1 -*-

import ez_setup

ez_setup.use_setuptools()

from setuptools import setup

setup(name="codepy",
      version="0.90",
      description="Generate and execute native code at run time.",
      long_description="""
      Pytools is a big bag of things that are "missing" from the Python standard
      library. This is mainly a dependency of my other software packages, and is
      probably of little interest to you unless you use those. If you're curious
      nonetheless, here's what's on offer:

      * A ton of small tool functions such as `len_iterable`, `argmin`, 
        tuple generation, permutation generation, ASCII table pretty printing,
        GvR's mokeypatch_xxx() hack, the elusive `flatten`, and much more.
      * Michele Simionato's decorator module
      * A time-series logging module, `pytools.log`.
      * Batch job submission, `pytools.batchjob`.
      * A lexer, `pytools.lex`.
      """,
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

      author=u"Andreas Kloeckner",
      url="http://mathema.tician.de/software/codepy",
      author_email="inform@tiker.net",
      license = "MIT",
      packages=["codepy"],
      package_dir={"codepy": "src"},
      zip_safe=False,
     )
