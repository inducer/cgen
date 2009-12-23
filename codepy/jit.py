"""Just-in-time Python extension compilation."""

from __future__ import division
from codepy import CompileError
from pytools import Record

__copyright__ = "Copyright (C) 2008 Andreas Kloeckner"




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


def extension_from_string(toolchain, name, source_string,
                          source_name="module.cpp", cache_dir=None,
                          debug=False, wait_on_error=None,
                          debug_recompile=True):
    """Return a reference to the extension module *name*, which can be built
    from the source code in *source_string* if necessary. Raise
    :exc:`CompileError` in case of error.

    Compiled code is cached in *cache_dir* and available immediately if it has
    been compiled at some point in the past. Compiler and Python API versions
    as well as versions of include files are taken into account when examining
    the cache. If *cache_dir* is ``None``, a default location is assumed.
    If it is ``False``, no caching is performed. Proper locking is performed
    on the cache directory. Simultaneous use of the cache by multiple
    processes works as expected, but may lead to delays because of locking.

    The code in *source_string* will be saved to a temporary file named
    *source_name* if it needs to be compiled.

    If *debug* is ``True``, commands involved in the build are printed.

    If *wait_on_error* is ``True``, the full path name of the temporary in
    which a :exc:`CompileError` occurred is shown and the user is expected
    to press a key before the temporary file gets deleted. If *wait_on_error*
    is ``None``, it is taken to be the same as *debug*.

    If *debug_recompile*, messages are printed indicating whether a
    recompilation is taking place.
    """
    mod_name, ext_file, recompiled = \
        compile_from_string(toolchain,
                            name, source_string,
                            source_name,
                            cache_dir, debug, wait_on_error, debug_recompile,
                            False)
     # try loading it
    from imp import load_dynamic
    return load_dynamic(mod_name, ext_file)




class _InvalidInfoFile(RuntimeError):
    pass



class _SourceInfo(Record):
    pass




def compile_from_string(toolchain, name, source_string,
                        source_name="module.cpp", cache_dir=None,
                        debug=False, wait_on_error=None, debug_recompile=True,
                        object=False):
    """Returns a tuple: mod_name, file_name, recompiled.
    mod_name is the name of the module represented by a compiled object,
    file_name is the name of the compiled object, which can be built from the
    source code in *source_string* if necessary,
    recompiled is True if the object had to be recompiled, False if the cache
    is hit.
    Raise :exc:`CompileError` in case of error.  The mod_name and file_name
    are designed to be used with load_dynamic to load a python module from
    this object, if desired.

    Compiled code is cached in *cache_dir* and available immediately if it
    has been compiled at some point in the past.  Compiler and Python API
    versions as well as versions of include files are taken into account when
    examining the cache. If *cache_dir* is ``None``, a default location is
    assumed. If it is ``False``, no caching is perfomed.  Proper locking is
    performed on the cache directory.  Simultaneous use of the cache by
    multiple processes works as expected, but may lead to delays because of
    locking.

    The code in *source_string* will be saved to a temporary file named
    *source_name* if it needs to be compiled.

    If *debug* is ``True``, commands involved in the build are printed.

    If *wait_on_error* is ``True``, the full path name of the temporary in
    which a :exc:`CompileError` occurred is shown and the user is expected
    to press a key before the temporary file gets deleted. If *wait_on_error*
    is ``None``, it is taken to be the same as *debug*.

    If *debug_recompile*, messages are printed indicating whether a
    recompilation is taking place.

    """

    if wait_on_error is not None:
        from warnings import warn
        warn("wait_on_error is deprecated and has no effect",
                DeprecationWarning)

    import os
    from os.path import join

    if cache_dir is None:
        from os.path import exists
        from tempfile import gettempdir
        cache_dir = join(gettempdir(),
                "codepy-compiler-cache-v5-uid%s" % os.getuid())

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

    def get_dep_structure(source_path):
        deps = list(toolchain.get_dependencies([source_path]))
        deps.sort()
        return [(dep, os.stat(dep).st_mtime, get_file_md5sum(dep)) for dep in deps
                if not dep == source_path]

    def write_source(name):
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

    def load_info(info_path):
        from cPickle import load

        try:
            info_file = open(info_path)
        except IOError:
            raise _InvalidInfoFile()

        try:
            return load(info_file)
        except EOFError:
            raise _InvalidInfoFile()
        finally:
            info_file.close()


    def check_deps(deps):
        for name, date, md5sum in deps:
            try:
                possibly_updated = os.stat(name).st_mtime != date
            except OSError, e:
                if debug_recompile:
                    print("recompiling because dependency %s is "
                    "inaccessible (%s)." % (name, e))
                return False
            else:
                if possibly_updated and md5sum != get_file_md5sum(name):
                    if debug_recompile:
                        print("recompiling because dependency %s was "
                        "updated." % name)
                    return False

        return True

    def check_source(source_path):
        try:
            src_f = open(source_path, "r")
        except IOError:
            if debug_recompile:
                print ("recompiling because cache directory does "
                        "not contain source file '%s'." % source_path)
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
        if object:
            suffix = toolchain.o_ext
        else:
            suffix = toolchain.so_ext
        if cache_dir:
            mod_cache_dir_m = ModuleCacheDirManager(cleanup_m,
                    join(cache_dir, hex_checksum))
            info_path = mod_cache_dir_m.sub("info")
            ext_file = mod_cache_dir_m.sub(name+suffix)

            if mod_cache_dir_m.existed:
                try:
                    info = load_info(info_path)
                except _InvalidInfoFile:
                    mod_cache_dir_m.reset()

                    if debug_recompile:
                        print "recompiling for invalid cache dir (%s)." % (
                                mod_cache_dir_m.path)
                else:
                    if check_deps(info.dependencies) and check_source(
                            mod_cache_dir_m.sub(info.source_name)):
                        return mod_name, ext_file, False
            else:
                if debug_recompile:
                    print "recompiling for non-existent cache dir (%s)." % (
                            mod_cache_dir_m.path)

            source_path = mod_cache_dir_m.sub(source_name)
        else:
            ext_file = join(temp_dir, source_name+suffix)
            done_path = None
            info_path = None

            temp_dir_m = TempDirManager(cleanup_m)
            source_path = temp_dir_m.sub(source_name)

        write_source(source_path)

        if object:
            toolchain.build_object(ext_file, [source_path], debug=debug)
        else:
            toolchain.build_extension(ext_file, [source_path], debug=debug)

        if info_path is not None:
            from cPickle import dump
            info_file = open(info_path, "w")
            dump(_SourceInfo(
                dependencies=get_dep_structure(source_path),
                source_name=source_name), info_file)
            info_file.close()

        return mod_name, ext_file, True
    except:
        cleanup_m.error_clean_up()
        raise
    finally:
        cleanup_m.clean_up()




def link_extension(toolchain, objects, mod_name, cache_dir=None,
        debug=False, wait_on_error=True):
    import os.path
    if cache_dir is not None:
        destination = os.path.join(cache_dir, mod_name + toolchain.so_ext)
    else:
        # put the linked object in the same directory as the first object
        destination_base, first_object = os.path.split(objects[0])
        destination = os.path.join(destination_base, mod_name
                                   + toolchain.so_ext)
    try:
        toolchain.link_extension(destination, objects, debug=debug)
    except CompileError:
        if wait_on_error:
            raw_input("Link error, examine %s, then press [Enter]" % objects)
            raise

    # try loading it
    from imp import load_dynamic
    return load_dynamic(mod_name, destination)




from pytools import MovedFunctionDeprecationWrapper
from codepy.toolchain import guess_toolchain as _gtc
guess_toolchain = MovedFunctionDeprecationWrapper(_gtc)

