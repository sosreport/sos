# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
import pwd
import re
import inspect
from subprocess import Popen, PIPE, STDOUT, SubprocessError, TimeoutExpired
import logging
import fnmatch
import errno
import shlex
import glob
import shutil
import signal
import sys
import tempfile
import threading
import time
import io
import mmap
import zlib

# pylint: disable-next=no-name-in-module
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from collections import deque

try:
    import lzma
except ImportError:
    # a Python built without it: no xz archives, see BlockXZFile
    lzma = None

try:
    from packaging.version import parse as parse_version
except ImportError:
    from pkg_resources import parse_version

log = logging.getLogger('sos')

# try loading magic>=0.4.20 which implements detect_from_filename method
magic_mod = False
try:
    import magic
    magic.detect_from_filename(__file__)
    magic_mod = True
except (ImportError, AttributeError):
    from textwrap import fill
    msg = """\
WARNING: Failed to load 'magic' module version >= 0.4.20 which sos aims to \
use for detecting binary files. A less effective method will be used. It is \
recommended to install proper python3-magic package with the module.
"""
    log.warning(f'\n{fill(msg, 72, replace_whitespace=False)}\n')


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
    'tac_logs',
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
            return open(path_or_file, mode, encoding='utf-8')
        except IOError:
            log.debug(f"fileobj: {path_or_file} could not be opened")
            return closing(io.StringIO())
    else:
        return closing(path_or_file)


def convert_bytes(num_bytes):
    """Converts a number of bytes to a shorter, more human friendly format"""
    sizes = {'T': 1 << 40, 'G': 1 << 30, 'M': 1 << 20, 'K': 1 << 10}
    for symbol, size in sizes.items():
        if num_bytes >= size:
            return f"{float(num_bytes) / size:.1f}{symbol}"
    return f"{num_bytes}"


def file_is_certificate(fname):
    """Helper to determine if a given file is a certificate or not.

    This is especially helpful for `sos clean`, which cannot obfuscate
    certificate files content and instead, by default, will keep them as is.

    :param fname:   The full path of the file to check
    :type fname:    ``str``

    :returns:   The type of the certificate or ``None``
    :rtype:     ``string`` or ``None``
    """
    if fname[-4:] in [".csr", ".crt", ".pem"]:
        with open(fname, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(r'-----BEGIN CERTIFICATE-----', content):
                return "certificate"
            if re.search(r'-----BEGIN [A-Z]+ PRIVATE KEY-----', content):
                return "certificatekey"
        return None
    return None


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
            # since `magic` (as well as "file" cmd) treats audit logs as
            # binary files due to 0x1d separator, we need to explicitly mark
            # audit.log and audit.log.[1-9]* as non-binary
            return (
                _ftup.encoding == 'binary' and not
                any(_ftup.mime_type.startswith(_mt) for _mt in _mimes) and not
                bool(re.search(r'audit\.log(?:\.[1-9]\d*)?$', fname))
            )
        except Exception:
            pass
    # if for some reason the above check fails or magic>=0.4.20 is not present,
    # fail over to checking the very first byte of the file content
    with open(fname, 'tr', encoding='utf-8') as tfile:
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


def scrub_url_credential(url: str):
    """
    Replace username:password@ with ********@ in proxy URL if present
    """
    from urllib.parse import urlparse, urlunparse
    try:
        parsed_url = urlparse(url)
        if parsed_url.username or parsed_url.password:
            netloc = "********@"
            if parsed_url.hostname:
                netloc += parsed_url.hostname
            if parsed_url.port:
                netloc += f":{parsed_url.port}"
            return urlunparse((
                parsed_url.scheme, netloc, parsed_url.path,
                parsed_url.params, parsed_url.query, parsed_url.fragment
            ))
        return url
    except Exception:  # pylint: disable=broad-except
        return url


def sos_get_command_output(command, timeout=TIMEOUT_DEFAULT, stderr=False,
                           chroot=None, chdir=None, env=None, foreground=False,
                           binary=False, sizelimit=None, poller=None,
                           to_file=False, tac=False, runas=None, stdin=None):
    # pylint: disable=too-many-locals,too-many-branches
    """Execute a command and return a dictionary of status and output,
    optionally changing root or current working directory before
    executing command.

    :param stdin: If not ``None``, open a pipe to the child's stdin and
        write this value (``str`` is encoded as UTF-8, ``bytes`` is sent
        as-is). If ``None``, the child inherits the parent's stdin.
    """
    # Change root or cwd for child only. Exceptions in the prexec_fn
    # closure are caught in the parent (chroot and chdir are bound from
    # the enclosing scope).
    def _child_prep_fn():
        if chroot and chroot != '/':
            os.chroot(chroot)
        if runas:
            # re-use pwd_user from the outer scope to avoid redundant lookups
            os.initgroups(runas, pwd_user.pw_gid)
            os.setgid(pwd_user.pw_gid)
            os.setuid(pwd_user.pw_uid)

        # prioritize explicit chdir and failback only if runas is set and
        # no explicit chdir was provided.
        if chdir:
            os.chdir(chdir)
        elif runas:
            os.chdir(pwd_user.pw_dir)

    def _check_poller(proc):
        if poller():
            proc.terminate()
            raise SoSTimeoutError
        time.sleep(0.01)

    def _timed_out(proc):
        # timeout exits with 124, or if it had to kill the command after it
        # ignored termination, with the status of SIGKILL. Outside of
        # foreground mode, that kill includes timeout itself
        if proc.returncode == 124:
            return True
        return (proc.returncode in (128 + signal.SIGKILL, -signal.SIGKILL)
                and wrapped and time.monotonic() - start >= timeout)

    def _release_reader(proc, reader):
        # After a timeout, give the command a moment to exit and the reader a
        # moment to consume any remaining output. A child of the command may
        # still hold stdout open, so the reader is not allowed to block us
        # indefinitely.
        try:
            # timeout kills the command 1 second after terminating it
            proc.wait(timeout=2)
        except TimeoutExpired:
            proc.kill()
            proc.wait()
        for _ in range(100):
            if not reader.running:
                return
            time.sleep(0.01)
        # leave the pipe for the reader to close once it drains, as closing
        # it here would block until the reader's pending read() returns
        proc.stdout = None
        reader.abandon()

    if runas:
        try:
            pwd_user = pwd.getpwnam(runas)
        except KeyError:  # no such user
            return {'status': 127, 'output': "", 'truncated': ''}

        # handle env=None case to prevent AttributeError on None.update()
        if env is None:
            env = {}

        env.update({
            'HOME': pwd_user.pw_dir,
            'LOGNAME': runas,
            'PWD': pwd_user.pw_dir,
            'USER': runas,
            # XDG_RUNTIME_DIR is required for rootless podman to access
            # user-specific runtime files and sockets
            'XDG_RUNTIME_DIR': f"/run/user/{pwd_user.pw_uid}",
            # DBUS_SESSION_BUS_ADDRESS is required for rootless podman
            'DBUS_SESSION_BUS_ADDRESS':
                f"unix:path=/run/user/{pwd_user.pw_uid}/bus"
        })

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
    # use /usr/bin/timeout to implement a timeout, killing the command if it
    # ignores termination
    wrapped = bool(timeout and is_executable("timeout"))
    if wrapped:
        command = (f"timeout {'--foreground' if foreground else ''} -k 1s "
                   f"{timeout}s {command}")

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
        if sizelimit:
            # going to use HeadReader
            _output = PIPE
        elif tac:
            # no limit but we need an intermediate file
            _output = tempfile.TemporaryFile(dir=os.path.dirname(to_file))
        else:
            # pylint: disable=consider-using-with
            _output = open(to_file, 'wb')
    else:
        _output = PIPE
    _stdin = PIPE if stdin is not None else None
    start = time.monotonic()
    try:
        with Popen(expanded_args, shell=False, stdin=_stdin, stdout=_output,
                   stderr=STDOUT if stderr else PIPE,
                   bufsize=-1, env=cmd_env, close_fds=True,
                   preexec_fn=_child_prep_fn) as p:
            stdin_writer = None
            try:
                if to_file:
                    if sizelimit:
                        if tac:
                            _output = tempfile.TemporaryFile(
                                dir=os.path.dirname(to_file)
                            )
                        else:
                            # pylint: disable=consider-using-with
                            _output = open(to_file, 'wb')
                        reader = HeadReader(p.stdout, _output, sizelimit,
                                            binary)
                    else:
                        reader = FakeReader(p, binary)
                else:
                    reader = TailReader(p.stdout, sizelimit, binary)

                if stdin is not None:
                    stdin_writer = StdinWriter(p.stdin, stdin)

                if poller:
                    try:
                        # the reader may finish before the command exits,
                        # e.g. once a sizelimit is reached
                        while p.poll() is None or reader.running:
                            _check_poller(p)
                            if p.returncode is not None and _timed_out(p):
                                # the command itself timed out
                                _release_reader(p, reader)
                                break
                    except SoSTimeoutError:
                        _release_reader(p, reader)
                        raise
                else:
                    try:
                        # override timeout=0 to timeout=None, as Popen will
                        # treat the former as a literal 0-second timeout
                        p.wait(timeout if timeout else None)
                        if _timed_out(p):
                            _release_reader(p, reader)
                    except Exception:
                        p.terminate()
                        _release_reader(p, reader)
                        if to_file:
                            if tac:
                                with open(to_file, 'wb') as f_dst:
                                    tac_logs(_output, f_dst, True)
                        # until we separate timeouts from the `timeout` command
                        # handle per-cmd timeouts via Plugin status checks
                        return {'status': 124,
                                'output': reader.get_contents(),
                                'truncated': reader.is_full}

                if to_file and tac:
                    with open(to_file, 'wb') as f_dst:
                        tac_logs(_output, f_dst,
                                 reader.is_full or p.returncode != 0)

                if p.returncode in (126, 127):
                    stdout = b""
                else:
                    stdout = reader.get_contents()

                return {
                    'status': 124 if _timed_out(p) else p.returncode,
                    'output': stdout,
                    'truncated': reader.is_full
                }
            finally:
                if stdin_writer is not None:
                    # the command has exited, but a child of it may still
                    # hold stdin open without reading from it
                    stdin_writer.join(timeout=1)
                    if stdin_writer.is_alive():
                        # closing stdin would block on the pending write
                        p.stdin = None
                        log.warning(f"Passing stdin to command {command} "
                                    "did not complete")
                    elif stdin_writer.error:
                        log.warning(f"Passing stdin to command {command} "
                                    f"raised an error: {stdin_writer.error}")
    except OSError as e:
        if e.errno == errno.ENOENT:
            return {'status': 127, 'output': "", 'truncated': ''}
        raise e
    except SubprocessError:
        # Handle exceptions in preexec_fn (e.g., user switching failures)
        # Return 126 (command cannot execute)
        return {'status': 126, 'output': "", 'truncated': ''}
    finally:
        if hasattr(_output, 'close'):
            _output.close()


def tac_logs(f_src, f_dst, drop_last_log=False):
    """Python implementation of the tac utility with support
    for multiline logs (starting with space). It is intended
    to reverse the output of 'journalctl --reverse'.
    """
    NEWLINE_B = b'\n'
    NEWLINE_I = 10
    SPACE_I = 32
    # make sure all python/libc buffers are flushed
    # else fstat()/mmap() might see partial data
    f_src.flush()
    if os.fstat(f_src.fileno()).st_size == 0:
        return
    with mmap.mmap(f_src.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        sep1 = sep2 = mm.size()-1
        if mm[sep2] != NEWLINE_I:
            drop_last_log = True
        while sep2 >= 0:
            sep1 = mm.rfind(NEWLINE_B, 0, sep1)
            # multiline logs have a first line not starting with space
            # followed by lines starting with spaces
            # line 5
            # line 4
            #  multiline 4
            # line 3
            if mm[sep1+1] == SPACE_I:
                # first line starts with a space
                # (this should not happen)
                if sep1 == -1:
                    break
                # go find the previous NEWLINE
                continue
            # When we truncate or timeout, the last log
            # might be a partial multiline log
            if drop_last_log:
                drop_last_log = False
            else:
                # write the (multi)line log ending with the NEWLINE
                f_dst.write(mm[sep1+1:sep2+1])
            sep2 = sep1


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
    dependencies to the project unnecessarily.

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

    :param dobj:    The 'top-level' dict to initially search by
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


class StdinWriter(threading.Thread):
    """Write bytes to a Popen child's stdin without blocking the main thread"""

    CHUNK = 64 * 1024

    def __init__(self, stdin_pipe, data):
        # daemonize so an abandoned writer cannot block sos from exiting
        super().__init__(daemon=True)
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._stdin = stdin_pipe
        self._data = memoryview(data) if data else None
        self.error = ''
        self.start()

    def run(self):
        if self._stdin is None:
            return
        try:
            if self._data:
                offset = 0
                total = len(self._data)
                while offset < total:
                    chunk = self._data[offset:offset + self.CHUNK]
                    n = self._stdin.write(chunk)
                    if n is None:
                        continue
                    offset += n
                self._stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            # pass error to the main thread
            self.error = str(exc)
        finally:
            try:
                self._stdin.close()
            except (BrokenPipeError, ValueError) as exc:
                # pass error to the main thread
                self.error += str(exc)


class ProgressBar:
    """Displays a terminal progress bar that overwrites itself in place."""

    def __init__(self, prefix, total, format_fn=None):
        self.prefix = prefix
        self.total = total
        self.format_fn = format_fn or str
        suffix_width = len(
            f" {self.format_fn(total)} / {self.format_fn(total)}"
        )
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        # Keeping bar width between 5 and 40 based on the size of the terminal
        # minus the size of prefix, suffix and surrounding "[]" brackets
        self.bar_width = max(5, min(40, cols - len(prefix) - suffix_width - 2))
        self._last_width = 0

    def update(self, done):
        filled = done * self.bar_width // self.total
        content = (
            f"{self.prefix}[{'=' * filled}{' ' * (self.bar_width - filled)}]"
            f" {self.format_fn(done)} / {self.format_fn(self.total)}"
        )
        padding = ' ' * max(0, self._last_width - len(content))
        sys.stdout.write(f"\r{content}{padding}")
        self._last_width = len(content)
        sys.stdout.flush()

    def finish(self):
        self.update(self.total)
        sys.stdout.write('\n')
        sys.stdout.flush()


class FakeReader():
    """Used when we are writing directly to disk without sizelimits,
    this allows us to keep more simplified flows for executing,
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

    def abandon(self):
        """Output is written directly to disk, there is no pipe to release"""


class HeadReader(threading.Thread):
    """Used to 'head' the command output (f_src) to a given size
    without deadlocking sos. Takes a sizelimit value in MB.
    """

    COPY_BUFSIZE = 1024*1024

    def __init__(self, f_src, f_dst, sizelimit, binary):
        # daemonize so an abandoned reader cannot block sos from exiting
        super().__init__(daemon=True)
        self.f_src = f_src
        self.f_dst = f_dst
        self.remaining = sizelimit * 1048576  # convert to bytes
        self.binary = binary
        self.abandoned = False
        self.running = True
        self.start()

    def run(self):
        """Reads from the f_src (Popen stdout pipe) until we reach sizelimit.
        once done, close f_src to signal the program that we are done.
        """
        try:
            while self.remaining > 0:
                try:
                    # read1() returns whatever is available instead of
                    # blocking until a full buffer, so partial output is
                    # still written if the command times out
                    buf = self.f_src.read1(
                        min(self.remaining, self.COPY_BUFSIZE))
                except (ValueError, IOError):
                    # a pipe error, terminate
                    break
                if not buf or self.abandoned:
                    break
                self.f_dst.write(buf)
                self.remaining -= len(buf)
        except (ValueError, IOError):
            # the destination could not be written to (e.g. ENOSPC);
            # keep what was copied so far and stop
            pass
        finally:
            try:
                self.f_src.close()
            except (ValueError, IOError):
                # the pipe is already broken or closed, nothing to release
                pass
            # always clear the flag, sos_get_command_output() polls it
            self.running = False

    def abandon(self):
        """Stop waiting on this reader. Any further output is discarded, and
        the reader closes the pipe once its pending read returns
        """
        self.abandoned = True
        self.running = False

    def get_contents(self):
        return '' if not self.binary else b''

    @property
    def is_full(self):
        return self.remaining <= 0


class TailReader(threading.Thread):
    """Used to tail the command output to a given size without deadlocking
    sos.

    Takes a sizelimit value in MB, and will compile stdout from Popen into a
    string that is limited to the given sizelimit.
    """

    CHUNKSIZE = 64 * 1024

    def __init__(self, channel, sizelimit, binary):
        # daemonize so an abandoned reader cannot block sos from exiting
        super().__init__(daemon=True)
        self.chan = channel
        self.binary = binary
        self.limit = int(sizelimit * 1048576) if sizelimit else None
        self.size = 0
        self.truncated = False
        self.deque = deque()
        self.abandoned = False
        self.running = True
        self.start()

    def run(self):
        """Reads from the channel (pipe) that is the output pipe for a
        called Popen. As we are reading from the pipe, the output is added
        to a deque. Once the output exceeds the sizelimit, the earliest
        output is removed.
        """
        try:
            while True:
                # read1() returns whatever is available instead of blocking
                # until a full chunk, so partial output is still kept if the
                # command times out
                chunk = self.chan.read1(self.CHUNKSIZE)
                if not chunk or self.abandoned:
                    break
                self._append(chunk)
        except (ValueError, IOError):
            # pipe has closed, meaning command output is done
            pass
        finally:
            try:
                self.chan.close()
            except (ValueError, IOError):
                # the pipe is already broken or closed, nothing to release
                pass
            self.running = False

    def _append(self, chunk):
        self.deque.append(chunk)
        self.size += len(chunk)
        while self.limit and self.size > self.limit:
            excess = self.size - self.limit
            if len(self.deque[0]) <= excess:
                self.size -= len(self.deque.popleft())
            else:
                self.deque[0] = self.deque[0][excess:]
                self.size -= excess
            self.truncated = True

    def abandon(self):
        """Stop waiting on this reader. Any further output is discarded, and
        the reader closes the pipe once its pending read returns
        """
        self.abandoned = True
        self.running = False

    def get_contents(self):
        """Returns the contents of the deque as a string"""
        # block until command completes or timesout (separate from the plugin
        # hitting a timeout)
        while self.running:
            time.sleep(0.01)
        # an abandoned reader may still be finishing its last append
        contents = b''.join(self.deque.copy())
        if not self.binary:
            return contents.decode('utf-8', 'ignore')
        return contents

    @property
    def is_full(self):
        """Checks if the output was truncated to the sizelimit"""
        return self.truncated


class ImporterHelper:
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
        name, _ = os.path.splitext(base)
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


class BlockXZFile():
    """A file for ``tarfile`` to write an xz archive to, compressed on
    several threads. The lzma module compresses on one, which for a large
    archive takes longer than everything before it.

    What is written is cut into blocks of ``BLOCK`` bytes, each of which
    is compressed on its own. The file is one xz stream with a block for
    each, in the order written, as ``xz --threads`` writes: every reader
    of xz reads it, and it is a little larger than a stream of one block.
    It holds the same bytes whatever the number of threads.

    The lzma module only writes whole streams, of one block each. Each
    block is compressed as such a stream; what goes to the file is the
    first one's header, the block of each, then an index of all the
    blocks and the footer, written here as the xz file format has them.

    :param path:        The file to write
    :type path:         ``str``

    :param threads:     How many blocks to compress at one time; each one
                        in progress is held in memory, in chunks of
                        ``CHUNK`` bytes, never as one piece
    :type threads:      ``int``

    :param preset:      The xz preset
    :type preset:       ``int``
    """

    BLOCK = 16 * 1024 * 1024
    CHUNK = 1024 * 1024
    HEADER_MAGIC = b'\xfd7zXZ\x00'
    FOOTER_MAGIC = b'YZ'
    # a stream's header and its footer are this long
    FRAME = 12

    def __init__(self, path, threads=1, preset=3):
        if lzma is None:
            raise ImportError('the lzma module is not available')
        # pylint: disable=consider-using-with
        self._file = open(path, 'wb')
        self._preset = preset
        self._threads = max(threads, 1)
        self._pool = ThreadPoolExecutor(max_workers=self._threads)
        # the blocks being compressed, in the order written
        self._pending = deque()
        # what tarfile's small writes leave until there is a chunk of it,
        # and the chunks of the block being filled, and their size
        self._buffer = bytearray()
        self._chunks = []
        self._held = 0
        self._position = 0
        self._taken = 0
        # the header of the stream, once written, and what the index
        # says of each block written: its size in the file without its
        # padding, and the size of what it holds
        self._header = None
        self._records = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args):
        if exc_type is None:
            self.close()
        else:
            # what failed is not to be hidden by an error from here, and
            # what is left is not worth compressing or waiting for
            self._release(wait=False)

    def tell(self):
        """How many bytes have been written, before compression"""
        return self._position

    def write(self, data):
        self._buffer += data
        self._position += len(data)
        while len(self._buffer) >= self._room():
            self._take(self._room())
        return len(data)

    def _room(self):
        """How much the next chunk takes: a chunk, or what the block being
        filled has room for"""
        return min(self.CHUNK, self.BLOCK - self._held)

    def _take(self, size):
        """Move the first ``size`` bytes written to the block being
        filled, and hand the block to a thread once it is full"""
        self._chunks.append(bytes(self._buffer[:size]))
        del self._buffer[:size]
        self._held += size
        if self._held == self.BLOCK:
            self._compress(self._chunks)
            self._chunks, self._held = [], 0

    @staticmethod
    def _pack(chunks, preset):
        """The xz stream of one block, compressed from its ``chunks`` one
        after another, each let go once it is compressed"""
        packer = lzma.LZMACompressor(preset=preset)
        parts = []
        for at, chunk in enumerate(chunks):
            parts.append(packer.compress(chunk))
            chunks[at] = None
        parts.append(packer.flush())
        return b''.join(parts)

    @staticmethod
    def _number(value):
        """``value`` as the file format writes a number of any size:
        seven bits a byte, the lowest first, the top bit set on every
        byte but the last
        """
        out = bytearray()
        while value >= 0x80:
            # the low seven bits with the top bit set, as more bytes
            # follow, then shift the next seven bits down
            out.append(value & 0x7f | 0x80)
            value >>= 7
        out.append(value)
        return bytes(out)

    @staticmethod
    def _read_number(data, at):
        """The number at ``data[at]`` and where the next thing starts"""
        value = shift = 0
        while True:
            byte = data[at]
            at += 1
            # the byte's low seven bits go above those read so far; a byte
            # without the top bit set is the last
            value |= (byte & 0x7f) << shift
            if not byte & 0x80:
                return value, at
            shift += 7

    def _pump(self):
        """Write the block that has waited longest, once it is compressed:
        what its stream holds between its header and its index, which
        the footer gives the size of. The index says what to put in the
        index of this file.
        """
        packed = self._pending.popleft().result()
        frame = self.FRAME
        if packed[:6] != self.HEADER_MAGIC or packed[-2:] != self.FOOTER_MAGIC:
            raise lzma.LZMAError('compressed block is not an xz stream')
        index_size = (int.from_bytes(packed[-8:-4], 'little') + 1) * 4
        index = packed[-frame - index_size:-frame]
        count, at = self._read_number(index, 1)
        for _ in range(count):
            unpadded, at = self._read_number(index, at)
            held, at = self._read_number(index, at)
            self._records.append((unpadded, held))
        if self._header is None:
            self._header = packed[:frame]
            self._file.write(self._header)
        self._file.write(packed[frame:-frame - index_size])

    def _compress(self, block):
        # no more blocks are held than there are threads to take them
        while len(self._pending) >= self._threads:
            self._pump()
        self._pending.append(
            self._pool.submit(self._pack, block, self._preset))
        self._taken += 1

    def _end_stream(self):
        """Write the index of the blocks and the stream's footer"""
        index = bytearray(b'\x00' + self._number(len(self._records)))
        for unpadded, held in self._records:
            index += self._number(unpadded) + self._number(held)
        index += bytes(-len(index) % 4)
        index += zlib.crc32(index).to_bytes(4, 'little')
        # the size of the index and the flags the header has
        ends = (len(index) // 4 - 1).to_bytes(4, 'little') + \
            self._header[6:8]
        self._file.write(index + zlib.crc32(ends).to_bytes(4, 'little') +
                         ends + self.FOOTER_MAGIC)

    def close(self):
        """Compress what is left, write every block still pending, then
        the end of the stream, and close the file. An error from a thread
        is raised here or by the ``write()`` that waited for it.
        """
        if self.closed:
            return
        try:
            while self._buffer:
                self._take(min(len(self._buffer), self._room()))
            if self._chunks or not self._taken:
                # an archive with nothing in it is still a stream
                self._compress(self._chunks)
            while self._pending:
                self._pump()
            self._end_stream()
        finally:
            self._release(wait=True)

    def _release(self, wait):
        """Close the file as it is and take no more blocks"""
        self.closed = True
        self._pool.shutdown(wait=wait, cancel_futures=True)
        self._file.close()


class SoSTimeoutError(OSError):
    pass

# vim: set et ts=4 sw=4 :
