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
import fnmatch

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pwd import getpwuid

import sos.cleaner.preppers

from sos import __version__
from sos.component import SoSComponent
from sos.cleaner.parsers.ip_parser import SoSIPParser
from sos.cleaner.parsers.mac_parser import SoSMacParser
from sos.cleaner.parsers.hostname_parser import SoSHostnameParser
from sos.cleaner.parsers.keyword_parser import SoSKeywordParser
from sos.cleaner.parsers.username_parser import SoSUsernameParser
from sos.cleaner.parsers.ipv6_parser import SoSIPv6Parser
from sos.cleaner.archives.sos import (SoSReportArchive, SoSReportDirectory,
                                      SoSCollectorArchive,
                                      SoSCollectorDirectory)
from sos.cleaner.archives.generic import DataDirArchive, TarballArchive
from sos.cleaner.archives.insights import InsightsArchive
from sos.utilities import (get_human_readable, import_module,
                           ImporterHelper, is_executable)


# an auxiliary method to kick off child processes over its instances
def obfuscate_arc_files(arc, flist):
    return arc.obfuscate_arc_files(flist)


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

    In the case of IP addresses, support is for IPv4 and IPv6 - effort is made
    to keep network topology intact so that later analysis is as accurate and
    easily understandable as possible. If an IP address is encountered that we
    cannot determine the netmask for, a private IP address from 172.17.0.0/22
    range is used instead.

    For IPv6, note that IPv4-mapped addresses, e.g. ::ffff:10.11.12.13, are
    NOT supported currently, and will remain unobfuscated.

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
        'skip_cleaning_files': [],
        'jobs': 4,
        'keywords': [],
        'keyword_file': None,
        'map_file': '/etc/sos/cleaner/default_mapping',
        'no_update': False,
        'keep_binary_files': False,
        'target': '',
        'usernames': [],
        'treat_certificates': 'obfuscate'
    }

    def __init__(self, parser=None, args=None, cmdline=None, in_place=False,
                 hook_commons=None):
        if not in_place:
            # we are running `sos clean` directly
            super().__init__(parser, args, cmdline)
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
            # precede 'report -t' option above 'cleaner --jobs'
            if not hasattr(self.opts, 'jobs'):
                self.opts.jobs = self.opts.threads
            self.opts.archive_type = 'auto'
            self.soslog = logging.getLogger('sos')
            self.ui_log = logging.getLogger('sos_ui')
            # create the tmp subdir here to avoid a potential race condition
            # when obfuscating a SoSCollector run during archive extraction
            os.makedirs(os.path.join(self.tmpdir, 'cleaner'), exist_ok=True)

        self.review_parser_values()

        self.cleaner_mapping = self.load_map_file()
        os.umask(0o77)
        self.in_place = in_place
        self.hash_name = self.policy.get_preferred_hash_name()

        self.cleaner_md = self.manifest.components.add_section('cleaner')

        cleaner_dir = os.path.dirname(self.opts.map_file) \
            if self.opts.map_file else '/etc/sos/cleaner'
        parser_args = [
            self.cleaner_mapping,
            cleaner_dir,
            self.opts.skip_cleaning_files,
        ]
        self.parsers = [
            SoSHostnameParser(*parser_args),
            SoSIPParser(*parser_args),
            SoSIPv6Parser(*parser_args),
            SoSMacParser(*parser_args),
            SoSKeywordParser(*parser_args),
            SoSUsernameParser(*parser_args),
        ]

        for _parser in self.opts.disable_parsers:
            for _loaded in self.parsers:
                _temp = _loaded.name.lower().split('parser', maxsplit=1)[0]
                _loaded_name = _temp.strip()
                if _parser.lower().strip() == _loaded_name:
                    self.log_info(f"Disabling parser: {_loaded_name}")
                    self.ui_log.warning(
                        f"Disabling the '{_parser}' parser. Be aware that this"
                        " may leave sensitive plain-text data in the archive."
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

        self.log_info(
            f"Cleaner initialized. From cmdline: {self.from_cmdline}")

    def _fmt_log_msg(self, msg, caller=None):
        return f"[cleaner{f':{caller}' if caller else ''}] {msg}"

    def log_debug(self, msg, caller=None):
        self.soslog.debug(self._fmt_log_msg(msg, caller))

    def log_info(self, msg, caller=None):
        self.soslog.info(self._fmt_log_msg(msg, caller))

    def log_error(self, msg, caller=None):
        self.soslog.error(self._fmt_log_msg(msg, caller))

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
            raise Exception(f"Requested map file {self.opts.map_file} is a "
                            "directory")
        if not os.path.exists(self.opts.map_file):
            if self.opts.map_file != default_map:
                self.log_error(
                    f"ERROR: map file {self.opts.map_file} does not exist, "
                    "will not load any obfuscation matches")
        else:
            with open(self.opts.map_file, 'r', encoding='utf-8') as mf:
                try:
                    _conf = json.load(mf)
                except json.JSONDecodeError:
                    self.log_error("ERROR: Unable to parse map file, json is "
                                   "malformed. Will not load any mappings.")
                except Exception as err:
                    self.log_error("ERROR: Could not load "
                                   f"'{self.opts.map_file}': {err}")
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
        self.ui_log.info(f"\nsos clean (version {__version__})\n")
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
        clean_grp.add_argument('--skip-cleaning-files', '--skip-masking-files',
                               action='extend', default=[],
                               dest='skip_cleaning_files',
                               help=('List of files to skip/ignore during '
                                     'cleaning. Globs are supported.'))
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
        clean_grp.add_argument('--treat-certificates', default='obfuscate',
                               choices=['obfuscate', 'keep', 'remove'],
                               dest='treat_certificates',
                               help=(
                                   'How to treat certificate files '
                                   '[.csr .crt .pem]. Defaults to "obfuscate" '
                                   'after convert the file to text. '
                                   '"Key" certificate files are always '
                                   'removed.'))

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
                    _arc = archive(self.opts.target, self.tmpdir,
                                   self.opts.keep_binary_files,
                                   self.opts.treat_certificates)
        else:
            for arc in self.archive_types:
                if arc.check_is_type(self.opts.target):
                    _arc = arc(self.opts.target, self.tmpdir,
                               self.opts.keep_binary_files,
                               self.opts.treat_certificates)
                    break
        if not _arc:
            return
        self.main_archive = _arc
        self.report_paths.append(_arc)
        if _arc.is_nested:
            self.report_paths.extend(_arc.get_nested_archives())
            # We need to preserve the top level archive until all
            # nested archives are processed
            self.report_paths.remove(_arc)
            self.nested_archive = _arc
        if self.nested_archive:
            self.nested_archive.ui_name = self.nested_archive.description

    def review_parser_values(self):
        """Check any values passed to the parsers via the commandline:
        - For the --domains option, ensure that they are valid for the parser
          in question.
        - Convert --skip-cleaning-files from globs to regular expressions.
        """
        for _dom in self.opts.domains:
            if len(_dom.split('.')) < 2:
                raise Exception(
                    f"Invalid value '{_dom}' given: --domains values must be "
                    "actual domains"
                )
        self.opts.skip_cleaning_files = [fnmatch.translate(p) for p in
                                         self.opts.skip_cleaning_files]

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
        self.opts.target = self.opts.target.rstrip('/')
        self.arc_name = self.opts.target.split('/')[-1].split('.tar')[0]
        if self.from_cmdline:
            self.print_disclaimer()
        self.report_paths = []
        if not os.path.exists(self.opts.target):
            self.ui_log.error("Invalid target: no such file or directory "
                              f"{self.opts.target}")
            self._exit(1)

        self.inspect_target_archive()

        if not self.report_paths:
            self.ui_log.error("No valid archives or directories found\n")
            self._exit(1)

        # we have at least one valid target to obfuscate
        self.completed_reports = []
        # TODO: as we separate mappings and parsers further, do this in a less
        # janky manner
        for parser in self.parsers:
            if parser.name == 'Hostname Parser':
                parser.mapping.set_initial_counts()
        self.preload_all_archives_into_maps()
        self.generate_parser_item_regexes()
        self.obfuscate_report_paths()

        if not self.completed_reports:
            if self.in_place:
                return None
            self.ui_log.info("No reports obfuscated, aborting...\n")
            self._exit(1)

        self.ui_log.info("\nSuccessfully obfuscated "
                         f"{len(self.completed_reports)} report(s)\n")

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
                    f"{arc_path.split('/')[-1]}.{self.hash_name}"
                )
                with open(os.path.join(self.sys_tmp, chksum_name), 'w',
                          encoding='utf-8') as cf:
                    cf.write(checksum)
            self.write_cleaner_log()

        final_path = os.path.join(
            self.sys_tmp,
            self.obfuscate_string(arc_path.split('/')[-1])
        )
        shutil.move(arc_path, final_path)
        arcstat = os.stat(final_path)

        # while these messages won't be included in the log file in the archive
        # some facilities, such as our avocado test suite, will sometimes not
        # capture print() output, so leverage the ui_log to print to console
        self.ui_log.info(
            f"A mapping of obfuscated elements is available at\n\t{map_path}"
        )
        self.ui_log.info(
            f"\nThe obfuscated archive is available at\n\t{final_path}\n"
        )

        self.ui_log.info(f"\tSize\t{get_human_readable(arcstat.st_size)}")
        self.ui_log.info(f"\tOwner\t{getpwuid(arcstat.st_uid).pw_name}\n")
        self.ui_log.info("Please send the obfuscated archive to your support "
                         "representative and keep the mapping file private")

        self.cleanup()
        return None

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
                dname = f"checksums/{arc_dest}.{self.hash_name}"
                self.archive.add_string(checksum, dest=dname)
        for dirn, _, files in os.walk(self.nested_archive.extracted_path):
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
            _map[parser.map_file_key].update(parser.get_map_contents())

        return _map

    def write_map_to_file(self, _map, path):
        """Write the mapping to a file on disk that is in the same location as
        the final archive(s).
        """
        with open(path, 'w', encoding='utf-8') as mf:
            mf.write(json.dumps(_map, indent=4))
        return path

    def write_map_for_archive(self, _map):
        try:
            map_path = os.path.join(
                self.sys_tmp,
                self.obfuscate_string(f"{self.arc_name}-private_map")
            )
            return self.write_map_to_file(_map, map_path)
        except Exception as err:
            self.log_error(f"Could not write private map file: {err}")
            return None

    def write_map_for_config(self, _map):
        """Write the mapping to the config file so that subsequent runs are
        able to provide the same consistent mapping
        """
        if self.opts.map_file and not self.opts.no_update:
            cleaner_dir = os.path.dirname(self.opts.map_file)
            # Attempt to create the directory /etc/sos/cleaner
            # just in case it didn't exist previously
            try:
                os.makedirs(cleaner_dir, exist_ok=True)
                self.write_map_to_file(_map, self.opts.map_file)
                self.log_debug(f"Wrote mapping to {self.opts.map_file}")
            except Exception as err:
                self.log_error(f"Could not update mapping config file: {err}")

    def write_cleaner_log(self, archive=False):
        """When invoked via the command line, the logging from SoSCleaner will
        not be added to the archive(s) it processes, so we need to write it
        separately to disk
        """
        log_name = os.path.join(
            self.sys_tmp, f"{self.arc_name}-obfuscation.log"
        )
        with open(log_name, 'w', encoding='utf-8') as logfile:
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
            with open(archive_path, 'rb') as archive_fp:
                digest = hashlib.new(self.hash_name)
                while True:
                    hashdata = archive_fp.read(hash_size)
                    if not hashdata:
                        break
                    digest.update(hashdata)
                return digest.hexdigest() + '\n'
        except Exception as err:
            self.log_debug(f"Could not generate new checksum: {err}")
        return None

    def obfuscate_report_paths(self):
        """Perform the obfuscation for each archive or sos directory discovered
        during setup.

        Each archive is handled in a separate thread, up to self.opts.jobs will
        be obfuscated concurrently.
        """
        try:
            msg = (
                f"Found {len(self.report_paths)} total reports to obfuscate, "
                f"processing up to {self.opts.jobs} concurrently within one "
                "archive\n"
            )
            self.ui_log.info(msg)
            if self.opts.keep_binary_files:
                self.ui_log.warning(
                    "WARNING: binary files that potentially contain sensitive "
                    "information will NOT be removed from the final archive\n"
                )
            if (self.opts.treat_certificates == "obfuscate"
                    and not is_executable("openssl")):
                self.opts.treat_certificates = "remove"
                self.ui_log.warning(
                    "WARNING: No `openssl` command available. Replacing "
                    "`--treat-certificates` from `obfuscate` to `remove`."
                )
            if self.opts.treat_certificates == "obfuscate":
                self.ui_log.warning(
                    "WARNING: certificate files that potentially contain "
                    "sensitive information will be CONVERTED to text and "
                    "OBFUSCATED in the final archive.\n"
                )
            elif self.opts.treat_certificates == "keep":
                self.ui_log.warning(
                    "WARNING: certificate files that potentially contain "
                    "sensitive information will be KEPT in the final "
                    "archive as is.\n"
                )
            elif self.opts.treat_certificates == "remove":
                self.ui_log.warning(
                    "WARNING: certificate files that potentially contain "
                    "sensitive information will be REMOVED in the final "
                    "archive.\n")
            for report_path in self.report_paths:
                self.ui_log.info(f"Obfuscating {report_path.archive_path}")
                self.obfuscate_report(report_path)
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

    def _prepare_archive_with_prepper(self, archive, prepper):
        """
        For each archive we've determined we need to operate on, pass it to
        each prepper so that we can extract necessary files and/or items for
        direct regex replacement. Preppers define these methods per parser,
        so it is possible that a single prepper will read the same file for
        different parsers/mappings. This is preferable to the alternative of
        building up monolithic lists of file paths, as we'd still need to
        manipulate these on a per-archive basis.

        :param archive: The archive we are currently using to prepare our
                        mappings with
        :type archive:  ``SoSObfuscationArchive`` subclass

        :param prepper: The individual prepper we're using to source items
        :type prepper:  ``SoSPrepper`` subclass
        """
        for _parser in self.parsers:
            pname = _parser.name.lower().split()[0].strip()
            for _file in prepper.get_parser_file_list(pname, archive):
                content = archive.get_file_content(_file)
                if not content:
                    continue
                self.log_debug(f"Prepping {pname} parser with file {_file} "
                               f"from {archive.ui_name}")
                for line in content.splitlines():
                    try:
                        _parser.parse_line(line)
                    except Exception as err:
                        self.log_debug(
                            f"Failed to prep {pname} map from {_file}: {err}"
                        )
            map_items = prepper.get_items_for_map(pname, archive)
            if map_items:
                self.log_debug(f"Prepping {pname} mapping with items from "
                               f"{archive.ui_name}")
                for item in map_items:
                    _parser.mapping.add(item)

            for ritem in prepper.regex_items[pname]:
                _parser.mapping.add_regex_item(ritem)
        # we must initialize stuff inside (cloned processes') archive - REALLY?
        archive.set_parsers(self.parsers)

    def get_preppers(self):
        """
        Discover all locally available preppers so that we can prepare the
        mappings with obfuscation matches in a controlled manner

        :returns: All preppers that can be leveraged locally
        :rtype:   A generator of `SoSPrepper` items
        """
        helper = ImporterHelper(sos.cleaner.preppers)
        preps = []
        for _prep in helper.get_modules():
            preps.extend(import_module(f"sos.cleaner.preppers.{_prep}"))
        for prepper in sorted(preps, key=lambda x: x.priority):
            yield prepper(options=self.opts)

    def preload_all_archives_into_maps(self):
        """Before doing the actual obfuscation, if we have multiple archives
        to obfuscate then we need to preload each of them into the mappings
        to ensure that node1 is obfuscated in node2 as well as node2 being
        obfuscated in node1's archive.
        """
        self.log_info("Pre-loading all archives into obfuscation maps")
        for prepper in self.get_preppers():
            for archive in self.report_paths:
                self._prepare_archive_with_prepper(archive, prepper)
        self.main_archive.set_parsers(self.parsers)

    def obfuscate_report(self, archive):  # pylint: disable=too-many-branches
        """Individually handle each archive or directory we've discovered by
        running through each file therein.

        Positional arguments:

            :param archive str:      Filepath to the directory or archive
        """

        try:
            arc_md = self.cleaner_md.add_section(archive.archive_name)
            start_time = datetime.now()
            arc_md.add_field('start_time', start_time)
            # don't double extract nested archives
            if not archive.is_extracted:
                archive.extract()
            archive.report_msg("Beginning obfuscation...")

            file_list = list(archive.get_files())
            # we can't call simple
            # executor.map(archive.obfuscate_arc_files,archive.get_files())
            # because a child process does not carry forward internal changes
            # (e.g. mappings' datasets) from one call of obfuscate_arc_files
            # method to another. Each obfuscate_arc_files method starts with
            # vanilla parent archive, that is initialised *once* at its
            # beginning via initializer=archive.load_parser_entries
            # - but not afterwards..
            #
            # So we must pass list of all files for each worker at the
            # beginning. This means less granularity of the child processes
            # work (one worker can finish much sooner than the other), but
            # it is the best we can have (or have found)
            #
            # At least, the "file_list[i::self.opts.jobs]" means subsequent
            # files (speculativelly of similar size and content) are
            # distributed to different processes, which attempts to split the
            # load evenly. Yet better approach might be reorderig file_list
            # based on files' sizes.

            files_obfuscated_count = total_sub_count = removed_file_count = 0
            archive_list = [archive for i in range(self.opts.jobs)]
            with ProcessPoolExecutor(
                    max_workers=self.opts.jobs,
                    initializer=archive.load_parser_entries) as executor:
                futures = executor.map(obfuscate_arc_files, archive_list,
                                       [file_list[i::self.opts.jobs] for i in
                                        range(self.opts.jobs)])
                for (foc, tsc, rfc) in futures:
                    files_obfuscated_count += foc
                    total_sub_count += tsc
                    removed_file_count += rfc

            # As there is no easy way to get dataset dicts from child
            # processes' mappings, we can reload our own parent-process
            # archive from the disk files. The trick is that sequence of
            # files/entries is the source of truth of *sequence* of calling
            # *all* mapping.all(item) methods - so replaying this will
            # generate the right datasets!
            archive.load_parser_entries()

            try:
                self.obfuscate_directory_names(archive)
            except Exception as err:
                self.log_info(f"Failed to obfuscate directories: {err}",
                              caller=archive.archive_name)

            try:
                self.obfuscate_symlinks(archive)
            except Exception as err:
                self.log_info(f"Failed to obfuscate symlinks: {err}",
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
                        self.log_debug(f"Archive {archive.archive_name} failed"
                                       f" to compress: {err}")
                        archive.report_msg(
                            f"Failed to re-compress archive: {err}")
                        return
                self.completed_reports.append(archive)

            end_time = datetime.now()
            arc_md.add_field('end_time', end_time)
            arc_md.add_field('run_time', end_time - start_time)
            arc_md.add_field('files_obfuscated', files_obfuscated_count)
            arc_md.add_field('total_substitutions', total_sub_count)
            rmsg = ''
            if removed_file_count:
                rmsg = " [removed %s unprocessable files]"
                rmsg = rmsg % removed_file_count
            archive.report_msg(f"Obfuscation completed{rmsg}")

        except Exception as err:
            self.ui_log.info("Exception while processing "
                             f"{archive.archive_name}: {err}")

    def obfuscate_file(self, filename):
        self.main_archive.obfuscate_arc_files([filename])

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
                # don't obfuscate symlinks for files that we skipped the first
                # obfuscation of, as that would create broken links
                _parsers = [
                    _p for _p in self.parsers if not
                    any(_skip.match(_sym) for _skip in _p.skip_patterns)
                ]
                if not _parsers:
                    self.log_debug(
                        f"Skipping obfuscation of symlink {_sym} due to skip "
                        f"pattern match"
                    )
                    continue
                self.log_debug(f"Obfuscating symlink {_sym}",
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
                self.log_info(f"Error obfuscating symlink '{symlink}': {err}")

    def obfuscate_directory_names(self, archive):
        """For all directories that exist within the archive, obfuscate the
        directory name if it contains sensitive strings found during execution
        """
        self.log_info("Obfuscating directory names in archive "
                      f"{archive.archive_name}")
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

    # TODO: this is a duplicate method from SoSObfuscationArchive but we can't
    # easily remove either of them..?
    def obfuscate_string(self, string_data):
        for parser in self.parsers:
            try:
                string_data = parser.parse_string_for_keys(string_data)
            except Exception as err:
                self.log_info(f"Error obfuscating string data: {err}")
        return string_data

    def write_stats_to_manifest(self):
        """Write some cleaner-level, non-report-specific stats to the manifest
        """
        parse_sec = self.cleaner_md.add_section('parsers')
        for parser in self.parsers:
            _sec = parse_sec.add_section(parser.name.replace(' ', '_').lower())
            _sec.add_field('entries', len(parser.mapping.dataset.keys()))

# vim: set et ts=4 sw=4 :
