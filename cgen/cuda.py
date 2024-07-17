__copyright__ = "Copyright (C) 2011-20 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


from cgen import DeclSpecifier, NestedDeclarator, Pointer


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
        return sub_tp, f"*__restrict__ {sub_decl}"

    mapper_method = "map_cuda_restrict_pointer"


class CudaLaunchBounds(NestedDeclarator):
    def __init__(self, max_threads_per_block, subdecl, min_blocks_per_mp=None):
        self.max_threads_per_block = max_threads_per_block
        self.min_blocks_per_mp = min_blocks_per_mp

        super().__init__(subdecl)

    def get_decl_pair(self):
        if self.min_blocks_per_mp is not None:
            lb = f"{self.max_threads_per_block}, {self.min_blocks_per_mp}"
        else:
            lb = f"{self.max_threads_per_block}"

        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, f"__launch_bounds__({lb}) {sub_decl}"

    mapper_method = "map_cuda_launch_bounds"
