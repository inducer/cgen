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

from cgen import (
    Block,
    DeclSpecifier,
    FunctionBody,
    Generable,
    Lamda,
    NestedDeclarator,
    Value,
)


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
    def __init__(self, subdecl, ndim, ndrange, queue):
        self.ndim = ndim
        subdecl.arg_decls.append(Value("sycl::queue", queue))
        subdecl.arg_decls.append(
            Value("sycl::nd_range<{}> ".format(self.ndim), ndrange)
        )
        DeclSpecifier.__init__(self, subdecl, "")

    mapper_method = "map_sycl_kernel"


# }}}


# {{{ kernel args


class SYCLConstant(DeclSpecifier):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return [f"sycl::constant_ptr<{sub_tp[0]}>"], sub_decl

    mapper_method = "map_sycl_constant"


class SYCLLocal(NestedDeclarator):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return [f"sycl::local_ptr<{sub_tp[0]}>"], sub_decl

    mapper_method = "map_sycl_local"


class SYCLGlobal(DeclSpecifier):
    def __init__(self, subdecl):
        self.subdecl = subdecl

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return [f"sycl::global_ptr<{sub_tp[0]}>"], sub_decl

    mapper_method = "map_sycl_global"


# TODO sycl Image
class SYCLImage(Value):
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
class _SYCLWorkGroupSizeDeclarator(Generable):
    def __init__(self, dim):

        while len(dim) < 3:
            dim = dim + (1,)
        self.dim = dim
        self.decl = 'extern "C" [[sycl::reqd_work_group_size({})]]'.format(
            ", ".join(str(d) for d in self.dim)
        )

    def generate(self):
        yield self.decl


class SYCLRequiredWorkGroupSize(_SYCLWorkGroupSizeDeclarator):
    mapper_method = "map_SYCL_required_wokgroup_size"


# }}}

# TODO SYCL vector
# {{{ vector PODs

# }}}
class SYCLAccessor(NestedDeclarator):
    def __init__(self, subdecl, handler, count=None):
        NestedDeclarator.__init__(self, subdecl)
        self.handler = handler
        self.count = count
        sub_tp, sub_decl = subdecl.get_decl_pair()
        self.type = sub_tp[0]
        self.sub_decl = sub_decl

    def get_decl_pair(self):
        if self.count is None:
            return [f"sycl::accessor<{ self.type}>"], f"{self.sub_decl}({self.handler})"
        else:
            return [
                f"sycl::accessor<{ self.type}>"
            ], f"{self.sub_decl}(sycl::range<1>({self.count}),{self.handler})"

    def get_type(self):
        return self.type

    mapper_method = "map_sycl_accessor"


class SYCLBody(Generable):
    def __init__(self, body, ndim, handler, nd_item, queue, ndrange):
        self.body = SYCLQueueSubmit(
            Block([SYCLparallel_for(body, ndim, handler, nd_item, ndrange)]),
            handler,
            queue,
        )

    def generate(self):
        yield from self.body.generate()

    mapper_method = "map_SYCL_function_body"


class SYCLparallel_for(Generable):
    def __init__(self, body, ndim, handler, nd_item, ndrange):
        self.handler = handler
        self.args = [
            ndrange,
            FunctionBody(Lamda("=", [Value(f"sycl::nd_item<{ndim}>", nd_item)]), body),
        ]

    def generate(self):
        yield "{}.parallel_for({});".format(
            self.handler, ", ".join(str(ad) for ad in self.args)
        )

    mapper_method = "map_SYCL_parallel_for"


class SYCLQueueSubmit(Generable):
    def __init__(self, body, handler, queue):
        self.queue = queue
        self.args = [
            FunctionBody(Lamda("&", [Value("sycl::handler &", handler)]), body)
        ]

    def generate(self):
        yield "{}.submit({});".format(
            self.queue, ", ".join(str(ad) for ad in self.args)
        )

    mapper_method = "map_SYCL_queue_submit"
