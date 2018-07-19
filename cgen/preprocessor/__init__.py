class Generable(object):
    def __str__(self):
        """Return a single string (possibly containing newlines) representing
        this code construct."""
        return "\n".join(l.rstrip() for l in self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""

        raise NotImplementedError


class Block(Generable):
    def __init__(self, contents=[]):
        if (isinstance(contents, Block)):
            contents = contents.contents
        self.contents = contents[:]

        for item in contents:
            assert isinstance(item, Generable)

    def generate(self):
        yield "{"
        for item in self.contents:
            for item_line in item.generate():
                yield "  " + item_line
        yield "}"

    def append(self, data):
        self.contents.append(data)

    def extend(self, data):
        self.contents.extend(data)

    def insert(self, i, data):
        self.contents.insert(i, data)

    def extend_log_block(self, descr, data):
        self.contents.append(Comment(descr))
        self.contents.extend(data)
        self.contents.append(Line())

    mapper_method = "map_block"


class Collection(Block):
    def generate(self):
        for c in self.contents:
            for line in c.generate():
                yield line


class Comment(Generable):
    def __init__(self, text, skip_space=False):
        self.text = text
        if skip_space is False:
            self.fmt_str = "/* %s */"
        else:
            self.fmt_str = "/*%s*/"

    def generate(self):
        yield self.fmt_str % self.text

    mapper_method = "map_comment"


class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text

    mapper_method = "map_line"


Module = Collection


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
