# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import re
import inspect
from subprocess import Popen, PIPE, STDOUT
import logging
import fnmatch
import errno
import shlex
import glob
import tempfile
import threading
import time
import io
from contextlib import closing
from collections import deque

try:
    from packaging.version import parse as parse_version
except ImportError:
    from pkg_resources import parse_version

# try loading magic>=0.4.20 which implements detect_from_filename method
magic_mod = False
try:
    import magic
    magic.detect_from_filename(__file__)
    magic_mod = True
except (ImportError, AttributeError):
    log = logging.getLogger('sos')
    from textwrap import fill
    msg = ("""\
WARNING: Failed to load 'magic' module version >= 0.4.20 which sos aims to \
use for detecting binary files. A less effective method will be used. It is \
recommended to install proper python3-magic package with the module.
""")
    log.warning('\n' + fill(msg, 72, replace_whitespace=False) + '\n')


TIMEOUT_DEFAULT = 300

__all__ = [
    'TIMEOUT_DEFAULT',
    'ImporterHelper',
    'SoSTimeoutError',
    'TempFileUtil',
    'bold',
    'file_is_binary',
    'fileobj',
    'find',
    'get_human_readable',
    'grep',
    'import_module',
    'is_executable',
    'listdir',
    'parse_version',
    'path_exists',
    'path_isdir',
    'path_isfile',
    'path_islink',
    'path_join',
    'recursive_dict_values_by_key',
    'shell_out',
    'sos_get_command_output',
    'tail',
]


def format_version_to_pep440(ver):
    """ Convert the version into a PEP440 compliant version scheme."""
    public_version_re = re.compile(
            r"^([0-9][0-9.]*(?:(?:a|b|rc|.post|.dev)[0-9]+)*)\+?"
            )
    try:
        _, public, local = public_version_re.split(ver, maxsplit=1)
        if not local:
            return ver
        sanitized_local = re.sub("[+~]+", ".", local).strip("-")
        pep440_version = f"{public}+{sanitized_local}"
        return pep440_version
    except Exception as err:
        log.debug(f"Unable to format {ver} to pep440 format: {err}")
        return ver


def sos_parse_version(ver, pep440=True):
    """ Converts the version to PEP440 format before parsing """
    if pep440:
        ver_pep440 = format_version_to_pep440(ver)
        return parse_version(ver_pep440)

    return parse_version(ver)


def tail(filename, number_of_bytes):
    """Returns the last number_of_bytes of filename"""
    with open(filename, "rb") as f:
        if os.stat(filename).st_size > number_of_bytes:
            f.seek(-number_of_bytes, 2)
        return f.read()


def fileobj(path_or_file, mode='r'):
    """Returns a file-like object that can be used as a context manager"""
    if isinstance(path_or_file, str):
        try:
            return open(path_or_file, mode)
        except IOError:
            log = logging.getLogger('sos')
            log.debug(f"fileobj: {path_or_file} could not be opened")
            return closing(io.StringIO())
    else:
        return closing(path_or_file)


def convert_bytes(bytes_, K=1 << 10, M=1 << 20, G=1 << 30, T=1 << 40):
    """Converts a number of bytes to a shorter, more human friendly format"""
    fn = float(bytes_)
    if bytes_ >= T:
        return f'{(fn / T):.1fT}'
    elif bytes_ >= G:
        return f'{(fn / G):.1fG}'
    elif bytes_ >= M:
        return f'{(fn / M):.1fM}'
    elif bytes_ >= K:
        return f'{(fn / K):.1fK}'
    else:
        return f'{bytes_}'


def file_is_binary(fname):
    """Helper to determine if a given file contains binary content or not.

    This is especially helpful for `sos clean`, which cannot obfuscate binary
    data and instead, by default, will remove binary files.

    :param fname:   The full path of the file to check binaryness of
    :type fname:    ``str``

    :returns:   True if binary, else False
    :rtype:     ``bool``
    """
    if magic_mod:
        try:
            _ftup = magic.detect_from_filename(fname)
            _mimes = ['text/', 'inode/']
            return (
                _ftup.encoding == 'binary' and not
                any(_ftup.mime_type.startswith(_mt) for _mt in _mimes)
            )
        except Exception:
            pass
    # if for some reason the above check fails or magic>=0.4.20 is not present,
    # fail over to checking the very first byte of the file content
    with open(fname, 'tr') as tfile:
        try:
            # when opened as above (tr), reading binary content will raise
            # an exception
            tfile.read(1)
            return False
        except UnicodeDecodeError:
            return True


def find(file_pattern, top_dir, max_depth=None, path_pattern=None):
    """Generator function to find files recursively.
    Usage::

        for filename in find("*.properties", "/var/log/foobar"):
            print filename
    """
    if max_depth:
        base_depth = os.path.dirname(top_dir).count(os.path.sep)
        max_depth += base_depth

    for path, dirlist, filelist in os.walk(top_dir):
        if max_depth and path.count(os.path.sep) >= max_depth:
            del dirlist[:]

        if path_pattern and not fnmatch.fnmatch(path, path_pattern):
            continue

        for name in fnmatch.filter(filelist, file_pattern):
            yield os.path.join(path, name)


def grep(pattern, *files_or_paths):
    """Returns lines matched in fnames, where fnames can either be pathnames to
    files to grep through or open file objects to grep through line by line"""
    matches = []

    for fop in files_or_paths:
        with fileobj(fop) as fo:
            matches.extend((line for line in fo if re.match(pattern, line)))

    return matches


def is_executable(command, sysroot=None):
    """Returns if a command matches an executable on the PATH"""

    paths = os.environ.get("PATH", "").split(os.path.pathsep)
    candidates = [command] + [os.path.join(p, command) for p in paths]
    if sysroot:
        candidates += [
            os.path.join(sysroot, c.lstrip('/')) for c in candidates
        ]
    return any(os.access(path, os.X_OK) for path in candidates)


def sos_get_command_output(command, timeout=TIMEOUT_DEFAULT, stderr=False,
                           chroot=None, chdir=None, env=None, foreground=False,
                           binary=False, sizelimit=None, poller=None,
                           to_file=False):
    """Execute a command and return a dictionary of status and output,
    optionally changing root or current working directory before
    executing command.
    """
    # Change root or cwd for child only. Exceptions in the prexec_fn
    # closure are caught in the parent (chroot and chdir are bound from
    # the enclosing scope).
    def _child_prep_fn():
        if chroot and chroot != '/':
            os.chroot(chroot)
        if (chdir):
            os.chdir(chdir)

    def _check_poller(proc):
        if poller() or proc.poll() == 124:
            proc.terminate()
            raise SoSTimeoutError
        time.sleep(0.01)

    cmd_env = os.environ.copy()
    # ensure consistent locale for collected command output
    cmd_env['LC_ALL'] = 'C.UTF-8'
    # optionally add an environment change for the command
    if env:
        for key, value in env.items():
            if value:
                cmd_env[key] = value
            else:
                cmd_env.pop(key, None)
    # use /usr/bin/timeout to implement a timeout
    if timeout and is_executable("timeout"):
        command = (f"timeout {'--foreground' if foreground else ''} {timeout}s"
                   f" {command}")

    args = shlex.split(command)
    # Expand arguments that are wildcard root paths.
    expanded_args = []
    for arg in args:
        if arg.startswith("/") and "*" in arg:
            expanded_arg = glob.glob(arg)
            if expanded_arg:
                expanded_args.extend(expanded_arg)
            else:
                expanded_args.append(arg)
        else:
            expanded_args.append(arg)
    if to_file:
        _output = open(to_file, 'w')
    else:
        _output = PIPE
    try:
        p = Popen(expanded_args, shell=False, stdout=_output,
                  stderr=STDOUT if stderr else PIPE,
                  bufsize=-1, env=cmd_env, close_fds=True,
                  preexec_fn=_child_prep_fn)

        if not to_file:
            reader = AsyncReader(p.stdout, sizelimit, binary)
        else:
            reader = FakeReader(p, binary)

        if poller:
            while reader.running:
                _check_poller(p)
        else:
            try:
                # override timeout=0 to timeout=None, as Popen will treat the
                # former as a literal 0-second timeout
                p.wait(timeout if timeout else None)
            except Exception:
                p.terminate()
                if to_file:
                    _output.close()
                # until we separate timeouts from the `timeout` command
                # handle per-cmd timeouts via Plugin status checks
                reader.running = False
                return {'status': 124, 'output': reader.get_contents(),
                        'truncated': reader.is_full}
        if to_file:
            _output.close()

        # wait for Popen to set the returncode
        while p.poll() is None:
            pass

        stdout = reader.get_contents()
        truncated = reader.is_full

    except OSError as e:
        if to_file:
            _output.close()
        if e.errno == errno.ENOENT:
            return {'status': 127, 'output': "", 'truncated': ''}
        else:
            raise e

    if p.returncode == 126 or p.returncode == 127:
        stdout = b""

    return {
        'status': p.returncode,
        'output': stdout,
        'truncated': truncated
    }


def import_module(module_fqname, superclasses=None):
    """Imports the module module_fqname and returns a list of defined classes
    from that module. If superclasses is defined then the classes returned will
    be subclasses of the specified superclass or superclasses. If superclasses
    is plural it must be a tuple of classes."""
    module_name = module_fqname.rpartition(".")[-1]
    try:
        module = __import__(module_fqname, globals(), locals(), [module_name])
    except ImportError as e:
        print(f'Error while trying to load module {module_fqname}: '
              f' {e.__class__.__name__}')
        raise e
    modules = [class_ for cname, class_ in
               inspect.getmembers(module, inspect.isclass)
               if class_.__module__ == module_fqname]
    if superclasses:
        modules = [m for m in modules if issubclass(m, superclasses)]

    return modules


def shell_out(cmd, timeout=30, chroot=None, runat=None):
    """Shell out to an external command and return the output or the empty
    string in case of error.
    """
    return sos_get_command_output(cmd, timeout=timeout,
                                  chroot=chroot, chdir=runat)['output']


def get_human_readable(size, precision=2):
    # Credit to Pavan Gupta https://stackoverflow.com/questions/5194057/
    suffixes = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    suffixindex = 0
    while size > 1024 and suffixindex < 4:
        suffixindex += 1
        size = size/1024.0
    return f"{size:.{precision}f}{suffixes[suffixindex]}"


def _os_wrapper(path, sysroot, method, module=os.path):
    if sysroot and sysroot != os.sep:
        if not path.startswith(sysroot):
            path = os.path.join(sysroot, path.lstrip('/'))
    _meth = getattr(module, method)
    return _meth(path)


def path_exists(path, sysroot):
    if '*' in path:
        return _os_wrapper(path, sysroot, 'glob', module=glob)
    return _os_wrapper(path, sysroot, 'exists')


def path_isdir(path, sysroot):
    return _os_wrapper(path, sysroot, 'isdir')


def path_isfile(path, sysroot):
    return _os_wrapper(path, sysroot, 'isfile')


def path_islink(path, sysroot):
    return _os_wrapper(path, sysroot, 'islink')


def listdir(path, sysroot):
    return _os_wrapper(path, sysroot, 'listdir', os)


def path_join(path, *p, sysroot=os.sep):
    if sysroot and not path.startswith(sysroot):
        path = os.path.join(sysroot, path.lstrip(os.sep))
    return os.path.join(path, *p)


def bold(text):
    """Helper to make text bold in console output, without pulling in
    dependencies to the project unneccessarily.

    :param text:    The text to make bold
    :type text:     ``str``

    :returns:       The text wrapped in the ASCII codes to display as bold
    :rtype:         ``str``
    """
    return '\033[1m' + text + '\033[0m'


def recursive_dict_values_by_key(dobj, keys=[]):
    """Recursively compile all elements of a potentially nested dict by a set
    of keys. If a given key is a dict within ``dobj``, then _all_ elements
    within that dict, regardless of child keys, will be returned.

    For example, if a Plugin searches the devices dict for the 'storage' key,
    then all storage devices under the that dict (e.g. block, fibre, etc...)
    will be returned. However, if the Plugin specifies 'block' via ``keys``,
    then only the block devices within the devices['storage'] dict will be
    returned.

    Any elements passed here that are _not_ keys within the dict or any nested
    dicts will also be returned.

    :param dobj:    The 'top-level' dict to intially search by
    :type dobj:     ``dict``

    :param keys:    Which keys to compile elements from within ``dobj``. If no
                    keys are given, all nested elements are returned
    :param keys:    ``list`` of ``str``

    :returns:       All elements within the dict and any nested dicts
    :rtype:         ``list``
    """
    _items = []
    _filt = []
    _items.extend(keys)
    if isinstance(dobj, dict):
        for k, v in dobj.items():
            _filt.append(k)
            # get everything below this key, including nested dicts
            if not keys or k in keys:
                _items.extend(recursive_dict_values_by_key(v))
            # recurse into this dict only for dict keys that match what
            # we're looking for
            elif isinstance(v, dict):
                try:
                    # this will return a nested list, extract it
                    _items.extend(
                        recursive_dict_values_by_key(
                            v[key] for key in keys if key in v
                        )[0]
                    )
                except IndexError:
                    # none of the keys given exist in the nested dict
                    pass
                _filt.extend(v.keys())

    else:
        _items.extend(dobj)

    return [d for d in _items if d not in _filt]


class FakeReader():
    """Used as a replacement AsyncReader for when we are writing directly to
    disk, and allows us to keep more simplified flows for executing,
    monitoring, and collecting command output.
    """

    def __init__(self, process, binary):
        self.process = process
        self.binary = binary

    @property
    def is_full(self):
        return False

    def get_contents(self):
        return '' if not self.binary else b''

    @property
    def running(self):
        return self.process.poll() is None


class AsyncReader(threading.Thread):
    """Used to limit command output to a given size without deadlocking
    sos.

    Takes a sizelimit value in MB, and will compile stdout from Popen into a
    string that is limited to the given sizelimit.
    """

    def __init__(self, channel, sizelimit, binary):
        super(AsyncReader, self).__init__()
        self.chan = channel
        self.binary = binary
        self.chunksize = 2048
        self.slots = None
        if sizelimit:
            sizelimit = sizelimit * 1048576  # convert to bytes
            self.slots = int(sizelimit / self.chunksize)
        self.deque = deque(maxlen=self.slots)
        self.running = True
        self.start()

    def run(self):
        """Reads from the channel (pipe) that is the output pipe for a
        called Popen. As we are reading from the pipe, the output is added
        to a deque. After the size of the deque exceeds the sizelimit
        earlier (older) entries are removed.

        This means the returned output is chunksize-sensitive, but is not
        really byte-sensitive.
        """
        try:
            while True:
                line = self.chan.read(self.chunksize)
                if not line:
                    # Pipe can remain open after output has completed
                    break
                self.deque.append(line)
        except (ValueError, IOError):
            # pipe has closed, meaning command output is done
            pass
        self.running = False

    def get_contents(self):
        """Returns the contents of the deque as a string"""
        # block until command completes or timesout (separate from the plugin
        # hitting a timeout)
        while self.running:
            time.sleep(0.01)
        if not self.binary:
            return ''.join(ln.decode('utf-8', 'ignore') for ln in self.deque)
        else:
            return b''.join(ln for ln in self.deque)

    @property
    def is_full(self):
        """Checks if the deque is full, implying that output was truncated"""
        if not self.slots:
            return False
        return len(self.deque) == self.slots


class ImporterHelper(object):
    """Provides a list of modules that can be imported in a package.
    Importable modules are located along the module __path__ list and modules
    are files that end in .py.
    """

    def __init__(self, package):
        """package is a package module
        import my.package.module
        helper = ImporterHelper(my.package.module)"""
        self.package = package

    def _plugin_name(self, path):
        "Returns the plugin module name given the path"
        base = os.path.basename(path)
        name, ext = os.path.splitext(base)
        return name

    def _get_plugins_from_list(self, list_):
        plugins = [self._plugin_name(plugin)
                   for plugin in list_
                   if "__init__" not in plugin and plugin.endswith(".py")]
        plugins.sort()
        return plugins

    def _find_plugins_in_dir(self, path):
        if os.path.exists(path):
            py_files = list(find("*.py", path))
            pnames = self._get_plugins_from_list(py_files)
            if pnames:
                return pnames
        return []

    def get_modules(self):
        """Returns the list of importable modules in the configured python
        package. """
        plugins = []
        for path in self.package.__path__:
            if os.path.isdir(path):
                plugins.extend(self._find_plugins_in_dir(path))

        return plugins


class TempFileUtil():

    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
        self.files = []

    def new(self):
        fd, fname = tempfile.mkstemp(dir=self.tmp_dir)
        # avoid TOCTOU race by using os.fdopen()
        fobj = os.fdopen(fd, 'w+')
        self.files.append((fname, fobj))
        return fobj

    def clean(self):
        for fname, f in self.files:
            try:
                f.flush()
                f.close()
            except Exception:
                # file already closed or potentially already removed, ignore
                pass
            try:
                os.unlink(fname)
            except Exception:
                # if the above failed, this is also likely to fail, ignore
                pass
        self.files = []


class SoSTimeoutError(OSError):
    pass

# vim: set et ts=4 sw=4 :
