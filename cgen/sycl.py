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

import numpy as np

from cgen import \
        Declarator, \
        DeclSpecifier, \
        NestedDeclarator, \
        Value,\
        Pointer,\
        Extern,\
NamespaceQualifier,\
    Generable


def dtype_to_cltype(dtype):
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

class SYCLKernel(DeclSpecifier):
    def __init__(self, subdecl,ndim):
        self.ndim=ndim
        subdecl.arg_decls.append(Value("sycl::queue","queue_"))
        subdecl.arg_decls.append(Value("sycl::nd_range<{}> ".format(self.ndim),"range_"))
        DeclSpecifier.__init__(self, subdecl,"")
        

    mapper_method = "map_cl_kernel"

# }}}


# {{{ kernel args

class CLConstant(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__constant")

    mapper_method = "map_cl_constant"


class SYCLLocal(NestedDeclarator):
    def __init__(self, subdecl):
        print(subdecl)
        self.type=subdecl.get_type()
        self.subdecl=subdecl

    def get_decl_pair(self):
        sub_tp,sub_decl=self.subdecl.get_decl_pair()
        return [f"sycl::local_accessor<{self.type}>"],sub_decl
    
    mapper_method = "map_sycl_local"


class CLGlobal(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__global")

    mapper_method = "map_cl_global"


class CLImage(Value):
    def __init__(self, dims, mode, name):
        if mode == "r":
            spec = "__read_only"
        elif mode == "w":
            spec = "__write_only"
        else:
            raise ValueError("mode must be one of 'r' or 'w'")

        Value.__init__(self, f"{spec} image{dims}d_t", name)

    mapper_method = "map_cl_image"

# }}}


# {{{ function attributes

class CLVecTypeHint(NestedDeclarator):
    def __init__(self, subdecl, dtype=None, count=None, type_str=None):
        if (dtype is None) != (count is None):
            raise ValueError("dtype and count must always be "
                    "specified together")

        if (dtype is None and type_str is None) or \
                (dtype is not None and type_str is not None):
            raise ValueError("exactly one of dtype and type_str must be specified")

        if type_str is None:
            self.type_str = dtype_to_cltype(dtype)+str(count)
        else:
            self.type_str = type_str

        super().__init__(subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("__attribute__ ((vec_type_hint({}))) {}".format(
            sub_decl, self.type_str))

    mapper_method = "map_cl_vec_type_hint"


class _SYCLWorkGroupSizeDeclarator(Generable):
    def __init__(self, dim):

        while len(dim) < 3:
            dim = dim + (1,)
        self.dim = dim
        self.decl='extern "C" [[sycl::reqd_work_group_size({})]]'.format(", ".join(str(d) for d in self.dim))

    def generate(self):
        yield self.decl

class CLWorkGroupSizeHint(_SYCLWorkGroupSizeDeclarator):
    """
    See Sec 6.7.2 of OpenCL 2.0 spec, Version V2.2-11.
    """

    mapper_method = "map_cl_workgroup_size_hint"


class SYCLRequiredWorkGroupSize(_SYCLWorkGroupSizeDeclarator):
    """
    See Sec 6.7.2 of OpenCL 2.0 spec, Version V2.2-11.
    """
    mapper_method = "map_cl_required_wokgroup_size"

# }}}


# {{{ vector PODs

class CLVectorPOD(Declarator):
    def __init__(self, dtype, count, name):
        self.dtype = np.dtype(dtype)
        self.count = count
        self.name = name

    def get_decl_pair(self):
        return [dtype_to_cltype(self.dtype)+str(self.count)], self.name

    def struct_maker_code(self, name):
        return name

    def struct_format(self):
        return str(self.count)+self.dtype.char

    def alignment_requirement(self):
        from struct import calcsize
        return calcsize(self.struct_format())

    def default_value(self):
        return [0]*self.count

    mapper_method = "map_cl_vector_pod"

# }}}

# vim: fdm=marker
class SYCLAccessor(NestedDeclarator):
    def __init__(self, subdecl,handler,count=None):
        NestedDeclarator.__init__(self, subdecl)
        self.handler=handler
        self.count=count
        sub_tp, sub_decl = subdecl.get_decl_pair()
        self.type=sub_tp[0]
        self.sub_decl=sub_decl

    def get_decl_pair(self):
        if self.count is None:
            return [f"sycl::accessor<{ self.type}>"], f"{self.sub_decl}({self.handler})"
        else:
            return [f"sycl::accessor<{ self.type}>"], f"{self.sub_decl}(sycl::range<1>({self.count}),{self.handler})"

    def get_type(self):
        return self.type
    mapper_method = "map_sycl_accessor"

    
class SYCLBody(Generable):
    def __init__(self, body,ndim):
        """Initialize a function definition. *fdecl* is expected to be
        a :class:`FunctionDeclaration` instance, while *body* is a
        :class:`Block`.
        """

        self.ndim=ndim
        self.upper = "queue_.submit([&](sycl::handler &h) {"+"\n h.parallel_for(range_, [=](sycl::nd_item<{}>  item)".format(self.ndim)
        self.body = body
        self.lower=");\n }).wait();"

    def generate(self):
        yield self.upper
        yield from self.body.generate()
        yield self.lower

    mapper_method = "map_function_body"
