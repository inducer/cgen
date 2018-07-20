class Generable(object):
    def __str__(self):
        """Return a single string (possibly containing newlines) representing
        this code construct."""
        return "\n".join(l.rstrip() for l in self.generate())

    def generate(self, with_semicolon=True):
        """Generate (i.e. yield) the lines making up this code construct."""

        raise NotImplementedError


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


class Line(Generable):
    def __init__(self, text=""):
        self.text = text

    def generate(self):
        yield self.text

    mapper_method = "map_line"


Module = Collection