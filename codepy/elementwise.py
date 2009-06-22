"""Elementwise functionality."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"




from pytools import memoize
import numpy
from codepy.cgen import Value, dtype_to_ctype




class Argument:
    def __init__(self, dtype, name):
        self.dtype = numpy.dtype(dtype)
        self.name = name

    def __repr__(self):
        return "%s(%r, %s)" % (
                self.__class__.__name__,
                self.name,
                self.dtype)

class VectorArg(Argument):
    def declarator(self):
        return Value("numpy_array<%s >" % dtype_to_ctype(self.dtype),
                self.name+"_ary")

    struct_char = "P"

class ScalarArg(Argument):
    def declarator(self):
        return Value(dtype_to_ctype(self.dtype), self.name)

    @property
    def struct_char(self):
        return self.dtype.char




def get_elwise_module(arguments, operation, name="kernel"):
    from codepy.bpl import BoostPythonModule

    from codepy.cgen import FunctionBody, FunctionDeclaration, \
            Value, POD, For, Initializer, Include, Statement, \
            Line, Block

    S = Statement

    mod = BoostPythonModule(max_arity=len(arguments)+1)
    mod.add_to_module([
        Include("pyublas/numpy.hpp"),
        Line(),
        S("namespace ublas = boost::numeric::ublas"),
        S("using namespace pyublas"),
        Line(),
        ])

    body = Block([
        Initializer(
            Value("numpy_array<%s >::iterator"
                % dtype_to_ctype(varg.dtype),
                varg.name),
            varg.name + "_ary.begin()")
        for varg in arguments if isinstance(varg, VectorArg)])

    body.extend([
        Line(),
        For("unsigned i = 0",
            "i < codepy_length",
            "++i",
            Block([S(operation)])
            )
        ])

    mod.add_function(
            FunctionBody(
                FunctionDeclaration(
                    Value("void", name),
                    [POD(numpy.uintp, "codepy_length")] +
                    [arg.declarator() for arg in arguments]),
                body))

    return mod



def get_elwise_kernel(arguments, operation, name="kernel", toolchain=None):
    if toolchain is None:
        from codepy.jit import guess_toolchain
        toolchain = guess_toolchain()

    toolchain = toolchain.copy()

    from codepy.libraries import add_pyublas
    toolchain = toolchain.copy()
    add_pyublas(toolchain)

    return getattr(
            get_elwise_module(arguments, operation, name)
            .compile(toolchain, wait_on_error=True), name)




class ElementwiseKernel:
    def __init__(self, arguments, operation,
            name="kernel", toolchain=None):
        self.arguments = arguments
        self.func = get_elwise_kernel(
                arguments, operation, name, toolchain)

        self.vec_arg_indices = [i for i, arg in enumerate(arguments)
                if isinstance(arg, VectorArg)]

        assert self.vec_arg_indices, \
                "ElementwiseKernel can only be used with functions that have at least one " \
                "vector argument"

    def __call__(self, *args):
        vectors = []

        from pytools import single_valued
        size = single_valued(args[i].size for i in self.vec_arg_indices)

        # no need to do type checking--pyublas does that for us
        self.func(size, *args)




@memoize
def make_linear_comb_kernel_with_result_dtype(
        result_dtype, scalar_dtypes, vector_dtypes):
    comp_count = len(vector_dtypes)
    from pytools import flatten
    return ElementwiseKernel([VectorArg(result_dtype, "result")] + list(flatten(
            (ScalarArg(scalar_dtypes[i], "a%d_fac" % i), 
                VectorArg(vector_dtypes[i], "a%d" % i))
            for i in range(comp_count))),
            "result[i] = " + " + ".join("a%d_fac*a%d[i]" % (i, i) 
                for i in range(comp_count)))




@memoize
def make_linear_comb_kernel(scalar_dtypes, vector_dtypes):
    from pytools import common_dtype
    result_dtype = common_dtype(scalar_dtypes+vector_dtypes)

    return make_linear_comb_kernel_with_result_dtype(
            result_dtype, scalar_dtypes, vector_dtypes), result_dtype





if __name__ == "__main__":
    import pyublas

    a = numpy.random.rand(50000)
    b = numpy.random.rand(50000)

    dtype = a.dtype

    lin_comb = ElementwiseKernel([
            ScalarArg(dtype, "a_fac"), VectorArg(dtype, "a"),
            ScalarArg(dtype, "b_fac"), VectorArg(dtype, "b"),
            VectorArg(dtype, "c"),
            ],
            "c[i] = a_fac*a[i] + b_fac*b[i]")

    c = numpy.empty_like(a)
    lin_comb(5, a, 6, b, c)

    import numpy.linalg as la
    print la.norm(c - (5*a+6*b))
