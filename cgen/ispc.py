__copyright__ = "Copyright (C) 2015 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from collections.abc import Sequence
from typing import ClassVar

from typing_extensions import override

from cgen import Declarator, DeclPair, DeclSpecifier, Pointer, Statement


class ISPCVarying(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "varying")

    mapper_method: ClassVar[str] = "map_ispc_varying"


class ISPCUniform(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "uniform")

    mapper_method: ClassVar[str] = "map_ispc_uniform"


class ISPCExport(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "export")

    mapper_method: ClassVar[str] = "map_ispc_export"


class ISPCTask(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "task")

    mapper_method: ClassVar[str] = "map_ispc_task"


class ISPCVaryingPointer(Pointer):
    @override
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*varying {sub_decl}"

    mapper_method: ClassVar[str] = "map_ispc_varying_pointer"


class ISPCUniformPointer(Pointer):
    @override
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*uniform {sub_decl}"

    mapper_method: ClassVar[str] = "map_ispc_uniform_pointer"


class ISPCLaunch(Statement):
    def __init__(self, grid: Sequence[str | int], expr: str) -> None:
        if grid:
            launch_spec = "[{}]".format(", ".join(str(gs_i) for gs_i in grid))
        else:
            launch_spec = ""

        super().__init__(f"launch{launch_spec} {expr}")
        self.grid: Sequence[str | int] = grid
        self.expr: str = expr

    mapper_method: ClassVar[str] = "map_ispc_launch"
