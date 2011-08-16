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

import os
import sys
import string
import fnmatch
import inspect
from stat import *
from itertools import *
from subprocess import Popen, PIPE
import logging
import zipfile


class DirTree(object):
    """Builds an ascii representation of a directory structure"""

    def __init__(self, top_directory):
        self.directory_count = 0
        self.file_count = 0
        self.buffer = []
        self.top_directory = top_directory
        self._build_tree()

    def buf(self, s):
        self.buffer.append(s)

    def printtree(self):
        print self.as_string()

    def as_string(self):
        return "\n".join(self.buffer)

    def _build_tree(self):
        self.buf(os.path.abspath(self.top_directory))
        self.tree_i(self.top_directory, first=True)

    def _convert_bytes(self, n):
        K, M, G, T = 1 << 10, 1 << 20, 1 << 30, 1 << 40
        if n >= T:
            return '%.1fT' % (float(n) / T)
        elif n >= G:
            return '%.1fG' % (float(n) / G)
        elif n >= M:
            return '%.1fM' % (float(n) / M)
        elif n >= K:
            return '%.1fK' % (float(n) / K)
        else:
            return '%d' % n

    def _format(self, path):
        """Conditionally adds detail to paths"""
        stats = os.stat(path)
        details = {
                "filename": os.path.basename(path),
                "user": pwd.getpwuid(stats.st_uid)[0],
                "group": grp.getgrgid(stats.st_gid)[0],
                "filesize": self._convert_bytes(stats.st_size),
                }
        return "[%(user)s %(group)s %(filesize)s] %(filename)s" % details

    def tree_i(self, dir_, padding='', first=False):
        if not first:
            self.buf(padding[:-1] +
                "+-- " + self._format(os.path.abspath(dir_)))
            padding += '   '

        count = 0
        files = os.listdir(dir_)
        files.sort(key=string.lower)
        for f in files:
            count += 1
            path = os.path.join(dir_, f)

            if f.startswith("."):
                pass
            elif os.path.isfile(path):
                self.file_count += 1
                self.buf(padding + '+-- ' + self._format(path))
            elif os.path.islink(path):
                self.buf(padding +
                         '+-- ' +
                         f +
                         ' -> ' + os.path.basename(os.path.realpath(path)))
                if os.path.isdir(path):
                    self.directory_count += 1
                else:
                    self.file_count += 1
            elif os.path.isdir(path):
                self.directory_count += 1
                if count == len(files):
                    self.tree_i(path, padding + ' ')
                else:
                    self.tree_i(path, padding + '|')


class ImporterHelper(object):
    """Provides a list of modules that can be imported in a package.
    The package is located along the base_path (default = sys.path)
    and modules are files that end in .py. This class will read from
    PKZip archives as well for listing out jar and egg contents."""

    def __init__(self, package_path, base_path=sys.path):
        self.package_path = package_path
        self.base_path = base_path

    def _plugin_name(self, path):
        "Returns the plugin module name given the path"
        base = os.path.basename(path)
        name, ext = os.path.splitext(base)
        return name

    def _get_plugins_from_list(self, list_):
        plugins = [self._plugin_name(plugin)
                for plugin in list_
                if self.package_path in plugin
                and "__init__" not in plugin
                and plugin.endswith(".py")]
        plugins.sort()
        return plugins

    def _find_plugins_in_dir(self, path):
        candidate = os.path.join(path, self.package_path)
        if os.path.exists(candidate):
           pnames = self._get_plugins_from_list(
                   list(find("*.py", candidate)))
           if pnames:
               return pnames

    def _get_path_to_zip(self, path):
        if path.endswith(('.jar', '.zip', '.egg')):
            return path

        head, tail = os.path.split(path)

        if head == path:
            return path
        else:
            return self._get_path_to_zip(head)

    def _find_plugins_in_zipfile(self, path):
        try:
            zf = zipfile.ZipFile(self._get_path_to_zip(path))
            candidates = self._get_plugins_from_list(zf.namelist())
            if candidates:
                return candidates
        except IOError:
            pass

    def get_modules(self):
        "Returns the list of importable modules in the configured python package."
        for path in self.base_path:
            if os.path.isdir(path) or path == '':
                plugins = self._find_plugins_in_dir(path)
            else:
                plugins = self._find_plugins_in_zipfile(path)

            if plugins:
                return plugins
        return []

def find(file_pattern, top_dir, max_depth=None, path_pattern=None):
    """generate function to find files recursively. Usage:

    for filename in find("*.properties", /var/log/foobar):
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


def sosGetCommandOutput(command, timeout = 300):
    """ Execute a command and gather stdin, stdout, and return status.
    """
    # soslog = logging.getLogger('sos')
    # Log if binary is not runnable or does not exist
    for path in os.environ["PATH"].split(":"):
        cmdfile = command.strip("(").split()[0]
        # handle both absolute or relative paths
        if ( ( not os.path.isabs(cmdfile) and os.access(os.path.join(path,cmdfile), os.X_OK) ) or \
           ( os.path.isabs(cmdfile) and os.access(cmdfile, os.X_OK) ) ):
            break
    else:
        # soslog.log(logging.VERBOSE, "binary '%s' does not exist or is not runnable" % cmdfile)
        return (127, "", 0)

    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, bufsize=-1)
    stdout, stderr = p.communicate()
    return (p.returncode, stdout.strip(), 0)

def import_module(module_fqname, superclass=None):
    module_name = module_fqname.rpartition(".")[-1]
    module = __import__(module_fqname, globals(), locals(), [module_name])
    modules = [class_ for cname, class_ in
               inspect.getmembers(module, inspect.isclass)
               if class_.__module__ == module_fqname]
    if superclass:
        modules = [m for m in modules if issubclass(m, superclass)]

    return modules
# vim:ts=4 sw=4 et
