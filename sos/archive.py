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
import shlex
# required for compression callout (FIXME: move to policy?)
from subprocess import Popen, PIPE, STDOUT

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class Archive(object):

    _name = "unset"

    def prepend(self, src):
        if src:
            name = os.path.split(self._name)[-1]
            renamed = os.path.join(name, src.lstrip(os.sep))
            return renamed

    def add_link(self, dest, link_name):
        pass

    def compress(self, method):
        """Compress an archive object via method. ZIP archives are ignored. If
        method is automatic then the following technologies are tried in order: xz,
        bz2 and gzip"""

        self.close()

class TarFileArchive(Archive):

    def __init__(self, name):
        self._name = name
        self._suffix = "tar"
        self.tarfile = tarfile.open(self.name(),
                    mode="w", format=tarfile.PAX_FORMAT)

    # this can be used to set permissions if using the
    # tarfile.add() interface to add directory trees.
    def copy_permissions_filter(self, tar_info):
        orig_path = tar_info.name[len(os.path.split(self._name)[-1]):]
        fstat = os.stat(orig_path)
        context = self.get_selinux_context(orig_path)
        if(context):
            tar_info.pax_headers['RHT.security.selinux'] = context
        self.set_tar_info_from_stat(tar_info,fstat)
        return tar_info

    def get_selinux_context(self, path):
        try:
            (rc, c) = selinux.getfilecon(path)
            return c
        except:
            return None

    def set_tar_info_from_stat(self, tar_info, fstat, mode=None):
        tar_info.mtime = fstat.st_mtime
        tar_info.pax_headers['atime'] = "%.9f" % fstat.st_atime
        tar_info.pax_headers['ctime'] = "%.9f" % fstat.st_ctime
        if mode:
            tar_info.mode = mode
        else:
            tar_info.mode = fstat.st_mode
        tar_info.uid = fstat.st_uid
        tar_info.gid = fstat.st_gid
    
    def name(self):
        return "%s.%s" % (self._name, self._suffix)

    def add_parent(self, path):
        path = os.path.split(path)[0]
        if path == '':
            return
        self.add_file(path)

    def add_file(self, src, dest=None):
        if dest:
            dest = self.prepend(dest)
        else:
            dest = self.prepend(src)

        if dest in self.tarfile.getnames():
            return
        if src != '/':
            self.add_parent(src)

        tar_info = tarfile.TarInfo(name=dest)

        if os.path.isdir(src):
            tar_info.type = tarfile.DIRTYPE            
            fileobj = None
        else:
            try:
                fp = open(src, 'rb')
                content = fp.read()
                fp.close()
            except:
                # files with read permissions that cannot be read may exist
                # in /proc, /sys and other virtual file systems.
                content = ""
            tar_info.size = len(content)
            fileobj = StringIO(content)

        # FIXME: handle this at a higher level?
        if src.startswith("/sys/") or src.startswith ("/proc/"):
            context = None
        else:
            context = self.get_selinux_context(src)
            if context:
                tar_info.pax_headers['RHT.security.selinux'] = context
        try:
            fstat = os.stat(src)
            if os.path.isdir(src) and not (fstat.st_mode & 000200):
                # directories not writable by their owner are a world of pain
                # in tar archives. Do not allow them (see Issue #85).
                mode = fstat.st_mode | 000200
            else:
                mode = None
            self.set_tar_info_from_stat(tar_info,fstat, mode)
            self.tarfile.addfile(tar_info, fileobj)
        except Exception as e:
            raise e
        finally:
            mode = None

    def add_string(self, content, dest):
        fstat = None
        if os.path.exists(dest):
            fstat = os.stat(dest)
        dest = self.prepend(dest)
        tar_info = tarfile.TarInfo(name=dest)
        tar_info.size = len(content)
        if fstat:
            context = self.get_selinux_context(dest)
            if context:
                tar_info.pax_headers['RHT.security.selinux'] = context
            self.set_tar_info_from_stat(tar_info, fstat)
        else:
            tar_info.mtime = time.time()
        self.tarfile.addfile(tar_info, StringIO(content))

    def add_link(self, dest, link_name):
        tar_info = tarfile.TarInfo(name=self.prepend(link_name))
        tar_info.type = tarfile.SYMTYPE
        tar_info.linkname = dest
        tar_info.mtime = time.time()
        self.tarfile.addfile(tar_info, None)

    def open_file(self, name):
        try:
            self.tarfile.close()
            self.tarfile = tarfile.open(self.name(), mode="r")
            name = self.prepend(name)
            file_obj = self.tarfile.extractfile(name)
            file_obj = StringIO(file_obj.read())
            return file_obj
        finally:
            self.tarfile.close()
            self.tarfile = tarfile.open(self.name(), mode="a")

    def close(self):
        self.tarfile.close()

    def compress(self, method):
        super(TarFileArchive, self).compress(method)

        methods = ['xz', 'bzip2', 'gzip']

        if method in methods:
            methods = [method]

        last_error = Exception("compression failed for an unknown reason")
        log = logging.getLogger('sos')

        for cmd in methods:
            try:
                command = shlex.split("%s %s" % (cmd,self.name()))
                p = Popen(command, stdout=PIPE, stderr=PIPE, bufsize=-1)
                stdout, stderr = p.communicate()
                if stdout:
                    log.info(stdout)
                if stderr:
                    log.error(stderr)
                self._suffix += "." + cmd.replace('ip', '')
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

    def compress(self, method):
        super(ZipFileArchive, self).compress(method)
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


