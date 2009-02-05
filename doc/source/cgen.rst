:mod:`codepy.cgen` -- C-Generation Reference Documentation
==========================================================

.. module:: codepy.cgen

.. autoclass:: Generable
    :members: generate, __str__
    :show-inheritance:

.. autoclass:: Block
    :show-inheritance:

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

.. autoclass:: Assign
    :show-inheritance:

.. autoclass:: If
    :show-inheritance:

.. autoclass:: DoWhile
    :show-inheritance:

.. autoclass:: For
    :show-inheritance:

.. autoclass:: While
    :show-inheritance:

.. autoclass:: Statement
    :show-inheritance:


:mod:`codepy.cgen.cuda` -- Extensions to generate CUDA-compatible C Sources
---------------------------------------------------------------------------

.. module:: codepy.cgen.cuda

.. autoclass:: CudaShared
.. autoclass:: CudaDevice
.. autoclass:: CudaShared
.. autoclass:: CudaConstant
