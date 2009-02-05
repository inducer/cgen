.. codepy documentation master file, created by sphinx-quickstart on Wed Feb  4 16:32:10 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to CodePy's documentation!
==================================

.. module:: codepy

CodePy is a C metaprogramming toolkit for Python. It handles two aspects of
metaprogramming:

* Generating C source code.
* Compiling this source code and dynamically loading it into the
  Python interpreter.

Both capabilities are meant to be used together, but also work
on their own. In particular, the code generation facilities work
well in conjunction with `PyCuda <http://mathema.tician.de/software/pycuda>`_.
Dynamic compilation and linking are so far only supported in Linux
with the GNU toolchain.

A taste of CodePy
-----------------

This sample CodePy program builds a Boost.Python C++ module that returns
the string "hello world"::

    from codepy.cgen import *
    from codepy.bpl import BoostPythonModule
    mod = BoostPythonModule()

    mod.add_function(
            FunctionBody(
                FunctionDeclaration(Const(Pointer(Value("char", "greet"))), []),
                Block([Statement('return "hello world"')])
                ))

    from codepy.jit import guess_toolchain
    cmod = mod.compile(guess_toolchain(), wait_on_error=True)

    print cmod.greet()


Boost.Python and CodePy
^^^^^^^^^^^^^^^^^^^^^^^

You may notice that the above code snippet refers to 
`Boost.Python <http://www.boost.org/doc/libs/release/libs/python/doc/>`_.
Boost.Python is a Python wrapper generator library for C++.
CodePy does not depend on it being available, but its use
is strongly encouraged--otherwise the generated sourcecode
would need to use another wrapper generator or talk directly
to the `Python C API <http://docs.python.org/c-api/>`_ to make
its functionality accessible from Python. Boost.Python is only
used at run time. CodePy has no install-time dependencies

`Instructions <http://mathema.tician.de/software/install-boost>`_
on how to install Boost.Python are available. As described in the
instructions, CodePy looks for the installation location of Boost.Python
in :file:`$HOME/.aksetup-defaults.py` and :file:`/etc/aksetup-defaults.py`.

.. note::

  Boost.Python is not needed at all if CodePy is used to generate code 
  for PyCuda.

Contents
--------

.. toctree::
    :maxdepth: 2

    cgen
    jit
    faq

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
