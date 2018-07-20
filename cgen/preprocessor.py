from cgen.infrastructure import Generable, Line, Module


class Define(Generable):
    def __init__(self, symbol, value):
        self.symbol = symbol
        self.value = value

    def generate(self):
        yield "#define %s %s" % (self.symbol, self.value)

    mapper_method = "map_pp_define"


class Include(Generable):
    def __init__(self, filename, system=True):
        self.filename = filename
        self.system = system

    def generate(self):
        if self.system:
            yield "#include <%s>" % self.filename
        else:
            yield "#include \"%s\"" % self.filename

    mapper_method = "map_pp_include"


class Pragma(Generable):
    def __init__(self, value):
        self.value = value

    def generate(self):
        yield "#pragma %s" % (self.value)

    mapper_method = "map_pp_pragma"


class If(Module):
    """Class to represent If-Else-EndIf construct for the C preprocessor.
    """

    def __init__(self, condition, iflines, elselines):
        if_line = Line('#if %s' % condition)
        if len(elselines):
            elselines.insert(0, Line('#else'))
        lines = [if_line] + iflines + elselines + [Line('#endif')]
        super(If, self).__init__(lines)

    mapper_method = "map_pp_if"


class IfDef(Module):
    """Class to represent IfDef-Else-EndIf construct for the C preprocessor.
    """

    def __init__(self, condition, iflines, elselines):
        ifdef_line = Line('#ifdef %s' % condition)
        if len(elselines):
            elselines.insert(0, Line('#else'))
        endif_line = Line('#endif')
        lines = [ifdef_line] + iflines + elselines + [endif_line]
        super(IfDef, self).__init__(lines)

    mapper_method = "map_pp_ifdef"


class IfNDef(Module):
    """Class to represent IfNDef-Else-EndIf construct for the C preprocessor.
    """

    def __init__(self, condition, ifndeflines, elselines):
        ifndefdef_line = Line('#ifndef %s' % condition)
        if len(elselines):
            elselines.insert(0, Line('#else'))
        lines = [ifndefdef_line] + ifndeflines + elselines + [Line('#endif')]
        super(IfNDef, self).__init__(lines)

    mapper_method = "map_pp_ifndef"
