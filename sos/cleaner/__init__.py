# Copyright 2020 Red Hat, Inc. Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import hashlib
import json
import logging
import os
import shutil
import tempfile

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pwd import getpwuid
from sos import __version__
from sos.component import SoSComponent
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.mac_parser import SoSMacParser
from sos.cleaner.parsers.hostname_parser import SoSHostnameParser
from sos.cleaner.parsers.keyword_parser import SoSKeywordParser
from sos.cleaner.parsers.username_parser import SoSUsernameParser
from sos.cleaner.archives.sos import (SoSReportArchive, SoSReportDirectory,
                                      SoSCollectorArchive,
                                      SoSCollectorDirectory)
from sos.cleaner.archives.generic import DataDirArchive, TarballArchive
from sos.cleaner.archives.insights import InsightsArchive
from sos.utilities import get_human_readable
from textwrap import fill


class SoSCleaner(SoSComponent):
    """
    This function is designed to obfuscate potentially sensitive information
    from an sos report archive in a consistent and reproducible manner.

    It may either be invoked during the creation of a report by using the
    --clean option in the report command, or may be used on an already existing
    archive by way of 'sos clean'.

    The target of obfuscation are items such as IP addresses, MAC addresses,
    hostnames, usernames, and also keywords provided by users via the
    --keywords and/or --keyword-file options.

    For every collection made in a report the collection is parsed for such
    items, and when items are found SoS will generate an obfuscated replacement
    for it, and in all places that item is found replace the text with the
    obfuscated replacement mapped to it. These mappings are saved locally so
    that future iterations will maintain the same consistent obfuscation
    pairing.

    In the case of IP addresses, support is for IPv4 and efforts are made to
    keep network topology intact so that later analysis is as accurate and
    easily understandable as possible. If an IP address is encountered that we
    cannot determine the netmask for, a random IP address is used instead.

    For hostnames, domains are obfuscated as whole units, leaving the TLD in
    place.

    For instance, 'example.com' may be obfuscated to 'obfuscateddomain0.com'
    and 'foo.example.com' may end up being 'obfuscateddomain1.com'.

    Users will be notified of a 'mapping' file that records all items and the
    obfuscated counterpart mapped to them for ease of reference later on. This
    file should be kept private.
    """

    desc = "Obfuscate sensitive networking information in a report"

    arg_defaults = {
        'archive_type': 'auto',
        'domains': [],
        'disable_parsers': [],
        'jobs': 4,
        'keywords': [],
        'keyword_file': None,
        'map_file': '/etc/sos/cleaner/default_mapping',
        'no_update': False,
        'keep_binary_files': False,
        'target': '',
        'usernames': []
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
            self.manifest = hook_commons['manifest']
            self.from_cmdline = False
            if not hasattr(self.opts, 'jobs'):
                self.opts.jobs = 4
            self.opts.archive_type = 'auto'
            self.soslog = logging.getLogger('sos')
            self.ui_log = logging.getLogger('sos_ui')
            # create the tmp subdir here to avoid a potential race condition
            # when obfuscating a SoSCollector run during archive extraction
            os.makedirs(os.path.join(self.tmpdir, 'cleaner'), exist_ok=True)

        self.cleaner_mapping = self.load_map_file()
        os.umask(0o77)
        self.in_place = in_place
        self.hash_name = self.policy.get_preferred_hash_name()

        self.cleaner_md = self.manifest.components.add_section('cleaner')

        self.parsers = [
            SoSHostnameParser(self.cleaner_mapping, self.opts.domains),
            SoSIPParser(self.cleaner_mapping),
            SoSMacParser(self.cleaner_mapping),
            SoSKeywordParser(self.cleaner_mapping, self.opts.keywords,
                             self.opts.keyword_file),
            SoSUsernameParser(self.cleaner_mapping, self.opts.usernames)
        ]

        for _parser in self.opts.disable_parsers:
            for _loaded in self.parsers:
                _loaded_name = _loaded.name.lower().split('parser')[0].strip()
                if _parser.lower().strip() == _loaded_name:
                    self.log_info("Disabling parser: %s" % _loaded_name)
                    self.ui_log.warn(
                        "Disabling the '%s' parser. Be aware that this may "
                        "leave sensitive plain-text data in the archive."
                        % _parser
                    )
                    self.parsers.remove(_loaded)

        self.archive_types = [
            SoSReportDirectory,
            SoSReportArchive,
            SoSCollectorDirectory,
            SoSCollectorArchive,
            InsightsArchive,
            # make sure these two are always last as they are fallbacks
            DataDirArchive,
            TarballArchive
        ]
        self.nested_archive = None

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

    @classmethod
    def display_help(cls, section):
        section.set_title("SoS Cleaner Detailed Help")
        section.add_text(cls.__doc__)

    def load_map_file(self):
        """Verifies that the map file exists and has usable content.

        If the provided map file does not exist, or it is empty, we will print
        a warning and continue on with cleaning building a fresh map
        """
        _conf = {}
        default_map = '/etc/sos/cleaner/default_mapping'
        if os.path.isdir(self.opts.map_file):
            raise Exception("Requested map file %s is a directory"
                            % self.opts.map_file)
        if not os.path.exists(self.opts.map_file):
            if self.opts.map_file != default_map:
                self.log_error(
                    "ERROR: map file %s does not exist, will not load any "
                    "obfuscation matches" % self.opts.map_file)
        else:
            with open(self.opts.map_file, 'r') as mf:
                try:
                    _conf = json.load(mf)
                except json.JSONDecodeError:
                    self.log_error("ERROR: Unable to parse map file, json is "
                                   "malformed. Will not load any mappings.")
                except Exception as err:
                    self.log_error("ERROR: Could not load '%s': %s"
                                   % (self.opts.map_file, err))
        return _conf

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
            except Exception as e:
                self._exit(1, e)

    @classmethod
    def add_parser_options(cls, parser):
        parser.usage = 'sos clean|mask TARGET [options]'
        clean_grp = parser.add_argument_group(
            'Cleaner/Masking Options',
            'These options control how data obfuscation is performed'
        )
        clean_grp.add_argument('target', metavar='TARGET',
                               help='The directory or archive to obfuscate')
        clean_grp.add_argument('--archive-type', default='auto',
                               choices=['auto', 'report', 'collect',
                                        'insights', 'data-dir', 'tarball'],
                               help=('Specify what kind of archive the target '
                                     'was generated as'))
        clean_grp.add_argument('--domains', action='extend', default=[],
                               help='List of domain names to obfuscate')
        clean_grp.add_argument('--disable-parsers', action='extend',
                               default=[], dest='disable_parsers',
                               help=('Disable specific parsers, so that those '
                                     'elements are not obfuscated'))
        clean_grp.add_argument('-j', '--jobs', default=4, type=int,
                               help='Number of concurrent archives to clean')
        clean_grp.add_argument('--keywords', action='extend', default=[],
                               dest='keywords',
                               help='List of keywords to obfuscate')
        clean_grp.add_argument('--keyword-file', default=None,
                               dest='keyword_file',
                               help='Provide a file a keywords to obfuscate')
        clean_grp.add_argument('--map-file', dest='map_file',
                               default='/etc/sos/cleaner/default_mapping',
                               help=('Provide a previously generated mapping '
                                     'file for obfuscation'))
        clean_grp.add_argument('--no-update', dest='no_update', default=False,
                               action='store_true',
                               help='Do not update the --map-file with new '
                                    'mappings from this run')
        clean_grp.add_argument('--keep-binary-files', default=False,
                               action='store_true',
                               dest='keep_binary_files',
                               help='Keep unprocessable binary files in the '
                                    'archive instead of removing them')
        clean_grp.add_argument('--usernames', dest='usernames', default=[],
                               action='extend',
                               help='List of usernames to obfuscate')

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
        _arc = None
        if self.opts.archive_type != 'auto':
            check_type = self.opts.archive_type.replace('-', '_')
            for archive in self.archive_types:
                if archive.type_name == check_type:
                    _arc = archive(self.opts.target, self.tmpdir)
        else:
            for arc in self.archive_types:
                if arc.check_is_type(self.opts.target):
                    _arc = arc(self.opts.target, self.tmpdir)
                    break
        if not _arc:
            return
        self.report_paths.append(_arc)
        if _arc.is_nested:
            self.report_paths.extend(_arc.get_nested_archives())
            # We need to preserve the top level archive until all
            # nested archives are processed
            self.report_paths.remove(_arc)
            self.nested_archive = _arc
        if self.nested_archive:
            self.nested_archive.ui_name = self.nested_archive.description

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
        self.arc_name = self.opts.target.split('/')[-1].split('.tar')[0]
        if self.from_cmdline:
            self.print_disclaimer()
        self.report_paths = []
        if not os.path.exists(self.opts.target):
            self.ui_log.error("Invalid target: no such file or directory %s"
                              % self.opts.target)
            self._exit(1)

        self.inspect_target_archive()

        if not self.report_paths:
            self.ui_log.error("No valid archives or directories found\n")
            self._exit(1)

        # we have at least one valid target to obfuscate
        self.completed_reports = []
        self.preload_all_archives_into_maps()
        self.generate_parser_item_regexes()
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
        self.write_stats_to_manifest()

        if self.in_place:
            arc_paths = [a.final_archive_path for a in self.completed_reports]
            return map_path, arc_paths

        final_path = None
        if len(self.completed_reports) > 1:
            arc_path = self.rebuild_nested_archive()
        else:
            arc = self.completed_reports[0]
            arc_path = arc.final_archive_path
            checksum = self.get_new_checksum(arc.final_archive_path)
            if checksum is not None:
                chksum_name = self.obfuscate_string(
                    "%s.%s" % (arc_path.split('/')[-1], self.hash_name)
                )
                with open(os.path.join(self.sys_tmp, chksum_name), 'w') as cf:
                    cf.write(checksum)
            self.write_cleaner_log()

        final_path = self.obfuscate_string(
            os.path.join(self.sys_tmp, arc_path.split('/')[-1])
        )
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

    def rebuild_nested_archive(self):
        """Handles repacking the nested tarball, now containing only obfuscated
        copies of the reports, log files, manifest, etc...
        """
        # we have an archive of archives, so repack the obfuscated tarball
        arc_name = self.arc_name + '-obfuscated'
        self.setup_archive(name=arc_name)
        for archive in self.completed_reports:
            arc_dest = archive.final_archive_path.split('/')[-1]
            checksum = self.get_new_checksum(archive.final_archive_path)
            if checksum is not None:
                dname = "checksums/%s.%s" % (arc_dest, self.hash_name)
                self.archive.add_string(checksum, dest=dname)
        for dirn, dirs, files in os.walk(self.nested_archive.extracted_path):
            for filename in files:
                fname = os.path.join(dirn, filename)
                dname = fname.split(self.nested_archive.extracted_path)[-1]
                dname = dname.lstrip('/')
                self.archive.add_file(fname, dest=dname)
                # remove it now so we don't balloon our fs space needs
                os.remove(fname)
        self.write_cleaner_log(archive=True)
        return self.archive.finalize(self.opts.compression_type)

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
            map_path = os.path.join(
                self.sys_tmp,
                self.obfuscate_string("%s-private_map" % self.arc_name)
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
            cleaner_dir = os.path.dirname(self.opts.map_file)
            """ Attempt to create the directory /etc/sos/cleaner
            just in case it didn't exist previously
            """
            try:
                os.makedirs(cleaner_dir, exist_ok=True)
                self.write_map_to_file(_map, self.opts.map_file)
                self.log_debug("Wrote mapping to %s" % self.opts.map_file)
            except Exception as err:
                self.log_error("Could not update mapping config file: %s"
                               % err)

    def write_cleaner_log(self, archive=False):
        """When invoked via the command line, the logging from SoSCleaner will
        not be added to the archive(s) it processes, so we need to write it
        separately to disk
        """
        log_name = os.path.join(
            self.sys_tmp, "%s-obfuscation.log" % self.arc_name
        )
        with open(log_name, 'w') as logfile:
            self.sos_log_file.seek(0)
            for line in self.sos_log_file.readlines():
                logfile.write(line)

        if archive:
            self.obfuscate_file(log_name)
            self.archive.add_file(log_name, dest="sos_logs/cleaner.log")

    def get_new_checksum(self, archive_path):
        """Calculate a new checksum for the obfuscated archive, as the previous
        checksum will no longer be valid
        """
        try:
            hash_size = 1024**2  # Hash 1MiB of content at a time.
            archive_fp = open(archive_path, 'rb')
            digest = hashlib.new(self.hash_name)
            while True:
                hashdata = archive_fp.read(hash_size)
                if not hashdata:
                    break
                digest.update(hashdata)
            archive_fp.close()
            return digest.hexdigest() + '\n'
        except Exception as err:
            self.log_debug("Could not generate new checksum: %s" % err)
        return None

    def obfuscate_report_paths(self):
        """Perform the obfuscation for each archive or sos directory discovered
        during setup.

        Each archive is handled in a separate thread, up to self.opts.jobs will
        be obfuscated concurrently.
        """
        try:
            msg = (
                "Found %s total reports to obfuscate, processing up to %s "
                "concurrently\n" % (len(self.report_paths), self.opts.jobs)
            )
            self.ui_log.info(msg)
            if self.opts.keep_binary_files:
                self.ui_log.warning(
                    "WARNING: binary files that potentially contain sensitive "
                    "information will NOT be removed from the final archive\n"
                )
            pool = ThreadPoolExecutor(self.opts.jobs)
            pool.map(self.obfuscate_report, self.report_paths, chunksize=1)
            pool.shutdown(wait=True)
            # finally, obfuscate the nested archive if one exists
            if self.nested_archive:
                self._replace_obfuscated_archives()
                self.obfuscate_report(self.nested_archive)
        except KeyboardInterrupt:
            self.ui_log.info("Exiting on user cancel")
            os._exit(130)

    def _replace_obfuscated_archives(self):
        """When we have a nested archive, we need to rebuild the original
        archive, which entails replacing the existing archives with their
        obfuscated counterparts
        """
        for archive in self.completed_reports:
            os.remove(archive.archive_path)
            dest = self.nested_archive.extracted_path
            tarball = archive.final_archive_path.split('/')[-1]
            dest_name = os.path.join(dest, tarball)
            shutil.move(archive.final_archive_path, dest)
            archive.final_archive_path = dest_name

    def generate_parser_item_regexes(self):
        """For the parsers that use prebuilt lists of items, generate those
        regexes now since all the parsers should be preloaded by the archive(s)
        as well as being handed cmdline options and mapping file configuration.
        """
        for parser in self.parsers:
            parser.generate_item_regexes()

    def preload_all_archives_into_maps(self):
        """Before doing the actual obfuscation, if we have multiple archives
        to obfuscate then we need to preload each of them into the mappings
        to ensure that node1 is obfuscated in node2 as well as node2 being
        obfuscated in node1's archive.
        """
        self.log_info("Pre-loading all archives into obfuscation maps")
        for _arc in self.report_paths:
            for _parser in self.parsers:
                try:
                    pfile = _arc.prep_files[_parser.name.lower().split()[0]]
                    if not pfile:
                        continue
                except (IndexError, KeyError):
                    continue
                if isinstance(pfile, str):
                    pfile = [pfile]
                for parse_file in pfile:
                    self.log_debug("Attempting to load %s" % parse_file)
                    try:
                        content = _arc.get_file_content(parse_file)
                        if not content:
                            continue
                        if isinstance(_parser, SoSUsernameParser):
                            _parser.load_usernames_into_map(content)
                        elif isinstance(_parser, SoSHostnameParser):
                            if 'hostname' in parse_file:
                                _parser.load_hostname_into_map(
                                    content.splitlines()[0]
                                )
                            elif 'etc/hosts' in parse_file:
                                _parser.load_hostname_from_etc_hosts(
                                    content
                                )
                        else:
                            for line in content.splitlines():
                                self.obfuscate_line(line)
                    except Exception as err:
                        self.log_info(
                            "Could not prepare %s from %s (archive: %s): %s"
                            % (_parser.name, parse_file, _arc.archive_name,
                               err)
                        )

    def obfuscate_report(self, archive):
        """Individually handle each archive or directory we've discovered by
        running through each file therein.

        Positional arguments:

            :param report str:      Filepath to the directory or archive
        """
        try:
            arc_md = self.cleaner_md.add_section(archive.archive_name)
            start_time = datetime.now()
            arc_md.add_field('start_time', start_time)
            # don't double extract nested archives
            if not archive.is_extracted:
                archive.extract()
            archive.report_msg("Beginning obfuscation...")

            for fname in archive.get_file_list():
                short_name = fname.split(archive.archive_name + '/')[1]
                if archive.should_skip_file(short_name):
                    continue
                if (not self.opts.keep_binary_files and
                        archive.should_remove_file(short_name)):
                    archive.remove_file(short_name)
                    continue
                try:
                    count = self.obfuscate_file(fname, short_name,
                                                archive.archive_name)
                    if count:
                        archive.update_sub_count(short_name, count)
                except Exception as err:
                    self.log_debug("Unable to parse file %s: %s"
                                   % (short_name, err))

            try:
                self.obfuscate_directory_names(archive)
            except Exception as err:
                self.log_info("Failed to obfuscate directories: %s" % err,
                              caller=archive.archive_name)

            try:
                self.obfuscate_symlinks(archive)
            except Exception as err:
                self.log_info("Failed to obfuscate symlinks: %s" % err,
                              caller=archive.archive_name)

            # if the archive was already a tarball, repack it
            if not archive.is_nested:
                method = archive.get_compression()
                if method:
                    archive.report_msg("Re-compressing...")
                    try:
                        archive.rename_top_dir(
                            self.obfuscate_string(archive.archive_name)
                        )
                        archive.compress(method)
                    except Exception as err:
                        self.log_debug("Archive %s failed to compress: %s"
                                       % (archive.archive_name, err))
                        archive.report_msg("Failed to re-compress archive: %s"
                                           % err)
                        return
                self.completed_reports.append(archive)

            end_time = datetime.now()
            arc_md.add_field('end_time', end_time)
            arc_md.add_field('run_time', end_time - start_time)
            arc_md.add_field('files_obfuscated', len(archive.file_sub_list))
            arc_md.add_field('total_substitutions', archive.total_sub_count)
            rmsg = ''
            if archive.removed_file_count:
                rmsg = " [removed %s unprocessable files]"
                rmsg = rmsg % archive.removed_file_count
            archive.report_msg("Obfuscation completed%s" % rmsg)

        except Exception as err:
            self.ui_log.info("Exception while processing %s: %s"
                             % (archive.archive_name, err))

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
        subs = 0
        if not short_name:
            short_name = filename.split('/')[-1]
        if not os.path.islink(filename):
            # don't run the obfuscation on the link, but on the actual file
            # at some other point.
            self.log_debug("Obfuscating %s" % short_name or filename,
                           caller=arc_name)
            tfile = tempfile.NamedTemporaryFile(mode='w', dir=self.tmpdir)
            _parsers = [
                _p for _p in self.parsers if not
                any(
                    _skip.match(short_name) for _skip in _p.skip_patterns
                )
            ]
            with open(filename, 'r') as fname:
                for line in fname:
                    try:
                        line, count = self.obfuscate_line(line, _parsers)
                        subs += count
                        tfile.write(line)
                    except Exception as err:
                        self.log_debug("Unable to obfuscate %s: %s"
                                       % (short_name, err), caller=arc_name)
            tfile.seek(0)
            if subs:
                shutil.copy(tfile.name, filename)
            tfile.close()

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

        return subs

    def obfuscate_symlinks(self, archive):
        """Iterate over symlinks in the archive and obfuscate their names.
        The content of the link target will have already been cleaned, and this
        second pass over just the names of the links is to ensure we avoid a
        possible race condition dependent on the order in which the link or the
        target get obfuscated.

        :param archive:     The archive being obfuscated
        :type archive:      ``SoSObfuscationArchive``
        """
        self.log_info("Obfuscating symlink names", caller=archive.archive_name)
        for symlink in archive.get_symlinks():
            try:
                # relative name of the symlink in the archive
                _sym = symlink.split(archive.extracted_path)[1].lstrip('/')
                self.log_debug("Obfuscating symlink %s" % _sym,
                               caller=archive.archive_name)
                # current target of symlink, again relative to the archive
                _target = os.readlink(symlink)
                # get the potentially renamed symlink name, this time the full
                # path as it exists on disk
                _ob_sym_name = os.path.join(archive.extracted_path,
                                            self.obfuscate_string(_sym))
                # get the potentially renamed relative target filename
                _ob_target = self.obfuscate_string(_target)

                # if either the symlink name or the target name has changed,
                # recreate the symlink
                if (_ob_sym_name != symlink) or (_ob_target != _target):
                    os.remove(symlink)
                    os.symlink(_ob_target, _ob_sym_name)
            except Exception as err:
                self.log_info("Error obfuscating symlink '%s': %s"
                              % (symlink, err))

    def obfuscate_directory_names(self, archive):
        """For all directories that exist within the archive, obfuscate the
        directory name if it contains sensitive strings found during execution
        """
        self.log_info("Obfuscating directory names in archive %s"
                      % archive.archive_name)
        for dirpath in sorted(archive.get_directory_list(), reverse=True):
            for _name in os.listdir(dirpath):
                _dirname = os.path.join(dirpath, _name)
                _arc_dir = _dirname.split(archive.extracted_path)[-1]
                if os.path.isdir(_dirname):
                    _ob_dirname = self.obfuscate_string(_name)
                    if _ob_dirname != _name:
                        _ob_arc_dir = _arc_dir.rstrip(_name)
                        _ob_arc_dir = os.path.join(
                            archive.extracted_path,
                            _ob_arc_dir.lstrip('/'),
                            _ob_dirname
                        )
                        os.rename(_dirname, _ob_arc_dir)

    def obfuscate_string(self, string_data):
        for parser in self.parsers:
            try:
                string_data = parser.parse_string_for_keys(string_data)
            except Exception as err:
                self.log_info("Error obfuscating string data: %s" % err)
        return string_data

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
                self.log_debug("failed to parse line: %s" % err, parser.name)
        return line, count

    def write_stats_to_manifest(self):
        """Write some cleaner-level, non-report-specific stats to the manifest
        """
        parse_sec = self.cleaner_md.add_section('parsers')
        for parser in self.parsers:
            _sec = parse_sec.add_section(parser.name.replace(' ', '_').lower())
            _sec.add_field('entries', len(parser.mapping.dataset.keys()))

# vim: set et ts=4 sw=4 :
