"""Generator for C/C++."""

from __future__ import division, absolute_import, print_function

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


class UnsupportedNodeError(ValueError):
    pass


class ASTMapper(object):
    def __call__(self, node, *args, **kwargs):
        """Dispatch *node* to its corresponding mapper method. Pass on
        ``*args`` and ``**kwargs`` unmodified.

        This method is intended as the top-level dispatch entry point and may
        be overridden by subclasses to present a different/more convenient
        interface. :meth:`rec` on the other hand is intended as the recursive
        dispatch method to be used to recurse within mapper method
        implementations.
        """

        try:
            method = getattr(self, node.mapper_method)
        except AttributeError:
            return self.handle_unsupported(
                    node, *args, **kwargs)

        return method(node, *args, **kwargs)

    def handle_unsupported(self, node, *args, **kwargs):
        """Mapper method that is invoked for node subclasses for which a mapper
        method does not exist in this mapper.
        """

        raise UnsupportedNodeError(
                "%s cannot handle nodes of type %s" % (
                    type(self), type(node)))

    rec = __call__


class IdentityMapper(ASTMapper):
    def map_pod(self, node, *args, **kwargs):
        return type(node)(node.dtype, node.name)

    def map_value(self, node, *args, **kwargs):
        return type(node)(node.typename, node.name)

    def map_namespace_qualifier(self, node, *args, **kwargs):
        return type(node)(node.namespace, self.rec(node.subdecl, *args, **kwargs))

    def map_typedef(self, node, *args, **kwargs):
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    map_static = map_typedef
    map_const = map_typedef

    def map_extern(self, node, *args, **kwargs):
        return type(node)(node.language, self.rec(node.subdecl, *args, **kwargs))

    def map_template_specializer(self, node, *args, **kwargs):
        return type(node)(node.specializer, self.rec(node.subdecl, *args, **kwargs))

    map_maybe_unused = map_typedef

    def map_aligned(self, node, *args, **kwargs):
        return type(node)(node.align_bytes, self.rec(node.subdecl, *args, **kwargs))

    map_pointer = map_typedef
    map_restrict_pointer = map_typedef
    map_reference = map_typedef

    def map_array_of(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.subdecl, *args, **kwargs),
                self.map_expression(node.count, *args, **kwargs))

    def map_function_declaration(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.subdecl),
                tuple(self.rec(sd, *args, **kwargs) for sd in node.arg_decls))

    def map_struct(self, node, *args, **kwargs):
        return type(node)(
                node.tpname,
                tuple(self.rec(f, *args, **kwargs) for f in node.fields),
                node.declname,
                node.pad_bytes)

    def map_generable_struct(self, node, *args, **kwargs):
        return type(node)(
                node.tpname,
                tuple(self.rec(f, *args, **kwargs) for f in node.fields),
                node.declname,
                node.align_bytes,
                node.aligned_prime_to)

    def map_template(self, node, *args, **kwargs):
        return type(node)(
                node.template_spec,
                self.rec(node.sub_decl, *args, **kwargs))

    def map_if(self, node, *args, **kwargs):
        return type(node)(
                self.map_expression(node.condition),
                self.rec(node.then_, *args, **kwargs),
                self.rec(node.else_, *args, **kwargs)
                if node.else_ is not None
                else None)

    def map_while(self, node, *args, **kwargs):
        return type(node)(
                self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_for(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.start, *args, **kwargs),
                self.map_expression(node.condition, *args, **kwargs),
                self.map_expression(node.update, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_do_while(self, node, *args, **kwargs):
        return type(node)(
                self.map_expression(node.condition, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_define(self, node, *args, **kwargs):
        return node

    def map_include(self, node, *args, **kwargs):
        return node

    def map_pragma(self, node, *args, **kwargs):
        return node

    def map_statement(self, node, *args, **kwargs):
        return type(node)(node.text)

    def map_expression_statement(self, node, *args, **kwargs):
        return type(node)(
                self.map_expression(node.expr, *args, **kwargs))

    def map_assignment(self, node, *args, **kwargs):
        return type(node)(
                self.map_expression(node.lvalue, *args, **kwargs),
                self.map_expression(node.rvalue, *args, **kwargs))

    def map_line(self, node, *args, **kwargs):
        return node

    def map_comment(self, node, *args, **kwargs):
        return node

    def map_line_comment(self, node, *args, **kwargs):
        return node

    def map_initializer(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.vdecl, *args, **kwargs),
                self.map_expression(node.data, *args, **kwargs))

    def map_array_initializer(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.vdecl, *args, **kwargs),
                tuple(
                    self.map_expression(expr, *args, **kwargs)
                    for expr in node.data))

    def map_function_body(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.fdecl, *args, **kwargs),
                self.rec(node.body, *args, **kwargs))

    def map_block(self, node, *args, **kwargs):
        return type(node)(
                tuple(self.rec(c, *args, **kwargs)
                    for c in node.contents))

    def map_literal_lines(self, node, *args, **kwargs):
        return node

    def map_literal_block(self, node, *args, **kwargs):
        return type(node)()

    def map_ifdef(self, node, *args, **kwargs):
        return node

    def map_custom_loop(self, node, *args, **kwargs):
        return type(node)(node.intro_line_,
                          self.rec(node.body, *args, **kwargs),
                          node.outro_line_,
                          )

    # {{{ opencl

    map_cl_kernel = map_typedef
    map_cl_constant = map_typedef
    map_cl_global = map_typedef
    map_cl_local = map_typedef

    def map_cl_image(self, node, *args, **kwargs):
        return node

    def map_cl_vec_type_hint(self, node, *args, **kwargs):
        return type(node)(
                self.rec(node.subdecl, *args, **kwargs),
                node.dtype, node.count, node.type_str)

    def map_cl_workgroup_size_declarator(self, node, *args, **kwargs):
        return type(node)(
                node.dim, self.rec(node.subdecl, *args, **kwargs))

    map_cl_workgroup_size_hint = map_cl_workgroup_size_declarator
    map_cl_required_wokgroup_size = map_cl_workgroup_size_declarator

    # }}}

    # {{{ ispc

    def map_ispc_varying(self, node, *args, **kwargs):
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    map_ispc_uniform = map_ispc_varying
    map_ispc_export = map_ispc_varying
    map_ispc_task = map_ispc_varying
    map_ispc_varying_pointer = map_ispc_varying
    map_ispc_uniform_pointer = map_ispc_varying

    def map_ispc_launch(self, node, *args, **kwargs):
        return type(node)(
                tuple(self.map_expression(gs_i, *args, **kwargs)
                    for gs_i in node.grid),
                self.map_expression(node.expr, *args, **kwargs))

    # }}}

    # {{{ cuda

    def map_cuda_global(self, node, *args, **kwargs):
        return type(node)(self.rec(node.subdecl, *args, **kwargs))

    map_cuda_device = map_cuda_global
    map_cuda_shared = map_cuda_global
    map_cuda_constant = map_cuda_global
    map_cuda_restrict_pointer = map_cuda_global

    def map_cuda_launch_bounds(self, node, *args, **kwargs):
        return type(node)(
                node.max_threads_per_block,
                self.rec(node.subdecl, *args, **kwargs),
                node.min_blocks_per_mp)

    # }}}

# vim: foldmethod=marker
