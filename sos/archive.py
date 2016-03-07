# Copyright (C) 2012 Red Hat, Inc.,
#   Jesse Jaggars <jjaggars@redhat.com>
#   Bryn M. Reeves <bmr@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
import os
import time
import tarfile
import shutil
import logging
import shlex
import re
import codecs
import sys

# required for compression callout (FIXME: move to policy?)
from subprocess import Popen, PIPE

from sos.utilities import sos_get_command_output, is_executable

try:
    import selinux
except ImportError:
    pass

# PYCOMPAT
import six
if six.PY3:
    long = int


class Archive(object):
    """Abstract base class for archives."""

    @classmethod
    def archive_type(class_):
        """Returns the archive class's name as a string.
        """
        return class_.__name__

    log = logging.getLogger("sos")

    _name = "unset"
    _debug = False

    def _format_msg(self, msg):
        return "[archive:%s] %s" % (self.archive_type(), msg)

    def set_debug(self, debug):
        self._debug = debug

    def log_error(self, msg):
        self.log.error(self._format_msg(msg))

    def log_warn(self, msg):
        self.log.warning(self._format_msg(msg))

    def log_info(self, msg):
        self.log.info(self._format_msg(msg))

    def log_debug(self, msg):
        if not self._debug:
            return
        self.log.debug(self._format_msg(msg))

    # this is our contract to clients of the Archive class hierarchy.
    # All sub-classes need to implement these methods (or inherit concrete
    # implementations from a parent class.
    def add_file(self, src, dest=None):
        raise NotImplementedError

    def add_string(self, content, dest):
        raise NotImplementedError

    def add_link(self, source, link_name):
        raise NotImplementedError

    def add_dir(self, path):
        raise NotImplementedError

    def add_node(self, path, mode, device):
        raise NotImplementedError

    def get_tmp_dir(self):
        """Return a temporary directory that clients of the archive may
        use to write content to. The content of the path is guaranteed
        to be included in the generated archive."""
        raise NotImplementedError

    def name_max(self):
        """Return the maximum file name length this archive can support.
        This is the lesser of the name length limit of the archive
        format and any temporary file system based cache."""
        raise NotImplementedError

    def get_archive_path(self):
        """Return a string representing the path to the temporary
        archive. For archive classes that implement in-line handling
        this will be the archive file itself. Archives that use a
        directory based cache prior to packaging should return the
        path to the temporary directory where the report content is
        located"""
        pass

    def cleanup(self):
        """Clean up any temporary resources used by an Archive class."""
        pass

    def finalize(self, method):
        """Finalize an archive object via method. This may involve creating
        An archive that is subsequently compressed or simply closing an
        archive that supports in-line handling. If method is automatic then
        the following methods are tried in order: xz, bz2 and gzip"""

        self.close()


class FileCacheArchive(Archive):
    """ Abstract superclass for archive types that use a temporary cache
    directory in the file system. """

    _tmp_dir = ""
    _archive_root = ""
    _archive_name = ""

    def __init__(self, name, tmpdir):
        self._name = name
        self._tmp_dir = tmpdir
        self._archive_root = os.path.join(tmpdir, name)
        os.makedirs(self._archive_root, 0o700)
        self.log_info("initialised empty FileCacheArchive at '%s'" %
                      (self._archive_root,))

    def dest_path(self, name):
        if os.path.isabs(name):
            name = name.lstrip(os.sep)
        return (os.path.join(self._archive_root, name))

    def _check_path(self, dest):
        dest_dir = os.path.split(dest)[0]
        if not dest_dir:
            return
        if not os.path.isdir(dest_dir):
            self._makedirs(dest_dir)

    def add_file(self, src, dest=None):
        if not dest:
            dest = src
        dest = self.dest_path(dest)
        self._check_path(dest)
        try:
            shutil.copy(src, dest)
        except IOError as e:
            self.log_info("caught '%s' copying '%s'" % (e, src))
        try:
            shutil.copystat(src, dest)
        except OSError:
            # SELinux xattrs in /proc and /sys throw this
            pass
        try:
            stat = os.stat(src)
            os.chown(dest, stat.st_uid, stat.st_gid)
        except Exception as e:
            self.log_debug("caught '%s' setting ownership of '%s'" % (e, dest))
        self.log_debug("added '%s' to FileCacheArchive '%s'" %
                       (src, self._archive_root))

    def add_string(self, content, dest):
        src = dest
        dest = self.dest_path(dest)
        self._check_path(dest)
        f = codecs.open(dest, 'w', encoding='utf-8')
        if isinstance(content, bytes):
            content = content.decode('utf8', 'ignore')
        f.write(content)
        if os.path.exists(src):
            try:
                shutil.copystat(src, dest)
            except OSError as e:
                self.log_error(
                    "Unable to add '%s' to FileCacheArchive: %s" % (dest, e))
        self.log_debug("added string at '%s' to FileCacheArchive '%s'"
                       % (src, self._archive_root))

    def add_link(self, source, link_name):
        dest = self.dest_path(link_name)
        self._check_path(dest)
        if not os.path.lexists(dest):
            os.symlink(source, dest)
        self.log_debug("added symlink at '%s' to '%s' in FileCacheArchive '%s'"
                       % (dest, source, self._archive_root))

    def add_dir(self, path):
        self.makedirs(path)

    def add_node(self, path, mode, device):
        dest = self.dest_path(path)
        self._check_path(dest)
        if not os.path.exists(dest):
            os.mknod(dest, mode, device)
            shutil.copystat(path, dest)

    def _makedirs(self, path, mode=0o700):
        os.makedirs(path, mode)

    def name_max(self):
        if 'PC_NAME_MAX' in os.pathconf_names:
            pc_name_max = os.pathconf_names['PC_NAME_MAX']
            return os.pathconf(self._archive_root, pc_name_max)
        else:
            return 255

    def get_tmp_dir(self):
        return self._archive_root

    def get_archive_path(self):
        return self._archive_root

    def makedirs(self, path, mode=0o700):
        self._makedirs(self.dest_path(path))
        self.log_debug("created directory at '%s' in FileCacheArchive '%s'"
                       % (path, self._archive_root))

    def open_file(self, path):
        path = self.dest_path(path)
        return codecs.open(path, "r", encoding='utf-8')

    def cleanup(self):
        shutil.rmtree(self._archive_root)

    def finalize(self, method):
        self.log_info("finalizing archive '%s' using method '%s'"
                      % (self._archive_root, method))
        self._build_archive()
        self.cleanup()
        self.log_info("built archive at '%s' (size=%d)" % (self._archive_name,
                      os.stat(self._archive_name).st_size))
        self.method = method
        try:
            return self._compress()
        except Exception as e:
            exp_msg = "An error occurred compressing the archive: "
            self.log_error("%s %s" % (exp_msg, e))
            return self.name()


# Compatibility version of the tarfile.TarFile class. This exists to allow
# compatibility with PY2 runtimes that lack the 'filter' parameter to the
# TarFile.add() method. The wrapper class is used on python2.6 and earlier
# only; all later versions include 'filter' and the native TarFile class is
# used directly.
class _TarFile(tarfile.TarFile):

    # Taken from the python 2.7.5 tarfile.py
    def add(self, name, arcname=None, recursive=True,
            exclude=None, filter=None):
        """Add the file `name' to the archive. `name' may be any type of file
           (directory, fifo, symbolic link, etc.). If given, `arcname'
           specifies an alternative name for the file in the archive.
           Directories are added recursively by default. This can be avoided by
           setting `recursive' to False. `exclude' is a function that should
           return True for each filename to be excluded. `filter' is a function
           that expects a TarInfo object argument and returns the changed
           TarInfo object, if it returns None the TarInfo object will be
           excluded from the archive.
        """
        self._check("aw")

        if arcname is None:
            arcname = name

        # Exclude pathnames.
        if exclude is not None:
            import warnings
            warnings.warn("use the filter argument instead",
                          DeprecationWarning, 2)
            if exclude(name):
                self._dbg(2, "tarfile: Excluded %r" % name)
                return

        # Skip if somebody tries to archive the archive...
        if self.name is not None and os.path.abspath(name) == self.name:
            self._dbg(2, "tarfile: Skipped %r" % name)
            return

        self._dbg(1, name)

        # Create a TarInfo object from the file.
        tarinfo = self.gettarinfo(name, arcname)

        if tarinfo is None:
            self._dbg(1, "tarfile: Unsupported type %r" % name)
            return

        # Change or exclude the TarInfo object.
        if filter is not None:
            tarinfo = filter(tarinfo)
            if tarinfo is None:
                self._dbg(2, "tarfile: Excluded %r" % name)
                return

        # Append the tar header and data to the archive.
        if tarinfo.isreg():
            with tarfile.bltn_open(name, "rb") as f:
                self.addfile(tarinfo, f)

        elif tarinfo.isdir():
            self.addfile(tarinfo)
            if recursive:
                for f in os.listdir(name):
                    self.add(os.path.join(name, f), os.path.join(arcname, f),
                             recursive, exclude, filter)

        else:
            self.addfile(tarinfo)


class TarFileArchive(FileCacheArchive):
    """ archive class using python TarFile to create tar archives"""

    method = None
    _with_selinux_context = False

    def __init__(self, name, tmpdir):
        super(TarFileArchive, self).__init__(name, tmpdir)
        self._suffix = "tar"
        self._archive_name = os.path.join(tmpdir, self.name())

    def set_tarinfo_from_stat(self, tar_info, fstat, mode=None):
        tar_info.mtime = fstat.st_mtime
        tar_info.pax_headers['atime'] = "%.9f" % fstat.st_atime
        tar_info.pax_headers['ctime'] = "%.9f" % fstat.st_ctime
        if mode:
            tar_info.mode = mode
        else:
            tar_info.mode = fstat.st_mode
        tar_info.uid = fstat.st_uid
        tar_info.gid = fstat.st_gid

    # this can be used to set permissions if using the
    # tarfile.add() interface to add directory trees.
    def copy_permissions_filter(self, tarinfo):
        orig_path = tarinfo.name[len(os.path.split(self._name)[-1]):]
        if not orig_path:
            orig_path = self._archive_root
        try:
            fstat = os.stat(orig_path)
        except OSError:
            return tarinfo
        if self._with_selinux_context:
            context = self.get_selinux_context(orig_path)
            if(context):
                tarinfo.pax_headers['RHT.security.selinux'] = context
        self.set_tarinfo_from_stat(tarinfo, fstat)
        return tarinfo

    def get_selinux_context(self, path):
        try:
            (rc, c) = selinux.getfilecon(path)
            return c
        except:
            return None

    def name(self):
        return "%s.%s" % (self._name, self._suffix)

    def name_max(self):
        # GNU Tar format supports unlimited file name length. Just return
        # the limit of the underlying FileCacheArchive.
        return super(TarFileArchive, self).name_max()

    def _build_archive(self):
        # python2.6 TarFile lacks the filter parameter
        if not six.PY3 and sys.version_info[1] < 7:
            tar = _TarFile.open(self._archive_name, mode="w")
        else:
            tar = tarfile.open(self._archive_name, mode="w")
        # we need to pass the absolute path to the archive root but we
        # want the names used in the archive to be relative.
        tar.add(self._archive_root, arcname=os.path.split(self._name)[1],
                filter=self.copy_permissions_filter)
        tar.close()

    def _compress(self):
        methods = []
        # Make sure that valid compression commands exist.
        for method in ['xz', 'bzip2', 'gzip']:
            if is_executable(method):
                methods.append(method)
            else:
                self.log_error("\"%s\" command not found." % method)
        if self.method in methods:
            methods = [self.method]

        exp_msg = "No compression utilities found."
        last_error = Exception(exp_msg)
        for cmd in methods:
            suffix = "." + cmd.replace('ip', '')
            # use fast compression if using xz or bz2
            if cmd != "gzip":
                cmd = "%s -1" % cmd
            try:
                r = sos_get_command_output("%s %s" % (cmd, self.name()))

                if r['status']:
                    self.log_info(r['output'])

                self._suffix += suffix
                return self.name()

            except Exception as e:
                last_error = e
        raise last_error

# vim: set et ts=4 sw=4 :
