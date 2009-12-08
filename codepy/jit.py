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
class Toolchain(Record):
    """Abstract base class for tools used to link dynamic Python modules."""

    def __init__(self, *args, **kwargs):
        Record.__init__(self, *args, **kwargs)
        self.features = set()

    def get_version(self):
        """Return a string describing the exact version of the tools (compilers etc.)
        involved in this toolchain.

        Implemented by subclasses.
        """

        raise NotImplementedError

    def abi_id(self):
        """Return a picklable Python object that describes the ABI (Python version,
        compiler versions, etc.) against which a Python module is compiled.
        """

        import sys
        return [self.get_version(), sys.version]

    def add_library(self, feature, include_dirs, library_dirs, libraries):
        """Add *include_dirs*, *library_dirs* and *libraries* describing the
        library named *feature* to the toolchain.

        Future toolchain invocations will include compiler flags referencing
        the respective resources.

        Duplicate directories are ignored, as will be attempts to add the same
        *feature* twice.
        """
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

    def get_dependencies(self,  source_files):
        """Return a list of header files referred to by *source_files.

        Implemented by subclasses.
        """

        raise NotImplementedError

    def build_extension(self, ext_file, source_files, debug=False):
        """Create the extension file *ext_file* from *source_files*
        by invoking the toolchain. Raise :exc:`CompileError` in
        case of error.

        If *debug* is True, print the commands executed.

        Implemented by subclasses.
        """

        raise NotImplementedError

    def with_optimization_level(self, level, **extra):
        """Return a new Toolchain object with the optimization level
        set to `level` , on the scale defined by the gcc -O option.
        Levels greater than four may be defined to perform certain, expensive
        optimizations. Further, extra keyword arguments may be defined.
        If a subclass doesn't understand an "extra" argument, it should
        simply ignore it.

        Level may also be "debug" to specifiy a debug build.

        Implemented by subclasses.
        """

        raise NotImplementedError




class GCCToolchain(Toolchain):
    def get_version(self):
        from pytools.prefork import call_capture_stdout
        return call_capture_stdout([self.cc, "--version"])

    def get_version_tuple(self):
        ver = self.get_version()
        lines = ver.split("\n")
        words = lines[0].split()
        numbers = words[2].split(".")

        result = []
        for n in numbers:
            try:
                result.append(int(n))
            except ValueError:
                # not an integer? too bad.
                break

        return tuple(result)

    def _cmdline(self, object=False):
        if object:
            ldOption = ['-c']
        else:
            ldOption = self.ldflags
        return (
            [self.cc]
            + self.cflags
            + ldOption
            + ["-D%s" % define for define in self.defines]
            + ["-U%s" % undefine for undefine in self.undefines]
            + ["-I%s" % idir for idir in self.include_dirs]
            + ["-L%s" % ldir for ldir in self.library_dirs]
            + ["-l%s" % lib for lib in self.libraries]
            )
    
    def abi_id(self):
        return Toolchain.abi_id(self) + [self._cmdline()]

    def get_dependencies(self, source_files):
        from pytools.prefork import call_capture_stdout
        lines = join_continued_lines(call_capture_stdout(
                [self.cc]
                + ["-M"]
                + ["-D%s" % define for define in self.defines]
                + ["-I%s" % idir for idir in self.include_dirs]
                + source_files
                ).split("\n"))

        from pytools import flatten
        return set(flatten(
            line.split()[1:] for line in lines))

    def build_extension(self, ext_file, source_files, object=False, debug=False):
        cc_cmdline = (
                self._cmdline(object)
                + ["-o", ext_file]
                + source_files
                )

        from pytools.prefork import call
        if debug:
            print " ".join(cc_cmdline)

        result = call(cc_cmdline)

        if result != 0:
            import sys
            print >> sys.stderr, "FAILED compiler invocation:", \
                    " ".join(cc_cmdline)
            raise CompileError, "module compilation failed"

    def with_optimization_level(self, level, debug=False, **extra):
        def remove_prefix(l, prefix):
            return [f for f in l if not f.startswith(prefix)]

        cflags = self.cflags
        for pfx in ["-O", "-g", "-march", "-mtune", "-DNDEBUG"]:
            cflags = remove_prefix(cflags, pfx)

        if level == "debug":
            oflags = ["-g"]
        else:
            oflags = ["-O%d" % level, "-DNDEBUG"]

            if level >= 2 and self.get_version_tuple() >= (4,3):
                oflags.extend(["-march=native", "-mtune=native", ])

        return self.copy(cflags=cflags + oflags)

class NVCCToolchain(Toolchain):
    def get_version(self):
        from pytools.prefork import call_capture_stdout
        return call_capture_stdout([self.cc, "--version"])
    def get_version_tuple(self):
        ver = self.get_version()
        lines = ver.split("\n")
        words = lines[3].split()
        numbers = words[4].split('.') + words[5].split('.')

        result = []
        for n in number:
            try:
                result.append(int(n))
            except ValueError:
                # not an integer? too bad.
                break

        return tuple(result)
    def _cmdline(self):
        return (
                [self.cc]
                + self.cflags
                + self.ldflags
                + ["-D%s" % define for define in self.defines]
                + ["-U%s" % undefine for undefine in self.undefines]
                + ["-I%s" % idir for idir in self.include_dirs]
                + ["-L%s" % ldir for ldir in self.library_dirs]
                + ["-l%s" % lib for lib in self.libraries]
                )
    def abi_id(self):
        return Toolchain.abi_id(self) + [self._cmdline()]
    
    def get_dependencies(self, source_files):
        from pytools.prefork import call_capture_stdout
        lines = join_continued_lines(call_capture_stdout(
                [self.cc]
                + ["-M"]
                + ["-D%s" % define for define in self.defines]
                + ["-U%s" % undefine for undefine in self.defines]
                + ["-I%s" % idir for idir in self.include_dirs]
                + source_files
                ).split("\n"))
        from pytools import flatten
        return set(flatten(
            line.split()[2:] for line in lines))

    def build_extension(self, ext_file, source_files, object=False, debug=False):
        cc_cmdline = (
                self._cmdline()
                + ["-o", ext_file]
                + source_files
                )
        
        from pytools.prefork import call
        if debug:
            print " ".join(cc_cmdline)

        result = call(cc_cmdline)

        if result != 0:
            import sys
            print >> sys.stderr, "FAILED compiler invocation:", \
                    " ".join(cc_cmdline)
            raise CompileError, "module compilation failed"
        
# drivers ---------------------------------------------------------------------
def _erase_dir(dir):
    from os import listdir, unlink, rmdir
    from os.path import join
    for name in listdir(dir):
        unlink(join(dir, name))
    rmdir(dir)




def extension_file_from_string(toolchain, ext_file, source_string,
        source_name="module.cpp", debug=False):
    """Using *toolchain*, build the extension file named *ext_file*
    from the source code in *source_string*, which is saved to a
    temporary file named *source_name*. Raise :exc:`CompileError` in
    case of error.

    If *debug* is True, show commands involved in the build.
    """
    from tempfile import mkdtemp
    src_dir = mkdtemp()

    from os.path import join
    source_file = join(src_dir, source_name)
    outf = open(source_file, "w")
    outf.write(str(source_string))
    outf.close()

    try:
        toolchain.build_extension(ext_file, [source_file], debug=debug)
    finally:
        _erase_dir(src_dir)




class CleanupBase(object):
    pass

class CleanupManager(CleanupBase):
    def __init__(self):
        self.cleanups = []

    def register(self, c):
        self.cleanups.insert(0, c)

    def clean_up(self):
        for c in self.cleanups:
            c.clean_up()

    def error_clean_up(self):
        for c in self.cleanups:
            c.error_clean_up()

class TempDirManager(CleanupBase):
    def __init__(self, cleanup_m):
        from tempfile import mkdtemp
        self.path = mkdtemp()
        cleanup_m.register(self)

    def sub(self, n):
        from os.path import join
        return join(self.path, n)

    def clean_up(self):
        _erase_dir(self.path)

    def error_clean_up(self):
        pass

class CacheLockManager(CleanupBase):
    def __init__(self, cleanup_m, cache_dir):
        import os

        if cache_dir is not None:
            self.lock_file = os.path.join(cache_dir, "lock")

            attempts = 0
            while True:
                try:
                    self.fd = os.open(self.lock_file,
                            os.O_CREAT | os.O_WRONLY | os.O_EXCL)
                    break
                except OSError:
                    pass

                from time import sleep
                sleep(1)

                attempts += 1

                if attempts > 10:
                    from warnings import warn
                    warn("could not obtain lock--delete '%s' if necessary"
                            % self.lock_file)

            cleanup_m.register(self)

    def clean_up(self):
        import os
        os.close(self.fd)
        os.unlink(self.lock_file)

    def error_clean_up(self):
        pass

class ModuleCacheDirManager(CleanupBase):
    def __init__(self, cleanup_m, path):
        from os import mkdir

        self.path = path
        try:
            mkdir(self.path)
            cleanup_m.register(self)
            self.existed = False
        except OSError:
            self.existed = True

    def sub(self, n):
        from os.path import join
        return join(self.path, n)

    def reset(self):
        import os
        _erase_dir(self.path)
        os.mkdir(self.path)

    def clean_up(self):
        pass

    def error_clean_up(self):
        _erase_dir(self.path)


def extension_from_string(toolchain, name, source_string, source_name="module.cpp",
        cache_dir=None, debug=False, wait_on_error=None, debug_recompile=True):
    """Return a reference to the extension module *name*, which can be built
    from the source code in *source_string* if necessary. Raise :exc:`CompileError` in
    case of error.

    Compiled code is cached in *cache_dir* and available immediately if it has
    been compiled at some point in the past. Compiler and Python API versions
    as well as versions of include files are taken into account when examining
    the cache. If *cache_dir* is ``None``, a default location is assumed.
    If it is ``False``, no caching is performed. Proper locking is performed
    on the cache directory. Simultaneous use of the cache by multiple processes
    works as expected, but may lead to delays because of locking.

    The code in *source_string* will be saved to a temporary file named
    *source_name* if it needs to be compiled.

    If *debug* is ``True``, commands involved in the build are printed.

    If *wait_on_error* is ``True``, the full path name of the temporary in
    which a :exc:`CompileError` occurred is shown and the user is expected
    to press a key before the temporary file gets deleted. If *wait_on_error*
    is ``None``, it is taken to be the same as *debug*.

    If *debug_recompile*, messages are printed indicating whether a recompilation
    is taking place.
    """
    mod_name, ext_file, recompiled = compile_from_string(toolchain, name, source_string, source_name,
                                             cache_dir, debug, wait_on_error, debug_recompile,
                                             toolchain.so_ext)
     # try loading it
    from imp import load_dynamic
    return load_dynamic(mod_name, ext_file)
    
    
def compile_from_string(toolchain, name, source_string, source_name="module.cpp",
                        cache_dir=None, debug=False, wait_on_error=None, debug_recompile=True,
                        object_suffix=".o", object=False):
    """Returns a tuple: mod_name, file_name, recompiled.
    mod_name is the name of the module represented by a compiled object,
    file_name is the name of the compiled object, which can be built from the source
    code in *source_string* if necessary,
    recompiled is True if the object had to be recompiled, False if the cache is hit.
    Raise :exc:`CompileError` in case of error.  The mod_name and file_name are designed
    to be used with load_dynamic to load a python module from this object, if desired.

    Compiled code is cached in *cache_dir* and available immediately if it has been
    compiled at some point in the past.  Compiler and Python API versions as well as
    versions of include files are taken into account when examining the cache.
    If *cache_dir* is ``None``, a default location is assumed.
    If it is ``False``, no caching is perfomed.  Proper locking is performed on the
    cache directory.  Simultaneous use of the cache by multiple processes works as
    expected, but may lead to delays because of locking.

    The code in *source_string* will be saved to a temporary file named
    *source_name* if it needs to be compiled.

    If *debug* is ``True``, commands involved in the build are printed.

    If *wait_on_error* is ``True``, the full path name of the temporary in
    which a :exc:`CompileError` occurred is shown and the user is expected
    to press a key before the temporary file gets deleted. If *wait_on_error*
    is ``None``, it is taken to be the same as *debug*.

    If *debug_recompile*, messages are printed indicating whether a recompilation
    is taking place.

    The object will have the suffix provided by *object_suffix*.
    """
    
    if wait_on_error is None:
        wait_on_error = debug

    import os
    from os.path import join

    if cache_dir is None:
        from os.path import exists
        from tempfile import gettempdir
        cache_dir = join(gettempdir(),
                "codepy-compiler-cache-v4-uid%s" % os.getuid())

        try:
            os.mkdir(cache_dir)
        except OSError, e:
            from errno import EEXIST
            if e.errno != EEXIST:
                raise

    def get_file_md5sum(fname):
        try:
            import hashlib
            checksum = hashlib.md5()
        except ImportError:
            # for Python << 2.5
            import md5
            checksum = md5.new()

        inf = open(fname)
        checksum.update(inf.read())
        inf.close()
        return checksum.hexdigest()

    def get_dep_structure():
        deps = list(toolchain.get_dependencies([source_file]))
        deps.sort()
        return [(dep, os.stat(dep).st_mtime, get_file_md5sum(dep)) for dep in deps
                if not dep == source_file]

    def write_source(name):
        from os.path import join
        outf = open(name, "w")
        outf.write(str(source_string))
        outf.close()

    def calculate_hex_checksum():
        try:
            import hashlib
            checksum = hashlib.md5()
        except ImportError:
            # for Python << 2.5
            import md5
            checksum = md5.new()

        checksum.update(source_string)
        checksum.update(str(toolchain.abi_id()))
        return checksum.hexdigest()

    def check_deps(dep_path):
        from cPickle import load

        try:
            dep_file = open(dep_path)
        except IOError:
            return False

        try:
            dep_struc = load(dep_file)
        except EOFError:
            # invalid file
            return False

        dep_file.close()

        for name, date, md5sum in dep_struc:
            try:
                possibly_updated = os.stat(name).st_mtime != date
            except OSError, e:
                if debug_recompile:
                    print "recompiling because dependency %s is inacessible (%s)." % (
                            name, e)
                return False
            else:
                if possibly_updated and md5sum != get_file_md5sum(name):
                    if debug_recompile:
                        print "recompiling because dependency %s was updated." % name
                    return False

        return True

    def check_source(source_path):
        try:
            src_f = open(source_path, "r")
        except IOError:
            if debug_recompile:
                print ("recompiling because cache directory does "
                        "not contain 'source' entry.")
            return False

        valid = src_f.read() == source_string
        src_f.close()

        if not valid:
            from warnings import warn
            warn("hash collision in compiler cache")
        return valid

    cleanup_m = CleanupManager()

    try:
        lock_m = CacheLockManager(cleanup_m, cache_dir)

        hex_checksum = calculate_hex_checksum()
        mod_name = "codepy.temp.%s.%s" % (hex_checksum, name)

        if cache_dir:
            mod_cache_dir_m = ModuleCacheDirManager(cleanup_m,
                    join(cache_dir, hex_checksum))
            source_path = mod_cache_dir_m.sub("source")
            deps_path = mod_cache_dir_m.sub("deps")
            ext_file = mod_cache_dir_m.sub(name+object_suffix)

            if mod_cache_dir_m.existed:
                if check_deps(deps_path) and check_source(source_path):
                    return mod_name, ext_file, False

                # the cache directory existed, but was invalid
                mod_cache_dir_m.reset()
            else:
                if debug_recompile:
                    print "recompiling for non-existent cache dir (%s)." % (
                            mod_cache_dir_m.path)
        else:
            ext_file = join(temp_dir, source_name+object_suffix)
            done_path = None
            deps_path = None
            source_path = None

        temp_dir_m = TempDirManager(cleanup_m)
        source_file = temp_dir_m.sub(source_name)
        write_source(source_file)
        try:
            toolchain.build_extension(ext_file, [source_file], debug=debug, object=object)
        except CompileError:
            if wait_on_error:
                raw_input("Examine %s, then press [Enter]:" % source_file)
            raise

        if source_path is not None:
            src_f = open(source_path, "w")
            src_f.write(source_string)
            src_f.close()

        if deps_path is not None:
            print(deps_path)
            from cPickle import dump
            deps_file = open(deps_path, "w")
            dump(get_dep_structure(), deps_file)
            deps_file.close()

        return mod_name, ext_file, True
    except:
        cleanup_m.error_clean_up()
        raise
    finally:
        cleanup_m.clean_up()


def link_extension(toolchain, objects, mod_name, debug=False, wait_on_error=True):
    #Put the linked object in the same directory as the first object
    import os.path
    destinationBase, objectExtension = os.path.splitext(objects[0])
    destination = destinationBase + toolchain.so_ext
    try:
        toolchain.build_extension(destination, objects, debug=debug, object=False)
    except CompileError:
        if wait_on_error:
            #raw_input("Examine %s, then press [Enter]:" % source_file)
            raise
    # try loading it
    from imp import load_dynamic
    return load_dynamic(mod_name, destination)

# configuration ---------------------------------------------------------------
class ToolchainGuessError(Exception):
    pass




def guess_toolchain():
    """Guess and return a :class:`Toolchain` instance.

    Raise :exc:`ToolchainGuessError` if no toolchain could be found.
    """
    def strip_prefix(pfx, value):
        if value.startswith(pfx):
            return value[len(pfx):]
        else:
            return value

    make_vars = parse_python_makefile()

    cc_cmdline = (make_vars["CXX"].split()
            + make_vars["CFLAGS"].split()
            + make_vars["CFLAGSFORSHARED"].split())

    from os.path import join
    kwargs = dict(
            cc=cc_cmdline[0],
            ld=make_vars["LDSHARED"].split()[0],
            cflags=cc_cmdline[1:],
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
            so_ext=make_vars["SO"],
            defines=[],
            undefines=[],
            )

    from pytools.prefork import call_capture_stdout
    version = call_capture_stdout([kwargs["cc"], "--version"])
    if "Free Software Foundation" in version:
        if "-Wstrict-prototypes" in kwargs["cflags"]:
            kwargs["cflags"].remove("-Wstrict-prototypes")
        if "darwin" in version:
            #Are we running in 32-bit mode?
            #The python interpreter may have been compiled as a Fat binary
            #So we need to check explicitly how we're running
            #And update the cflags accordingly
            import sys
            if sys.maxint == 0x7fffffff:
                kwargs["cflags"].extend(['-arch', 'i386'])
        return GCCToolchain(**kwargs)
    else:
        raise ToolchainGuessError("unknown compiler")

def guess_nvcctoolchain():
    kwargs = dict(cc='nvcc',
                  include_dirs=[],
                  library_dirs=[],
                  libraries=[],
                  cflags=['-c'],
                  ldflags=[],
                  defines=[],
                  undefines=['__BLOCKS__'])
    return NVCCToolchain(**kwargs)
