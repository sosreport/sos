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
import tempfile
import re

from concurrent.futures import ProcessPoolExecutor
from sos.utilities import (file_is_binary, sos_get_command_output,
                           file_is_certificate)


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

    files_obfuscated_count = 0
    total_sub_count = 0
    removed_file_count = 0
    type_name = 'undetermined'
    description = 'undetermined'
    is_nested = False
    prep_files = {}

    def __init__(self, archive_path, tmpdir, keep_binary_files,
                 treat_certificates):
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
        self.keep_binary_files = keep_binary_files
        self.treat_certificates = treat_certificates
        self.parsers = ()
        self.log_info(
            f"Loaded {self.archive_path} as type {self.description}"
        )

    def obfuscate_string(self, string_data):
        for parser in self.parsers:
            try:
                string_data = parser.parse_string_for_keys(string_data)
            except Exception as err:
                self.log_info(f"Error obfuscating string data: {err}")
        return string_data

    # TODO: merge content to obfuscate_arc_files as that is the only place we
    # call obfuscate_filename ?
    def obfuscate_filename(self, short_name, filename):
        _ob_short_name = self.obfuscate_string(short_name.split('/')[-1])
        _ob_filename = short_name.replace(short_name.split('/')[-1],
                                          _ob_short_name)

        if _ob_filename != short_name:
            arc_path = filename.split(short_name)[0]
            _ob_path = os.path.join(arc_path, _ob_filename)
            # ensure that any plugin subdirs that contain obfuscated strings
            # get created with obfuscated counterparts
            if not os.path.islink(filename):
                os.rename(filename, _ob_path)
            else:
                # generate the obfuscated name of the link target
                _target_ob = self.obfuscate_string(os.readlink(filename))
                # remove the unobfuscated original symlink first, in case the
                # symlink name hasn't changed but the target has
                os.remove(filename)
                # create the newly obfuscated symlink, pointing to the
                # obfuscated target name, which may not exist just yet, but
                # when the actual file is obfuscated, will be created
                os.symlink(_target_ob, _ob_path)

    def set_parsers(self, parsers):
        self.parsers = parsers  # TODO: include this in __init__?

    def load_parser_entries(self):
        for parser in self.parsers:
            parser.load_map_entries()

    def obfuscate_line(self, line, parsers=None):
        """Run a line through each of the obfuscation parsers, keeping a
        cumulative total of substitutions done on that particular line.

        Positional arguments:

            :param line str:        The raw line as read from the file being
                                    processed
            :param parsers:         A list of parser objects to obfuscate
                                    with. If None, use all.

        Returns the fully obfuscated line and the number of substitutions made
        """
        # don't iterate over blank lines, but still write them to the tempfile
        # to maintain the same structure when we write a scrubbed file back
        count = 0
        if not line.strip():
            return line, count
        if parsers is None:
            parsers = self.parsers
        for parser in parsers:
            try:
                line, _count = parser.parse_line(line)
                count += _count
            except Exception as err:
                self.log_debug(f"failed to parse line: {err}", parser.name)
        return line, count

    def obfuscate_arc_files(self, flist):
        for filename in flist:
            self.log_debug(f"    pid={os.getpid()}: obfuscating {filename}")
            try:
                short_name = filename.split(self.archive_name + '/')[1]
                if self.should_skip_file(short_name):
                    continue
                if (not self.keep_binary_files and
                        self.should_remove_file(short_name)):
                    # We reach this case if the option --keep-binary-files
                    # was not used, and the file is in a list to be removed
                    self.remove_file(short_name)
                    continue
                if (self.keep_binary_files and
                        (file_is_binary(filename) or
                         self.should_remove_file(short_name))):
                    # We reach this case if the option --keep-binary-files
                    # is used. In this case we want to make sure
                    # the cleaner doesn't try to clean a binary file
                    continue
                if os.path.islink(filename):
                    # don't run the obfuscation on the link, but on the actual
                    # file at some other point.
                    continue
                is_certificate = file_is_certificate(filename)
                if is_certificate:
                    if is_certificate == "certificatekey":
                        # Always remove certificate Key files
                        self.remove_file(short_name)
                        continue
                    if self.treat_certificates == "keep":
                        continue
                    if self.treat_certificates == "remove":
                        self.remove_file(short_name)
                        continue
                    if self.treat_certificates == "obfuscate":
                        self.certificate_to_text(filename)
                _parsers = [
                    _p for _p in self.parsers if not
                    any(
                        _skip.match(short_name) for _skip in _p.skip_patterns
                    )
                ]
                if not _parsers:
                    self.log_debug(
                        f"Skipping obfuscation of {short_name or filename} "
                        f"due to matching file skip pattern"
                    )
                    continue
                self.log_debug(f"Obfuscating {short_name or filename}")
                subs = 0
                with tempfile.NamedTemporaryFile(mode='w', dir=self.tmpdir) \
                        as tfile:
                    with open(filename, 'r', encoding='utf-8',
                              errors='replace') as fname:
                        for line in fname:
                            try:
                                line, cnt = self.obfuscate_line(line, _parsers)
                                subs += cnt
                                tfile.write(line)
                            except Exception as err:
                                self.log_debug(f"Unable to obfuscate "
                                               f"{short_name}: {err}")
                    tfile.seek(0)
                    if subs:
                        shutil.copyfile(tfile.name, filename)
                        self.update_sub_count(subs)

                self.obfuscate_filename(short_name, filename)

            except Exception as err:
                self.log_debug(f"    pid={os.getpid()}: caught exception on "
                               f"obfuscating file {filename}: {err}")

        return (self.files_obfuscated_count, self.total_sub_count,
                self.removed_file_count)

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

    def _fmt_log_msg(self, msg, caller=None):
        return f"[cleaner{f':{caller}' if caller else ''}" \
               f"[{self.archive_name}]] {msg}"

    def log_debug(self, msg, caller=None):
        self.soslog.debug(self._fmt_log_msg(msg, caller))

    def log_info(self, msg, caller=None):
        self.soslog.info(self._fmt_log_msg(msg, caller))

    def log_error(self, msg, caller=None):
        self.soslog.error(self._fmt_log_msg(msg, caller))

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

    def certificate_to_text(self, fname):
        """Convert a certificate to text. This is used when cleaner encounters
        a certificate file and the option 'treat_certificates' is 'obfuscate'.
        """
        self.log_info(f"Converting certificate file '{fname}' to text")
        sos_get_command_output(
            f"openssl storeutl -noout -text -certs {str(fname)}",
            to_file=f"{fname}.text")
        os.remove(fname)

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
            self.tarobj = None    # we can't pickle this & not further needed
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

    def get_files(self):
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

    def update_sub_count(self, count):
        """Called when a file has finished being parsed and used to track
        total substitutions made and number of files that had changes made
        """
        self.files_obfuscated_count += 1
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
