"""Convenience interface for using CodePy with Boost.Python."""




class BoostPythonModule(object):
    def __init__(self, name="module", max_arity=None,
            use_private_namespace=True):
        self.name = name
        self.preamble = []
        self.mod_body = []
        self.init_body = []

        self.has_codepy_include = False
        self.has_raw_function_include = False
        self.max_arity = max_arity
        self.use_private_namespace = use_private_namespace

    def add_to_init(self, body):
        """Add the blocks or statements contained in the iterable *body* to the
        module initialization function.
        """
        self.init_body.extend(body)

    def add_to_preamble(self, pa):
        self.preamble.extend(pa)

    def add_to_module(self, body):
        """Add the :class:`codepy.cgen.Generable` instances in the iterable
        *body* to the body of the module *self*.
        """

        self.mod_body.extend(body)

    def add_codepy_include(self):
        if self.has_codepy_include:
            return

        from codepy.cgen import Include

        self.add_to_preamble([
            Include("codepy/bpl.hpp")
            ])
        self.has_codepy_include = True

    def add_raw_function_include(self):
        if self.has_raw_function_include:
            return

        from codepy.cgen import Include

        self.add_to_preamble([
            Include("boost/python/raw_function.hpp")
            ])
        self.has_raw_function_include = True                        

    def expose_vector_type(self, name, py_name=None):
        self.add_codepy_include()

        if py_name is None:
            py_name = name

        from codepy.cgen import (Block, Typedef, Line, Statement, Value)

        self.init_body.append(
            Block([
                Typedef(Value(name, "cl")),
                Line(),
                Statement(
                    "boost::python::class_<cl>(\"%s\")"
                    ".def(codepy::no_compare_indexing_suite<cl>())" % py_name),
                ]))

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

    def add_raw_function(self, func):
        """Add a function to be exposed using boost::python::raw_function.
        *func* is expected to be a :class:`codepy.cgen.FunctionBody`.
        """
        self.mod_body.append(func)
        from codepy.cgen import Statement
        self.add_raw_function_include()
        raw_function = "boost::python::raw_function(&%s)" % func.fdecl.name
        self.init_body.append(
            Statement(
                "boost::python::def(\"%s\", %s)" % (
                    func.fdecl.name, raw_function)))
        
    def add_struct(self, struct, py_name=None, py_member_name_transform=lambda x: x,
            by_value_members=set()):
        from codepy.cgen import Block, Line, Statement, Typedef, Value

        if py_name is None:
            py_name = struct.tpname

        self.mod_body.append(struct)

        member_defs = []
        for f in struct.fields:
            py_f_name = py_member_name_transform(f.name)
            tp_lines, declarator = f.get_decl_pair()
            if f.name in by_value_members or tp_lines[0].startswith("numpy_"):
                member_defs.append(".def(pyublas::by_value_rw_member(\"%s\", &cl::%s))"
                        % (py_f_name, f.name))
            else:
                member_defs.append(".def_readwrite(\"%s\", &cl::%s)"
                        % (py_f_name, f.name))

        self.init_body.append(
            Block([
                Typedef(Value(struct.tpname, "cl")),
                Line(),
                Statement(
                    "boost::python::class_<cl>(\"%s\")%s" % (
                        py_name, "".join(member_defs))),
                ]))

    def generate(self):
        """Generate (i.e. yield) the source code of the
        module line-by-line.
        """

        from codepy.cgen import Block, Module, Include, Line, Define, \
                PrivateNamespace

        body = []

        if self.max_arity is not None:
            body.append(Define("BOOST_PYTHON_MAX_ARITY", self.max_arity))

        if self.use_private_namespace:
            mod_body = [PrivateNamespace(self.mod_body)]
        else:
            mod_body = self.mod_body

        body += ([Include("boost/python.hpp")]
                + self.preamble + [Line()]
                + mod_body
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

