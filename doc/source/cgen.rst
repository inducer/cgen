:mod:`cgen` -- C-Generation Reference Documentation
==========================================================

.. module:: cgen

.. autofunction:: dtype_to_ctype

.. autoclass:: Generable
    :members: generate, __str__
    :show-inheritance:

.. autoclass:: Block
    :show-inheritance:
    :members: append, extend, extend_log_block

.. autoclass:: Module
    :show-inheritance:

.. autoclass:: Line
    :show-inheritance:

Data and Functions
------------------

.. autoclass:: FunctionBody
    :show-inheritance:

.. autoclass:: Initializer
    :show-inheritance:

Preprocessor Code
-----------------

.. autoclass:: Define
    :show-inheritance:

.. autoclass:: Comment
    :show-inheritance:

.. autoclass:: Include
    :show-inheritance:

.. autoclass:: Pragma
    :show-inheritance:

Declarators
-----------

.. autoclass:: Declarator
    :members:
    :show-inheritance:

.. autoclass:: Value
    :show-inheritance:

.. autoclass:: POD
    :show-inheritance:

.. autoclass:: Struct
    :show-inheritance:

.. autoclass:: GenerableStruct
    :show-inheritance:
    :members: __init__, make, make_with_defaults, __len__, struct_format

Nested Declarators
------------------

.. autoclass:: NestedDeclarator
    :show-inheritance:

.. autoclass:: ArrayOf
    :show-inheritance:

.. autoclass:: Const
    :show-inheritance:

.. autoclass:: FunctionDeclaration
    :show-inheritance:

.. autoclass:: MaybeUnused
    :show-inheritance:

.. autoclass:: Pointer
    :show-inheritance:

.. autoclass:: Reference
    :show-inheritance:

.. autoclass:: Template
    :show-inheritance:

Declaration Specifiers
----------------------

.. autoclass:: DeclSpecifier
    :show-inheritance:

.. autoclass:: Static
    :show-inheritance:

.. autoclass:: Typedef
    :show-inheritance:

Statements
----------

.. autoclass:: Statement
    :show-inheritance:

.. autoclass:: Assign
    :show-inheritance:

.. autoclass:: If
    :show-inheritance:

.. autofunction:: make_multiple_ifs

.. autoclass:: DoWhile
    :show-inheritance:

.. autoclass:: For
    :show-inheritance:

.. autoclass:: While
    :show-inheritance:

:mod:`cgen.cuda` -- Extensions to generate CUDA-compatible C Sources
---------------------------------------------------------------------------

.. automodule:: cgen.cuda

This module adds a few Nvidia `CUDA <http://nvidia.com/cuda>`_ features to
cgen's repertoire. This makes cgen a perfect complement to
`PyCuda <http://mathema.tician.de/software/pycuda>`_: cgen generates
the code, PyCuda compiles it, uploads it to the GPU and executes it.

The PyCuda manual has a tutorial on using the two together.

.. autoclass:: CudaGlobal
    :show-inheritance:

.. autoclass:: CudaDevice
    :show-inheritance:

.. autoclass:: CudaShared
    :show-inheritance:

.. autoclass:: CudaConstant
    :show-inheritance:

:mod:`cgen.opencl` -- Extensions to generate OpenCL-compatible C Sources
-------------------------------------------------------------------------------

.. automodule:: cgen.opencl

.. autofunction:: dtype_to_cltype

Kernels and Kernel Arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: CLKernel
    :show-inheritance:

.. autoclass:: CLConstant
    :show-inheritance:

.. autoclass:: CLLocal
    :show-inheritance:

.. autoclass:: CLGlobal
    :show-inheritance:

.. autoclass:: CLImage
    :show-inheritance:

Function Attributes
^^^^^^^^^^^^^^^^^^^

.. autoclass:: CLVecTypeHint
    :show-inheritance:

.. autoclass:: CLWorkGroupSizeHint
    :show-inheritance:

.. autoclass:: CLRequiredWorkGroupSize
    :show-inheritance:

Vector PODs
^^^^^^^^^^^

.. autoclass:: CLVectorPOD
    :show-inheritance:
