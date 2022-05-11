cgen: An Abstract Syntax Tree for C, in Python
----------------------------------------------

.. image:: https://gitlab.tiker.net/inducer/cgen/badges/main/pipeline.svg
    :alt: Gitlab Build Status
    :target: https://gitlab.tiker.net/inducer/cgen/commits/main
.. image:: https://github.com/inducer/cgen/workflows/CI/badge.svg?branch=main&event=push
    :alt: Github Build Status
    :target: https://github.com/inducer/cgen/actions?query=branch%3Amain+workflow%3ACI+event%3Apush
.. image:: https://badge.fury.io/py/cgen.svg
    :alt: Python Package Index Release Page
    :target: https://pypi.org/project/cgen/

cgen offers a simple abstract syntax tree for C and related languages
(C++/CUDA/OpenCL) to allow structured code generation from Python.
To represent mathematical expressions, cgen can be used with `pymbolic
<https://github.com/inducer/pymbolic>`_.

Places on the web related to cgen:

* `Python package index <http://pypi.python.org/pypi/cgen>`_ (download releases)
* `Documentation <http://documen.tician.de/cgen>`_ (read how things work)
* `Github <http://github.com/inducer/cgen>`_ (get latest source code, file bugs)

cgen is licensed under the liberal `MIT license
<http://en.wikipedia.org/wiki/MIT_License>`_ and free for commercial, academic,
and private use. All of cgen's dependencies can be automatically installed from
the package index after using::

    pip install cgen
