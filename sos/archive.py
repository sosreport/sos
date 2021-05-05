# Copyright (C) 2012 Red Hat, Inc.,
#   Jesse Jaggars <jjaggars@redhat.com>
#   Bryn M. Reeves <bmr@redhat.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.
import os
import tarfile
import shutil
import logging
import codecs
import errno
import stat
from datetime import datetime
from threading import Lock

from importlib.util import find_spec
from sos.utilities import sos_get_command_output

try:
    import selinux
except ImportError:
    pass

P_FILE = "file"
P_LINK = "link"
P_NODE = "node"
P_DIR = "dir"


class Archive(object):
    """Abstract base class for archives."""

    @classmethod
    def archive_type(cls):
        """Returns the archive class's name as a string.
        """
        return cls.__name__

    log = logging.getLogger("sos")

    _name = "unset"
    _debug = False

    _path_lock = Lock()

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

    def add_string(self, content, dest, mode='w'):
        raise NotImplementedError

    def add_binary(self, content, dest):
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
        the following methods are tried in order: xz, gzip"""

        self.close()


class FileCacheArchive(Archive):
    """ Abstract superclass for archive types that use a temporary cache
    directory in the file system. """

    _tmp_dir = ""
    _archive_root = ""
    _archive_name = ""

    def __init__(self, name, tmpdir, policy, threads, enc_opts, sysroot,
                 manifest=None):
        self._name = name
        self._tmp_dir = tmpdir
        self._policy = policy
        self._threads = threads
        self.enc_opts = enc_opts
        self.sysroot = sysroot or '/'
        self.manifest = manifest
        self._archive_root = os.path.join(tmpdir, name)
        with self._path_lock:
            os.makedirs(self._archive_root, 0o700)
        self.log_info("initialised empty FileCacheArchive at '%s'" %
                      (self._archive_root,))

    def dest_path(self, name):
        if os.path.isabs(name):
            name = name.lstrip(os.sep)
        return (os.path.join(self._archive_root, name))

    def join_sysroot(self, path):
        if path.startswith(self.sysroot):
            return path
        if path[0] == os.sep:
            path = path[1:]
        return os.path.join(self.sysroot, path)

    def _make_leading_paths(self, src, mode=0o700):
        """Create leading path components

            The standard python `os.makedirs` is insufficient for our
            needs: it will only create directories, and ignores the fact
            that some path components may be symbolic links.

            :param src: The source path in the host file system for which
                        leading components should be created, or the path
                        to an sos_* virtual directory inside the archive.

                        Host paths must be absolute (initial '/'), and
                        sos_* directory paths must be a path relative to
                        the root of the archive.

            :param mode: An optional mode to be used when creating path
                         components.
            :returns: A rewritten destination path in the case that one
                      or more symbolic links in intermediate components
                      of the path have altered the path destination.
        """
        self.log_debug("Making leading paths for %s" % src)
        root = self._archive_root
        dest = src

        def in_archive(path):
            """Test whether path ``path`` is inside the archive.
            """
            return path.startswith(os.path.join(root, ""))

        if not src.startswith("/"):
            # Sos archive path (sos_commands, sos_logs etc.)
            src_dir = src
        else:
            # Host file path
            src_dir = (src if os.path.isdir(self.join_sysroot(src))
                       else os.path.split(src)[0])

        # Build a list of path components in root-to-leaf order.
        path = src_dir
        path_comps = []
        while path != '/' and path != '':
            head, tail = os.path.split(path)
            path_comps.append(tail)
            path = head
        path_comps.reverse()

        abs_path = root
        src_path = "/"

        # Check and create components as needed
        for comp in path_comps:
            abs_path = os.path.join(abs_path, comp)

            # Do not create components that are above the archive root.
            if not in_archive(abs_path):
                continue

            src_path = os.path.join(src_path, comp)

            if not os.path.exists(abs_path):
                self.log_debug("Making path %s" % abs_path)
                if os.path.islink(src_path) and os.path.isdir(src_path):
                    target = os.readlink(src_path)

                    # The directory containing the source in the host fs,
                    # adjusted for the current level of path creation.
                    target_dir = os.path.split(src_path)[0]

                    # The source path of the target in the host fs to be
                    # recursively copied.
                    target_src = os.path.join(target_dir, target)

                    # Recursively create leading components of target
                    dest = self._make_leading_paths(target_src, mode=mode)
                    dest = os.path.normpath(dest)

                    # In case symlink target is an absolute path, make it
                    # relative to the directory with symlink source
                    if os.path.isabs(target):
                        target = os.path.relpath(target, target_dir)

                    self.log_debug("Making symlink '%s' -> '%s'" %
                                   (abs_path, target))
                    os.symlink(target, abs_path)
                else:
                    self.log_debug("Making directory %s" % abs_path)
                    os.mkdir(abs_path, mode)
                    dest = src_path

        return dest

    def _check_path(self, src, path_type, dest=None, force=False):
        """Check a new destination path in the archive.

            Since it is possible for multiple plugins to collect the same
            paths, and since plugins can now run concurrently, it is possible
            for two threads to race in archive methods: historically the
            archive class only needed to test for the actual presence of a
            path, since it was impossible for another `Archive` client to
            enter the class while another method invocation was being
            dispatched.

            Deal with this by implementing a locking scheme for operations
            that modify the path structure of the archive, and by testing
            explicitly for conflicts with any existing content at the
            specified destination path.

            It is not an error to attempt to create a path that already
            exists in the archive so long as the type of the object to be
            added matches the type of object already found at the path.

            It is an error to attempt to re-create an existing path with
            a different path type (for example, creating a symbolic link
            at a path already occupied by a regular file).

            :param src: the source path to be copied to the archive
            :param path_type: the type of object to be copied
            :param dest: an optional destination path
            :param force: force file creation even if the path exists
            :returns: An absolute destination path if the path should be
                      copied now or `None` otherwise
        """
        dest = dest or self.dest_path(src)
        if path_type == P_DIR:
            dest_dir = dest
        else:
            dest_dir = os.path.split(dest)[0]
        if not dest_dir:
            return dest

        # Check containing directory presence and path type
        if os.path.exists(dest_dir) and not os.path.isdir(dest_dir):
            raise ValueError("path '%s' exists and is not a directory" %
                             dest_dir)
        elif not os.path.exists(dest_dir):
            src_dir = src if path_type == P_DIR else os.path.split(src)[0]
            self._make_leading_paths(src_dir)

        def is_special(mode):
            return any([
                stat.S_ISBLK(mode),
                stat.S_ISCHR(mode),
                stat.S_ISFIFO(mode),
                stat.S_ISSOCK(mode)
            ])

        if force:
            return dest

        # Check destination path presence and type
        if os.path.exists(dest):
            # Use lstat: we care about the current object, not the referent.
            st = os.lstat(dest)
            ve_msg = "path '%s' exists and is not a %s"
            if path_type == P_FILE and not stat.S_ISREG(st.st_mode):
                raise ValueError(ve_msg % (dest, "regular file"))
            if path_type == P_LINK and not stat.S_ISLNK(st.st_mode):
                raise ValueError(ve_msg % (dest, "symbolic link"))
            if path_type == P_NODE and not is_special(st.st_mode):
                raise ValueError(ve_msg % (dest, "special file"))
            if path_type == P_DIR and not stat.S_ISDIR(st.st_mode):
                raise ValueError(ve_msg % (dest, "directory"))
            # Path has already been copied: skip
            return None
        return dest

    def add_file(self, src, dest=None):
        with self._path_lock:
            if not dest:
                dest = src

            dest = self._check_path(dest, P_FILE)
            if not dest:
                return

            # Handle adding a file from either a string respresenting
            # a path, or a File object open for reading.
            if not getattr(src, "read", None):
                # path case
                try:
                    shutil.copy(src, dest)
                except OSError as e:
                    # Filter out IO errors on virtual file systems.
                    if src.startswith("/sys/") or src.startswith("/proc/"):
                        pass
                    else:
                        self.log_info("File %s not collected: '%s'" % (src, e))

                # copy file attributes, skip SELinux xattrs for /sys and /proc
                try:
                    stat = os.stat(src)
                    if src.startswith("/sys/") or src.startswith("/proc/"):
                        shutil.copymode(src, dest)
                        os.utime(dest, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                    else:
                        shutil.copystat(src, dest)
                    os.chown(dest, stat.st_uid, stat.st_gid)
                except Exception as e:
                    self.log_debug("caught '%s' setting attributes of '%s'"
                                   % (e, dest))
                file_name = "'%s'" % src
            else:
                # Open file case: first rewind the file to obtain
                # everything written to it.
                src.seek(0)
                with open(dest, "w") as f:
                    for line in src:
                        f.write(line)
                file_name = "open file"

            self.log_debug("added %s to FileCacheArchive '%s'" %
                           (file_name, self._archive_root))

    def add_string(self, content, dest, mode='w'):
        with self._path_lock:
            src = dest

            # add_string() is a special case: it must always take precedence
            # over any exixting content in the archive, since it is used by
            # the Plugin postprocessing hooks to perform regex substitution
            # on file content.
            dest = self._check_path(dest, P_FILE, force=True)

            f = codecs.open(dest, mode, encoding='utf-8')
            if isinstance(content, bytes):
                content = content.decode('utf8', 'ignore')
            f.write(content)
            if os.path.exists(src):
                try:
                    shutil.copystat(src, dest)
                except OSError as e:
                    self.log_error("Unable to add '%s' to archive: %s" %
                                   (dest, e))
            self.log_debug("added string at '%s' to FileCacheArchive '%s'"
                           % (src, self._archive_root))

    def add_binary(self, content, dest):
        with self._path_lock:
            dest = self._check_path(dest, P_FILE)
            if not dest:
                return

            f = codecs.open(dest, 'wb', encoding=None)
            f.write(content)
            self.log_debug("added binary content at '%s' to archive '%s'"
                           % (dest, self._archive_root))

    def add_link(self, source, link_name):
        self.log_debug("adding symlink at '%s' -> '%s'" % (link_name, source))
        with self._path_lock:
            dest = self._check_path(link_name, P_LINK)
            if not dest:
                return

            if not os.path.lexists(dest):
                os.symlink(source, dest)
                self.log_debug("added symlink at '%s' to '%s' in archive '%s'"
                               % (dest, source, self._archive_root))

        # Follow-up must be outside the path lock: we recurse into
        # other monitor methods that will attempt to reacquire it.

        self.log_debug("Link follow up: source=%s link_name=%s dest=%s" %
                       (source, link_name, dest))

        source_dir = os.path.dirname(link_name)
        host_path_name = os.path.realpath(os.path.join(source_dir, source))
        dest_path_name = self.dest_path(host_path_name)

        def is_loop(link_name, source):
            """Return ``True`` if the symbolic link ``link_name`` is part
                of a file system loop, or ``False`` otherwise.
            """
            link_dir = os.path.dirname(link_name)
            if not os.path.isabs(source):
                source = os.path.realpath(os.path.join(link_dir, source))
            link_name = os.path.realpath(link_name)

            # Simple a -> a loop
            if link_name == source:
                return True

            # Find indirect loops (a->b-a) by stat()ing the first step
            # in the symlink chain
            try:
                os.stat(link_name)
            except OSError as e:
                if e.errno == 40:
                    return True
                raise
            return False

        if not os.path.exists(dest_path_name):
            if os.path.islink(host_path_name):
                # Normalised path for the new link_name
                link_name = host_path_name
                # Containing directory for the new link
                dest_dir = os.path.dirname(link_name)
                # Relative source path of the new link
                source = os.path.join(dest_dir, os.readlink(host_path_name))
                source = os.path.relpath(source, dest_dir)
                if is_loop(link_name, source):
                    self.log_debug("Link '%s' - '%s' loops: skipping..." %
                                   (link_name, source))
                    return
                self.log_debug("Adding link %s -> %s for link follow up" %
                               (link_name, source))
                self.add_link(source, link_name)
            elif os.path.isdir(host_path_name):
                self.log_debug("Adding dir %s for link follow up" % source)
                self.add_dir(host_path_name)
            elif os.path.isfile(host_path_name):
                self.log_debug("Adding file %s for link follow up" % source)
                self.add_file(host_path_name)
            else:
                self.log_debug("No link follow up: source=%s link_name=%s" %
                               (source, link_name))

    def add_dir(self, path):
        """Create a directory in the archive.

            :param path: the path in the host file system to add
        """
        # Establish path structure
        with self._path_lock:
            self._check_path(path, P_DIR)

    def add_node(self, path, mode, device):
        dest = self._check_path(path, P_NODE)
        if not dest:
            return

        if not os.path.exists(dest):
            try:
                os.mknod(dest, mode, device)
            except OSError as e:
                if e.errno == errno.EPERM:
                    msg = "Operation not permitted"
                    self.log_info("add_node: %s - mknod '%s'" % (msg, dest))
                    return
                raise e
            shutil.copystat(path, dest)

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
        """Create path, including leading components.

            Used by sos.sosreport to set up sos_* directories.
        """
        os.makedirs(os.path.join(self._archive_root, path), mode=mode)
        self.log_debug("created directory at '%s' in FileCacheArchive '%s'"
                       % (path, self._archive_root))

    def open_file(self, path):
        path = self.dest_path(path)
        return codecs.open(path, "r", encoding='utf-8', errors='ignore')

    def cleanup(self):
        if os.path.isdir(self._archive_root):
            shutil.rmtree(self._archive_root)

    def add_final_manifest_data(self, method):
        """Adds component-agnostic data to the manifest so that individual
        SoSComponents do not need to redundantly add these manually
        """
        end = datetime.now()
        start = self.manifest.start_time
        run_time = end - start
        self.manifest.add_field('end_time', end)
        self.manifest.add_field('run_time', run_time)
        self.manifest.add_field('compression', method)
        self.add_string(self.manifest.get_json(indent=4),
                        os.path.join('sos_reports', 'manifest.json'))

    def rename_archive_root(self, cleaner):
        """Rename the archive to an obfuscated version using an initialized
        SoSCleaner instance
        """
        self._name = cleaner.obfuscate_string(self._name)
        _new_root = os.path.join(self._tmp_dir, self._name)
        os.rename(self._archive_root, _new_root)
        self._archive_root = _new_root
        self._archive_name = os.path.join(self._tmp_dir, self.name())

    def finalize(self, method):
        self.log_info("finalizing archive '%s' using method '%s'"
                      % (self._archive_root, method))
        try:
            res = self._build_archive(method)
        except Exception as err:
            self.log_error("An error occurred compressing the archive: %s"
                           % err)
            return self.name()

        self.cleanup()
        self.log_info("built archive at '%s' (size=%d)" % (self._archive_name,
                      os.stat(self._archive_name).st_size))

        if self.enc_opts['encrypt']:
            try:
                return self._encrypt(res)
            except Exception as e:
                exp_msg = "An error occurred encrypting the archive:"
                self.log_error("%s %s" % (exp_msg, e))
                return res
        else:
            return res

    def _encrypt(self, archive):
        """Encrypts the compressed archive using GPG.

        If encryption fails for any reason, it should be logged by sos but not
        cause execution to stop. The assumption is that the unencrypted archive
        would still be of use to the user, and/or that the end user has another
        means of securing the archive.

        Returns the name of the encrypted archive, or raises an exception to
        signal that encryption failed and the unencrypted archive name should
        be used.
        """
        arc_name = archive.replace("sosreport-", "secured-sosreport-")
        arc_name += ".gpg"
        enc_cmd = "gpg --batch -o %s " % arc_name
        env = None
        if self.enc_opts["key"]:
            # need to assume a trusted key here to be able to encrypt the
            # archive non-interactively
            enc_cmd += "--trust-model always -e -r %s " % self.enc_opts["key"]
            enc_cmd += archive
        if self.enc_opts["password"]:
            # prevent change of gpg options using a long password, but also
            # prevent the addition of quote characters to the passphrase
            passwd = "%s" % self.enc_opts["password"].replace('\'"', '')
            env = {"sos_gpg": passwd}
            enc_cmd += "-c --passphrase-fd 0 "
            enc_cmd = "/bin/bash -c \"echo $sos_gpg | %s\"" % enc_cmd
            enc_cmd += archive
        r = sos_get_command_output(enc_cmd, timeout=0, env=env)
        if r["status"] == 0:
            return arc_name
        elif r["status"] == 2:
            if self.enc_opts["key"]:
                msg = "Specified key not in keyring"
            else:
                msg = "Could not read passphrase"
        else:
            # TODO: report the actual error from gpg. Currently, we cannot as
            # sos_get_command_output() does not capture stderr
            msg = "gpg exited with code %s" % r["status"]
        raise Exception(msg)


class TarFileArchive(FileCacheArchive):
    """ archive class using python TarFile to create tar archives"""

    method = None
    _with_selinux_context = False

    def __init__(self, name, tmpdir, policy, threads, enc_opts, sysroot,
                 manifest=None):
        super(TarFileArchive, self).__init__(name, tmpdir, policy, threads,
                                             enc_opts, sysroot, manifest)
        self._suffix = "tar"
        self._archive_name = os.path.join(
            tmpdir, self.name()  # lgtm [py/init-calls-subclass]
        )

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
        except Exception:
            return None

    def name(self):
        return "%s.%s" % (self._name, self._suffix)

    def name_max(self):
        # GNU Tar format supports unlimited file name length. Just return
        # the limit of the underlying FileCacheArchive.
        return super(TarFileArchive, self).name_max()

    def _build_archive(self, method):
        if method == 'auto':
            method = 'xz' if find_spec('lzma') is not None else 'gzip'
        _comp_mode = method.strip('ip')
        self._archive_name = self._archive_name + ".%s" % _comp_mode
        # tarfile does not currently have a consistent way to define comnpress
        # level for both xz and gzip ('preset' for xz, 'compresslevel' for gz)
        if method == 'gzip':
            kwargs = {'compresslevel': 6}
        else:
            kwargs = {'preset': 3}
        tar = tarfile.open(self._archive_name, mode="w:%s" % _comp_mode,
                           **kwargs)
        # we need to pass the absolute path to the archive root but we
        # want the names used in the archive to be relative.
        tar.add(self._archive_root, arcname=os.path.split(self._name)[1],
                filter=self.copy_permissions_filter)
        tar.close()
        self._suffix += ".%s" % _comp_mode
        return self.name()


# vim: set et ts=4 sw=4 :
