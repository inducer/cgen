"""Configure JIT platforms to link with external libraries."""

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"




from pytools import memoize




@memoize
def get_aksetup_config():
    def update_config(fname):
        import os
        if os.access(fname, os.R_OK):
            filevars = {}
            execfile(fname, filevars)

            for key, value in filevars.iteritems():
                if key != "__builtins__":
                    config[key] = value

    config = {}
    from os.path import expanduser
    update_config(expanduser("~/.aksetup-defaults.py"))

    import sys
    if not sys.platform.lower().startswith("win"):
        update_config(expanduser("/etc/aksetup-defaults.py"))

    return config




def add_boost_python(platform):
    aksetup = get_aksetup_config()
    platform.add_library(
            "boost-python",
            aksetup["BOOST_INC_DIR"],
            aksetup["BOOST_LIB_DIR"],
            aksetup["BOOST_PYTHON_LIBNAME"],
            )




def add_boost_numeric_bindings(platform):
    aksetup = get_aksetup_config()
    platform.add_library(
            "boost-numeric-bindings",
            aksetup["BOOST_BINDINGS_INC_DIR"], [], [])




def add_numpy(platform):
    def get_numpy_incpath():
        from imp import find_module
        file, pathname, descr = find_module("numpy")
        from os.path import join
        return join(pathname, "core", "include")

    platform.add_library("numpy", [get_numpy_incpath()], [], [])




def add_py_module(platform, name):
    def get_module_include_path(name):
        from imp import find_module
        file, pathname, descr = find_module(name)
        from os.path import join
        return join(pathname, "..", "include")

    platform.add_library(name, [get_module_include_path(name)], [], [])



def add_pyublas(platform):
    add_boost_python(platform)
    add_numpy(platform)
    add_py_module(platform, "pyublas")




def add_hedge(platform):
    add_pyublas(platform)
    add_boost_numeric_bindings(platform)
    add_py_module(platform, "hedge")
