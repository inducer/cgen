import codepy.cgen
"""Convenience interface for using CodePy with CUDA"""




class CudaModule(object):
    def __init__(self, boostModule, name="module"):
        """*boostModule* is a codepy.BoostPythonModule containing host code which
        calls CUDA code.
        Current limitations of nvcc preclude compiling anything which references Boost by
        nvcc, so the code needs to be split in two pieces: a BoostPythonModule compiled
        by the host c++ compiler, as well as CUDA code which is compiled by nvcc.
        This module allows the construction of CUDA code to be compiled by nvcc, as well
        as bridges between the CUDA code and the BoostPythonModule"""
        self.name = name

        self.preamble = []
        self.body = []
        self.boostModule = boostModule
        self.boostModule.add_to_preamble([codepy.cgen.Include('cuda.h')])
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
        not a CUDA __global__ entrypoint."""
        self.boostModule.add_to_preamble([func.fdecl])
        self.body.append(func)
    def generate(self):
        """Generate (i.e. yield) the source code of the
        module line-by-line.
        """

        body = []


        body += (self.preamble + [codepy.cgen.Line()]
                + self.body)
        return codepy.cgen.Module(body)
  
    def compile(self, hostToolchain, nvccToolchain, **kwargs):
        """Return the extension module generated from the code described
        by *self*. If necessary, build the code using *toolchain* with
        :func:`codepy.jit.extension_from_string`. Any keyword arguments
        accept by that latter function may be passed in *kwargs*.
        """

        from codepy.libraries import add_boost_python, add_cuda
        hostToolchain = hostToolchain.copy()
        add_boost_python(hostToolchain)
        add_cuda(hostToolchain)
        
        nvccToolchain = nvccToolchain.copy()
        add_cuda(nvccToolchain)
       
        
        hostCode = str(self.boostModule.generate()) + "\n"
        deviceCode = str(self.generate()) + "\n"
        
        from codepy.jit import compile_from_string, extension_from_string, link_extension
        #Don't compile shared objects, just normal objects (on some platforms, they're different)
        
        
        host_mod_name, host_object, host_compiled = compile_from_string(hostToolchain, self.boostModule.name, hostCode, object=True, **kwargs)  
        device_mod_name, device_object, device_compiled = compile_from_string(nvccToolchain, 'gpu', deviceCode, 'gpu.cu', **kwargs)

       
        if host_compiled or device_compiled:
            return link_extension(hostToolchain, [host_object, device_object], host_mod_name, **kwargs)
        else:
          
            import os.path
            moduleBase, objectExtension = os.path.splitext(host_object)
            moduleName = moduleBase + hostToolchain.so_ext
            try:
                from imp import load_dynamic
                return load_dynamic(host_mod_name, moduleName)
            except:
                return link_extension(hostToolchain, [host_object, device_object], host_mod_name, **kwargs)
