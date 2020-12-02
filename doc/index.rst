Welcome to cgen's documentation!
==================================

cgen offers a simple abstract syntax tree for C and related languages
(C++/CUDA/OpenCL) to allow structured code generation from Python.

Here's an example, to give you an impression:

.. literalinclude:: ../examples/hello-cgen.py

This prints the following::

    char const *greet()
    {
      return "hello world";
    }

:mod:`cgen` deliberately does not worry about expression trees. Its sister
package :mod:`pymbolic` can help you build those.


Contents
--------

.. toctree::
    :maxdepth: 2

    cgen
    faq
    🚀 Github <https://github.com/inducer/cgen>
    💾 Download Releases <https://pypi.python.org/pypi/cgen>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
