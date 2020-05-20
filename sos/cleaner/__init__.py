# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import json
import logging
import os
import re
import shutil
import tarfile
import tempfile

from concurrent.futures import ThreadPoolExecutor
from pwd import getpwuid
from sos import __version__
from sos.component import SoSComponent
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.mac_parser import SoSMacParser
from sos.cleaner.obfuscation_archive import SoSObfuscationArchive
from sos.utilities import get_human_readable
from textwrap import fill


class SoSCleaner(SoSComponent):
    """Take an sos report, or collection of sos reports, and scrub them of
    potentially sensitive data such as IP addresses, hostnames, MAC addresses,
    etc.. that are not obfuscated by individual plugins
    """

    desc = "Obfuscate sensitive networking information in a report"

    arg_defaults = {
        'jobs': 4,
        'map_file': '/etc/sos/cleaner/mapping',
        'no_update': False,
        'target': ''
    }

    def __init__(self, parser=None, args=None, cmdline=None, in_place=False,
                 hook_commons=None):
        if not in_place:
            # we are running `sos clean` directly
            super(SoSCleaner, self).__init__(parser, args, cmdline)
            self.from_cmdline = True
        else:
            # we are being hooked by either SoSReport or SoSCollector, don't
            # re-init everything as that will cause issues, but instead load
            # the needed bits from the calling component
            self.opts = hook_commons['options']
            self.tmpdir = hook_commons['tmpdir']
            self.sys_tmp = hook_commons['sys_tmp']
            self.policy = hook_commons['policy']
            self.from_cmdline = False
            self.opts.map_file = '/etc/sos/cleaner/default_mapping'
            self.opts.jobs = 4
            self.opts.no_update = False
            self.soslog = logging.getLogger('sos')
            self.ui_log = logging.getLogger('sos_ui')

        self.validate_map_file()
        os.umask(0o77)
        self.in_place = in_place

        self.parsers = [
            SoSIPParser(self.opts.map_file),
            SoSMacParser(self.opts.map_file)
        ]

        self.log_info("Cleaner initialized. From cmdline: %s"
                      % self.from_cmdline)

    def _fmt_log_msg(self, msg, caller=None):
        return "[cleaner%s] %s" % (":%s" % caller if caller else '', msg)

    def log_debug(self, msg, caller=None):
        self.soslog.debug(self._fmt_log_msg(msg, caller))

    def log_info(self, msg, caller=None):
        self.soslog.info(self._fmt_log_msg(msg, caller))

    def log_error(self, msg, caller=None):
        self.soslog.error(self._fmt_log_msg(msg, caller))

    def _fmt_msg(self, msg):
        width = 80
        _fmt = ''
        for line in msg.splitlines():
            _fmt = _fmt + fill(line, width, replace_whitespace=False) + '\n'
        return _fmt

    def validate_map_file(self):
        """Verifies that the map file exists and has usable content.

        If the provided map file does not exist, or it is empty, we will print
        a warning and continue on with cleaning building a fresh map
        """
        default_map = '/etc/sos/cleaner/default_mapping'
        if os.path.isdir(self.opts.map_file):
            raise Exception("Requested map file %s is a directory"
                            % self.opts.map_file)
        if not os.path.exists(self.opts.map_file):
            if self.opts.map_file != default_map:
                self.log_error(
                    "ERROR: map file %s does not exist, will not load any "
                    "obfuscation matches" % self.opts.map_file)

    def print_disclaimer(self):
        """When we are directly running `sos clean`, rather than hooking into
        SoSCleaner via report or collect, print a disclaimer banner
        """
        msg = self._fmt_msg("""\
This command will attempt to obfuscate information that is generally \
considered to be potentially sensitive. Such information includes IP \
addresses, MAC addresses, domain names, and any user-provided keywords.

Note that this utility provides a best-effort approach to data obfuscation, \
but it does not guarantee that such obfuscation provides complete coverage of \
all such data in the archive, or that any obfuscation is provided to data that\
 does not fit the description above.

Users should review any resulting data and/or archives generated or processed \
by this utility for remaining sensitive content before being passed to a \
third party.
""")
        self.ui_log.info("\nsos clean (version %s)\n" % __version__)
        self.ui_log.info(msg)
        if not self.opts.batch:
            try:
                input("\nPress ENTER to continue, or CTRL-C to quit.\n")
            except KeyboardInterrupt:
                self.ui_log.info("\nExiting on user cancel")
                self._exit(130)

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos clean|mask TARGET [options]'
        clean_grp = parser.add_argument_group(
            'Cleaner/Masking Options',
            'These options control how data obfuscation is performed'
        )
        clean_grp.add_argument('target',
                               help='The directory or archive to obfuscate')
        clean_grp.add_argument('-j', '--jobs', default=4, type=int,
                               help='Number of concurrent archives to clean')
        clean_grp.add_argument('--map', dest='map_file',
                               default='/etc/sos/cleaner/default_mapping',
                               help=('Provide a previously generated mapping '
                                     'file for obfuscation'))
        clean_grp.add_argument('--no-update', dest='no_update', default=False,
                               action='store_true',
                               help='Do not update the --map file with new '
                                    'mappings from this run')

    def set_target_path(self, path):
        """For use by report and collect to set the TARGET option appropriately
        so that execute() can be called just as if we were running `sos clean`
        directly from the cmdline.
        """
        self.opts.target = path

    def inspect_target_archive(self):
        """The target path is not a directory, so inspect it for being an
        archive or an archive of archives.

        In the event the target path is not an archive, abort.
        """
        if not tarfile.is_tarfile(self.opts.target):
            self.ui_log.error(
                "Invalid target: must be directory or tar archive"
            )
            self._exit(1)

        archive = tarfile.open(self.opts.target)
        self.arc_name = self.opts.target.split('/')[-1].split('.')[:-2][0]

        try:
            archive.getmember(os.path.join(self.arc_name, 'logs'))
        except Exception:
            # this is not a sos archive
            self.ui_log.error("Invalid target: not an sos archive")
            self._exit(1)

        # see if there are archives within this archive
        nested_archives = []
        for _file in archive.getmembers():
            if (re.match('sosreport-.*.tar', _file.name.split('/')[-1]) and not
                    _file.name.endswith('.md5')):
                nested_archives.append(_file.name.split('/')[-1])

        if nested_archives:
            self.log_info("Found nested archive(s), extracting top level")
            nested_path = self.extract_archive(archive)
            for arc_file in os.listdir(nested_path):
                if re.match('sosreport.*.tar.*', arc_file):
                    self.report_paths.append(os.path.join(nested_path,
                                                          arc_file))
            # add the toplevel extracted archive
            self.report_paths.append(nested_path)
        else:
            self.report_paths.append(self.opts.target)

        archive.close()

    def extract_archive(self, archive):
        """Extract an archive into our tmpdir so that we may inspect it or
        iterate through its contents for obfuscation

        Positional arguments:

            :param archive:     An open TarFile object for the archive

        """
        if not isinstance(archive, tarfile.TarFile):
            archive = tarfile.open(archive)
        path = os.path.join(self.tmpdir, 'cleaner')
        archive.extractall(path)
        return os.path.join(path, archive.name.split('/')[-1].split('.tar')[0])

    def execute(self):
        """SoSCleaner will begin by inspecting the TARGET option to determine
        if it is a directory, archive, or archive of archives.

        In the case of a directory, the default behavior will be to edit the
        data in place. For an archive will we unpack the archive, iterate
        over the contents, and then repack the archive. In the case of an
        archive of archives, such as one from SoSCollector, each archive will
        be unpacked, cleaned, and repacked and the final top-level archive will
        then be repacked as well.
        """
        if self.from_cmdline:
            self.print_disclaimer()
        self.report_paths = []
        if not os.path.exists(self.opts.target):
            self.ui_log.error("Invalid target: no such file or directory %s"
                              % self.opts.target)
            self._exit(1)
        if os.path.isdir(self.opts.target):
            self.arc_name = self.opts.target.split('/')[-1]
            for _file in os.listdir(self.opts.target):
                if _file == 'sos_logs':
                    self.report_paths.append(self.opts.target)
                if re.match('sosreport.*.tar.*', _file):
                    self.report_paths.append(_file)
            if not self.report_paths:
                self.ui_log.error("Invalid target: not an sos directory")
                self._exit(1)
        else:
            self.inspect_target_archive()

        if not self.report_paths:
            self.ui_log.error("No valid sos archives or directories found\n")
            self._exit(1)

        # we have at least one valid target to obfuscate
        self.completed_reports = []
        self.obfuscate_report_paths()

        if not self.completed_reports:
            if self.in_place:
                return None
            self.ui_log.info("No reports obfuscated, aborting...\n")
            self._exit(1)

        self.ui_log.info("\nSuccessfully obfuscated %s report(s)\n"
                         % len(self.completed_reports))

        _map = self.compile_mapping_dict()
        map_path = self.write_map_for_archive(_map)
        self.write_map_for_config(_map)

        if self.in_place:
            return map_path

        final_path = None
        self.hash_name = self.policy.get_preferred_hash_name()
        if len(self.completed_reports) > 1:
            # we have an archive of archives, so repack the obfuscated tarball
            arc_name = self.arc_name + '-obfuscated'
            self.setup_archive(name=arc_name)
            for arc in self.completed_reports:
                if arc.is_tarfile:
                    arc_dest = arc.final_archive_path.split('/')[-1]
                    self.archive.add_file(arc.final_archive_path,
                                          dest=arc_dest)
                    checksum = self.get_new_checksum(arc)
                    if checksum is not None:
                        dname = "checksums/%s.%s" % (arc_dest, self.hash_name)
                        self.archive.add_string(checksum, dest=dname)
                else:
                    for dirname, dirs, files in os.walk(arc.archive_path):
                        for filename in files:
                            if filename.startswith('sosreport'):
                                continue
                            fname = os.path.join(dirname, filename)
                            dnm = fname.split(arc.archive_name)[-1].lstrip('/')
                            self.archive.add_file(fname, dest=dnm)
            arc_path = self.archive.finalize(self.opts.compression_type)
        else:
            arc = self.completed_reports[0]
            arc_path = arc.final_archive_path
            checksum = self.get_new_checksum(arc)
            if checksum is not None:
                chksum_name = "%s.%s" % (arc_path.split('/')[-1],
                                         self.hash_name)
                with open(os.path.join(self.sys_tmp, chksum_name), 'w') as cf:
                    cf.write(checksum)

        final_path = os.path.join(self.sys_tmp, arc_path.split('/')[-1])
        shutil.move(arc_path, final_path)
        arcstat = os.stat(final_path)

        # logging will have been shutdown at this point
        print("A mapping of obfuscated elements is available at\n\t%s"
              % map_path)

        print("\nThe obfuscated archive is available at\n\t%s\n" % final_path)
        print("\tSize\t%s" % get_human_readable(arcstat.st_size))
        print("\tOwner\t%s\n" % getpwuid(arcstat.st_uid).pw_name)

        print("Please send the obfuscated archive to your support "
              "representative and keep the mapping file private")

        self.cleanup()

    def compile_mapping_dict(self):
        """Build a dict that contains each parser's map as a key, with the
        contents as that key's value. This will then be written to disk in the
        same directory as the obfuscated report so that sysadmins have a way
        to 'decode' the obfuscation locally
        """
        _map = {}
        for parser in self.parsers:
            _map[parser.map_file_key] = {}
            _map[parser.map_file_key].update(parser.mapping.dataset)

        return _map

    def write_map_to_file(self, _map, path):
        """Write the mapping to a file on disk that is in the same location as
        the final archive(s).
        """
        with open(path, 'w') as mf:
            mf.write(json.dumps(_map, indent=4))
        return path

    def write_map_for_archive(self, _map):
        try:
            map_path = self.obfuscate_string(
                os.path.join(self.sys_tmp, "%s_private_map" % self.arc_name)
            )
            return self.write_map_to_file(_map, map_path)
        except Exception as err:
            self.log_error("Could not write private map file: %s" % err)
            return None

    def write_map_for_config(self, _map):
        """Write the mapping to the config file so that subsequent runs are
        able to provide the same consistent mapping
        """
        if self.opts.map_file and not self.opts.no_update:
            try:
                self.write_map_to_file(_map, self.opts.map_file)
                self.log_debug("Wrote mapping to %s" % self.opts.map_file)
            except Exception as err:
                self.log_error("Could not update mapping config file: %s"
                               % err)

    def get_new_checksum(self, archive):
        """Get a new checksum for each archive"""
        checksum = archive.generate_checksum(self.hash_name)
        if checksum:
            return checksum + '\n'
        return None

    def obfuscate_report_paths(self):
        """Perform the obfuscation for each archive or sos directory discovered
        during setup.

        Each archive is handled in a separate thread, up to self.opts.jobs will
        be obfuscated concurrently.
        """
        try:
            pool = ThreadPoolExecutor(self.opts.jobs)
            pool.map(self.obfuscate_report, self.report_paths, chunksize=1)
            pool.shutdown(wait=True)
        except KeyboardInterrupt:
            self.ui_log.info("Exiting on user cancel")
            os._exit(130)

    def obfuscate_report(self, report):
        """Individually handle each archive or directory we've discovered by
        running through each file therein.

        Positional arguments:

            :param report str:      Filepath to the directory or archive
        """
        try:
            if not os.access(report, os.W_OK):
                self.log_info("Insufficient permissions on %s" % report)
                self.report_msg(report, "Insufficient permissions")
                return

            archive = SoSObfuscationArchive(report, self.tmpdir)
            archive.extract()
            self.prep_maps_from_archive(archive)
            archive.report_msg("Beginning obfuscation...")

            file_list = archive.get_file_list()
            for fname in file_list:
                short_name = fname.split(archive.archive_name)[1]
                if archive.should_skip_file(short_name):
                    continue
                try:
                    count = self.obfuscate_file(fname)
                    if count:
                        archive.update_sub_count(short_name, count)
                except Exception as err:
                    self.log_debug("Unable to parse file %s: %s"
                                   % (short_name, err))

            # if the archive was already a tarball, repack it
            method = archive.get_compression()
            if method:
                archive.report_msg("Re-compressing...")
                try:
                    cmd = self.policy.get_cmd_for_compress_method(
                        method,
                        self.opts.threads
                    )
                    archive.compress(cmd)
                except Exception as err:
                    self.log_debug("Archive %s failed to compress: %s"
                                   % (archive.archive_name, err))
                    archive.report_msg("Failed to re-compress archive: %s"
                                       % err)
                    return

            self.completed_reports.append(archive)
            archive.report_msg("Obfuscation completed")

        except Exception as err:
            self.ui_log.info("Exception while processing %s: %s"
                             % (report, err))
            os._exit(1)

    def prep_maps_from_archive(self, archive):
        """Open specific files from an archive and try to load those values
        into our mappings before iterating through the entire archive.

        Positional arguments:

            :param archive SoSObfuscationArchive:   An open archive object
        """
        for parser in self.parsers:
            self.obfuscate_file(archive.get_file_path(parser.prep_map_file))

    def obfuscate_file(self, filename, short_name=None, arc_name=None):
        """Obfuscate and individual file, line by line.

        Lines processed, even if no substitutions occur, are then written to a
        temp file without our own tmpdir. Once the file has been completely
        iterated through, if there have been substitutions then the temp file
        overwrites the original file. If there are no substitutions, then the
        original file is left in place.

        Positional arguments:

            :param filename str:        Filename relative to the extracted
                                        archive root
        """
        if not filename:
            # the requested file doesn't exist in the archive
            return
        self.log_debug("Obfuscating %s" % filename)
        subs = 0
        tfile = tempfile.NamedTemporaryFile(mode='w', dir=self.tmpdir)
        with open(filename, 'r') as fname:
            for line in fname:
                if not line.strip() or line.startswith('#'):
                    continue
                try:
                    line, count = self.obfuscate_line(line)
                    subs += count
                    tfile.write(line)
                except Exception as err:
                    self.log_debug("Unable to obfuscate %s: %s"
                                   % (filename, err))
        tfile.seek(0)
        if subs:
            shutil.copy(tfile.name, filename)
        tfile.close()
        return subs

    def obfuscate_line(self, line):
        """Run a line through each of the obfuscation parsers, keeping a
        cumulative total of substitutions done on that particular line.

        Positional arguments:

            :param line str:        The raw line as read from the file being
                                    processed

        Returns the fully obfuscated line and the number of substitutions made
        """
        count = 0
        for parser in self.parsers:
            try:
                line, _count = parser.parse_line(line)
                count += _count
            except Exception as err:
                self.log_debug("failed to parse line: %s" % err, parser.name)
        return line, count
