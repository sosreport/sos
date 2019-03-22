# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from __future__ import with_statement

import os
import re
import inspect
from subprocess import Popen, PIPE, STDOUT
import logging
import fnmatch
import errno
import shlex
import glob
import threading

from contextlib import closing
from collections import deque

# PYCOMPAT
import six


def tail(filename, number_of_bytes):
    """Returns the last number_of_bytes of filename"""
    with open(filename, "rb") as f:
        if os.stat(filename).st_size > number_of_bytes:
            f.seek(-number_of_bytes, 2)
        return f.read()


def fileobj(path_or_file, mode='r'):
    """Returns a file-like object that can be used as a context manager"""
    if isinstance(path_or_file, six.string_types):
        try:
            return open(path_or_file, mode)
        except IOError:
            log = logging.getLogger('sos')
            log.debug("fileobj: %s could not be opened" % path_or_file)
            return closing(six.StringIO())
    else:
        return closing(path_or_file)


def convert_bytes(bytes_, K=1 << 10, M=1 << 20, G=1 << 30, T=1 << 40):
    """Converts a number of bytes to a shorter, more human friendly format"""
    fn = float(bytes_)
    if bytes_ >= T:
        return '%.1fT' % (fn / T)
    elif bytes_ >= G:
        return '%.1fG' % (fn / G)
    elif bytes_ >= M:
        return '%.1fM' % (fn / M)
    elif bytes_ >= K:
        return '%.1fK' % (fn / K)
    else:
        return '%d' % bytes_


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


def is_executable(command):
    """Returns if a command matches an executable on the PATH"""

    paths = os.environ.get("PATH", "").split(os.path.pathsep)
    candidates = [command] + [os.path.join(p, command) for p in paths]
    return any(os.access(path, os.X_OK) for path in candidates)


def sos_get_command_output(command, timeout=300, stderr=False,
                           chroot=None, chdir=None, env=None,
                           binary=False, sizelimit=None, poller=None):
    """Execute a command and return a dictionary of status and output,
    optionally changing root or current working directory before
    executing command.
    """
    # Change root or cwd for child only. Exceptions in the prexec_fn
    # closure are caught in the parent (chroot and chdir are bound from
    # the enclosing scope).
    def _child_prep_fn():
        if (chroot):
            os.chroot(chroot)
        if (chdir):
            os.chdir(chdir)

    cmd_env = os.environ.copy()
    # ensure consistent locale for collected command output
    cmd_env['LC_ALL'] = 'C'
    # optionally add an environment change for the command
    if env:
        for key, value in env.items():
            if value:
                cmd_env[key] = value
            else:
                cmd_env.pop(key, None)
    # use /usr/bin/timeout to implement a timeout
    if timeout and is_executable("timeout"):
        command = "timeout %ds %s" % (timeout, command)

    # shlex.split() reacts badly to unicode on older python runtimes.
    if not six.PY3:
        command = command.encode('utf-8', 'ignore')
    args = shlex.split(command)
    # Expand arguments that are wildcard paths.
    expanded_args = []
    for arg in args:
        expanded_arg = glob.glob(arg)
        if expanded_arg:
            expanded_args.extend(expanded_arg)
        else:
            expanded_args.append(arg)
    try:
        p = Popen(expanded_args, shell=False, stdout=PIPE,
                  stderr=STDOUT if stderr else PIPE,
                  bufsize=-1, env=cmd_env, close_fds=True,
                  preexec_fn=_child_prep_fn)

        reader = AsyncReader(p.stdout, sizelimit, binary)
        if poller:
            while reader.running:
                if poller():
                    p.terminate()
                    raise SoSTimeoutError
        stdout = reader.get_contents()
        while p.poll() is None:
            pass

    except OSError as e:
        if e.errno == errno.ENOENT:
            return {'status': 127, 'output': ""}
        else:
            raise e

    if p.returncode == 126 or p.returncode == 127:
        stdout = six.binary_type(b"")

    return {
        'status': p.returncode,
        'output': stdout
    }


def import_module(module_fqname, superclasses=None):
    """Imports the module module_fqname and returns a list of defined classes
    from that module. If superclasses is defined then the classes returned will
    be subclasses of the specified superclass or superclasses. If superclasses
    is plural it must be a tuple of classes."""
    module_name = module_fqname.rpartition(".")[-1]
    module = __import__(module_fqname, globals(), locals(), [module_name])
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


class AsyncReader(threading.Thread):
    '''Used to limit command output to a given size without deadlocking
    sos.

    Takes a sizelimit value in MB, and will compile stdout from Popen into a
    string that is limited to the given sizelimit.
    '''

    def __init__(self, channel, sizelimit, binary):
        super(AsyncReader, self).__init__()
        self.chan = channel
        self.binary = binary
        self.chunksize = 2048
        slots = None
        if sizelimit:
            sizelimit = sizelimit * 1048576  # convert to bytes
            slots = int(sizelimit / self.chunksize)
        self.deque = deque(maxlen=slots)
        self.running = True
        self.start()

    def run(self):
        '''Reads from the channel (pipe) that is the output pipe for a
        called Popen. As we are reading from the pipe, the output is added
        to a deque. After the size of the deque exceeds the sizelimit
        earlier (older) entries are removed.

        This means the returned output is chunksize-sensitive, but is not
        really byte-sensitive.
        '''
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
        '''Returns the contents of the deque as a string'''
        # block until command completes or timesout (separate from the plugin
        # hitting a timeout)
        while self.running:
            pass
        if not self.binary:
            return ''.join(ln.decode('utf-8', 'ignore') for ln in self.deque)
        else:
            return b''.join(ln for ln in self.deque)


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
            else:
                return []

    def get_modules(self):
        """Returns the list of importable modules in the configured python
        package. """
        plugins = []
        for path in self.package.__path__:
            if os.path.isdir(path):
                plugins.extend(self._find_plugins_in_dir(path))

        return plugins


class SoSTimeoutError(OSError):
    pass

# vim: set et ts=4 sw=4 :
