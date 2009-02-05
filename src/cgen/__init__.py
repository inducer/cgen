"""Generator for C/C++."""

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"



import numpy
import numpy.linalg as la
from pytools import memoize_method




def dtype_to_ctype(dtype):
    dtype = numpy.dtype(dtype)
    if dtype == numpy.int32:
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
    elif dtype == numpy.intp or dtype == numpy.uintp:
        return "void *"
    elif dtype == numpy.float32:
        return "float"
    elif dtype == numpy.float64:
        return "double"
    else:
        raise ValueError, "unable to map dtype '%s'" % dtype




class Generable(object):
    def __str__(self):
        """Return a single string (possibly containing newlines) representing this
        code construct."""
        return "\n".join(self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""

        raise NotImplementedError

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
        """Return a tuple ``(typename, rhs)``.

        *typename* is a list of lines (most often just a single one)
        describing the type of this declarator. *rhs* is the right-
        hand side that actually contains the function/array/constness 
        notation making up the bulk of the declarator syntax.
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

    def default_value(self):
        return 0

class Value(Declarator):
    """A simple declarator: *typename* and *name* are given as strings."""
    
    def __init__(self, typename, name):
        self.typename = typename
        self.name = name
        
    def get_decl_pair(self):
        return [self.typename], self.name

    def struct_maker_code(self, data):
        raise RuntimeError, "named-type values can't be put into structs"

    def struct_format(self):
        raise RuntimeError, "named-type values have no struct format"

    def default_value(self):
        return 0




class NestedDeclarator(Declarator):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    @property 
    def name(self):
        return self.subdecl.name

    def struct_format(self):
        return self.subdecl.struct_format()

    def struct_maker_code(self, data):
        return self.subdecl.struct_maker_code(data)

    def get_decl_pair(self):
        return self.subdecl.get_decl_pair()

class DeclSpecifier(NestedDeclarator):
    def __init__(self, subdecl, spec):
        NestedDeclarator.__init__(self, subdecl)
        self.spec = spec

    def get_decl_pair(self):
        def add_spec(sub_it):
            it = iter(sub_it)
            try:
                yield "%s %s" % (self.spec, it.next())
            except StopIteration:
                pass

            for line in it:
                yield line

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return add_spec(sub_tp), sub_decl

class Typedef(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "typedef")

class Static(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "static")

class Const(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("const %s" % sub_decl)

class MaybeUnused(NestedDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("%s __attribute__ ((unused))" % sub_decl)

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

class Reference(Pointer):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("&%s" % sub_decl)

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

    def default_value(self):
        return self.count*[self.subdecl.default_value()]



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
        raise RuntimeError, "function pointers can't be put into structs"

    def struct_format(self):
        raise RuntimeError, "function pointers have no struct format"




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
                yield "  unsigned char _codepy_pad[%d];" % self.pad_bytes
            yield "}"
        return get_tp(), self.declname




class GenerableStruct(Struct):
    def __init__(self, tpname, fields, declname=None,
            align_bytes=1, aligned_prime_to=[]):
        """Initialize a structure declarator.
        *tpname* is the name of the structure, while *declname* is the
        name used for the declarator. *pad_bytes* is the number of
        padding bytes added at the end of the structure.
        *fields* is a list of :class:`Declarator` instances.

        *align_bytes* is an integer that causes the structure to be 
        padded to an integer multiple of itself.
        *aligned_prime_to* is a list of integers. If the resulting structure's size
        is ``s``, then ``s//align_bytes`` will be made prime to all
        numbers in *aligned_prime_to*. (Sounds obscure? It's needed
        for avoiding bank conflicts in CUDA programming.)
        """
        self.tpname = tpname
        self.fields = fields
        self.declname = declname

        format = "".join(f.struct_format() for f in self.fields)
        from struct import calcsize
        bytes = calcsize(format)
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
            self.format = "%s%dx" % (format, self.pad_bytes)
            self.bytes = padded_bytes
        else:
            self.format = format
            self.bytes = bytes

        assert calcsize(self.format) == self.bytes

    def make(self, **kwargs):
        """Build a binary, packed representation of *self* in a 
        :class:`str` instance with members set to the values specified 
        in *kwargs*.
        """
        from struct import pack
        return self._maker()(pack, **kwargs)

    def make_with_defaults(self, **kwargs):
        """Build a binary, packed representation of *self* in a 
        :class:`str` instance with members set to the values specified 
        in *kwargs*.

        Unlike :meth:`make`, not all members have to occur in *kwargs*.
        """
        from struct import pack
        return self._maker(with_defaults=True)(pack, **kwargs)

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
        """Return the format of the struct as digested by the :mod:`struct` module."""
        return self.format

    def __len__(self):
        """Return the number of bytes occupied by this struct."""
        return self.bytes




# template --------------------------------------------------------------------
class Template(NestedDeclarator):
    def __init__(self, template_spec, subdecl):
        self.template_spec = template_spec
        self.subdecl = subdecl

    def generate(self, with_semicolon=False):
        yield "template <%s>" % self.template_spec
        for i in self.subdecl.generate(with_semicolon):
            yield i




# control flow/statement stuff ------------------------------------------------
class If(Generable):
    def __init__(self, condition, then_, else_=None):
        self.condition = condition
        self.then_ = then_
        self.else_ = else_

    def generate(self):
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

class While(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def intro_line(self):
        return "while (%s)" % self.condition

class For(Loop):
    def __init__(self, start, condition, end, body):
        self.start = start
        self.condition = condition
        self.end = end
        self.body = body

    def intro_line(self):
        return "for (%s; %s; %s)" % (self.start, self.condition, self.end)

class DoWhile(Loop):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def intro_line(self):
        return "do"
    def outro_line(self):
        yield "while (%s)" % self.condition

def make_multiple_ifs(conditions_and_blocks, base=None):
    for cond, block in conditions_and_blocks[::-1]:
        base = If(cond, block, base)
    return base




# simple statements -----------------------------------------------------------
class Define(Generable):
    def __init__(self, symbol, value):
        self.symbol = symbol
        self.value = value

    def generate(self):
        yield "#define %s %s" % (self.symbol, self.value)

class Include(Generable):
    def __init__(self, filename, system=True):
        self.filename = filename
        self.system = system

    def generate(self):
        if self.system:
            yield "#include <%s>" % self.filename
        else:
            yield "#include \"%s\"" % self.filename

class Pragma(Generable):
    def __init__(self, value):
        self.value = value

    def generate(self):
        yield "#pragma %s" % (self.value)

class Statement(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield self.text+";"

class Assign(Generable):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue
        self.rvalue = rvalue

    def generate(self):
        yield "%s = %s;" % (self.lvalue, self.rvalue)

class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text

class Comment(Generable):
    def __init__(self, text):
        self.text = text

    def generate(self):
        yield "/* %s */" % self.text



# initializers ----------------------------------------------------------------
class Initializer(Generable):
    def __init__(self, vdecl, data):
        self.vdecl = vdecl
        self.data = data

    def generate(self):
        tp_lines, tp_decl = self.vdecl.get_decl_pair()
        tp_lines = list(tp_lines)
        for line in tp_lines[:-1]:
            yield line
        yield "%s %s = %s;" % (tp_lines[-1], tp_decl, self.data)

def Constant(vdecl, data):
    return Initializer(Const(vdecl), data)

class ArrayInitializer(Generable):
    def __init__(self, vdecl, data):
        self.vdecl = vdecl
        self.data = data

    def generate(self):
        for v_line in self.vdecl.generate(with_semicolon=False):
            yield v_line
        yield "  = { %s };" % (", ".join(str(item) for item in self.data))

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





# block -----------------------------------------------------------------------
class Block(Generable):
    def __init__(self, contents=[]):
        self.contents = contents[:]

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
        
    def extend_log_block(self, descr, data):
        self.contents.append(Comment(descr))
        self.contents.extend(data)
        self.contents.append(Line())
        
class Module(Block):
    def generate(self):
        for c in self.contents:
            for line in c.generate():
                yield line

def _test():
    s = Struct("yuck", [
        POD(numpy.float32, "h", ),
        POD(numpy.float32, "order"),
        POD(numpy.float32, "face_jacobian"),
        ArrayOf(POD(numpy.float32, "normal"), 17),
        POD(numpy.uint16, "a_base"),
        POD(numpy.uint16, "b_base"),
        CudaGlobal(POD(numpy.uint8, "a_ilist_number")),
        POD(numpy.uint8, "b_ilist_number"),
        POD(numpy.uint8, "bdry_flux_number"), # 0 if not on boundary
        POD(numpy.uint8, "reserved"),
        POD(numpy.uint32, "b_global_base"),
        ])
    f_decl = FunctionDeclaration(POD(numpy.uint16, "get_num"), [ 
        POD(numpy.uint8, "reserved"),
        POD(numpy.uint32, "b_global_base"),
        ])
    f_body = FunctionBody(f_decl, Block([
        POD(numpy.uint32, "i"),
        For("i = 0", "i < 17", "++i",
            If("a > b",
                Assign("a", "b"),
                Block([
                    Assign("a", "b-1", "+="),
                    Break(),
                    ])
                ),
            ),
        BlankLine(),
        Comment("all done"),
        ]))
    print s
    print f_body




if __name__ == "__main__":
    _test()
