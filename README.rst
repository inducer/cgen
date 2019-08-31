cgen: An Abstract Syntax Tree for C, in Python
----------------------------------------------

.. image:: https://gitlab.tiker.net/inducer/cgen/badges/master/pipeline.svg
    :alt: Gitlab Build Status
    :target: https://gitlab.tiker.net/inducer/cgen/commits/master
.. image:: https://dev.azure.com/ak-spam/inducer/_apis/build/status/inducer.cgen?branchName=master
    :alt: Azure Build Status
    :target: https://dev.azure.com/ak-spam/inducer/_build/latest?definitionId=7&branchName=master
.. image:: https://badge.fury.io/py/cgen.png
    :alt: Python Package Index Release Page
    :target: https://pypi.org/project/cgen/

cgen offers a simple abstract syntax tree for C and related languages
(C++/CUDA/OpenCL) to allow structured code generation from Python.
To represent mathematical expressions, cgen can be used with `pymbolic
<https://github.com/inducer/pymbolic>`_.

Places on the web related to cgen:

* `Python package index <http://pypi.python.org/pypi/cgen>`_ (download releases)

  .. image:: https://badge.fury.io/py/cgen.png
      :target: http://pypi.python.org/pypi/cgen

* `Documentation <http://documen.tician.de/cgen>`_ (read how things work)
* `Github <http://github.com/inducer/cgen>`_ (get latest source code, file bugs)

cgen is licensed under the liberal `MIT license
<http://en.wikipedia.org/wiki/MIT_License>`_ and free for commercial, academic,
and private use. All of cgen's dependencies can be automatically installed from
the package index after using::

    pip install cgen
