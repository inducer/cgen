__copyright__ = "Copyright (C) 2011-20 Andreas Kloeckner"

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

from typing import Any, ClassVar, Literal, TypeAlias

import numpy as np
from typing_extensions import override

from cgen import Declarator, DeclPair, DeclSpecifier, NestedDeclarator, Value


def dtype_to_cltype(dtype: Any) -> str:
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = np.dtype(dtype)
    if dtype == np.int64:
        return "long"
    elif dtype == np.uint64:
        return "ulong"
    elif dtype == np.int32:
        return "int"
    elif dtype == np.uint32:
        return "uint"
    elif dtype == np.int16:
        return "short"
    elif dtype == np.uint16:
        return "ushort"
    elif dtype == np.int8:
        return "char"
    elif dtype == np.uint8:
        return "uchar"
    elif dtype == np.float32:
        return "float"
    elif dtype == np.float64:
        return "double"
    else:
        raise ValueError(f"unable to map dtype '{dtype}'")


# {{{ kernel

class CLKernel(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "__kernel")

    mapper_method: ClassVar[str] = "map_cl_kernel"

# }}}


# {{{ kernel args

Mode: TypeAlias = Literal["r"] | Literal["w"]


class CLConstant(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "__constant")

    mapper_method: ClassVar[str] = "map_cl_constant"


class CLLocal(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "__local")

    mapper_method: ClassVar[str] = "map_cl_local"


class CLGlobal(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "__global")

    mapper_method: ClassVar[str] = "map_cl_global"


class CLImage(Value):
    def __init__(self, dims: int, mode: Mode, name: str) -> None:
        if mode == "r":
            spec = "__read_only"
        elif mode == "w":
            spec = "__write_only"
        else:
            raise ValueError("mode must be one of 'r' or 'w'")  # pyright: ignore[reportUnreachable]

        super().__init__(f"{spec} image{dims}d_t", name)

    mapper_method: ClassVar[str] = "map_cl_image"

# }}}


# {{{ function attributes

class CLVecTypeHint(NestedDeclarator):
    def __init__(self,
                 subdecl: Declarator,
                 dtype: Any = None,
                 count: int | None = None,
                 type_str: str | None = None) -> None:
        if (dtype is None) != (count is None):
            raise ValueError(
                "'dtype' and 'count' must always be specified together: "
                f"dtype is '{dtype}' and count is '{count}'")

        if (
                (dtype is None and type_str is None)
                or (dtype is not None and type_str is not None)):
            raise ValueError(
                "Exactly one of 'dtype' and 'type_str' must be specified: "
                f"dtype is '{dtype}' and type_str is '{type_str}'")

        self.dtype: np.dtype[Any] = np.dtype(dtype)
        if type_str is None:
            type_str = f"{dtype_to_cltype(self.dtype)}{count}"
        else:
            type_str = type_str

        super().__init__(subdecl)
        self.count: int | None = count
        self.type_str: str = type_str

    @override
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, (
            "__attribute__ ((vec_type_hint({}))) {}"
            .format(sub_decl, self.type_str))

    mapper_method: ClassVar[str] = "map_cl_vec_type_hint"


class _CLWorkGroupSizeDeclarator(NestedDeclarator):
    def __init__(self, dim: tuple[int, ...], subdecl: Declarator) -> None:
        super().__init__(subdecl)

        while len(dim) < 3:
            dim = (*dim, 1)

        self.dim: tuple[int, ...] = dim


class CLWorkGroupSizeHint(_CLWorkGroupSizeDeclarator):
    """
    See Sec 6.7.2 of OpenCL 2.0 spec, Version V2.2-11.
    """

    @override
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, (
            "__attribute__ ((work_group_size_hint({}))) {}"
            .format(", ".join(str(d) for d in self.dim), sub_decl))

    mapper_method: ClassVar[str] = "map_cl_workgroup_size_hint"


class CLRequiredWorkGroupSize(_CLWorkGroupSizeDeclarator):
    """
    See Sec 6.7.2 of OpenCL 2.0 spec, Version V2.2-11.
    """

    @override
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, (
            "__attribute__ ((reqd_work_group_size({}))) {}"
            .format(", ".join(str(d) for d in self.dim), sub_decl))

    mapper_method: ClassVar[str] = "map_cl_required_wokgroup_size"

# }}}


# {{{ vector PODs

class CLVectorPOD(Declarator):
    def __init__(self, dtype: Any, count: int, name: str) -> None:
        self.dtype: np.dtype[Any] = np.dtype(dtype)
        self.count: int = count
        self.name: str = name

    @override
    def get_decl_pair(self) -> DeclPair:
        return [f"{dtype_to_cltype(self.dtype)}{self.count}"], self.name

    @override
    def struct_maker_code(self, data: str) -> str:
        return data

    @override
    def struct_format(self) -> str:
        return f"{self.count}{self.dtype.char}"

    @override
    def alignment_requirement(self) -> int:
        from struct import calcsize
        return calcsize(self.struct_format())

    @override
    def default_value(self) -> Any:
        return [0] * self.count

    mapper_method: ClassVar[str] = "map_cl_vector_pod"

# }}}

# vim: fdm=marker
