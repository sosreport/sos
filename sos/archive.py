## Copyright (C) 2012 Red Hat, Inc., 
##   Jesse Jaggars <jjaggars@redhat.com>
##   Bryn M. Reeves <bmr@redhat.com>
##
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
import os
import time
import tempfile
import tarfile
import zipfile
import shutil
import logging
import shutil
import shlex
import re
# required for compression callout (FIXME: move to policy?)
from subprocess import Popen, PIPE, STDOUT

try:
    import selinux
except ImportError:
    pass

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class Archive(object):

    log = logging.getLogger("sos")

    _name = "unset"

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

    def cleanup(self):
        """Clean up any temporary resources used by an Archive class."""
        pass

    def finalize(self, method):
        """Finalize an archive object via method. This may involve creating
        An archive that is subsequently compressed or simply closing an 
        archive that supports in-line handling. If method is automatic then
        the following technologies are tried in order: xz, bz2 and gzip"""

        self.close()

class FileCacheArchive(Archive):

    _tmp_dir = ""
    _archive_root = ""
    _archive_path = ""
    
    def __init__(self, name, tmpdir):
        self._name = name
        self._tmp_dir = tmpdir
        self._archive_root = os.path.join(tmpdir, name)
        os.makedirs(self._archive_root, 0700)
        self.log.debug("initialised empty FileCacheArchive at %s"
                        % self._archive_root)

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
            shutil.copystat(src, dest)
            stat = os.stat(src)
            os.chown(dest, stat.st_uid, stat.st_gid)
        except IOError as e:
            self.log.info("caught IO error copying %s" % src)
        self.log.debug("added %s to FileCacheArchive %s"
                        % (src, self._archive_root))

    def add_string(self, content, dest):
        src = dest
        dest = self.dest_path(dest)
        self._check_path(dest)
        f = open(dest, 'w')
        f.write(content)
        if os.path.exists(src):
                shutil.copystat(src, dest)
        self.log.debug("added string at %s to FileCacheArchive %s"
                        % (src, self._archive_root))

    def add_link(self, source, link_name):
        dest = self.dest_path(link_name)
        self._check_path(dest)
        os.symlink(source, dest)
        self.log.debug("added symlink at %s to %s in FileCacheArchive %s"
                        % (dest, source, self._archive_root))

    def add_dir(self, path):
        self.makedirs(path)

    def _makedirs(self, path, mode=0700):
        os.makedirs(path, mode)
        
    def makedirs(self, path, mode=0700):
        self._makedirs(self.dest_path(path))
        self.log.debug("created directory at %s in FileCacheArchive %s"
                        % (path, self._archive_root))

    def open_file(self, path):
        path = self.dest_path(path)
        return open(path, "r")

    def cleanup(self):
        shutil.rmtree(self._archive_root)
        
    def finalize(self, method):
        self.log.debug("finalizing archive %s" % self._archive_root)
        self._build_archive()
        self.cleanup()
        self.log.debug("built archive at %s (size=%d)" % (self._archive_path,
        os.stat(self._archive_path).st_size))
        return self._compress()

class TarFileArchive(FileCacheArchive):

    method = None
    _with_selinux_context = False

    def __init__(self, name, tmpdir):
        super(TarFileArchive, self).__init__(name, tmpdir)
        self._suffix = "tar"
        self._archive_path = os.path.join(tmpdir, self.name())

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
        self.set_tarinfo_from_stat(tarinfo,fstat)
        return tarinfo

    def get_selinux_context(self, path):
        try:
            (rc, c) = selinux.getfilecon(path)
            return c
        except:
            return None

    def name(self):
        return "%s.%s" % (self._name, self._suffix)

    def _build_archive(self):
        old_pwd = os.getcwd()
        os.chdir(self._tmp_dir)
        tar = tarfile.open(self._archive_path,
                    mode="w", format=tarfile.PAX_FORMAT)
        tar.add(os.path.split(self._name)[1], filter=self.copy_permissions_filter)
        tar.close()
        os.chdir(old_pwd)
        
    def _compress(self):
        methods = ['xz', 'bzip2', 'gzip']
        if self.method in methods:
            methods = [self.method]

        last_error = Exception("compression failed for an unknown reason")
        log = logging.getLogger('sos')

        for cmd in methods:
            suffix = "." + cmd.replace('ip', '')
            # use fast compression if using xz or bz2
            if cmd != "gzip":
                cmd = "%s -1" % cmd
            try:
                command = shlex.split("%s %s" % (cmd,self.name()))
                p = Popen(command, stdout=PIPE, stderr=PIPE, bufsize=-1)
                stdout, stderr = p.communicate()
                if stdout:
                    log.info(stdout)
                if stderr:
                    log.error(stderr)
                self._suffix += suffix
                return self.name()
            except Exception, e:
                last_error = e
        else:
            raise last_error

class ZipFileArchive(Archive):

    def __init__(self, name):
        self._name = name
        try:
            import zlib
            self.compression = zipfile.ZIP_DEFLATED
        except:
            self.compression = zipfile.ZIP_STORED

        self.zipfile = zipfile.ZipFile(self.name(), mode="w", compression=self.compression)

    def name(self):
        return "%s.zip" % self._name

    def finalize(self, method):
        super(ZipFileArchive, self).finalize(method)
        return self.name()

    def add_file(self, src, dest=None):
        src = str(src)
        if dest:
            dest = str(dest)

        if os.path.isdir(src):
            # We may not need, this, but if we do I only want to do it
            # one time
            regex = re.compile(r"^" + src)
            for path, dirnames, filenames in os.walk(src):
                for filename in filenames:
                    filename = "/".join((path, filename))
                    if dest:
                        self.zipfile.write(filename,
                                self.prepend(re.sub(regex, dest, filename)))
                    else:
                        self.zipfile.write(filename, self.prepend(filename))
        else:
            if dest:
                self.zipfile.write(src, self.prepend(dest))
            else:
                self.zipfile.write(src, self.prepend(src))

    def add_string(self, content, dest):
        info = zipfile.ZipInfo(self.prepend(dest),
                date_time=time.localtime(time.time()))
        info.compress_type = self.compression
        info.external_attr = 0400 << 16L
        self.zipfile.writestr(info, content)

    def open_file(self, name):
        try:
            self.zipfile.close()
            self.zipfile = zipfile.ZipFile(self.name(), mode="r")
            name = self.prepend(name)
            file_obj = self.zipfile.open(name)
            return file_obj
        finally:
            self.zipfile.close()
            self.zipfile = zipfile.ZipFile(self.name(), mode="a")

    def close(self):
        self.zipfile.close()


