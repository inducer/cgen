"""Convenience interface for using CodePy with Boost.Python."""




class BoostPythonModule(object):
    def __init__(self, name="module", max_arity=None):
        self.name = name
        self.mod_body = []
        self.init_body = []

        self.max_arity = max_arity

    def add_to_init(self, body):
        """Add the blocks or statements contained in the iterable *body* to the 
        module initialization function.
        """
        self.init_body.extend(body)

    def add_to_module(self, body):
        """Add the :class:`codepy.cgen.Generable` instances in the iterable 
        *body* to the body of the module *self*.
        """

        self.mod_body.extend(body)

    def add_function(self, func):
        """Add a function to be exposed. *func* is expected to be a
        :class:`codepy.cgen.FunctionBody`.
        """

        self.mod_body.append(func)
        from codepy.cgen import Statement
        self.init_body.append(
                Statement(
                    "boost::python::def(\"%s\", &%s)" % (
                        func.fdecl.name, func.fdecl.name)))

    def generate(self):
        """Generate (i.e. yield) the source code of the 
        module line-by-line.
        """

        from codepy.cgen import Block, Module, Include, Line, Define
        body = []

        if self.max_arity is not None:
            body.append(Define("BOOST_PYTHON_MAX_ARITY", self.max_arity))
        
        body += ([Include("boost/python.hpp"), Line()]
                + self.mod_body
                + [Line(), Line("BOOST_PYTHON_MODULE(%s)" % self.name)]
                + [Block(self.init_body)])

        return Module(body)

    def compile(self, toolchain, **kwargs):
        """Return the extension module generated from the code described
        by *self*. If necessary, build the code using *toolchain* with
        :func:`codepy.jit.extension_from_string`. Any keyword arguments
        accept by that latter function may be passed in *kwargs*.
        """

        from codepy.libraries import add_boost_python
        toolchain = toolchain.copy()
        add_boost_python(toolchain)

        from codepy.jit import extension_from_string
        return extension_from_string(toolchain, self.name, 
                str(self.generate())+"\n", **kwargs)

