from __future__ import division


from cgen import DeclSpecifier


class CudaGlobal(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__global__")


class CudaDevice(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__device__")


class CudaShared(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__shared__")


class CudaConstant(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__constant__")


class CudaLaunchBounds(DeclSpecifier):
    def __init__(self, max_threads_per_block, subdecl, min_blocks_per_mp=None):
        if min_blocks_per_mp is not None:
            lb = "%s, %s" % (max_threads_per_block, min_blocks_per_mp)
        else:
            lb = "%s" % (max_threads_per_block)            

        DeclSpecifier.__init__(self, subdecl, "__launch_bounds__(%s)" % (lb,))
