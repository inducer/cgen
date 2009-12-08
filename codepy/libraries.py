"""Configure JIT platforms to link with external libraries."""

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"




from pytools import memoize




# aksetup handling ------------------------------------------------------------
def expand_str(s, options):
    import re

    def my_repl(match):
        sym = match.group(1)
        try:
            repl = options[sym]
        except KeyError:
            from os import environ
            repl = environ[sym]

        return expand_str(repl, options)

    return re.subn(r"\$\{([a-zA-Z0-9_]+)\}", my_repl, s)[0]

def expand_value(v, options):
    if isinstance(v, (str, unicode)):
        return expand_str(v, options)
    elif isinstance(v, list):
        return [expand_value(i, options) for i in v]
    else:
        return v


def expand_options(options):
    for k in options.keys():
        options[k] = expand_value(options[k], options)
    return options




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

    return expand_options(config)




# libraries -------------------------------------------------------------------
def get_boost_compiler(aksetup):
    return aksetup.get("BOOST_COMPILER", "gcc43")




def get_boost_libname(basename, aksetup):
    try:
        return aksetup["BOOST_%s_LIBNAME" % basename.upper()]
    except KeyError:
        return ["boost_%s-%s-mt" % (basename, get_boost_compiler(aksetup))]




def add_boost_python(toolchain):
    aksetup = get_aksetup_config()
    toolchain.add_library(
            "boost-python",
            aksetup["BOOST_INC_DIR"],
            aksetup["BOOST_LIB_DIR"],
            get_boost_libname("python", aksetup)
            )




def add_boost_numeric_bindings(toolchain):
    aksetup = get_aksetup_config()
    toolchain.add_library(
            "boost-numeric-bindings",
            aksetup["BOOST_BINDINGS_INC_DIR"], [], [])




def add_numpy(toolchain):
    def get_numpy_incpath():
        from imp import find_module
        file, pathname, descr = find_module("numpy")
        from os.path import join
        return join(pathname, "core", "include")

    toolchain.add_library("numpy", [get_numpy_incpath()], [], [])




def add_py_module(toolchain, name):
    def get_module_include_path(name):
        from imp import find_module
        file, pathname, descr = find_module(name)

        from os.path import join, exists

        installed_path = join(pathname, "..", "include")
        development_path = join(pathname, "..", "src", "cpp")

        if exists(installed_path):
            return installed_path
        elif exists(development_path):
            return development_path
        else:
            raise RuntimeError("could not find C include path for module '%s'" % name)

    toolchain.add_library(name, [get_module_include_path(name)], [], [])



def add_pyublas(toolchain):
    add_boost_python(toolchain)
    add_numpy(toolchain)
    add_py_module(toolchain, "pyublas")




def add_hedge(toolchain):
    add_pyublas(toolchain)
    add_boost_numeric_bindings(toolchain)
    add_py_module(toolchain, "hedge")


def add_cuda(toolchain):
    aksetup = get_aksetup_config()
    cudaLibPath = aksetup['CUDADRV_LIB_DIR']
    cudaLibrary = aksetup['CUDADRV_LIBNAME']
    cudaIncludePath = aksetup['CUDA_INC_DIR']
    cudaRtPath = aksetup['CUDART_LIB_DIR']
    cudaRtLibrary = aksetup['CUDART_LIBNAME']
    toolchain.add_library('cuda', cudaIncludePath, cudaLibPath + cudaRtPath, cudaLibrary + cudaRtLibrary)
