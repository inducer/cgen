"""Convenience interface for using CodePy with Boost.Python."""



class BoostPythonModule(object):
    def __init__(self, name="module"):
        self.name = name
        self.mod_body = []
        self.init_body = []

    def add_function(self, func):
        self.mod_body.append(func)
        from codepy.cgen import Statement
        self.init_body.append(
                Statement(
                    "boost::python::def(\"%s\", &%s)" % (
                        func.fdecl.name, func.fdecl.name)))

    def generate(self):
        from codepy.cgen import Block, Module, Include, Line
        return Module(
            [Include("boost/python.hpp"), Line()]
            + self.mod_body
            + [Line(), Line("BOOST_PYTHON_MODULE(%s)" % self.name)]
            + [Block(self.init_body)])

    def compile(self, platform, **kwargs):
        from codepy.libraries import add_boost_python
        platform = platform.copy()
        add_boost_python(platform)

        from codepy.jit import extension_from_string
        return extension_from_string(platform, self.name, 
                str(self.generate())+"\n", **kwargs)



