"""Generator for C/C++."""

from __future__ import division, absolute_import, print_function

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

import numpy
from pytools import memoize_method, memoize

try:
    import pycuda._pvt_struct as _struct
except ImportError:
    import struct as _struct


@memoize
def is_64_bit_platform():
    return _struct.calcsize('l') == 8


def dtype_to_ctype(dtype):
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = numpy.dtype(dtype)
    if dtype == numpy.int64 and is_64_bit_platform():
        return "long"
    elif dtype == numpy.uint64 and is_64_bit_platform():
        return "unsigned long"
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
    else:
        raise ValueError("unable to map dtype '%s'" % dtype)


class Generable(object):
    def __str__(self):
        """Return a single string (possibly containing newlines) representing
        this code construct."""
        return "\n".join(l.rstrip() for l in self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""

        raise NotImplementedError


# {{{ declarators

class Declarator(Generable):
    def generate(self, with_semicolon=True):
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = list(tp_lines)
        for line in tp_lines[:-1]:
            yield line
        sc = ";"
        if not with_semicolon:
            sc = ""
        if tp_decl is None:
            yield "%s%s" % (tp_lines[-1], sc)
        else:
            yield "%s %s%s" % (tp_lines[-1], tp_decl, sc)

    def get_decl_pair(self):
        """Return a tuple ``(type_lines, rhs)``.

        *type_lines* is a non-empty list of lines (most often just a
        single one) describing the type of this declarator. *rhs* is the right-
        hand side that actually contains the function/array/constness notation
        making up the bulk of the declarator syntax.
        """

    def inline(self, with_semicolon=True):
        """Return the declarator as a single line."""
        tp_lines, tp_decl = self.get_decl_pair()
        tp_lines = " ".join(tp_lines)
        if tp_decl is None:
            return tp_lines
        else:
            return "%s %s" % (tp_lines, tp_decl)


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
    def __init__(self, subdecl, spec, sep=' '):
        NestedDeclarator.__init__(self, subdecl)
        self.spec = spec
        self.sep = sep

    def get_decl_pair(self):
        def add_spec(sub_it):
            it = iter(sub_it)
            try:
                yield "%s%s%s" % (self.spec, self.sep, next(it))
            except StopIteration:
                pass

            for line in it:
                yield line

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return add_spec(sub_tp), sub_decl


class NamespaceQualifier(DeclSpecifier):
    def __init__(self, namespace, subdecl):
        DeclSpecifier.__init__(self, subdecl, namespace, '::')

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
        return sub_tp, ("const %s" % sub_decl)

    mapper_method = "map_const"


class Extern(DeclSpecifier):
    def __init__(self, language, subdecl):
        self.language = language
        super(Extern, self).__init__(subdecl, "extern \"%s\"" % language)

    mapper_method = "map_extern"


class TemplateSpecializer(NestedDeclarator):
    def __init__(self, specializer, subdecl):
        self.specializer = specializer
        NestedDeclarator.__init__(self, subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        sub_tp[-1] = sub_tp[-1] + '<%s>' % self.specializer
        return sub_tp, sub_decl

    mapper_method = "map_template_specializer"


class MaybeUnused(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("%s __attribute__ ((unused))" % sub_decl)

    mapper_method = "map_maybe_unused"


class AlignedAttribute(NestedDeclarator):
    def __init__(self, align_bytes, subdecl):
        super(AlignedAttribute, self).__init__(subdecl)
        self.align_bytes = align_bytes

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("%s __attribute__ ((aligned (%d)))"
                % (sub_decl, self.align_bytes))

    mapper_method = "map_aligned"


class Pointer(NestedDeclarator):
    def __init__(self, subdecl):
        NestedDeclarator.__init__(self, subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("*%s" % sub_decl)

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
        return sub_tp, ("*restrict %s" % sub_decl)

    mapper_method = "map_restrict_pointer"


class Reference(Pointer):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("&%s" % sub_decl)

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
        return sub_tp, ("%s[%s]" % (sub_decl, count_str))

    def struct_maker_code(self, name):
        return ", ".join("%s[%d]" % (name, i) for i in range(self.count))

    def struct_format(self):
        if self.count is None:
            return "P"
        else:
            return "%d%s" % (self.count, self.subdecl.struct_format())

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

        return sub_tp, ("%s(%s)" % (
            sub_decl,
            ", ".join(ad.inline() for ad in self.arg_decls)))

    def struct_maker_code(self, data):
        raise RuntimeError("function pointers can't be put into structs")

    def struct_format(self):
        raise RuntimeError("function pointers have no struct format")

    mapper_method = "map_function_declaration"

# }}}


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
                yield "struct %s" % self.tpname
            else:
                yield "struct"
            yield "{"
            for f in self.fields:
                for f_line in f.generate():
                    yield "  " + f_line
            if self.pad_bytes:
                yield "  unsigned char _cgen_pad[%d];" % self.pad_bytes
            yield "} " + self.struct_attributes()
        return get_tp(), self.declname

    def alignment_requirement(self):
        return max(f.alignment_requirement() for f in self.fields)

    def struct_attributes(self):
        return ""

    mapper_method = "map_struct"


class GenerableStruct(Struct):
    def __init__(self, tpname, fields, declname=None,
            align_bytes=None, aligned_prime_to=[]):
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
            from pymbolic.algorithm import gcd
            for p in aligned_prime_to:
                if gcd(n, p) != 1:
                    return False
            return True

        while not satisfies_primality(padded_bytes // align_bytes):
            padded_bytes += align_bytes

        Struct.__init__(self, tpname, fields, declname, padded_bytes - bytes)

        if self.pad_bytes:
            self.format = format + "%dx" % self.pad_bytes
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
                return "%s=%s" % (f.name, repr(f.default_value()))
            else:
                return f.name

        code = "lambda pack, %s: pack(%s, %s)" % (
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
    declaration. Does not work within the usual 'declarator' framework
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

    @classmethod
    def get_flag_names_and_values(cls):
        return [(name, getattr(cls, name))
                for name in sorted(dir(cls))
                if name[0].isupper()]

    @classmethod
    def get_c_defines_lines(cls):
        return [
                "#define %s%s %d" % (cls.c_value_prefix, flag_name, value)
                for flag_name, value in cls.get_flag_names_and_values()]

    @classmethod
    def get_c_defines(cls):
        """Return a string with C defines corresponding to these constants.
        """

        return "\n".join(cls.get_c_defines_lines())

    @classmethod
    def get_c_typedef_line(cls):
        """Returns a typedef to define this enum in C."""

        from pyopencl.tools import dtype_to_ctype
        return "typedef %s %s;" % (dtype_to_ctype(cls.dtype), cls.c_name)

    @classmethod
    def get_c_typedef(cls):
        return "\n\n%s\n\n" % cls.get_c_typedef_line()

    @classmethod
    def generate(cls):
        yield cls.get_c_typedef_line()
        for l in cls.get_c_defines_lines():
            yield l

    @classmethod
    def stringify_value(cls, val):
        "Return a string description of the flags set in *val*."

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
        yield "template <%s>" % self.template_spec
        for i in self.subdecl.generate(with_semicolon):
            yield i

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
            for l in condition_lines:
                yield "    "+l
            yield "  )"
        else:
            yield "if (%s)" % self.condition

        if isinstance(self.then_, Block):
            for line in self.then_.generate():
                yield line
        else:
            for line in self.then_.generate():
                yield "  "+line

        if self.else_ is not None:
            yield "else"
            if isinstance(self.else_, Block):
                for line in self.else_.generate():
                    yield line
            else:
                for line in self.else_.generate():
                    yield "  "+line

    mapper_method = "map_if"


class Loop(Generable):
    def __init__(self, body):
        self.body = body

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
        return "while (%s)" % self.condition

    mapper_method = "map_while"


class For(Loop):
    def __init__(self, start, condition, update, body):
        self.start = start
        self.condition = condition
        self.update = update

        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return "for (%s; %s; %s)" % (self.start, self.condition, self.update)

    mapper_method = "map_for"


class DoWhile(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        assert isinstance(body, Generable)
        self.body = body

    def intro_line(self):
        return "do"

    def outro_line(self):
        return "while (%s);" % self.condition

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
        yield "#define %s %s" % (self.symbol, self.value)

    mapper_method = "map_define"


class Include(Generable):
    def __init__(self, filename, system=True):
        self.filename = filename
        self.system = system

    def generate(self):
        if self.system:
            yield "#include <%s>" % self.filename
        else:
            yield "#include \"%s\"" % self.filename

    mapper_method = "map_include"


class Pragma(Generable):
    def __init__(self, value):
        self.value = value

    def generate(self):
        yield "#pragma %s" % (self.value)

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
        yield "%s = %s;" % (self.lvalue, self.rvalue)

    mapper_method = "map_assignment"


class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text

    mapper_method = "map_line"


class Comment(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield "/* %s */" % self.text

    mapper_method = "map_comment"


class LineComment(Generable):
    def __init__(self, text):
        assert "\n" not in text
        self.text = text

    def generate(self):
        yield "// %s" % self.text

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
        for line in tp_lines[:-1]:
            yield line
        if isinstance(self.data, str) and "\n" in self.data:
            data_lines = self.data.split("\n")
            yield "%s %s =" % (tp_lines[-1], tp_decl)
            for i, l in enumerate(data_lines):
                if i == len(data_lines)-1:
                    yield "  %s;" % l
                else:
                    yield "  %s" % l
        else:
            yield "%s %s = %s;" % (tp_lines[-1], tp_decl, self.data)

    mapper_method = "map_initializer"


class InlineInitializer(Initializer):
    """
    Class to represent Initializers (int i=0) without the semicolon in the end
    (e.g. in a for statement)
    Usage: same as cgen.Initializer
    Result: same as cgen.Initializer except for the lack of a semi-colon at the end
    """
    def generate(self):
        result = super(InlineInitializer, self).generate()
        for v in result:
            if v.endswith(';'):
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
        for v_line in self.vdecl.generate(with_semicolon=False):
            yield v_line
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
        for f_line in self.fdecl.generate(with_semicolon=False):
            yield f_line
        for b_line in self.body.generate():
            yield b_line

    mapper_method = "map_function_body"

# }}}


# {{{ block

class Block(Generable):
    def __init__(self, contents=[]):
        if(isinstance(contents, Block)):
            contents = contents.contents
        self.contents = contents[:]

        for item in contents:
            assert isinstance(item, Generable)

    def generate(self):
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield "  " + item_line
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
        text = text.lstrip("//CL//")

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
        for line in self.lines:
            yield line

    mapper_method = "map_literal_lines"


class LiteralBlock(LiteralLines):
    def generate(self):
        yield "{"
        for line in self.lines:
            yield "  " + line
        yield "}"


class Collection(Block):
    def generate(self):
        for c in self.contents:
            for line in c.generate():
                yield line


Module = Collection


class IfDef(Module):
    """
    Class to represent IfDef-Else-EndIf construct for the C preprocessor.
    :param condition: the condition in IfDef
    :param iflines: the block of code inside the if [an array of type Generable]
    :param elselines: the block of code inside the else [an array of type Generable]
    """
    def __init__(self, condition, iflines, elselines):
        ifdef_line = Line('#ifdef %s' % condition)
        else_line = Line('#else')
        endif_line = Line('#endif')
        lines = [ifdef_line]+iflines+[else_line]+elselines+[endif_line]
        super(IfDef, self).__init__(lines)

    mapper_method = "map_ifdef"


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
                checksum.update(line.encode('utf-8'))

        return "private_namespace_"+checksum.hexdigest()

    def generate(self):
        yield "namespace "+self.get_namespace_name()
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield "  " + item_line
        yield "}"
        yield ""
        yield "using namespace %s;" % self.get_namespace_name()

# }}}

# vim: fdm=marker
