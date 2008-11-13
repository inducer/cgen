"""Just-in-time Python extension compilation."""

from __future__ import division

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"




class CompileError(Exception):
    pass




def join_continued_lines(lines):
    result = []
    it = iter(lines)
    append_line = False
    try:
        while True:
            line = it.next().rstrip("\n")
            append_next_line = line.endswith("\\")
            if append_next_line:
                line = line[:-1]

            if append_line:
                result[-1] += line
            else:
                result.append(line)
            append_line = append_next_line
    except StopIteration:
        if append_line:
            from warnings import warn
            warn("line continuation at end of file")

    return result




def parse_makefile(lines):
    lines = join_continued_lines(lines)

    import re
    assign_re = re.compile("^([_a-zA-Z0-9]+)\s*=(.*)$")
    expand_re = re.compile(r"\$(\(([_a-zA-Z0-9]+)\)|\{([a-zA-Z0-9]+)\})")

    def expand(s):
        def get_replacement(match):
            return result.get(match.group(2) or match.group(3), "")

        new_s = expand_re.sub(get_replacement, s)
        if new_s != s:
            return expand(new_s)
        else:
            return s

    result = {}

    for l in lines:
        assign_match = assign_re.match(l)
        if assign_match is not None:
            result[assign_match.group(1)] = assign_match.group(2).strip()

    for k in result.keys():
        result[k] = expand(result[k])

    return result




def parse_python_makefile():
    import sys
    from os.path import join
    py_makefile = join(
            sys.prefix,
            "lib",
            "python%d.%d" % (sys.version_info[0], sys.version_info[1]),
            "config",
            "Makefile")
    return parse_makefile(open(py_makefile, "r").readlines())



    
from pytools import Record
class Platform(Record):
    def __init__(self, *args, **kwargs):
        Record.__init__(self, *args, **kwargs)
        self.features = set()

    def abi_id(self):
        import sys
        return [self.get_version(), sys.version]

    def add_library(self, feature, include_dirs, library_dirs, libraries):
        if feature in self.features:
            return

        self.features.add(feature)

        for idir in include_dirs:
            if not idir in self.include_dirs:
                self.include_dirs.append(idir)

        for ldir in library_dirs:
            if not ldir in self.library_dirs:
                self.library_dirs.append(ldir)

        self.libraries = libraries + self.libraries

        


class GCCPlatform(Platform):
    def get_version(self):
        from subprocess import Popen, PIPE
        return Popen([self.cc, "--version"], 
                stdout=PIPE).communicate()[0]

    def _cmdline(self):
        return (
                [self.cc] 
                + self.cflags 
                + self.ldflags 
                + ["-I%s" % idir for idir in self.include_dirs]
                + ["-L%s" % ldir for ldir in self.library_dirs]
                + ["-l%s" % lib for lib in self.libraries]
                )

    def abi_id(self):
        return Platform.abi_id(self) + [self._cmdline()]

    def build_extension(self, ext_file, source_files, debug=False):
        cc_cmdline = (
                self._cmdline()
                + ["-o%s" % ext_file]
                + source_files
                )
        from subprocess import call
        if debug:
            print " ".join(cc_cmdline)

        result = call(cc_cmdline)

        if result != 0:
            raise CompileError, "module compilation failed"




# drivers ---------------------------------------------------------------------
def _erase_dir(dir):
    from os import listdir, unlink, rmdir
    from os.path import join
    for name in listdir(dir):
        unlink(join(dir, name))
    rmdir(dir)




def extension_file_from_string(platform, ext_file, source_string, 
        source_name="module.cpp", debug=False):
    from tempfile import mkdtemp
    src_dir = mkdtemp()

    from os.path import join
    source_file = join(src_dir, source_name)
    outf = open(source_file, "w")
    outf.write(str(source_string))
    outf.close()

    try:
        platform.build_extension(ext_file, [source_file], debug=debug)
    finally:
        _erase_dir(src_dir)




def extension_from_string(platform, name, source_string, source_name="module.cpp", 
        cache_dir=None, debug=False, wait_on_error=None):
    if wait_on_error is None:
        wait_on_error = debug

    from os import mkdir
    from os.path import join
    from imp import load_dynamic

    if cache_dir is None:
        from os.path import expanduser, exists
        cache_dir = join(expanduser("~"), 
                ".codepy-compiler-cache")

        if not exists(cache_dir):
            mkdir(cache_dir)

    from tempfile import mkdtemp
    temp_dir = mkdtemp()

    import md5
    checksum = md5.new()

    checksum.update(source_string)
    checksum.update(str(platform.abi_id()))
    hex_checksum = checksum.hexdigest()
    mod_name = "codepy.temp.%s.%s" % (hex_checksum, name)

    if cache_dir:
        cache_path = join(cache_dir, hex_checksum)
        if not exists(cache_path):
            mkdir(cache_path)

        ext_file = join(cache_path, name+platform.so_ext)

        try:
            return load_dynamic(mod_name, ext_file)
        except ImportError:
            pass
    else:
        ext_file = join(temp_dir, source_name+platform.so_ext)

    from os.path import join
    source_file = join(temp_dir, source_name)
    outf = open(source_file, "w")
    outf.write(str(source_string))
    outf.close()

    try:
        platform.build_extension(ext_file, [source_file], debug=debug)
        return load_dynamic(mod_name, ext_file)
    except CompileError:
        if wait_on_error:
            raw_input("Examine %s, then press [Enter]:" % source_file)
        raise
    finally:
        _erase_dir(temp_dir)




# configuration ---------------------------------------------------------------
def guess_platform():
    def strip_prefix(pfx, value):
        if value.startswith(pfx):
            return value[len(pfx):]
        else:
            return value

    make_vars = parse_python_makefile()
    from os.path import join
    kwargs = dict(
            cc=make_vars["CC"].split()[0],
            ld=make_vars["LDSHARED"].split()[0],
            cflags=(
                make_vars["CC"].split()[1:]
                + make_vars["CFLAGS"].split()
                + make_vars["CFLAGSFORSHARED"].split()
                ),
            ldflags=(
                make_vars["LDSHARED"].split()[1:]
                + make_vars["LINKFORSHARED"].split()
                ),
            libraries=[strip_prefix("-l", lib) 
                for lib in make_vars["LIBS"].split()],
            include_dirs=[
                make_vars["INCLUDEPY"]
                ],
            library_dirs=[make_vars["LIBDIR"]],
            so_ext=make_vars["SO"]
            )

    if kwargs["cc"] in ["gcc", "cc"]:
        if "-Wstrict-prototypes" in kwargs["cflags"]:
            kwargs["cflags"].remove("-Wstrict-prototypes")

        return GCCPlatform(**kwargs)
    else:
        raise RuntimeError("unknown compiler")
