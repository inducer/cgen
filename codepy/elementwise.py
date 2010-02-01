"""Elementwise functionality."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Andreas Kloeckner"




from pytools import memoize
import numpy
from codepy.cgen import POD, Value, dtype_to_ctype




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

    def arg_name(self):
        return self.name + "_ary"

    struct_char = "P"

class ScalarArg(Argument):
    def declarator(self):
        return POD(self.dtype, self.name)

    def arg_name(self):
        return self.name

    @property
    def struct_char(self):
        return self.dtype.char




def get_elwise_module_descriptor(arguments, operation, name="kernel"):
    from codepy.bpl import BoostPythonModule

    from codepy.cgen import FunctionBody, FunctionDeclaration, \
            Value, POD, Struct, For, Initializer, Include, Statement, \
            Line, Block

    S = Statement

    mod = BoostPythonModule()
    mod.add_to_preamble([
        Include("pyublas/numpy.hpp"),
        ])

    mod.add_to_module([
        S("namespace ublas = boost::numeric::ublas"),
        S("using namespace pyublas"),
        Line(),
        ])

    body = Block([
        Initializer(
            Value("numpy_array<%s >::iterator"
                % dtype_to_ctype(varg.dtype),
                varg.name),
            "args.%s_ary.begin()" % varg.name)
        for varg in arguments if isinstance(varg, VectorArg)]
        +[Initializer(
            sarg.declarator(), "args." + sarg.name)
        for sarg in arguments if isinstance(sarg, ScalarArg)]
        )

    body.extend([
        Line(),
        For("unsigned i = 0",
            "i < codepy_length",
            "++i",
            Block([S(operation)])
            )
        ])

    arg_struct = Struct("arg_struct", 
            [arg.declarator() for arg in arguments])
    mod.add_struct(arg_struct, "ArgStruct")
    mod.add_to_module([Line()])

    mod.add_function(
            FunctionBody(
                FunctionDeclaration(
                    Value("void", name),
                    [POD(numpy.uintp, "codepy_length"),
                        Value("arg_struct", "args")]),
                body))

    return mod



def get_elwise_module_binary(arguments, operation, name="kernel", toolchain=None):
    if toolchain is None:
        from codepy.toolchain import guess_toolchain
        toolchain = guess_toolchain()

    toolchain = toolchain.copy()

    from codepy.libraries import add_pyublas
    toolchain = toolchain.copy()
    add_pyublas(toolchain)

    return get_elwise_module_descriptor(arguments, operation, name) \
            .compile(toolchain)




def get_elwise_kernel(arguments, operation, name="kernel", toolchain=None):
    return getattr(get_elwise_module_binary(
        arguments, operation, name, toolchain), name)




class ElementwiseKernel:
    def __init__(self, arguments, operation, name="kernel", toolchain=None):
        self.arguments = arguments
        self.module = get_elwise_module_binary(
                arguments, operation, name, toolchain)
        self.func = getattr(self.module, name)

        self.vec_arg_indices = [i for i, arg in enumerate(arguments)
                if isinstance(arg, VectorArg)]

        assert self.vec_arg_indices, \
                "ElementwiseKernel can only be used with functions that have at least one " \
                "vector argument"

    def __call__(self, *args):
        vectors = []
        args = list(args)

        from pytools import single_valued
        size = single_valued(args[i].size for i in self.vec_arg_indices
                if not (isinstance(args[i], (int, float)) and args[i] == 0))
        for i in self.vec_arg_indices:
            if isinstance(args[i], (int, float)) and args[i] == 0:
                args[i] = numpy.zeros(size, dtype=self.arguments[i].dtype)

        # no need to do type checking--pyublas does that for us
        arg_struct = self.module.ArgStruct()
        for arg_descr, arg in zip(self.arguments, args):
            setattr(arg_struct, arg_descr.arg_name(), arg)

        assert not arg_struct.__dict__

        self.func(size, arg_struct)




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
