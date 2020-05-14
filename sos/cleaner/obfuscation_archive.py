# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import hashlib
import logging
import os
import tarfile
import re

from sos.utilities import sos_get_command_output


class SoSObfuscationArchive():
    """A representation of an extracted archive or an sos archive build
    directory which is used by SoSCleaner.

    Each archive that needs to be obfuscated is loaded into an instance of this
    class. All report-level operations should be contained within this class.
    """

    file_sub_list = []
    total_sub_count = 0

    def __init__(self, archive_path, tmpdir):
        self.archive_path = archive_path
        self.final_archive_path = self.archive_path
        self.tmpdir = tmpdir
        self.archive_name = self.archive_path.split('/')[-1].split('.tar')[0]
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self.skip_list = self._load_skip_list()
        self.log_info("Loaded %s as an archive" % self.archive_path)

    def report_msg(self, msg):
        """Helper to easily format ui messages on a per-report basis"""
        self.ui_log.info("{:<50} {}".format(self.archive_name + ' :', msg))

    def _fmt_log_msg(self, msg):
        return "[cleaner:%s] %s" % (self.archive_name, msg)

    def log_debug(self, msg):
        self.soslog.debug(self._fmt_log_msg(msg))

    def log_info(self, msg):
        self.soslog.info(self._fmt_log_msg(msg))

    def _load_skip_list(self):
        """Provide a list of files and file regexes to skip obfuscation on

        Returns: list of files and file regexes
        """
        return [
            '/installed-debs',
            '/installed-rpms',
            '/sos_commands/dpkg',
            '/sos_commands/python/pip_list',
            '/sos_commands/rpm',
            '/sos_commands/yum/.*list.*',
            '/sos_commands/snappy/snap_list_--all',
            '/sos_commands/snappy/snap_--version',
            '/sos_commands/vulkan/vulkaninfo',
            '/sys/firmware',
            '/sys/fs',
            '/sys/kernel/debug',
            '/sys/module',
            '/var/log/.*dnf.*',
            '.*.tar.*',  # TODO: support archive unpacking
            '.*.gz'
        ]

    @property
    def is_tarfile(self):
        try:
            return tarfile.is_tarfile(self.archive_path)
        except Exception:
            return False

    def extract(self):
        if self.is_tarfile:
            self.report_msg("Extracting...")
            self.extracted_path = self.extract_self()
        else:
            self.extracted_path = self.archive_path

    def get_compression(self):
        """Return the compression type used by the archive, if any. This is
        then used by SoSCleaner to generate a policy-derived compression
        command to repack the archive
        """
        if self.is_tarfile:
            if self.archive_path.endswith('xz'):
                return 'xz'
            return 'gzip'
        return None

    def build_tar_file(self):
        """Pack the extracted archive as a tarfile to then be re-compressed
        """
        self.tarpath = self.extracted_path + '-obfuscated.tar'
        self.log_debug("building tar file %s" % self.tarpath)
        tar = tarfile.open(self.tarpath, mode="w")
        tar.add(self.extracted_path,
                arcname=os.path.split(self.archive_name)[1])
        tar.close()

    def compress(self, cmd):
        """Execute the compression command, and set the appropriate final
        archive path for later reference by SoSCleaner on a per-archive basis
        """
        self.build_tar_file()
        exec_cmd = "%s %s" % (cmd, self.tarpath)
        res = sos_get_command_output(exec_cmd, timeout=0, stderr=True)
        if res['status'] == 0:
            self.final_archive_path = self.tarpath + '.' + exec_cmd[0:2]
        else:
            err = res['output'].split(':')[-1]
            self.log_debug("Exception while compressing archive: %s" % err)
            raise Exception(err)

    def generate_checksum(self, hash_name):
        """Calculate a new checksum for the obfuscated archive, as the previous
        checksum will no longer be valid
        """
        try:
            hash_size = 1024**2  # Hash 1MiB of content at a time.
            archive_fp = open(self.final_archive_path, 'rb')
            digest = hashlib.new(hash_name)
            while True:
                hashdata = archive_fp.read(hash_size)
                if not hashdata:
                    break
                digest.update(hashdata)
            archive_fp.close()
            return digest.hexdigest()
        except Exception as err:
            self.log_debug("Could not generate new checksum: %s" % err)
        return None

    def extract_self(self):
        """Extract an archive into our tmpdir so that we may inspect it or
        iterate through its contents for obfuscation
        """
        archive = tarfile.open(self.archive_path)
        path = os.path.join(self.tmpdir, 'cleaner')
        archive.extractall(path)
        archive.close()
        return os.path.join(path, archive.name.split('/')[-1].split('.tar')[0])

    def get_file_list(self):
        """Return a list of all files within the archive"""
        self.file_list = []
        for dirname, dirs, files in os.walk(self.extracted_path):
            for filename in files:
                self.file_list.append(os.path.join(dirname, filename))
        return self.file_list

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
        if filename in self.file_sub_list:
            return True

        if not os.path.isfile(self.get_file_path(filename)):
            return True

        for _skip in self.skip_list:
            if filename.startswith(_skip) or re.match(_skip, filename):
                return True
        return False
