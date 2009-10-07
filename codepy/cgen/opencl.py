from __future__ import division




from codepy.cgen import \
        Declarator, \
        DeclSpecifier, \
        NestedDeclarator, \
        Value




def dtype_to_cltype(dtype):
    if dtype is None:
        raise ValueError("dtype may not be None")

    dtype = numpy.dtype(dtype)
    if dtype == numpy.int64:
        return "long"
    elif dtype == numpy.uint64:
        return "ulong"
    elif dtype == numpy.int32:
        return "int"
    elif dtype == numpy.uint32:
        return "uint"
    elif dtype == numpy.int16:
        return "short"
    elif dtype == numpy.uint16:
        return "ushort"
    elif dtype == numpy.int8:
        return "char"
    elif dtype == numpy.uint8:
        return "uchar"
    elif dtype == numpy.float32:
        return "float"
    elif dtype == numpy.float64:
        return "double"
    else:
        raise ValueError, "unable to map dtype '%s'" % dtype




# kernel ----------------------------------------------------------------------
class CLKernel(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__kernel")




# kernel args -----------------------------------------------------------------
class CLConstant(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__constant")

class CLLocal(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__local")

class CLGlobal(DeclSpecifier):
    def __init__(self, subdecl):
        DeclSpecifier.__init__(self, subdecl, "__global")

class CLImage(Value):
    def __init__(self, dims, mode="r"):
        if mode == "r":
            spec = "__read_only"
        elif mode == "w":
            spec = "__write_only"
        else:
            raise ValueError("mode must be one of 'r' or 'w'")

        Value.__init__(self, "%s image%d_t" % (spec, dims))




# function attributes ---------------------------------------------------------
class CLVecTypeHint(NestedDeclarator):
    def __init__(self, dtype=None, count=None, type_str=None):
        if (dtype is None) != (count is None):
            raise ValueError("dtype and count must always be "
                    "specified together")

        if (dtype is None and type_str is None) or \
                (dtype is not None and type_str is not None):
            raise ValueError("exactly one of dtype and type_str must be specified")

        if dtype is not None:
            type_str = dtype_to_cltype(dtype)+str(count)

    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("__attribute__ ((vec_type_hint(%s))) %s" % (
            sub_decl, type_str))

class _CLWorkGroupSizeDeclarator(NestedDeclarator):
    def __init__(self, dim, subdecl):
        NestedDeclarator.__init__(self, subdecl)

        while len(dim) < 3:
            dim = dim + (1,)

        self.dim = dim

class CLWorkGroupSizeHint(_CLWorkGroupSizeDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("__attribute__ ((work_group_size_hint(%s))) %s" % (
            ", ".join(str(d) for d in self.dim), sub_decl))

class CLRequiredWorkGroupSize(_CLWorkGroupSizeDeclarator):
    def get_decl_pair(self):
        sub_tp, sub_decl = self.subdecl.get_decl_pair()
        return sub_tp, ("__attribute__ ((reqd_work_group_size(%s))) %s" % (
            ", ".join(str(d) for d in self.dim), sub_decl))




# vector PODs -----------------------------------------------------------------
class CLVectorPOD(Declarator):
    def __init__(self, dtype, count, name):
        self.dtype = numpy.dtype(dtype)
        self.count = count
        self.name = name

    def get_decl_pair(self):
        return [dtype_to_cltype(self.dtype)+str(self.count)], self.name

    def struct_maker_code(self, name):
        return name

    def struct_format(self):
        return str(self.count)+self.dtype.char

    def alignment_requirement(self):
        from struct import calcsize
        return calcsize(self.struct_format())

    def default_value(self):
        return [0]*self.count

