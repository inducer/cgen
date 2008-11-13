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
    def abi_id(self):
        import sys
        return [self.get_version(), sys.version]

    def add_package(self, include_dirs, library_dirs, libraries):
        self.include_dirs.extend(include_dirs)
        self.library_dirs.extend(library_dirs)
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

    def build_extension(self, ext_file, source_files):
        cc_cmdline = (
                self._cmdline()
                + ["-o%s" % ext_file]
                + source_files
                )
        from subprocess import call
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




def extension_file_from_string(platform, ext_file, source_string, source_name="module.cpp"):
    from tempfile import mkdtemp
    src_dir = mkdtemp()

    from os.path import join
    source_file = join(src_dir, source_name)
    outf = open(source_file, "w")
    outf.write(str(source_string))
    outf.close()

    try:
        platform.build_extension(ext_file, [source_file])
    finally:
        _erase_dir(src_dir)




def extension_from_string(platform, name, source_string, source_name="module.cpp", 
        cache_dir=None):
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
        platform.build_extension(ext_file, [source_file])
        return load_dynamic(mod_name, ext_file)
    finally:
        _erase_dir(temp_dir)




# configuration ---------------------------------------------------------------
def get_aksetup_config():
    def update_config(fname):
        import os
        if os.access(fname, os.R_OK):
            filevars = {}
            execfile(fname, filevars)

            for key, value in filevars.iteritems():
                if key != "__builtins__":
                    config[key] = value

    config = {}
    from os.path import expanduser
    update_config(expanduser("~/.aksetup-defaults.py"))

    import sys
    if not sys.platform.lower().startswith("win"):
        update_config(expanduser("/etc/aksetup-defaults.py"))

    return config

def platform_from_makefile():
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
        return GCCPlatform(**kwargs)
    else:
        raise RuntimeError("unknown compiler")



if __name__ == "__main__":
    ext = """
    #include <boost/python.hpp>

    char const* greet()
    {
      return "hello, world";
    }

    BOOST_PYTHON_MODULE(hello)
    {
      using namespace boost::python;
      def("greet", greet);
    }
    \n"""

    plat = platform_from_makefile()
    aksetup = get_aksetup_config()
    plat.add_package(
            aksetup["BOOST_INC_DIR"],
            aksetup["BOOST_LIB_DIR"],
            aksetup["BOOST_PYTHON_LIBNAME"],
            )
    mod = extension_from_string(plat, "hello", ext)
    print mod.greet()
