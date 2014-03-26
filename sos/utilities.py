### This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# pylint: disable-msg = R0902
# pylint: disable-msg = R0904
# pylint: disable-msg = W0702
# pylint: disable-msg = W0703
# pylint: disable-msg = R0201
# pylint: disable-msg = W0611
# pylint: disable-msg = W0613

from __future__ import with_statement

import os
import re
import inspect
from stat import *
#from itertools import *
from subprocess import Popen, PIPE, STDOUT
import logging
import zipfile
import tarfile
import hashlib
import logging
import fnmatch

from contextlib import closing

# PYCOMPAT
import six
from six import StringIO

import time

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
        except:
            log = logging.getLogger('sos')
            log.debug("fileobj: %s could not be opened" % path_or_file)
            return closing(StringIO())
    else:
        return closing(path_or_file)

def checksum(file_, chunk_size=128, algorithm=None):
    """Returns the checksum of the supplied filename. The file is read in
    chunk_size blocks"""
    if not algorithm:
        algorithm = get_hash_name()
    digest = hashlib.new(algorithm)
    with fileobj(file_, 'rb') as fd:
        data = fd.read(chunk_size)
        while data:
            digest.update(six.b(data))
            data = fd.read(chunk_size)
        return digest.hexdigest()

def get_hash_name():
    """Returns the algorithm used when computing a hash"""
    import sos.policies
    policy = sos.policies.load()
    try:
        name = policy.get_preferred_hash_algorithm()
        hashlib.new(name)
        return name
    except:
        return 'sha256'

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
    """generator function to find files recursively. Usage:

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
    """Returns lines matched in fnames, where fnames can either be pathnames to files
    to grep through or open file objects to grep through line by line"""
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

def sos_get_command_output(command, timeout=300):
    """Execute a command through the system shell. First checks to see if the
    requested command is executable. Returns (returncode, stdout, 0)"""
    # XXX: what is this doing this for?
    cmdfile = command.strip("(").split()[0]

    cmd_env = os.environ
    # ensure consistent locale for collected command output
    cmd_env['LC_ALL'] = 'C'
    if is_executable(cmdfile):

        # use /usr/bin/timeout to implement a timeout
        if timeout and is_executable("/usr/bin/timeout"):
            command = "/usr/bin/timeout %ds %s" % (timeout, command)

        p = Popen(command, shell=True,
                stdout=PIPE, stderr=STDOUT,
                bufsize=-1, env = cmd_env, close_fds = True)
        stdout, stderr = p.communicate()
        return (p.returncode, stdout.decode('utf-8'), 0)
    else:
        return (127, "", 0)

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

def shell_out(cmd):
    """Uses subprocess.Popen to make a system call and returns stdout.
    Does not handle exceptions."""
    return sos_get_command_output(cmd)[1]

class ImporterHelper(object):
    """Provides a list of modules that can be imported in a package.
    Importable modules are located along the module __path__ list and modules
    are files that end in .py. This class will read from PKZip archives as well
    for listing out jar and egg contents."""

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
                if "__init__" not in plugin
                and plugin.endswith(".py")]
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

    def _get_path_to_zip(self, path, tail_list=None):
        if not tail_list:
            tail_list = ['']

        if path.endswith(('.jar', '.zip', '.egg')):
            return path, os.path.join(*tail_list)

        head, tail = os.path.split(path)
        tail_list.insert(0, tail)

        if head == path:
            raise Exception("not a zip file")
        else:
            return self._get_path_to_zip(head, tail_list)


    def _find_plugins_in_zipfile(self, path):
        try:
            path_to_zip, tail = self._get_path_to_zip(path)
            zf = zipfile.ZipFile(path_to_zip)
            # the path will have os separators, but the zipfile will always have '/'
            tail = tail.replace(os.path.sep, "/")
            root_names = [name for name in zf.namelist() if tail in name]
            candidates = self._get_plugins_from_list(root_names)
            zf.close()
            if candidates:
                return candidates
            else:
                return []
        except (IOError, Exception):
            return []

    def get_modules(self):
        "Returns the list of importable modules in the configured python package."
        plugins = []
        for path in self.package.__path__:
            if os.path.isdir(path) or path == '':
                plugins.extend(self._find_plugins_in_dir(path))
            else:
                plugins.extend(self._find_plugins_in_zipfile(path))

        return plugins
