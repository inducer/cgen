import codepy.cgen
"""Convenience interface for using CodePy with CUDA"""




class CudaModule(object):
    def __init__(self, boost_module, name="module"):
        """*boost_module* is a codepy.BoostPythonModule containing host code
        which calls CUDA code.
        Current limitations of nvcc preclude compiling anything which
        references Boost by nvcc, so the code needs to be split in two pieces:
        a BoostPythonModule compiled by the host c++ compiler, as well as CUDA
        code which is compiled by nvcc.  This module allows the construction of
        CUDA code to be compiled by nvcc, as well as bridges between the CUDA
        code and the BoostPythonModule.
        """
        self.name = name

        self.preamble = []
        self.body = []
        self.boost_module = boost_module
        self.boost_module.add_to_preamble([codepy.cgen.Include('cuda.h')])

    def add_to_preamble(self, pa):
        self.preamble.extend(pa)

    def add_to_module(self, body):
        """Add the :class:`codepy.cgen.Generable` instances in the iterable
        *body* to the body of the module *self*.
        """
        self.body.extend(body)

    def add_function(self, func):
        """Add a function to be exposed to code in the BoostPythonModule.
        *func* is expected to be a :class:`codepy.cgen.FunctionBody`.
        Additionally, *func* must be a host callable function,
        not a CUDA __global__ entrypoint.
        """
        self.boost_module.add_to_preamble([func.fdecl])
        self.body.append(func)

    def generate(self):
        """Generate (i.e. yield) the source code of the
        module line-by-line.
        """
        body = []
        body += (self.preamble + [codepy.cgen.Line()]
                + self.body)
        return codepy.cgen.Module(body)

    def compile(self, host_toolchain, nvcc_toolchain, host_kwargs={},
                nvcc_kwargs={}, **kwargs):
        """Return the extension module generated from the code described
        by *self*. If necessary, build the code using *toolchain* with
        :func:`codepy.jit.extension_from_string`. Any keyword arguments
        accept by that latter function may be passed in *kwargs*.
        """

        from codepy.libraries import add_boost_python, add_cuda
        host_toolchain = host_toolchain.copy()
        add_boost_python(host_toolchain)
        add_cuda(host_toolchain)

        nvcc_toolchain = nvcc_toolchain.copy()
        add_cuda(nvcc_toolchain)

        host_code = str(self.boost_module.generate()) + "\n"
        device_code = str(self.generate()) + "\n"

        from codepy.jit import compile_from_string, extension_from_string
        from codepy.jit import link_extension

        local_host_kwargs = kwargs.copy()
        local_host_kwargs.update(host_kwargs)
        local_nvcc_kwargs = kwargs.copy()
        local_nvcc_kwargs.update(nvcc_kwargs)

        # Don't compile shared objects, just normal objects
        # (on some platforms, they're different)
        host_mod_name, host_object, host_compiled = compile_from_string(
            host_toolchain, self.boost_module.name, host_code,
            object=True, **local_host_kwargs)
        device_mod_name, device_object, device_compiled = compile_from_string(
            nvcc_toolchain, 'gpu', device_code, 'gpu.cu',
            object=True, **local_nvcc_kwargs)

        if host_compiled or device_compiled:
            return link_extension(host_toolchain,
                                  [host_object, device_object],
                                  host_mod_name, **kwargs)
        else:
            import os.path

            destination_base, first_object = os.path.split(host_object)
            module_path = os.path.join(destination_base, host_mod_name
                                       + host_toolchain.so_ext)
            try:
                from imp import load_dynamic
                return load_dynamic(host_mod_name, module_path)
            except:
                return link_extension(host_toolchain,
                                      [host_object, device_object],
                                      host_mod_name, **kwargs)
