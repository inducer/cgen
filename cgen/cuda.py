from __future__ import division


from cgen import NestedDeclarator, DeclSpecifier, Pointer


class CudaGlobal(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__global__")

    mapper_method = "map_cuda_global"


class CudaDevice(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__device__")

    mapper_method = "map_cuda_device"


class CudaShared(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__shared__")

    mapper_method = "map_cuda_shared"


class CudaConstant(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__constant__")

    mapper_method = "map_cuda_constant"


class CudaRestrictPointer(Pointer):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("*__restrict__ %s" % sub_decl)

    mapper_method = "map_cuda_restrict_pointer"


class CudaLaunchBounds(NestedDeclarator):
    def __init__(self, max_threads_per_block, subdecl, min_blocks_per_mp=None):
        if min_blocks_per_mp is not None:
            self.lb = "%s, %s" % (max_threads_per_block, min_blocks_per_mp)
        else:
            self.lb = "%s" % (max_threads_per_block)

        super(CudaLaunchBounds, self).__init__(subdecl)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, "__launch_bounds__(%s) %s" % (self.lb, sub_decl)

    mapper_method = "map_cuda_launch_bounds"
