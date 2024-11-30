"""Generator for C/C++."""

from __future__ import annotations


__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"

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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeAlias

import numpy as np

from pytools import memoize, memoize_method


try:
    # NOTE: pycuda still needs this for complex number support.
    import pycuda._pvt_struct as _struct
except ImportError:
    import struct as _struct

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence


@memoize
def is_long_64_bit() -> bool:
    return bool(_struct.calcsize("l") == 8)


def dtype_to_ctype(dtype: Any) -> str:
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = np.dtype(dtype)
    if dtype == np.int64:
        if is_long_64_bit():
            return "long"
        else:
            return "long long"
    elif dtype == np.uint64:
        if is_long_64_bit():
            return "unsigned long"
        else:
            return "unsigned long long"
    elif dtype == np.int32:
        return "int"
    elif dtype == np.uint32:
        return "unsigned int"
    elif dtype == np.int16:
        return "short int"
    elif dtype == np.uint16:
        return "short unsigned int"
    elif dtype == np.int8:
        return "signed char"
    elif dtype == np.uint8:
        return "unsigned char"
    elif dtype == np.float32:
        return "float"
    elif dtype == np.float64:
        return "double"
    elif dtype == np.complex64:
        return "std::complex<float>"
    elif dtype == np.complex128:
        return "std::complex<double>"
    elif dtype == np.void:
        return "void"
    else:
        raise ValueError(f"unable to map dtype '{dtype}'")


class Generable(ABC):
    def __str__(self) -> str:
        """
        :returns: a single string (possibly containing newlines) representing
            this code construct.
        """
        return "\n".join(line.rstrip() for line in self.generate())

    @abstractmethod
    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        """Generate (i.e. yield) the lines making up this code construct."""


# {{{ declarators

DeclPair: TypeAlias = tuple[list[str], str | None]


class Declarator(Generable, ABC):
    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        tp_lines, tp_decl = self.get_decl_pair()

        yield from tp_lines[:-1]

        sc = ";" if with_semicolon else ""
        if tp_decl is None:
            yield f"{tp_lines[-1]}{sc}"
        else:
            yield f"{tp_lines[-1]} {tp_decl}{sc}"

    @abstractmethod
    def get_decl_pair(self) -> DeclPair:
        """
        :returns: a tuple ``(type_lines, rhs)``. *type_lines* is a non-empty list
            of lines (most often just a single one) describing the type of this
            declarator. *rhs* is the right-hand side that actually contains the
            function/array/constness notation making up the bulk of the
            declarator syntax.
        """

    def struct_format(self) -> str:
        raise NotImplementedError

    def alignment_requirement(self) -> int:
        raise NotImplementedError

    def struct_maker_code(self, data: str) -> str:
        raise NotImplementedError

    def default_value(self) -> Any:
        raise NotImplementedError

    def inline(self, with_semicolon: bool = False) -> str:
        """
        :returns: the declarator as a single line.
        """
        tp_lines, tp_decl = self.get_decl_pair()
        tp = " ".join(tp_lines)

        sc = ";" if with_semicolon else ""
        if tp_decl is None:
            return f"{tp}{sc}"
        else:
            return f"{tp} {tp_decl}{sc}"


class POD(Declarator):
    """A simple declarator: The type is given as a :class:`numpy.dtype`
    and the *name* is given as a string.
    """

    def __init__(self, dtype: Any, name: str) -> None:
        self.dtype = np.dtype(dtype)
        self.name = name

    def get_decl_pair(self) -> DeclPair:
        return [dtype_to_ctype(self.dtype)], self.name

    def struct_maker_code(self, name: str) -> str:
        return name

    def struct_format(self) -> str:
        return str(self.dtype.char)

    def alignment_requirement(self) -> int:
        return int(_struct.calcsize(self.struct_format()))

    def default_value(self) -> Any:
        return 0

    mapper_method = "map_pod"


class Value(Declarator):
    """A simple declarator: *typename* and *name* are given as strings."""

    def __init__(self, typename: str, name: str) -> None:
        self.typename = typename
        self.name = name

    def get_decl_pair(self) -> DeclPair:
        return [self.typename], self.name

    def struct_maker_code(self, name: str) -> str:
        raise RuntimeError("named-type values can't be put into structs")

    def struct_format(self) -> str:
        raise RuntimeError("named-type values have no struct format")

    def default_value(self) -> Any:
        return 0

    mapper_method = "map_value"


class NestedDeclarator(Declarator):
    def __init__(self, subdecl: Declarator) -> None:
        self.subdecl = subdecl

    @property
    def name(self) -> str:
        if hasattr(self.subdecl, "name"):
            return str(self.subdecl.name)

        raise AttributeError("name")

    def struct_format(self) -> str:
        return self.subdecl.struct_format()

    def alignment_requirement(self) -> int:
        return self.subdecl.alignment_requirement()

    def struct_maker_code(self, data: str) -> str:
        return self.subdecl.struct_maker_code(data)

    def get_decl_pair(self) -> DeclPair:
        return self.subdecl.get_decl_pair()


class DeclSpecifier(NestedDeclarator):
    def __init__(self, subdecl: Declarator, spec: str, sep: str = " ") -> None:
        super().__init__(subdecl)
        self.spec = spec
        self.sep = sep

    def get_decl_pair(self) -> DeclPair:
        def add_spec(sub_it: list[str]) -> Iterator[str]:
            it = iter(sub_it)
            try:
                yield f"{self.spec}{self.sep}{next(it)}"
            except StopIteration:
                pass

            yield from it

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return list(add_spec(sub_tp)), sub_decl


class NamespaceQualifier(DeclSpecifier):
    def __init__(self, namespace: str, subdecl: Declarator) -> None:
        super().__init__(subdecl, namespace, sep="::")

    mapper_method = "map_namespace_qualifier"


class Typedef(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "typedef")

    mapper_method = "map_typedef"


class Static(DeclSpecifier):
    def __init__(self, subdecl: Declarator) -> None:
        super().__init__(subdecl, "static")

    mapper_method = "map_static"


class Const(NestedDeclarator):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"const {sub_decl}"

    mapper_method = "map_const"


class Volatile(NestedDeclarator):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"volatile {sub_decl}"

    mapper_method = "map_volatile"


class Extern(DeclSpecifier):
    def __init__(self, language: str, subdecl: Declarator) -> None:
        self.language = language
        super().__init__(subdecl, f'extern "{language}"')

    mapper_method = "map_extern"


class TemplateSpecializer(NestedDeclarator):
    def __init__(self, specializer: str, subdecl: Declarator) -> None:
        self.specializer = specializer
        super().__init__(subdecl)

    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        sub_tp[-1] = f"{sub_tp[-1]}<{self.specializer}>"
        return sub_tp, sub_decl

    mapper_method = "map_template_specializer"


class MaybeUnused(NestedDeclarator):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"{sub_decl} __attribute__ ((unused))"

    mapper_method = "map_maybe_unused"


class AlignedAttribute(NestedDeclarator):
    """
    Assigns an alignment for a definition of a type or an array.
    """
    def __init__(self, align_bytes: int, subdecl: Declarator) -> None:
        super().__init__(subdecl)
        self.align_bytes = align_bytes

    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"{sub_decl} __attribute__ ((aligned ({self.align_bytes})))"

    mapper_method = "map_aligned"


class AlignValueAttribute(NestedDeclarator):
    """
    Assigns an alignment for value of a pointer.

    This is used for pointers where the user guarantees to the compiler that the
    value of the pointer has the alignment stated. :class:`AlignedAttribute` on
    the other hand tells the compiler to declare the type or the array with the
    given alignment and cannot be used for telling the compiler that an existing
    pointer has a certain alignment guarantee.

    This attribute is currently supported by clang [1]_ and Intel [2]_ and is ignored
    by ``gcc``.

    .. [1] https://reviews.llvm.org/D4635

    .. [2] https://www.intel.com/content/www/us/en/develop/documentation/oneapi-dpcpp-cpp-compiler-dev-guide-and-reference/top/compiler-reference/attributes/align-value.html
    """
    def __init__(self, align_bytes: int, subdecl: Declarator) -> None:
        super().__init__(subdecl)
        self.align_bytes = align_bytes

    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return (sub_tp,
            f"{sub_decl} __attribute__ ((align_value ({self.align_bytes})))")

    mapper_method = "map_align_value"


class Pointer(NestedDeclarator):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*{sub_decl}"

    def struct_maker_code(self, data: str) -> str:
        raise NotImplementedError

    def struct_format(self) -> str:
        return "P"

    def alignment_requirement(self) -> int:
        return int(_struct.calcsize(self.struct_format()))

    mapper_method = "map_pointer"


class RestrictPointer(Pointer):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*__restrict__ {sub_decl}"

    mapper_method = "map_restrict_pointer"


class Reference(Pointer):
    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"&{sub_decl}"

    mapper_method = "map_reference"


class ArrayOf(NestedDeclarator):
    def __init__(self, subdecl: Declarator, count: int | None = None) -> None:
        super().__init__(subdecl)
        self.count = count

    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        if self.count is None:
            count_str = ""
        else:
            count_str = str(self.count)
        return sub_tp, f"{sub_decl}[{count_str}]"

    def struct_maker_code(self, name: str) -> str:
        if self.count is None:
            return name

        return ", ".join(f"{name}[{i}]" for i in range(self.count))

    def struct_format(self) -> str:
        if self.count is None:
            return "P"
        else:
            return f"{self.count}{self.subdecl.struct_format()}"

    def alignment_requirement(self) -> int:
        return self.subdecl.alignment_requirement()

    def default_value(self) -> Any:
        if self.count is None:
            return []

        return self.count*[self.subdecl.default_value()]

    mapper_method = "map_array_of"


class FunctionDeclaration(NestedDeclarator):
    def __init__(self, subdecl: Declarator, arg_decls: Sequence[Declarator]) -> None:
        super().__init__(subdecl)
        self.arg_decls = tuple(arg_decls)

    def get_decl_pair(self) -> DeclPair:
        sub_tp, sub_decl = self.subdecl.get_decl_pair()

        return sub_tp, ("{}({})".format(
            sub_decl,
            ", ".join(ad.inline() for ad in self.arg_decls)))

    def struct_maker_code(self, data: str) -> str:
        raise RuntimeError("function pointers can't be put into structs")

    def struct_format(self) -> str:
        raise RuntimeError("function pointers have no struct format")

    mapper_method = "map_function_declaration"

# }}}


# {{{ struct-like

class Struct(Declarator):
    """A structure declarator."""

    def __init__(self,
                 tpname: str,
                 fields: list[Declarator],
                 declname: str | None = None,
                 pad_bytes: int = 0) -> None:
        """Initialize the structure declarator.
        *tpname* is the name of the structure, while *declname* is the
        name used for the declarator. *pad_bytes* is the number of
        padding bytes added at the end of the structure.
        *fields* is a list of :class:`Declarator` instances.
        """
        self.tpname = tpname
        self.fields = fields
        self.declname = declname
        self.pad_bytes = pad_bytes

    def get_decl_pair(self) -> DeclPair:
        def get_tp() -> Iterator[str]:
            if self.tpname is not None:
                yield f"struct {self.tpname}"
            else:
                yield "struct"

            yield "{"

            for f in self.fields:
                for f_line in f.generate():
                    yield f"  {f_line}"

            if self.pad_bytes:
                yield f"  unsigned char _cgen_pad[{self.pad_bytes}];"

            yield "} " + self.struct_attributes()

        return list(get_tp()), self.declname

    def alignment_requirement(self) -> int:
        return max((f.alignment_requirement() for f in self.fields), default=0)

    def struct_attributes(self) -> str:
        return ""

    mapper_method = "map_struct"


class GenerableStruct(Struct):
    def __init__(self,
                 tpname: str,
                 fields: list[Declarator],
                 declname: str | None = None,
                 align_bytes: int | None = None,
                 aligned_prime_to: list[int] | None = None) -> None:
        """Initialize a structure declarator.

        :arg tpname: the name of the structure.
        :arg declname: the name used for the declarator.
        :arg pad_bytes: the number of padding bytes added at the end of the structure.
        :arg fields: a list of :class:`Declarator` instances.

        :arg align_bytes: an integer that causes the structure to be padded to
            an integer multiple of itself.
        :arg aligned_prime_to: a list of integers. If the resulting structure's
            size is ``s``, then ``s//align_bytes`` will be made prime to all
            numbers in *aligned_prime_to*. (Sounds obscure? It's needed for
            avoiding bank conflicts in CUDA programming.)
        """
        if aligned_prime_to is None:
            aligned_prime_to = []

        format = "".join(f.struct_format() for f in fields)
        bytes = _struct.calcsize(format)

        natural_align_bytes = max(f.alignment_requirement() for f in fields)
        if align_bytes is None:
            align_bytes = natural_align_bytes
        elif align_bytes < natural_align_bytes:
            from warnings import warn
            warn("requested struct alignment smaller than natural alignment",
                 stacklevel=2)

        self.align_bytes = align_bytes

        padded_bytes = ((bytes + align_bytes - 1) // align_bytes) * align_bytes

        def satisfies_primality(n: int) -> bool:
            import math
            for p in aligned_prime_to:
                if math.gcd(n, p) != 1:
                    return False
            return True

        while not satisfies_primality(padded_bytes // align_bytes):
            padded_bytes += align_bytes

        super().__init__(tpname, fields, declname, padded_bytes - bytes)

        if self.pad_bytes:
            self.format = format + f"{self.pad_bytes}x"
            self.bytes = padded_bytes
        else:
            self.format = format
            self.bytes = bytes

        assert _struct.calcsize(self.format) == self.bytes

    # until nvcc bug is fixed
    # def struct_attributes(self):
    #     return "__attribute__ ((packed))"

    def alignment_requirement(self) -> int:
        return self.align_bytes

    def make(self, **kwargs: Any) -> str:
        """Build a binary, packed representation of *self* in a
        :class:`str` instance with members set to the values specified
        in *kwargs*.
        """
        return self._maker()(_struct.pack, **kwargs)

    def make_with_defaults(self, **kwargs: Any) -> str:
        """Build a binary, packed representation of *self* in a
        :class:`str` instance with members set to the values specified
        in *kwargs*.

        Unlike :meth:`make`, not all members have to occur in *kwargs*.
        """
        return self._maker(with_defaults=True)(_struct.pack, **kwargs)

    @memoize_method
    def _maker(self, with_defaults: bool = False) -> Callable[..., str]:
        def format_arg(f: Declarator) -> str:
            # FIXME: should this be narrowed from "Declarator"?
            assert hasattr(f, "name")
            if with_defaults:
                return f"{f.name}={f.default_value()!r}"
            else:
                return str(f.name)

        code = "lambda pack, {}: pack({}, {})".format(
                ", ".join(format_arg(f) for f in self.fields),
                repr(self.struct_format()),
                ", ".join(f.struct_maker_code(f.name) for f in self.fields))  # type: ignore[attr-defined]

        return eval(code)  # type: ignore[no-any-return]

    def struct_format(self) -> str:
        """Return the format of the struct as digested by the :mod:`struct`
        module.
        """
        return self.format

    def __len__(self) -> int:
        """Return the number of bytes occupied by this struct."""
        return int(self.bytes)

    mapper_method = "map_generable_struct"


class Enum(Generable):
    """An enum-like class for Python that can generate an equivalent C-level
    declaration. Does not work within the usual "declarator" framework
    because it uses macros to define values, and a separate typedef to define the
    value type.

    .. versionadded:: 2013.2

    To use, derive from this class, and define the following things:

    .. autoattribute:: c_name
    .. autoattribute:: dtype
    .. autoattribute:: c_value_prefix
    .. attribute:: VALUE

        Any class attribute with an all-upper-case name is taken to be as an
        enum value.
    """

    c_name: ClassVar[str]
    dtype: ClassVar[np.dtype[Any]]
    c_value_prefix: ClassVar[str]
    """A (usually upper-case) prefix to be used as a prefix to the names defined
    on the Python side.
    """

    @classmethod
    def get_flag_names_and_values(cls) -> list[tuple[str, Any]]:
        return [(name, getattr(cls, name))
                for name in sorted(dir(cls))
                if name[0].isupper()]

    @classmethod
    def get_c_defines_lines(cls) -> list[str]:
        return [
                f"#define {cls.c_value_prefix}{flag_name} {value}"
                for flag_name, value in cls.get_flag_names_and_values()]

    @classmethod
    def get_c_defines(cls) -> str:
        """Return a string with C defines corresponding to these constants.
        """

        return "\n".join(cls.get_c_defines_lines())

    @classmethod
    def get_c_typedef_line(cls) -> str:
        """Returns a typedef to define this enum in C."""

        from pyopencl.tools import dtype_to_ctype  # pylint: disable=import-error
        return f"typedef {dtype_to_ctype(cls.dtype)} {cls.c_name};"

    @classmethod
    def get_c_typedef(cls) -> str:
        return f"\n\n{cls.get_c_typedef_line()}\n\n"

    @classmethod
    def generate(cls, with_semicolon: bool = True) -> Iterator[str]:
        yield cls.get_c_typedef_line()
        yield from cls.get_c_defines_lines()

    @classmethod
    def stringify_value(cls, val: Any) -> str:
        """Return a string description of the flags set in *val*."""

        return "|".join(
                flag_name
                for flag_name, flag_value in cls.get_flag_names_and_values()
                if val & flag_value)

# }}}


# {{{ template

class Template(NestedDeclarator):
    def __init__(self, template_spec: str, subdecl: Declarator) -> None:
        self.template_spec = template_spec
        self.subdecl = subdecl

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield f"template <{self.template_spec}>"
        yield from self.subdecl.generate(with_semicolon=with_semicolon)

    mapper_method = "map_template"

# }}}


# {{{ control flow/statement stuff

class If(Generable):
    def __init__(self,
                 condition: str,
                 then_: Generable,
                 else_: Generable | None = None) -> None:
        assert isinstance(then_, Generable)
        if else_ is not None:
            assert isinstance(else_, Generable)

        self.condition = condition
        self.then_ = then_
        self.else_ = else_

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        cond_str = str(self.condition)
        condition_lines = cond_str.split("\n")

        if len(condition_lines) > 1:
            yield "if ("
            for line in condition_lines:
                yield f"    {line}"
            yield "  )"
        else:
            yield f"if ({self.condition})"

        if isinstance(self.then_, Block):
            for line in self.then_.generate():
                yield line
        else:
            for line in self.then_.generate():
                yield f"  {line}"

        if self.else_ is not None:
            yield "else"
            if isinstance(self.else_, Block):
                for line in self.else_.generate():
                    yield line
            else:
                for line in self.else_.generate():
                    yield f"  {line}"

    mapper_method = "map_if"


class Loop(Generable):
    def __init__(self, body: Generable) -> None:
        self.body = body

    def intro_line(self) -> str | None:
        raise NotImplementedError

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        intro_line = self.intro_line()
        if intro_line is not None:
            yield intro_line

        if isinstance(self.body, Block):
            for line in self.body.generate():
                yield line
        else:
            for line in self.body.generate():
                yield f"  {line}"

        outro_line = self.outro_line()  # pylint: disable=assignment-from-none
        if outro_line is not None:
            yield outro_line

    def outro_line(self) -> str | None:
        return None


class CustomLoop(Loop):
    def __init__(self,
                 intro_line: str | None,
                 body: Generable,
                 outro_line: str | None = None) -> None:
        self.intro_line_ = intro_line
        self.body = body
        self.outro_line_ = outro_line

    def intro_line(self) -> str | None:
        return self.intro_line_

    def outro_line(self) -> str | None:
        return self.outro_line_

    mapper_method = "map_custom_loop"


class While(Loop):
    def __init__(self, condition: str, body: Generable) -> None:
        assert isinstance(body, Generable)

        self.condition = condition
        self.body = body

    def intro_line(self) -> str | None:
        return f"while ({self.condition})"

    mapper_method = "map_while"


class For(Loop):
    def __init__(self,
                 start: str, condition: str, update: str,
                 body: Generable) -> None:
        self.start = start
        self.condition = condition
        self.update = update

        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self) -> str | None:
        return f"for ({self.start}; {self.condition}; {self.update})"

    mapper_method = "map_for"


class DoWhile(Loop):
    def __init__(self, condition: str, body: Generable) -> None:
        assert isinstance(body, Generable)

        self.condition = condition
        self.body = body

    def intro_line(self) -> str | None:
        return "do"

    def outro_line(self) -> str | None:
        return f"while ({self.condition});"

    mapper_method = "map_do_while"


def make_multiple_ifs(conditions_and_blocks: Sequence[tuple[str, Generable]],
                      base: str | Generable | None = None) -> Generable | None:
    if base == "last":
        _, base = conditions_and_blocks[-1]
        conditions_and_blocks = conditions_and_blocks[:-1]

    assert not isinstance(base, str)
    for cond, block in conditions_and_blocks[::-1]:
        base = If(cond, block, base)

    return base

# }}}


# {{{ simple statements

class Define(Generable):
    def __init__(self, symbol: str, value: str) -> None:
        self.symbol = symbol
        self.value = value

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield f"#define {self.symbol} {self.value}"

    mapper_method = "map_define"


class Include(Generable):
    def __init__(self, filename: str, system: bool = True) -> None:
        self.filename = filename
        self.system = system

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        if self.system:
            yield f"#include <{self.filename}>"
        else:
            yield f'#include "{self.filename}"'

    mapper_method = "map_include"


class Pragma(Generable):
    def __init__(self, value: str) -> None:
        self.value = value

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield f"#pragma {self.value}"

    mapper_method = "map_pragma"


class Statement(Generable):
    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        sc = ";" if with_semicolon else ""
        yield f"{self.text}{sc}"

    mapper_method = "map_statement"


class ExpressionStatement(Generable):
    def __init__(self, expr: str) -> None:
        self.expr = expr

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        sc = ";" if with_semicolon else ""
        yield f"{self.expr}{sc}"

    mapper_method = "map_expression_statement"


class Assign(Generable):
    def __init__(self, lvalue: str, rvalue: str) -> None:
        self.lvalue = lvalue
        self.rvalue = rvalue

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        sc = ";" if with_semicolon else ""
        yield f"{self.lvalue} = {self.rvalue}{sc}"

    mapper_method = "map_assignment"


class Line(Generable):
    def __init__(self, text: str = "") -> None:
        self.text = text

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield self.text

    mapper_method = "map_line"


class Comment(Generable):
    def __init__(self, text: str, skip_space: bool = False) -> None:
        self.text = text
        if skip_space:
            self.fmt_str = "/*{comment}*/"
        else:
            self.fmt_str = "/* {comment} */"

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield self.fmt_str.format(comment=self.text)

    mapper_method = "map_comment"


class MultilineComment(Generable):
    def __init__(self, text: str, skip_space: bool = False) -> None:
        self.text = text
        self.skip_space = skip_space

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield "/**"

        if self.skip_space:
            line_begin, comment_end = "*", "*/"
        else:
            line_begin, comment_end = " * ", " */"

        for line in self.text.splitlines():
            yield line_begin + line

        yield comment_end

    mapper_method = "map_multiline_comment"


class LineComment(Generable):
    def __init__(self, text: str) -> None:
        assert "\n" not in text
        self.text = text

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield f"// {self.text}"

    mapper_method = "map_line_comment"


def add_comment(comment: str | None, stmt: Generable) -> Generable:
    if comment is None:
        return stmt

    if isinstance(stmt, Block):
        result = Block([Comment(comment), Line()])
        result.extend(stmt.contents)
        return result
    else:
        return Block([Comment(comment), Line(), stmt])

# }}}


# {{{ initializers

class Initializer(Generable):
    def __init__(self, vdecl: Declarator, data: str) -> None:
        self.vdecl = vdecl
        self.data = data

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        tp_lines, tp_decl = self.vdecl.get_decl_pair()
        tp_lines = list(tp_lines)
        yield from tp_lines[:-1]

        sc = ";" if with_semicolon else ""
        if isinstance(self.data, str) and "\n" in self.data:
            data_lines = self.data.split("\n")
            yield f"{tp_lines[-1]} {tp_decl} ="
            for i, line in enumerate(data_lines):
                if i == len(data_lines)-1:
                    yield f"  {line}{sc}"
                else:
                    yield f"  {line}"
        else:
            yield f"{tp_lines[-1]} {tp_decl} = {self.data}{sc}"

    mapper_method = "map_initializer"


class InlineInitializer(Initializer):
    """
    Class to represent Initializers (int i=0) without the semicolon in the end
    (e.g. in a for statement)
    Usage: same as cgen.Initializer
    Result: same as cgen.Initializer except for the lack of a semi-colon at the end
    """
    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        for v in super().generate(with_semicolon=with_semicolon):
            if v.endswith(";"):
                yield v[:-1]
            else:
                yield v


def Constant(vdecl: Declarator, data: str) -> Initializer:  # noqa: N802
    return Initializer(Const(vdecl), data)


class ArrayInitializer(Generable):
    def __init__(self, vdecl: Declarator, data: str) -> None:
        self.vdecl = vdecl
        self.data = data

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        yield from self.vdecl.generate(with_semicolon=False)

        sc = ";" if with_semicolon else ""
        yield "  = { %s }%s" % (", ".join(str(item) for item in self.data), sc)

    mapper_method = "map_array_initializer"


class FunctionBody(Generable):
    # FIXME: fdecl should be a FunctionDeclaration, but loopy uses a light
    # wrapper around it, so we can't specialize at the moment
    def __init__(self, fdecl: NestedDeclarator, body: Block) -> None:
        """Initialize a function definition."""

        self.fdecl = fdecl
        self.body = body

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield from self.fdecl.generate(with_semicolon=False)
        yield from self.body.generate()

    mapper_method = "map_function_body"

# }}}


# {{{ block

class Block(Generable):
    def __init__(self, contents: Sequence[Generable] | None = None) -> None:
        if contents is None:
            contents = []

        if isinstance(contents, Block):
            contents = contents.contents

        self.contents: list[Generable] = list(contents)
        for item in self.contents:
            assert isinstance(item, Generable)

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield f"  {item_line}"
        yield "}"

    def append(self, data: Generable) -> None:
        self.contents.append(data)

    def extend(self, data: Iterable[Generable]) -> None:
        self.contents.extend(data)

    def insert(self, i: int, data: Generable) -> None:
        self.contents.insert(i, data)

    def extend_log_block(self, descr: str, data: Iterable[Generable]) -> None:
        self.contents.append(Comment(descr))
        self.contents.extend(data)
        self.contents.append(Line())

    mapper_method = "map_block"


def block_if_necessary(contents: Sequence[Generable]) -> Generable:
    if len(contents) == 1:
        return contents[0]
    else:
        return Block(contents)


class LiteralLines(Generable):
    def __init__(self, text: str) -> None:
        # accommodate pyopencl syntax highlighting
        if text.startswith("//CL//"):
            text = text[6:]

        if not text.startswith("\n"):
            raise ValueError("expected newline as first character "
                    "in literal lines")

        lines = text.split("\n")
        while lines[0].strip() == "":
            lines.pop(0)
        while lines[-1].strip() == "":
            lines.pop(-1)

        if lines:
            base_indent = 0
            while lines[0][base_indent] in " \t":
                base_indent += 1

            for line in lines[1:]:
                if line[:base_indent].strip():
                    raise ValueError("inconsistent indentation")

        self.lines = [line[base_indent:] for line in lines]

    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield from self.lines

    mapper_method = "map_literal_lines"


class LiteralBlock(LiteralLines):
    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        yield "{"
        for line in self.lines:
            yield f"  {line}"
        yield "}"


class Collection(Block):
    def generate(self, with_semicolon: bool = False) -> Iterator[str]:
        for c in self.contents:
            yield from c.generate()


Module = Collection


class IfDef(Module):
    """Class to represent IfDef-Else-EndIf construct for the C preprocessor."""

    def __init__(self,
                 condition: str,
                 iflines: Iterable[Generable],
                 elselines: Iterable[Generable]) -> None:
        """
        :arg condition: the condition in IfDef.
        :arg iflines: the block of code inside the if.
        :arg elselines: the block of code inside the else.
        """

        iflines = list(iflines)
        elselines = list(elselines)

        ifdef_line = Line(f"#ifdef {condition}")
        if len(elselines):
            elselines.insert(0, Line("#else"))
        endif_line = Line("#endif")
        lines = [ifdef_line, *iflines, *elselines, endif_line]
        super().__init__(lines)

    mapper_method = "map_ifdef"


class IfNDef(Module):
    """
    Class to represent IfNDef-Else-EndIf construct for the C preprocessor.
    :param condition: the condition in IfNDef
    :param ifndeflines: the block of code inside the if not
        [an array of type Generable]
    :param elselines: the block of code inside the else [an array of type Generable]
    """
    def __init__(self,
                 condition: str,
                 ifndeflines: Iterable[Generable],
                 elselines: Iterable[Generable]) -> None:
        ifndeflines = list(ifndeflines)
        elselines = list(elselines)

        ifndefdef_line = Line(f"#ifndef {condition}")
        if len(elselines):
            elselines.insert(0, Line("#else"))
        lines = [ifndefdef_line, *ifndeflines, *elselines, Line("#endif")]
        super().__init__(lines)

    mapper_method = "map_ifndef"


class PrivateNamespace(Block):
    def get_namespace_name(self) -> str:
        import hashlib
        checksum = hashlib.md5()

        for c in self.contents:
            for line in c.generate():
                checksum.update(line.encode("utf-8"))

        return f"private_namespace_{checksum.hexdigest()}"

    def generate(self, with_semicolon: bool = True) -> Iterator[str]:
        name = self.get_namespace_name()

        sc = ";" if with_semicolon else ""
        yield f"namespace {name}"
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield f"  {item_line}"
        yield "}"
        yield ""
        yield f"using namespace {name}{sc}"

# }}}

# vim: fdm=marker
