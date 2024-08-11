# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import logging
import os
import shutil
import stat
import tarfile
import re

from concurrent.futures import ProcessPoolExecutor
from sos.utilities import file_is_binary


# python older than 3.8 will hit a pickling error when we go to spawn a new
# process for extraction if this method is a part of the SoSObfuscationArchive
# class. So, the simplest solution is to remove it from the class.
def extract_archive(archive_path, tmpdir):
    with tarfile.open(archive_path) as archive:
        path = os.path.join(tmpdir, 'cleaner')
        # set extract filter since python 3.12 (see PEP-706 for more)
        # Because python 3.10 and 3.11 raises false alarms as exceptions
        # (see #3330 for examples), we can't use data filter but must
        # fully trust the archive (legacy behaviour)
        archive.extraction_filter = getattr(tarfile, 'fully_trusted_filter',
                                            (lambda member, path: member))

        # Guard against "Arbitrary file write during tarfile extraction"
        # Checks the extracted files don't stray out of the target directory.
        for member in archive.getmembers():
            member_path = os.path.join(path, member.name)
            abs_directory = os.path.abspath(path)
            abs_target = os.path.abspath(member_path)
            prefix = os.path.commonprefix([abs_directory, abs_target])
            if prefix != abs_directory:
                raise Exception(f"Attempted path traversal in tarfle"
                                f"{prefix} != {abs_directory}")
            archive.extract(member, path)
        return os.path.join(path, archive.name.split('/')[-1].split('.tar')[0])


class SoSObfuscationArchive():
    """A representation of an extracted archive or an sos archive build
    directory which is used by SoSCleaner.

    Each archive that needs to be obfuscated is loaded into an instance of this
    class. All report-level operations should be contained within this class.
    """

    file_sub_list = []
    total_sub_count = 0
    removed_file_count = 0
    type_name = 'undetermined'
    description = 'undetermined'
    is_nested = False
    prep_files = {}

    def __init__(self, archive_path, tmpdir):
        self.archive_path = archive_path
        self.final_archive_path = self.archive_path
        self.tmpdir = tmpdir
        self.archive_name = self.archive_path.split('/')[-1].split('.tar')[0]
        self.ui_name = self.archive_name
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self.skip_list = self._load_skip_list()
        self.is_extracted = False
        self._load_self()
        self.archive_root = ''
        self.log_info(
            f"Loaded {self.archive_path} as type {self.description}"
        )

    @classmethod
    def check_is_type(cls, arc_path):
        """Check if the archive is a well-known type we directly support"""
        raise NotImplementedError

    @property
    def is_sos(self):
        return 'sos' in self.__class__.__name__.lower()

    @property
    def is_insights(self):
        return 'insights' in self.type_name

    def _load_self(self):
        if self.is_tarfile:
            # pylint: disable=consider-using-with
            self.tarobj = tarfile.open(self.archive_path)

    def get_nested_archives(self):
        """Return a list of ObfuscationArchives that represent additional
        archives found within the target archive. For example, an archive from
        `sos collect` will return a list of ``SoSReportArchive`` objects.

        This should be overridden by individual types of ObfuscationArchive's
        """
        return []

    def get_archive_root(self):
        """Set the root path for the archive that should be prepended to any
        filenames given to methods in this class.
        """
        if self.is_tarfile:
            toplevel = self.tarobj.firstmember
            if toplevel.isdir():
                return toplevel.name
            return os.path.dirname(toplevel.name) or os.sep
        return os.path.abspath(self.archive_path)

    def report_msg(self, msg):
        """Helper to easily format ui messages on a per-report basis"""
        self.ui_log.info(f"{self.ui_name + ' :':<50} {msg}")

    def _fmt_log_msg(self, msg):
        return f"[cleaner:{self.archive_name}] {msg}"

    def log_debug(self, msg):
        self.soslog.debug(self._fmt_log_msg(msg))

    def log_info(self, msg):
        self.soslog.info(self._fmt_log_msg(msg))

    def _load_skip_list(self):
        """Provide a list of files and file regexes to skip obfuscation on

        Returns: list of files and file regexes
        """
        return [
            'proc/kallsyms',
            'sosreport-',
            'sys/firmware',
            'sys/fs',
            'sys/kernel/debug',
            'sys/module'
        ]

    @property
    def is_tarfile(self):
        try:
            return tarfile.is_tarfile(self.archive_path)
        except Exception:
            return False

    def remove_file(self, fname):
        """Remove a file from the archive. This is used when cleaner encounters
        a binary file, which we cannot reliably obfuscate.
        """
        full_fname = self.get_file_path(fname)
        # don't call a blank remove() here
        if full_fname:
            self.log_info(f"Removing binary file '{fname}' from archive")
            os.remove(full_fname)
            self.removed_file_count += 1

    def format_file_name(self, fname):
        """Based on the type of archive we're dealing with, do whatever that
        archive requires to a provided **relative** filepath to be able to
        access it within the archive
        """
        if not self.is_extracted:
            if not self.archive_root:
                self.archive_root = self.get_archive_root()
            return os.path.join(self.archive_root, fname)
        return os.path.join(self.extracted_path, fname)

    def get_file_content(self, fname):
        """Return the content from the specified fname. Particularly useful for
        tarball-type archives so we can retrieve prep file contents prior to
        extracting the entire archive
        """
        if self.is_extracted is False and self.is_tarfile:
            filename = self.format_file_name(fname)
            try:
                return self.tarobj.extractfile(filename).read().decode('utf-8')
            except KeyError:
                self.log_debug(
                    f"Unable to retrieve {fname}: no such file in archive"
                )
                return ''
        else:
            try:
                with open(self.format_file_name(fname), 'r',
                          encoding='utf-8') as to_read:
                    return to_read.read()
            except Exception as err:
                self.log_debug(f"Failed to get contents of {fname}: {err}")
                return ''

    def extract(self, quiet=False):
        if self.is_tarfile:
            if not quiet:
                self.report_msg("Extracting...")
            self.extracted_path = self.extract_self()
            self.is_extracted = True
        else:
            self.extracted_path = self.archive_path
        # if we're running as non-root (e.g. collector), then we can have a
        # situation where a particular path has insufficient permissions for
        # us to rewrite the contents and/or add it to the ending tarfile.
        # Unfortunately our only choice here is to change the permissions
        # that were preserved during report collection
        if os.getuid() != 0:
            self.log_debug('Verifying permissions of archive contents')
            for dirname, dirs, files in os.walk(self.extracted_path):
                try:
                    for _dir in dirs:
                        _dirname = os.path.join(dirname, _dir)
                        _dir_perms = os.stat(_dirname).st_mode
                        os.chmod(_dirname, _dir_perms | stat.S_IRWXU)
                    for filename in files:
                        fname = os.path.join(dirname, filename)
                        # protect against symlink race conditions
                        if not os.path.exists(fname) or os.path.islink(fname):
                            continue
                        if (not os.access(fname, os.R_OK) or not
                                os.access(fname, os.W_OK)):
                            self.log_debug(
                                "Adding owner rw permissions to "
                                f"{fname.split(self.archive_path)[-1]}"
                            )
                            os.chmod(fname, stat.S_IRUSR | stat.S_IWUSR)
                except Exception as err:
                    self.log_debug(f"Error while trying to set perms: {err}")
        self.log_debug(f"Extracted path is {self.extracted_path}")

    def rename_top_dir(self, new_name):
        """Rename the top-level directory to new_name, which should be an
        obfuscated string that scrubs the hostname from the top-level dir
        which would be named after the unobfuscated sos report
        """
        _path = self.extracted_path.replace(self.archive_name, new_name)
        self.archive_name = new_name
        os.rename(self.extracted_path, _path)
        self.extracted_path = _path

    def get_compression(self):
        """Return the compression type used by the archive, if any. This is
        then used by SoSCleaner to generate a policy-derived compression
        command to repack the archive
        """
        if self.is_tarfile:
            if self.archive_path.endswith('xz'):
                return 'xz'
            return 'gz'
        return None

    def build_tar_file(self, method):
        """Pack the extracted archive as a tarfile to then be re-compressed
        """
        mode = 'w'
        tarpath = self.extracted_path + '-obfuscated.tar'
        compr_args = {}
        if method:
            mode += f":{method}"
            tarpath += f".{method}"
            if method == 'xz':
                compr_args = {'preset': 3}
            else:
                compr_args = {'compresslevel': 6}
        self.log_debug(f"Building tar file {tarpath}")
        with tarfile.open(tarpath, mode=mode, **compr_args) as tar:
            tar.add(self.extracted_path,
                    arcname=os.path.split(self.archive_name)[1])
        return tarpath

    def compress(self, method):
        """Execute the compression command, and set the appropriate final
        archive path for later reference by SoSCleaner on a per-archive basis
        """
        try:
            self.final_archive_path = self.build_tar_file(method)
        except Exception as err:
            self.log_debug(f"Exception while re-compressing archive: {err}")
            raise
        self.log_debug(f"Compressed to {self.final_archive_path}")
        try:
            self.remove_extracted_path()
        except Exception as err:
            self.log_debug(f"Failed to remove extraction directory: {err}")
            self.report_msg('Failed to remove temporary extraction directory')

    def remove_extracted_path(self):
        """After the tarball has been re-compressed, remove the extracted path
        so that we don't take up that duplicate space any longer during
        execution
        """
        try:
            self.log_debug(f"Removing {self.extracted_path}")
            shutil.rmtree(self.extracted_path)
        except OSError:
            os.chmod(self.extracted_path, stat.S_IWUSR)
            if os.path.isfile(self.extracted_path):
                os.remove(self.extracted_path)
            else:
                shutil.rmtree(self.extracted_path)

    def extract_self(self):
        """Extract an archive into our tmpdir so that we may inspect it or
        iterate through its contents for obfuscation
        """

        with ProcessPoolExecutor(1) as _pool:
            _path_future = _pool.submit(extract_archive,
                                        self.archive_path, self.tmpdir)
            path = _path_future.result()
            return path

    def get_symlinks(self):
        """Iterator for a list of symlinks in the archive"""
        for dirname, dirs, files in os.walk(self.extracted_path):
            for _dir in dirs:
                _dirpath = os.path.join(dirname, _dir)
                if os.path.islink(_dirpath):
                    yield _dirpath
            for filename in files:
                _fname = os.path.join(dirname, filename)
                if os.path.islink(_fname):
                    yield _fname

    def get_file_list(self):
        """Iterator for a list of files in the archive, to allow clean to
        iterate over.

        Will not include symlinks, as those are handled separately
        """
        for dirname, _, files in os.walk(self.extracted_path):
            for filename in files:
                _fname = os.path.join(dirname, filename.lstrip('/'))
                if not os.path.islink(_fname):
                    yield _fname

    def get_directory_list(self):
        """Return a list of all directories within the archive"""
        dir_list = []
        for dirname, _, _ in os.walk(self.extracted_path):
            dir_list.append(dirname)
        return dir_list

    def update_sub_count(self, fname, count):
        """Called when a file has finished being parsed and used to track
        total substitutions made and number of files that had changes made
        """
        self.file_sub_list.append(fname)
        self.total_sub_count += count

    def get_file_path(self, fname):
        """Return the filepath of a specific file within the archive so that
        it may be selectively inspected if it exists
        """
        _path = os.path.join(self.extracted_path, fname.lstrip('/'))
        return _path if os.path.exists(_path) else ''

    def should_skip_file(self, filename):
        """Checks the provided filename against a list of filepaths to not
        perform obfuscation on, as defined in self.skip_list

        Positional arguments:

            :param filename str:        Filename relative to the extracted
                                        archive root
        """

        if (not os.path.isfile(self.get_file_path(filename)) and not
                os.path.islink(self.get_file_path(filename))):
            return True

        for _skip in self.skip_list:
            if filename.startswith(_skip) or re.match(_skip, filename):
                return True
        return False

    def should_remove_file(self, fname):
        """Determine if the file should be removed or not, due to an inability
        to reliably obfuscate that file based on the filename.

        :param fname:       Filename relative to the extracted archive root
        :type fname:        ``str``

        :returns:   ``True`` if the file cannot be reliably obfuscated
        :rtype:     ``bool``
        """
        obvious_removes = [
            r'.*\.gz$',  # TODO: support flat gz/xz extraction
            r'.*\.xz$',
            r'.*\.bzip2$',
            r'.*\.tar\..*',  # TODO: support archive unpacking
            r'.*\.txz$',
            r'.*\.tgz$',
            r'.*\.bin$',
            r'.*\.journal$',
            r'.*\~$'
        ]

        # if the filename matches, it is obvious we can remove them without
        # doing the read test
        for _arc_reg in obvious_removes:
            if re.match(_arc_reg, fname):
                return True

        _full_path = self.get_file_path(fname)
        if os.path.isfile(_full_path):
            return file_is_binary(_full_path)
        # don't fail on dir-level symlinks
        return False

# vim: set et ts=4 sw=4 :
