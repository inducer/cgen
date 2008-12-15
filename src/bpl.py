"""Convenience interface for using CodePy with Boost.Python."""



class BoostPythonModule(object):
    def __init__(self, name="module", max_arity=None):
        self.name = name
        self.mod_body = []
        self.init_body = []

        self.max_arity = max_arity

    def add_to_init(self, body):
        self.init_body.extend(body)

    def add_to_module(self, body):
        self.mod_body.extend(body)

    def add_function(self, func):
        self.mod_body.append(func)
        from codepy.cgen import Statement
        self.init_body.append(
                Statement(
                    "boost::python::def(\"%s\", &%s)" % (
                        func.fdecl.name, func.fdecl.name)))

    def generate(self):
        from codepy.cgen import Block, Module, Include, Line, Define
        body = []

        if self.max_arity is not None:
            body.append(Define("BOOST_PYTHON_MAX_ARITY", self.max_arity))
        
        body += ([Include("boost/python.hpp"), Line()]
                + self.mod_body
                + [Line(), Line("BOOST_PYTHON_MODULE(%s)" % self.name)]
                + [Block(self.init_body)])

        return Module(body)

    def compile(self, platform, **kwargs):
        from codepy.libraries import add_boost_python
        platform = platform.copy()
        add_boost_python(platform)

        from codepy.jit import extension_from_string
        return extension_from_string(platform, self.name, 
                str(self.generate())+"\n", **kwargs)



