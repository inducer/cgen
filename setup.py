#!/usr/bin/env python
# -*- coding: latin1 -*-

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup
import glob

setup(name="codepy",
      version="2011.1",
      description="Generate and execute native code at run time.",
      long_description="""
      CodePy is a C/C++ metaprogramming toolkit for Python. It handles two aspects of
      native-code metaprogramming:

      * Generating C/C++ source code.
      * Compiling this source code and dynamically loading it into the
        Python interpreter.

      Both capabilities are meant to be used together, but also work
      on their own. In particular, the code generation facilities work
      well in conjunction with `PyCuda <http://mathema.tician.de/software/pycuda>`_.
      Dynamic compilation and linking are so far only supported in Linux
      with the GNU toolchain.
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

      packages=["codepy", "codepy.cgen"],
      install_requires=[
          "pytools>=8",
          ],
      data_files=[("include/codepy", glob.glob("include/codepy/*.hpp"))],
     )
