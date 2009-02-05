Wrapping and Linking
====================

:mod:`codepy.jit` -- Compilation and Linking of C Source Code
-------------------------------------------------------------

.. module:: codepy.jit

.. autoclass:: Toolchain
    :members: copy, get_version, abi_id, add_library, build_extension
    :undoc-members:

.. autoclass:: GCCToolchain
    :show-inheritance:

.. autofunction:: guess_toolchain
.. autofunction:: extension_file_from_string
.. autofunction:: extension_from_string

Errors
^^^^^^

.. autoexception:: CompileError

.. autoexception:: ToolchainGuessError


:mod:`codepy.bpl` -- Support for Boost.Python
---------------------------------------------

.. automodule:: codepy.bpl

.. autoclass:: BoostPythonModule
    :members:
    :undoc-members:
