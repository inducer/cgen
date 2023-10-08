"""Generator for C/C++."""


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

from typing import Any

import numpy
from pytools import memoize_method, memoize

try:
    import pycuda._pvt_struct as _struct
except ImportError:
    import struct as _struct


@memoize
def is_long_64_bit():
    return _struct.calcsize("l") == 8


def dtype_to_ctype(dtype):
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = numpy.dtype(dtype)
    if dtype == numpy.int64:
        if is_long_64_bit():
            return "long"
        else:
            return "long long"
    elif dtype == numpy.uint64:
        if is_long_64_bit():
            return "unsigned long"
        else:
            return "unsigned long long"
    elif dtype == numpy.int32:
        return "int"
    elif dtype == numpy.uint32:
        return "unsigned int"
    elif dtype == numpy.int16:
        return "short int"
    elif dtype == numpy.uint16:
        return "short unsigned int"
    elif dtype == numpy.int8:
        return "signed char"
    elif dtype == numpy.uint8:
        return "unsigned char"
    elif dtype == numpy.float32:
        return "float"
    elif dtype == numpy.float64:
        return "double"
    elif dtype == numpy.complex64:
        return "std::complex<float>"
    elif dtype == numpy.complex128:
        return "std::complex<double>"
    elif dtype == numpy.void:
        return "void"
    else:
        raise ValueError(f"unable to map dtype '{dtype}'")


class Generable:
    def __str__(self):
        """Return a single string (possibly containing newlines) representing
        this code construct."""
        return "\n".join(line.rstrip() for line in self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""

        raise NotImplementedError


# {{{ declarators

class Declarator(Generable):
    def generate(self, with_semicolon=True):
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = list(tp_lines)
        yield from tp_lines[:-1]
        sc = ";"
        if not with_semicolon:
            sc = ""
        if tp_decl is None:
            yield f"{tp_lines[-1]}{sc}"
        else:
            yield f"{tp_lines[-1]} {tp_decl}{sc}"

    def get_decl_pair(self):
        """Return a tuple ``(type_lines, rhs)``.

        *type_lines* is a non-empty list of lines (most often just a
        single one) describing the type of this declarator. *rhs* is the right-
        hand side that actually contains the function/array/constness notation
        making up the bulk of the declarator syntax.
        """
        raise NotImplementedError

    def inline(self, with_semicolon=True):
        """Return the declarator as a single line."""
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = " ".join(tp_lines)
        if tp_decl is None:
            return tp_lines
        else:
            return f"{tp_lines} {tp_decl}"


class POD(Declarator):
    """A simple declarator: The type is given as a :class:`numpy.dtype`
    and the *name* is given as a string.
    """

    def __init__(self, dtype, name):
        self.dtype = numpy.dtype(dtype)
        self.name = name

    def get_decl_pair(self):
        return [dtype_to_ctype(self.dtype)], self.name

    def struct_maker_code(self, name):
        return name

    def struct_format(self):
        return self.dtype.char

    def alignment_requirement(self):
        return _struct.calcsize(self.struct_format())

    def default_value(self):
        return 0

    mapper_method = "map_pod"


class Value(Declarator):
    """A simple declarator: *typename* and *name* are given as strings."""

    def __init__(self, typename, name):
        self.typename = typename
        self.name = name

    def get_decl_pair(self):
        return [self.typename], self.name

    def struct_maker_code(self, data):
        raise RuntimeError("named-type values can't be put into structs")

    def struct_format(self):
        raise RuntimeError("named-type values have no struct format")

    def default_value(self):
        return 0

    mapper_method = "map_value"


class NestedDeclarator(Declarator):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    @property
    def name(self):
        return self.subdecl.name

    def struct_format(self):
        return self.subdecl.struct_format()

    def alignment_requirement(self):
        return self.subdecl.alignment_requirement()

    def struct_maker_code(self, data):
        return self.subdecl.struct_maker_code(data)

    def get_decl_pair(self):
        return self.subdecl.get_decl_pair()


class DeclSpecifier(NestedDeclarator):
    def __init__(self, subdecl, spec, sep=" "):
        NestedDeclarator.__init__(self, subdecl)
        self.spec = spec
        self.sep = sep

    def get_decl_pair(self):
        def add_spec(sub_it):
            it = iter(sub_it)
            try:
                yield f"{self.spec}{self.sep}{next(it)}"
            except StopIteration:
                pass

            yield from it

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return add_spec(sub_tp), sub_decl


class NamespaceQualifier(DeclSpecifier):
    def __init__(self, namespace, subdecl):
        DeclSpecifier.__init__(self, subdecl, namespace, "::")

    mapper_method = "map_namespace_qualifier"


class Typedef(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "typedef")

    mapper_method = "map_typedef"


class Static(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "static")

    mapper_method = "map_static"


class Const(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"const {sub_decl}"

    mapper_method = "map_const"


class Volatile(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"volatile {sub_decl}"

    mapper_method = "map_volatile"


class Extern(DeclSpecifier):
    def __init__(self, language, subdecl):
        self.language = language
        super().__init__(subdecl, f'extern "{language}"')

    mapper_method = "map_extern"


class TemplateSpecializer(NestedDeclarator):
    def __init__(self, specializer, subdecl):
        self.specializer = specializer
        NestedDeclarator.__init__(self, subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        sub_tp[-1] = f"{sub_tp[-1]}<{self.specializer}>"
        return sub_tp, sub_decl

    mapper_method = "map_template_specializer"


class MaybeUnused(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"{sub_decl} __attribute__ ((unused))"

    mapper_method = "map_maybe_unused"


class AlignedAttribute(NestedDeclarator):
    """
    Assigns an alignment for a definition of a type or an array.
    """
    def __init__(self, align_bytes, subdecl):
        super().__init__(subdecl)
        self.align_bytes = align_bytes

    def get_decl_pair(self):
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
    This attribute is currently supported by clang [1] and Intel [2] and is ignored
    by gcc.

    [1]: https://reviews.llvm.org/D4635
    [2]: https://www.intel.com/content/www/us/en/develop/documentation/oneapi-dpcpp-cpp-compiler-dev-guide-and-reference/top/compiler-reference/attributes/align-value.html  # noqa: E501
    """
    def __init__(self, align_bytes, subdecl):
        super().__init__(subdecl)
        self.align_bytes = align_bytes

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return (sub_tp,
            f"{sub_decl} __attribute__ ((align_value ({self.align_bytes})))")

    mapper_method = "map_align_value"


class Pointer(NestedDeclarator):
    def __init__(self, subdecl):
        NestedDeclarator.__init__(self, subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*{sub_decl}"

    def struct_maker_code(self, data):
        raise NotImplementedError

    def struct_format(self):
        return "P"

    def alignment_requirement(self):
        return _struct.calcsize(self.struct_format())

    mapper_method = "map_pointer"


class RestrictPointer(Pointer):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"*__restrict__ {sub_decl}"

    mapper_method = "map_restrict_pointer"


class Reference(Pointer):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"&{sub_decl}"

    mapper_method = "map_reference"


class ArrayOf(NestedDeclarator):
    def __init__(self, subdecl, count=None):
        NestedDeclarator.__init__(self, subdecl)
        self.count = count

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        if self.count is None:
            count_str = ""
        else:
            count_str = str(self.count)
        return sub_tp, (f"{sub_decl}[{count_str}]")

    def struct_maker_code(self, name):
        return ", ".join(f"{name}[{i}]" for i in range(self.count))

    def struct_format(self):
        if self.count is None:
            return "P"
        else:
            return f"{self.count}{self.subdecl.struct_format()}"

    def alignment_requirement(self):
        return self.subdecl.alignment_requirement()

    def default_value(self):
        return self.count*[self.subdecl.default_value()]

    mapper_method = "map_array_of"


class FunctionDeclaration(NestedDeclarator):
    def __init__(self, subdecl, arg_decls):
        NestedDeclarator.__init__(self, subdecl)
        self.arg_decls = arg_decls

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()

        return sub_tp, ("{}({})".format(
            sub_decl,
            ", ".join(ad.inline() for ad in self.arg_decls)))

    def struct_maker_code(self, data):
        raise RuntimeError("function pointers can't be put into structs")

    def struct_format(self):
        raise RuntimeError("function pointers have no struct format")

    mapper_method = "map_function_declaration"

# }}}
class Lamda(NestedDeclarator):
    def __init__(self, capture_clause,subdecl ,arg_decls):
        self.capture_clause = capture_clause
        self.arg_decls = arg_decls
        NestedDeclarator.__init__(self, subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"{sub_decl} = [{self.capture_clause}]({'{}'.format(', '.join(ad.inline() for ad in self.arg_decls))})"

    mapper_method = "map_lamda"

# {{{ struct-like

class Struct(Declarator):
    """A structure declarator."""

    def __init__(self, tpname, fields, declname=None, pad_bytes=0):
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

    def get_decl_pair(self):
        def get_tp():
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
        return get_tp(), self.declname

    def alignment_requirement(self):
        return max(f.alignment_requirement() for f in self.fields)

    def struct_attributes(self):
        return ""

    mapper_method = "map_struct"


class GenerableStruct(Struct):
    def __init__(self, tpname, fields, declname=None,
            align_bytes=None, aligned_prime_to=None):
        """Initialize a structure declarator.
        *tpname* is the name of the structure, while *declname* is the
        name used for the declarator. *pad_bytes* is the number of
        padding bytes added at the end of the structure.
        *fields* is a list of :class:`Declarator` instances.

        *align_bytes* is an integer that causes the structure to be
        padded to an integer multiple of itself.
        *aligned_prime_to* is a list of integers.
        If the resulting structure's size
        is ``s``, then ``s//align_bytes`` will be made prime to all
        numbers in *aligned_prime_to*. (Sounds obscure? It's needed
        for avoiding bank conflicts in CUDA programming.)
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
            warn("requested struct alignment smaller than natural alignment")

        self.align_bytes = align_bytes

        padded_bytes = ((bytes + align_bytes - 1) // align_bytes) * align_bytes

        def satisfies_primality(n):
            import math
            for p in aligned_prime_to:
                if math.gcd(n, p) != 1:
                    return False
            return True

        while not satisfies_primality(padded_bytes // align_bytes):
            padded_bytes += align_bytes

        Struct.__init__(self, tpname, fields, declname, padded_bytes - bytes)

        if self.pad_bytes:
            self.format = format + f"{self.pad_bytes}x"
            self.bytes = padded_bytes
        else:
            self.format = format
            self.bytes = bytes

        assert _struct.calcsize(self.format) == self.bytes

    # until nvcc bug is fixed
    #def struct_attributes(self):
        #return "__attribute__ ((packed))"

    def alignment_requirement(self):
        return self.align_bytes

    def make(self, **kwargs):
        """Build a binary, packed representation of *self* in a
        :class:`str` instance with members set to the values specified
        in *kwargs*.
        """
        return self._maker()(_struct.pack, **kwargs)

    def make_with_defaults(self, **kwargs):
        """Build a binary, packed representation of *self* in a
        :class:`str` instance with members set to the values specified
        in *kwargs*.

        Unlike :meth:`make`, not all members have to occur in *kwargs*.
        """
        return self._maker(with_defaults=True)(_struct.pack, **kwargs)

    @memoize_method
    def _maker(self, with_defaults=False):
        def format_arg(f):
            if with_defaults:
                return f"{f.name}={repr(f.default_value())}"
            else:
                return f.name

        code = "lambda pack, {}: pack({}, {})".format(
                ", ".join(format_arg(f) for f in self.fields),
                repr(self.struct_format()),
                ", ".join(f.struct_maker_code(f.name) for f in self.fields))
        return eval(code)

    def struct_format(self):
        """Return the format of the struct as digested by the :mod:`struct`
        module.
        """
        return self.format

    def __len__(self):
        """Return the number of bytes occupied by this struct."""
        return self.bytes

    mapper_method = "map_generable_struct"


class Enum(Generable):
    """An enum-like class for Python that can generate an equivalent C-level
    declaration. Does not work within the usual "declarator" framework
    because it uses macros to define values, and a separate typedef to define the
    value type.

    .. versionadded:: 2013.2

    To use, derive from this class, and define the following things:

    .. attribute:: c_name
    .. attribute:: dtype
    .. attribute:: c_value_prefix

        A (usually upper-case) prefix to be used as a prefix to the names defined
        on the Python side.
    .. attribute:: VALUE

        Any class attribute with an all-upper-case name is taken to be as an
        enum value.
    """

    c_name: str
    dtype: "numpy.dtype[Any]"
    c_value_prefix: str

    @classmethod
    def get_flag_names_and_values(cls):
        return [(name, getattr(cls, name))
                for name in sorted(dir(cls))
                if name[0].isupper()]

    @classmethod
    def get_c_defines_lines(cls):
        return [
                f"#define {cls.c_value_prefix}{flag_name} {value}"
                for flag_name, value in cls.get_flag_names_and_values()]

    @classmethod
    def get_c_defines(cls):
        """Return a string with C defines corresponding to these constants.
        """

        return "\n".join(cls.get_c_defines_lines())

    @classmethod
    def get_c_typedef_line(cls):
        """Returns a typedef to define this enum in C."""

        from pyopencl.tools import dtype_to_ctype   # pylint: disable=import-error
        return f"typedef {dtype_to_ctype(cls.dtype)} {cls.c_name};"

    @classmethod
    def get_c_typedef(cls):
        return f"\n\n{cls.get_c_typedef_line()}\n\n"

    @classmethod
    def generate(cls):
        yield cls.get_c_typedef_line()
        yield from cls.get_c_defines_lines()

    @classmethod
    def stringify_value(cls, val):
        """Return a string description of the flags set in *val*."""

        return "|".join(
                flag_name
                for flag_name, flag_value in cls.get_flag_names_and_values()
                if val & flag_value)

# }}}


# {{{ template

class Template(NestedDeclarator):
    def __init__(self, template_spec, subdecl):
        self.template_spec = template_spec
        self.subdecl = subdecl

    def generate(self, with_semicolon=False):
        yield f"template <{self.template_spec}>"
        yield from self.subdecl.generate(with_semicolon)

    mapper_method = "map_template"

# }}}


# {{{ control flow/statement stuff

class If(Generable):
    def __init__(self, condition, then_, else_=None):
        self.condition = condition

        assert isinstance(then_, Generable)
        if else_ is not None:
            assert isinstance(else_, Generable)

        self.then_ = then_
        self.else_ = else_

    def generate(self):
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
    def __init__(self, body):
        self.body = body

    def intro_line(self):
        raise NotImplementedError

    def generate(self):
        if self.intro_line() is not None:
            yield self.intro_line()

        if isinstance(self.body, Block):
            for line in self.body.generate():
                yield line
        else:
            for line in self.body.generate():
                yield "  "+line

        if self.outro_line() is not None:
            yield self.outro_line()

    def outro_line(self):
        return None


class CustomLoop(Loop):
    def __init__(self, intro_line, body, outro_line=None):
        self.intro_line_ = intro_line
        self.body = body
        self.outro_line_ = outro_line

    def intro_line(self):
        return self.intro_line_

    def outro_line(self):
        return self.outro_line_

    mapper_method = "map_custom_loop"


class While(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return f"while ({self.condition})"

    mapper_method = "map_while"


class For(Loop):
    def __init__(self, start, condition, update, body):
        self.start = start
        self.condition = condition
        self.update = update

        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return f"for ({self.start}; {self.condition}; {self.update})"

    mapper_method = "map_for"


class DoWhile(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return "do"

    def outro_line(self):
        return f"while ({self.condition});"

    mapper_method = "map_do_while"


def make_multiple_ifs(conditions_and_blocks, base=None):
    if base == "last":
        _, base = conditions_and_blocks[-1]
        conditions_and_blocks = conditions_and_blocks[:-1]

    for cond, block in conditions_and_blocks[::-1]:
        base = If(cond, block, base)
    return base

# }}}


# {{{ simple statements

class Define(Generable):
    def __init__(self, symbol, value):
        self.symbol = symbol
        self.value = value

    def generate(self):
        yield f"#define {self.symbol} {self.value}"

    mapper_method = "map_define"


class Include(Generable):
    def __init__(self, filename, system=True):
        self.filename = filename
        self.system = system

    def generate(self):
        if self.system:
            yield f"#include <{self.filename}>"
        else:
            yield f'#include "{self.filename}"'

    mapper_method = "map_include"


class Pragma(Generable):
    def __init__(self, value):
        self.value = value

    def generate(self):
        yield f"#pragma {self.value}"

    mapper_method = "map_pragma"


class Statement(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield self.text+";"

    mapper_method = "map_statement"


class ExpressionStatement(Generable):
    def __init__(self, expr):
        self.expr = expr

    def generate(self):
        yield str(self.expr)+";"

    mapper_method = "map_expression_statement"


class Assign(Generable):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

    def generate(self):
        yield f"{self.lvalue} = {self.rvalue};"

    mapper_method = "map_assignment"


class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text

    mapper_method = "map_line"


class Comment(Generable):
    def __init__(self, text, skip_space=False):
        self.text = text
        if skip_space:
            self.fmt_str = "/*{text}*/"
        else:
            self.fmt_str = "/* {text} */"

    def generate(self):
        yield self.fmt_str.format(text=self.text)

    mapper_method = "map_comment"


class MultilineComment(Generable):
    def __init__(self, text, skip_space=False):
        self.text = text
        self.skip_space = skip_space

    def generate(self):
        yield "/**"
        if self.skip_space is True:
            line_begin, comment_end = "*", "*/"
        else:
            line_begin, comment_end = " * ", " */"
        for line in self.text.splitlines():
            yield line_begin + line
        yield comment_end

    mapper_method = "map_multiline_comment"


class LineComment(Generable):
    def __init__(self, text):
        assert "\n" not in text
        self.text = text

    def generate(self):
        yield f"// {self.text}"

    mapper_method = "map_line_comment"


def add_comment(comment, stmt):
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
    def __init__(self, vdecl, data):
        self.vdecl = vdecl
        self.data = data

    def generate(self):
        tp_lines, tp_decl = self.vdecl.get_decl_pair()
        tp_lines = list(tp_lines)
        yield from tp_lines[:-1]
        if isinstance(self.data, str) and "\n" in self.data:
            data_lines = self.data.split("\n")
            yield f"{tp_lines[-1]} {tp_decl} ="
            for i, l in enumerate(data_lines):
                if i == len(data_lines)-1:
                    yield f"  {l};"
                else:
                    yield f"  {l}"
        else:
            yield f"{tp_lines[-1]} {tp_decl} = {self.data};"

    mapper_method = "map_initializer"


class InlineInitializer(Initializer):
    """
    Class to represent Initializers (int i=0) without the semicolon in the end
    (e.g. in a for statement)
    Usage: same as cgen.Initializer
    Result: same as cgen.Initializer except for the lack of a semi-colon at the end
    """
    def generate(self):
        result = super().generate()
        for v in result:
            if v.endswith(";"):
                yield v[:-1]
            else:
                yield v


def Constant(vdecl, data):  # noqa
    return Initializer(Const(vdecl), data)


class ArrayInitializer(Generable):
    def __init__(self, vdecl, data):
        self.vdecl = vdecl
        self.data = data

    def generate(self):
        yield from self.vdecl.generate(with_semicolon=False)
        yield "  = { %s };" % (", ".join(str(item) for item in self.data))

    mapper_method = "map_array_initializer"


class FunctionBody(Generable):
    def __init__(self, fdecl, body):
        """Initialize a function definition. *fdecl* is expected to be
        a :class:`FunctionDeclaration` instance, while *body* is a
        :class:`Block`.
        """

        self.fdecl = fdecl
        self.body = body

    def generate(self):
        yield from self.fdecl.generate(with_semicolon=False)
        yield from self.body.generate()

    mapper_method = "map_function_body"

# }}}


# {{{ block

class Block(Generable):
    def __init__(self, contents=None):
        if contents is None:
            contents = []
        if isinstance(contents, Block):
            contents = contents.contents
        self.contents = contents[:]

        for item in contents:
            assert isinstance(item, Generable)

    def generate(self):
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield f"  {item_line}"
        yield "}"

    def append(self, data):
        self.contents.append(data)

    def extend(self, data):
        self.contents.extend(data)

    def insert(self, i, data):
        self.contents.insert(i, data)

    def extend_log_block(self, descr, data):
        self.contents.append(Comment(descr))
        self.contents.extend(data)
        self.contents.append(Line())

    mapper_method = "map_block"


def block_if_necessary(contents):
    if len(contents) == 1:
        return contents[0]
    else:
        return Block(contents)


class LiteralLines(Generable):
    def __init__(self, text):
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

    def generate(self):
        yield from self.lines

    mapper_method = "map_literal_lines"


class LiteralBlock(LiteralLines):
    def generate(self):
        yield "{"
        for line in self.lines:
            yield f"  {line}"
        yield "}"


class Collection(Block):
    def generate(self):
        for c in self.contents:
            yield from c.generate()


Module = Collection


class IfDef(Module):
    """
    Class to represent IfDef-Else-EndIf construct for the C preprocessor.
    :param condition: the condition in IfDef
    :param iflines: the block of code inside the if [an array of type Generable]
    :param elselines: the block of code inside the else [an array of type Generable]
    """
    def __init__(self, condition, iflines, elselines):
        ifdef_line = Line(f"#ifdef {condition}")
        if len(elselines):
            elselines.insert(0, Line("#else"))
        endif_line = Line("#endif")
        lines = [ifdef_line]+iflines+elselines+[endif_line]
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
    def __init__(self, condition, ifndeflines, elselines):
        ifndefdef_line = Line(f"#ifndef {condition}")
        if len(elselines):
            elselines.insert(0, Line("#else"))
        lines = [ifndefdef_line]+ifndeflines+elselines+[Line("#endif")]
        super().__init__(lines)

    mapper_method = "map_ifndef"


class PrivateNamespace(Block):
    def get_namespace_name(self):
        try:
            import hashlib
            checksum = hashlib.md5()
        except ImportError:
            # for Python << 2.5
            import md5
            checksum = md5.new()

        for c in self.contents:
            for line in c.generate():
                checksum.update(line.encode("utf-8"))

        return "private_namespace_"+checksum.hexdigest()

    def generate(self):
        yield "namespace "+self.get_namespace_name()
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield f"  {item_line}"
        yield "}"
        yield ""
        yield f"using namespace {self.get_namespace_name()};"

# }}}

# vim: fdm=marker
