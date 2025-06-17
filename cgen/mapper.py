"""Generator for C/C++."""


__copyright__ = "Copyright (C) 2016 Andreas Kloeckner"

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

from typing import Any, Generic, ParamSpec, TypeVar, cast

from typing_extensions import override

import cgen
from cgen import cuda, ispc, opencl as cl


R = TypeVar("R")
P = ParamSpec("P")


class UnsupportedNodeError(ValueError):
    pass


class ASTMapper(Generic[P, R]):
    def __call__(self, node: object, *args: P.args, **kwargs: P.kwargs) -> R:
        """Dispatch *node* to its corresponding mapper method. Pass on
        ``*args`` and ``**kwargs`` unmodified.

        This method is intended as the top-level dispatch entry point and may
        be overridden by subclasses to present a different/more convenient
        interface. :meth:`rec` on the other hand is intended as the recursive
        dispatch method to be used to recurse within mapper method
        implementations.
        """

        try:
            method = getattr(self, node.mapper_method)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
        except AttributeError:
            return self.handle_unsupported(node, *args, **kwargs)

        return cast("R", method(node, *args, **kwargs))

    def handle_unsupported(
            self, node: Any, *args: P.args, **kwargs: P.kwargs) -> R:
        """Mapper method that is invoked for node subclasses for which a mapper
        method does not exist in this mapper.
        """

        raise UnsupportedNodeError(
            f"{type(self)} cannot handle nodes of type {type(node)}")

    def rec(self, node: object, *args: P.args, **kwargs: P.kwargs) -> R:
        return self(node, *args, **kwargs)


class IdentityMapper(ASTMapper[P, cgen.Generable]):
    @override
    def rec(self, node: R, *args: P.args, **kwargs: P.kwargs) -> R:  # pyright: ignore[reportIncompatibleMethodOverride]
        return cast("R", super().rec(node, *args, **kwargs))

    def map_expression(
            self, node: R, *args: P.args, **kwargs: P.kwargs
        ) -> R:
        raise NotImplementedError

    def map_pod(
            self, node: cgen.POD, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.POD:
        return type(node)(node.dtype, node.name)

    def map_value(
            self, node: cgen.Value, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Value:
        return type(node)(node.typename, node.name)

    def map_namespace_qualifier(
            self, node: cgen.NamespaceQualifier, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.NamespaceQualifier:
        return type(node)(node.namespace, self.rec(node.subdecl, *args, **kwargs))

    def map_typedef(
            self, node: cgen.Typedef, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Typedef:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_static(
            self, node: cgen.Static, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Static:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_const(
            self, node: cgen.Const, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Const:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_volatile(
            self, node: cgen.Volatile, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Volatile:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_maybe_unused(
            self, node: cgen.MaybeUnused, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.MaybeUnused:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_pointer(
            self, node: cgen.Pointer, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Pointer:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_restrict_pointer(
            self, node: cgen.RestrictPointer, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.RestrictPointer:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_reference(
            self, node: cgen.Reference, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Reference:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_extern(
            self, node: cgen.Extern, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Extern:
        return type(node)(node.language, self.rec(node.subdecl, *args, **kwargs))

    def map_template_specializer(
            self, node: cgen.TemplateSpecializer, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.TemplateSpecializer:
        return type(node)(node.specializer, self.rec(node.subdecl, *args, **kwargs))

    def map_aligned(
            self, node: cgen.AlignedAttribute, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.AlignedAttribute:
        return type(node)(node.align_bytes, self.rec(node.subdecl, *args, **kwargs))

    def map_array_of(
            self, node: cgen.ArrayOf, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.ArrayOf:
        return type(node)(
                self.rec(node.subdecl, *args, **kwargs),
                self.map_expression(node.count, *args, **kwargs))

    def map_function_declaration(
            self, node: cgen.FunctionDeclaration, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.FunctionDeclaration:
        return type(node)(
                self.rec(node.subdecl, *args, **kwargs),
                tuple(self.rec(sd, *args, **kwargs) for sd in node.arg_decls))

    def map_struct(
            self, node: cgen.Struct, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Struct:
        return type(node)(
                node.tpname,
                tuple(self.rec(f, *args, **kwargs) for f in node.fields),
                node.declname,
                node.pad_bytes)

    def map_generable_struct(
            self, node: cgen.GenerableStruct, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.GenerableStruct:
        return type(node)(
                node.tpname,
                tuple(self.rec(f, *args, **kwargs) for f in node.fields),
                node.declname,
                node.align_bytes,
                node.aligned_prime_to)

    def map_template(
            self, node: cgen.Template, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Template:
        return type(node)(
                node.template_spec,
                self.rec(node.subdecl, *args, **kwargs))

    def map_if(
            self, node: cgen.If, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.If:
        return type(node)(
                self.rec(node.condition, *args, **kwargs)
                if isinstance(node.condition, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.then_, *args, **kwargs),
                self.rec(node.else_, *args, **kwargs)
                if node.else_ is not None
                else None)

    def map_while(
            self, node: cgen.While, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.While:
        return type(node)(
                self.rec(node.condition, *args, **kwargs)
                if isinstance(node.condition, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_for(
            self, node: cgen.For, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.For:
        return type(node)(
                self.rec(node.start, *args, **kwargs)
                if isinstance(node.condition, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.start, *args, **kwargs),
                self.rec(node.condition, *args, **kwargs)
                if isinstance(node.condition, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.update, *args, **kwargs)
                if isinstance(node.update, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.update, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_do_while(
            self, node: cgen.DoWhile, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.DoWhile:
        return type(node)(
                self.rec(node.condition, *args, **kwargs)
                if isinstance(node.condition, cgen.Generable)  # pyright: ignore[reportUnnecessaryIsInstance]
                else self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_define(
            self, node: cgen.Define, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Define:
        return node

    def map_include(
            self, node: cgen.Include, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Include:
        return node

    def map_pragma(
            self, node: cgen.Pragma, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Pragma:
        return node

    def map_statement(
            self, node: cgen.Statement, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Statement:
        return type(node)(node.text)

    def map_expression_statement(
            self, node: cgen.ExpressionStatement, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.ExpressionStatement:
        return type(node)(
                self.map_expression(node.expr, *args, **kwargs))

    def map_assignment(
            self, node: cgen.Assign, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Assign:
        return type(node)(
                self.map_expression(node.lvalue, *args, **kwargs),
                self.map_expression(node.rvalue, *args, **kwargs))

    def map_line(
            self, node: cgen.Line, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Line:
        return node

    def map_comment(
            self, node: cgen.Comment, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Comment:
        return node

    def map_multiline_comment(
            self, node: cgen.MultilineComment, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.MultilineComment:
        return node

    def map_line_comment(
            self, node: cgen.LineComment, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.LineComment:
        return node

    def map_initializer(
            self, node: cgen.Initializer, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Initializer:
        return type(node)(
                self.rec(node.vdecl, *args, **kwargs),
                self.map_expression(node.data, *args, **kwargs))

    def map_array_initializer(
            self, node: cgen.ArrayInitializer, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.ArrayInitializer:
        return type(node)(
                self.rec(node.vdecl, *args, **kwargs),
                tuple(
                    self.map_expression(expr, *args, **kwargs)
                    for expr in node.data))

    def map_function_body(
            self, node: cgen.FunctionBody, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.FunctionBody:
        return type(node)(
                self.rec(node.fdecl, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_block(
            self, node: cgen.Block, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.Block:
        return type(node)(
                tuple(self.rec(c, *args, **kwargs)
                    for c in node.contents))

    def map_literal_lines(
            self, node: cgen.LiteralLines, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.LiteralLines:
        return node

    def map_literal_block(
            self, node: cgen.LiteralBlock, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.LiteralBlock:
        return node

    def map_ifdef(
            self, node: cgen.IfDef, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.IfDef:
        return node

    def map_ifndef(
            self, node: cgen.IfNDef, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.IfNDef:
        return node

    def map_custom_loop(
            self, node: cgen.CustomLoop, *args: P.args, **kwargs: P.kwargs
        ) -> cgen.CustomLoop:
        return type(node)(node.intro_line_,
                          self.rec(node.body, *args, **kwargs),
                          node.outro_line_,
                          )

    # {{{ opencl

    def map_cl_kernel(
            self, node: cl.CLKernel, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLKernel:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cl_constant(
            self, node: cl.CLConstant, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLConstant:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cl_global(
            self, node: cl.CLGlobal, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLGlobal:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cl_local(
            self, node: cl.CLLocal, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLLocal:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cl_image(
            self, node: cl.CLImage, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLImage:
        return node

    def map_cl_vec_type_hint(
            self, node: cl.CLVecTypeHint, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLVecTypeHint:
        return type(node)(
                self.rec(node.subdecl, *args, **kwargs),
                node.dtype, node.count, node.type_str)

    def map_cl_workgroup_size_hint(
            self, node: cl.CLWorkGroupSizeHint, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLWorkGroupSizeHint:
        return type(node)(node.dim, self.rec(node.subdecl, *args, **kwargs))

    def map_cl_required_wokgroup_size(
            self, node: cl.CLRequiredWorkGroupSize, *args: P.args, **kwargs: P.kwargs
        ) -> cl.CLRequiredWorkGroupSize:
        return type(node)(node.dim, self.rec(node.subdecl, *args, **kwargs))

    # }}}

    # {{{ ispc

    def map_ispc_varying(
            self, node: ispc.ISPCVarying, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCVarying:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_uniform(
            self, node: ispc.ISPCUniform, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCUniform:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_export(
            self, node: ispc.ISPCExport, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCExport:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_task(
            self, node: ispc.ISPCTask, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCTask:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_varying_pointer(
            self, node: ispc.ISPCVaryingPointer, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCVaryingPointer:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_uniform_pointer(
            self, node: ispc.ISPCUniformPointer, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCUniformPointer:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_ispc_launch(
            self, node: ispc.ISPCLaunch, *args: P.args, **kwargs: P.kwargs
        ) -> ispc.ISPCLaunch:
        return type(node)(
            tuple(self.map_expression(gs_i, *args, **kwargs) for gs_i in node.grid),
            self.map_expression(node.expr, *args, **kwargs))

    # }}}

    # {{{ cuda

    def map_cuda_global(
            self, node: cuda.CudaGlobal, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaGlobal:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cuda_device(
            self, node: cuda.CudaDevice, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaDevice:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cuda_shared(
            self, node: cuda.CudaShared, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaShared:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cuda_constant(
            self, node: cuda.CudaConstant, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaConstant:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cuda_restrict_pointer(
            self, node: cuda.CudaRestrictPointer, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaRestrictPointer:
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    def map_cuda_launch_bounds(
            self, node: cuda.CudaLaunchBounds, *args: P.args, **kwargs: P.kwargs
        ) -> cuda.CudaLaunchBounds:
        return type(node)(
                node.max_threads_per_block,
                self.rec(node.subdecl, *args, **kwargs),
                node.min_blocks_per_mp)

    # }}}

# vim: foldmethod=marker
