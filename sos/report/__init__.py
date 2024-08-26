# Copyright (C) 2006 Steve Conklin <sconklin@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# pylint: disable=too-many-branches,too-many-locals

import sys
import traceback
import os
import errno
import logging
import hashlib
import pdb
from datetime import datetime
import glob

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from shutil import rmtree

import sos.report.plugins
from sos.utilities import (ImporterHelper, SoSTimeoutError, bold,
                           sos_get_command_output, TIMEOUT_DEFAULT, listdir,
                           is_executable)

from sos import _sos as _
from sos import __version__
from sos.component import SoSComponent
import sos.policies
from sos.report.reporting import (Report, Section, Command, CopiedFile,
                                  CreatedFile, Alert, Note, PlainTextReport,
                                  JSONReport, HTMLReport)
from sos.cleaner import SoSCleaner

# file system errors that should terminate a run
fatal_fs_errors = (errno.ENOSPC, errno.EROFS)


def _format_list(first_line, items, indent=False, sep=", "):
    lines = []
    line = first_line
    if indent:
        newline = len(first_line) * ' '
    else:
        newline = ""
    for item in items:
        if len(line) + len(item) + len(sep) > 72:
            lines.append(line)
            line = newline
        line = line + item + sep
    if line[-len(sep):] == sep:
        line = line[:-len(sep)]
    lines.append(line)
    return lines


def _format_since(date):
    """ This function will format --since arg to append 0s if enduser
    didn't. It's used in the _get_parser.
    This will also be a good place to add human readable and relative
    date parsing (like '2 days ago') in the future """
    return datetime.strptime(f"{date:<014s}", '%Y%m%d%H%M%S')


# valid modes for --chroot
chroot_modes = ["auto", "always", "never"]


class SoSReport(SoSComponent):
    """Run a set of commands and file collections and save them to a report for
    future analysis
    """

    desc = "Collect files and command output in an archive"
    root_required = True

    arg_defaults = {
        'alloptions': False,
        'all_logs': False,
        'build': False,
        'case_id': '',
        'chroot': 'auto',
        'clean': False,
        'container_runtime': 'auto',
        'keep_binary_files': False,
        'desc': '',
        'domains': [],
        'disable_parsers': [],
        'skip_cleaning_files': [],
        'dry_run': False,
        'estimate_only': False,
        'experimental': False,
        'enable_plugins': [],
        'journal_size': 100,
        'keywords': [],
        'keyword_file': None,
        'plugopts': [],
        'label': '',
        'list_plugins': False,
        'list_presets': False,
        'list_profiles': False,
        'log_size': 25,
        'low_priority': False,
        'map_file': '/etc/sos/cleaner/default_mapping',
        'skip_commands': [],
        'skip_files': [],
        'skip_plugins': [],
        'namespaces': None,
        'no_report': False,
        'no_env_vars': False,
        'no_postproc': False,
        'no_update': False,
        'note': '',
        'only_plugins': [],
        'preset': 'auto',
        'plugin_timeout': TIMEOUT_DEFAULT,
        'cmd_timeout': TIMEOUT_DEFAULT,
        'profiles': [],
        'since': None,
        'verify': False,
        'allow_system_changes': False,
        'usernames': [],
        'upload': False,
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False,
        'upload_protocol': 'auto',
        'upload_s3_endpoint': None,
        'upload_s3_region': None,
        'upload_s3_bucket': None,
        'upload_s3_access_key': None,
        'upload_s3_secret_key': None,
        'upload_s3_object_prefix': None,
        'add_preset': '',
        'del_preset': ''
    }

    def __init__(self, parser, args, cmdline):
        super().__init__(parser, args, cmdline)
        self.loaded_plugins = []
        self.skipped_plugins = []
        self.all_options = []
        self.env_vars = set()
        self._args = args
        self.sysroot = "/"
        self.estimated_plugsizes = {}

        self.print_header()
        self._set_debug()

        self._is_root = self.policy.is_root()

        # add a manifest section for report
        self.report_md = self.manifest.components.add_section('report')

        self._set_directories()

        msg = "default"
        self.sysroot = self.policy.sysroot
        # set alternate system root directory
        if self.opts.sysroot:
            msg = "cmdline"
        elif self.policy.in_container() and self.sysroot != os.sep:
            msg = "policy"
        self.soslog.debug(f"set sysroot to '{self.sysroot}' ({msg})")

        if self.opts.chroot not in chroot_modes:
            self.soslog.error(f"invalid chroot mode: {self.opts.chroot}")
            logging.shutdown()
            self.tempfile_util.clean()
            self._exit(1)

        self._check_container_runtime()
        self._get_namespaces()
        self._get_hardware_devices()

    @classmethod
    def add_parser_options(cls, parser):
        report_grp = parser.add_argument_group(
            'Report Options',
            'These options control how report collects data'
            )
        report_grp.add_argument("-a", "--alloptions", action="store_true",
                                dest="alloptions", default=False,
                                help="enable all options for loaded plugins")
        report_grp.add_argument("--all-logs", action="store_true",
                                dest="all_logs", default=False,
                                help="collect all available logs regardless "
                                     "of size")
        report_grp.add_argument("--since", action="store",
                                dest="since", default=None, type=_format_since,
                                help="Escapes archived files older than date. "
                                     "This will also affect --all-logs. "
                                     "Format: YYYYMMDD[HHMMSS]")
        report_grp.add_argument("--build", action="store_true",
                                dest="build", default=False,
                                help="preserve the temporary directory and do "
                                     "not package results")
        report_grp.add_argument("--case-id", action="store", dest="case_id",
                                help="specify case identifier")
        report_grp.add_argument("-c", "--chroot", action="store",
                                dest="chroot", default='auto',
                                help="chroot executed commands to SYSROOT "
                                     "[auto, always, never] (default=auto)")
        report_grp.add_argument("--container-runtime", default="auto",
                                help="Default container runtime to use for "
                                     "collections. 'auto' for policy control.")
        report_grp.add_argument("--desc", "--description", type=str,
                                action="store", default="",
                                help="Description for a new preset",)
        report_grp.add_argument("--dry-run", action="store_true",
                                help="Run plugins but do not collect data")
        report_grp.add_argument("--estimate-only", action="store_true",
                                help="Approximate disk space requirements for "
                                     "a real sos run; disables --clean and "
                                     "--collect, sets --threads=1 and "
                                     "--no-postproc")
        report_grp.add_argument("--experimental", action="store_true",
                                dest="experimental", default=False,
                                help="enable experimental plugins")
        report_grp.add_argument("-e", "--enable-plugins", action="extend",
                                dest="enable_plugins", type=str,
                                help="enable these plugins", default=[])
        report_grp.add_argument("--journal-size", type=int, default=100,
                                dest="journal_size",
                                help="limit the size of collected journals "
                                     "in MiB")
        report_grp.add_argument("-k", "--plugin-option", "--plugopts",
                                action="extend",
                                dest="plugopts", type=str,
                                help="plugin options in plugname.option=value "
                                     "format (see -l)", default=[])
        report_grp.add_argument("--label", "--name", action="store",
                                dest="label",
                                help="specify an additional report label")
        report_grp.add_argument("-l", "--list-plugins", action="store_true",
                                dest="list_plugins", default=False,
                                help="list plugins and available plugin "
                                     "options")
        report_grp.add_argument("--list-presets", action="store_true",
                                help="display a list of available presets")
        report_grp.add_argument("--list-profiles", action="store_true",
                                dest="list_profiles", default=False,
                                help="display a list of available profiles and"
                                     " plugins that they include")
        report_grp.add_argument("--log-size", action="store", dest="log_size",
                                type=int, default=25,
                                help="limit the size of collected logs "
                                     "(not journals) in MiB")
        report_grp.add_argument("--low-priority", action="store_true",
                                default=False,
                                help="generate report with low system priority"
                                )
        report_grp.add_argument("--namespaces", default=None,
                                help="limit number of namespaces to collect "
                                     "output for - 0 means unlimited")
        report_grp.add_argument("-n", "--skip-plugins", action="extend",
                                dest="skip_plugins", type=str,
                                help="disable these plugins", default=[])
        report_grp.add_argument("--no-report", action="store_true",
                                dest="no_report", default=False,
                                help="disable plaintext/HTML reporting")
        report_grp.add_argument("--no-env-vars", action="store_true",
                                dest="no_env_vars", default=False,
                                help="Do not collect environment variables")
        report_grp.add_argument("--no-postproc", default=False,
                                dest="no_postproc", action="store_true",
                                help="Disable all post-processing")
        report_grp.add_argument("--note", type=str, action="store", default="",
                                help="Behaviour notes for new preset")
        report_grp.add_argument("-o", "--only-plugins", action="extend",
                                dest="only_plugins", type=str,
                                help="enable these plugins only", default=[])
        report_grp.add_argument("--preset", action="store", type=str,
                                help="A preset identifier", default="auto")
        report_grp.add_argument("--plugin-timeout", default=None,
                                help="set a timeout for all plugins")
        report_grp.add_argument("--cmd-timeout", default=None,
                                help="set a command timeout for all plugins")
        report_grp.add_argument("-p", "--profile", "--profiles",
                                action="extend", dest="profiles", type=str,
                                default=[],
                                help="enable plugins used by the given "
                                     "profiles")
        report_grp.add_argument('--skip-commands', default=[], action='extend',
                                dest='skip_commands',
                                help="do not execute these commands")
        report_grp.add_argument('--skip-files', default=[], action='extend',
                                dest='skip_files',
                                help="do not collect these files")
        report_grp.add_argument("--verify", action="store_true",
                                dest="verify", default=False,
                                help="perform data verification during "
                                     "collection")
        report_grp.add_argument("--allow-system-changes", action="store_true",
                                dest="allow_system_changes", default=False,
                                help="Run commands even if they can change the"
                                     " system (e.g. load kernel modules)")
        report_grp.add_argument("--upload", action="store_true", default=False,
                                help="Upload archive to a policy-default "
                                     "location")
        report_grp.add_argument("--upload-url", default=None,
                                help="Upload the archive to specified server")
        report_grp.add_argument("--upload-directory", default=None,
                                help="Specify upload directory for archive")
        report_grp.add_argument("--upload-user", default=None,
                                help="Username to authenticate to server with")
        report_grp.add_argument("--upload-pass", default=None,
                                help="Password to authenticate to server with")
        report_grp.add_argument("--upload-method", default='auto',
                                choices=['auto', 'put', 'post'],
                                help="HTTP method to use for uploading")
        report_grp.add_argument("--upload-no-ssl-verify", default=False,
                                action='store_true',
                                help="Disable SSL verification for upload url")
        report_grp.add_argument("--upload-s3-endpoint", default=None,
                                help="Endpoint to upload to for S3 bucket")
        report_grp.add_argument("--upload-s3-region", default=None,
                                help="Region to upload to for S3 bucket")
        report_grp.add_argument("--upload-s3-bucket", default=None,
                                help="Name of the S3 bucket to upload to")
        report_grp.add_argument("--upload-s3-access-key", default=None,
                                help="Access key for the S3 bucket")
        report_grp.add_argument("--upload-s3-secret-key", default=None,
                                help="Secret key for the S3 bucket")
        report_grp.add_argument("--upload-s3-object-prefix", default=None,
                                help="Prefix for the S3 object/key")
        report_grp.add_argument("--upload-protocol", default='auto',
                                choices=['auto', 'https', 'ftp', 'sftp',
                                         's3'],
                                help="Manually specify the upload protocol")

        # Group to make add/del preset exclusive
        preset_grp = report_grp.add_mutually_exclusive_group()
        preset_grp.add_argument("--add-preset", type=str, action="store",
                                help="Add a new named command line preset")
        preset_grp.add_argument("--del-preset", type=str, action="store",
                                help="Delete the named command line preset")

        # Group the cleaner options together
        cleaner_grp = parser.add_argument_group(
            'Cleaner/Masking Options',
            'These options control how data obfuscation is performed'
        )
        cleaner_grp.add_argument('--clean', '--cleaner', '--mask',
                                 dest='clean',
                                 default=False, action='store_true',
                                 help='Obfuscate sensitive information')
        cleaner_grp.add_argument('--domains', dest='domains', default=[],
                                 action='extend',
                                 help='Additional domain names to obfuscate')
        cleaner_grp.add_argument('--disable-parsers', action='extend',
                                 default=[], dest='disable_parsers',
                                 help=('Disable specific parsers, so that '
                                       'those elements are not obfuscated'))
        cleaner_grp.add_argument('--skip-cleaning-files',
                                 '--skip-masking-files', action='extend',
                                 default=[], dest='skip_cleaning_files',
                                 help=('List of files to skip/ignore during '
                                       'cleaning. Globs are supported.'))
        cleaner_grp.add_argument('--keywords', action='extend', default=[],
                                 dest='keywords',
                                 help='List of keywords to obfuscate')
        cleaner_grp.add_argument('--keyword-file', default=None,
                                 dest='keyword_file',
                                 help='Provide a file a keywords to obfuscate')
        cleaner_grp.add_argument('--no-update', action='store_true',
                                 default=False, dest='no_update',
                                 help='Do not update the default cleaner map')
        cleaner_grp.add_argument('--map-file', dest='map_file',
                                 default='/etc/sos/cleaner/default_mapping',
                                 help=('Provide a previously generated mapping'
                                       ' file for obfuscation'))
        cleaner_grp.add_argument('--keep-binary-files', default=False,
                                 action='store_true',
                                 dest='keep_binary_files',
                                 help='Keep unprocessable binary files in the '
                                      'archive instead of removing them')
        cleaner_grp.add_argument('--usernames', dest='usernames', default=[],
                                 action='extend',
                                 help='List of usernames to obfuscate')

    @classmethod
    def display_help(cls, section):
        section.set_title('SoS Report Detailed Help')
        section.add_text(
            'The report command is the most common use case for SoS, and aims '
            'to collect relevant diagnostic and troubleshooting data to assist'
            ' with issue analysis without actively performing that analysis on'
            ' the system while it is in use.'
        )
        section.add_text(
            'Additionally, sos report archives can be used for ongoing '
            'inspection for pre-emptive issue monitoring, such as that done '
            'by the Insights project.'
        )

        section.add_text(
            'The typical result of an execution of \'sos report\' is a tarball'
            ' that contains troubleshooting command output, copies of config '
            'files, and copies of relevant sections of the host filesystem. '
            'Root privileges are required for collections.'
        )

        psec = section.add_section(title='How Collections Are Determined')
        psec.add_text(
            'SoS report performs its collections by way of \'plugins\' that '
            'individually specify what files to copy and what commands to run.'
            ' Plugins typically map to specific components or software '
            'packages.'
        )
        psec.add_text(
            'Plugins may specify different collections on different distribu'
            'tions, and some plugins may only be for specific distributions. '
            'Distributions are represented within SoS by \'policies\' and may '
            'influence how other SoS commands or options function. For '
            'example policies can alter where the --upload option defaults '
            'to or functions.'
        )

        ssec = section.add_section(title='See Also')
        ssec.add_text(
            "For information on available options for report, see "
            f"{bold('sos report --help')} and {bold('man sos-report')}"
        )
        ssec.add_text(f"The following {bold('sos help')} sections may be of "
                      "interest:\n")
        help_lines = {
            'report.plugins': 'Information on the plugin design of sos',
            'report.plugins.$plugin': 'Information on a specific $plugin',
            'policies': 'How sos operates on different distributions'
        }
        helpln = ''
        for ln, value in help_lines.items():
            ssec.add_text(f"\t{ln:<36}{value}", newline=False)
        ssec.add_text(helpln)

    def print_header(self):
        print(f"\n{_(f'sos report (version {__version__})')}\n")

    def _get_hardware_devices(self):
        self.devices = {
            'storage': {
                'block': self._get_block_devs(),
                'fibre': self._get_fibre_devs()
            },
            'network': self._get_network_devs(),
            'namespaced_network': self._get_network_namespace_devices(),
            'fstype': self._get_devices_by_fstype()
        }

    def _check_container_runtime(self):
        """Check the loaded container runtimes, and the policy default runtime
        (if set), against any requested --container-runtime value. This can be
        useful for systems that have multiple runtimes, such as RHCOS, but do
        not have a clearly defined 'default' (or one that is determined based
        entirely on configuration).
        """
        if self.opts.container_runtime != 'auto':
            crun = self.opts.container_runtime.lower()
            if crun in ['none', 'off', 'diabled']:
                self.policy.runtimes = {}
                self.soslog.info(
                    "Disabled all container runtimes per user option."
                )
            elif not self.policy.runtimes:
                msg = ("WARNING: No container runtimes are active, ignoring "
                       f"option to set default runtime to '{crun}'\n")
                self.soslog.warning(msg)
            elif crun not in self.policy.runtimes.keys():
                valid = ', '.join(p for p in self.policy.runtimes.keys()
                                  if p != 'default')
                raise Exception(f"Cannot use container runtime '{crun}': no "
                                "such runtime detected. Available runtimes: "
                                f"{valid}")
            else:
                self.policy.runtimes['default'] = self.policy.runtimes[crun]
                self.soslog.info(
                    "Set default container runtime to "
                    f"'{self.policy.runtimes['default'].name}'"
                )

    def _get_fibre_devs(self):
        """Enumerate a list of fibrechannel devices on this system so that
        plugins can iterate over them

        These devices are used by add_device_cmd() in the Plugin class.
        """
        try:
            devs = []
            devdirs = [
                'fc_host',
                'fc_transport',
                'fc_remote_ports',
                'fc_vports'
            ]
            for devdir in devdirs:
                if os.path.isdir(f"/sys/class/{devdir}"):
                    devs.extend(glob.glob(f"/sys/class/{devdir}/*"))
            return devs
        except Exception as err:
            self.soslog.error(f"Could not get fibre device list: {err}")
            return []

    def _get_block_devs(self):
        """Enumerate a list of block devices on this system so that plugins
        can iterate over them

        These devices are used by add_device_cmd() in the Plugin class.
        """
        try:
            device_list = [f"/dev/{d}" for d in os.listdir('/sys/block')]
            loop_devices = sos_get_command_output('losetup --all --noheadings')
            real_loop_devices = []
            if loop_devices['status'] == 0:
                for loop_dev in loop_devices['output'].splitlines():
                    loop_device = loop_dev.split()[0].replace(':', '')
                    real_loop_devices.append(loop_device)
            ghost_loop_devs = [dev for dev in device_list
                               if dev.startswith("loop")
                               if dev not in real_loop_devices]
            dev_list = list(set(device_list) - set(ghost_loop_devs))
            return dev_list
        except Exception as err:
            self.soslog.error(f"Could not get block device list: {err}")
            return []

    def _get_namespaces(self):
        self.namespaces = {
            'network': self._get_network_namespaces()
        }

    def _get_network_devs(self):
        """Helper to encapsulate network devices probed by sos. Rather than
        probing lists of distinct device types like we do for storage, we can
        do some introspection of device enumeration where a single interface
        may have multiple device types. E.G an 'ethernet' device could also be
        a bond, and that is pertinent information for device iteration.

        :returns:   A collection of enumerated devices sorted by device type
        :rtype:     ``dict`` with keys being device types
        """
        _devs = {
            'ethernet': [],
            'bridge': [],
            'team': [],
            'bond': []
        }
        try:
            if is_executable('nmcli', sysroot=self.opts.sysroot):
                _devs.update(self._get_nmcli_devs())
            # if nmcli failed for some reason, fallback
            if not _devs['ethernet']:
                self.soslog.debug(
                    'Network devices not enumerated by nmcli. Will attempt to '
                    'manually compile list of devices.'
                )
                _devs.update(self._get_eth_devs())
                _devs['bridge'] = self._get_bridge_devs()
        except Exception as err:
            self.soslog.warning(f"Could not enumerate network devices: {err}")
        return _devs

    def _get_network_namespace_devices(self):
        """Enumerate the network devices that exist within each network
        namespace that exists on the system
        """
        _nmdevs = {}
        for nmsp in self.namespaces['network']:
            _nmdevs[nmsp] = {
                'ethernet': self._get_eth_devs(nmsp)
            }
        return _nmdevs

    def _get_nmcli_devs(self):
        """Use nmcli, if available, to enumerate network devices. From this
        output, manually grok together lists of devices.
        """
        _devs = {}
        try:
            _ndevs = sos_get_command_output('nmcli --fields DEVICE,TYPE dev')
            if _ndevs['status'] == 0:
                for dev in _ndevs['output'].splitlines()[1:]:
                    dname, dtype = dev.split()
                    if dtype not in _devs:
                        _devs[dtype] = [dname]
                    else:
                        _devs[dtype].append(dname)
                    _devs['ethernet'].append(dname)
            _devs['ethernet'] = list(set(_devs['ethernet']))
        except Exception as err:
            self.soslog.debug(f"Could not parse nmcli devices: {err}")
        return _devs

    def _get_eth_devs(self, namespace=None):
        """Enumerate a list of ethernet network devices so that plugins can
        reliably iterate over the same set of devices without doing piecemeal
        discovery.

        These devices are used by `add_device_cmd()` when `devices` includes
        "ethernet" or "network".

        :param namespace:   Inspect this existing network namespace, if
                            provided
        :type namespace:    ``str``

        :returns:   All valid ethernet devices found, potentially within a
                    given namespace
        :rtype:     ``list``
        """
        filt_devs = ['bonding_masters']
        _eth_devs = []
        if not namespace:
            try:
                # Override checking sysroot here, as network devices will not
                # be under the sysroot in live environments or in containers
                # that are correctly setup to collect from the host
                _eth_devs = [
                    dev for dev in listdir('/sys/class/net', None)
                    if dev not in filt_devs
                ]
            except Exception as err:
                self.soslog.warning(
                    f'Failed to manually determine network devices: {err}'
                )
        else:
            try:
                _nscmd = f"ip netns exec {namespace} ls /sys/class/net"
                _nsout = sos_get_command_output(_nscmd)
                if _nsout['status'] == 0:
                    for _nseth in _nsout['output'].split():
                        if _nseth not in filt_devs:
                            _eth_devs.append(_nseth)
            except Exception as err:
                self.soslog.warning(
                    f"Could not determine network namespace '{namespace}' "
                    f"devices: {err}"
                )
        return {
            'ethernet': _eth_devs,
            'bond': [bd for bd in _eth_devs if bd.startswith('bond')],
            'tun': [td for td in _eth_devs if td.startswith('tun')]
        }

    def _get_bridge_devs(self):
        """Enumerate a list of bridge devices so that plugins can reliably
        iterate over the same set of bridges.

        These devices are used by `add_device_cmd()` when `devices` includes
        "bridge" or "network".
        """
        _bridges = []
        try:
            _bout = sos_get_command_output('brctl show', timeout=15)
        except Exception as err:
            self.soslog.warning(f"Unable to enumerate bridge devices: {err}")
        if _bout['status'] == 0:
            for _bline in _bout['output'].splitlines()[1:]:
                try:
                    _bridges.append(_bline.split()[0])
                except Exception as err:
                    self.soslog.info(
                        f"Could not parse device from line '{_bline}': {err}"
                    )
        return _bridges

    def _get_network_namespaces(self):
        """Enumerate a list of network namespaces on this system so that
        plugins can iterate over them

        Note that stderr is not collected, so no handling of error lines.
        """
        out_ns = []

        ip_netns = sos_get_command_output("ip netns")
        if ip_netns['status'] == 0:
            for line in ip_netns['output'].splitlines():
                if line.isspace() or line[:1].isspace():
                    continue
                out_ns.append(line.partition(' ')[0])
        return out_ns

    def _get_devices_by_fstype(self):
        _dev_fstypes = {}
        _devs = sos_get_command_output("lsblk -snrpo FSTYPE,NAME")
        if _devs['status'] != 0:
            return _dev_fstypes
        for line in (_devs['output'].splitlines()):
            helper = line.strip().split()
            if len(helper) == 1:
                helper.insert(0, 'unknown')
            if "ext" in helper[0]:
                helper[0] = 'ext4'
            _dev_fstypes.setdefault(helper[0], [])
            _dev_fstypes[helper[0]].append(helper[1])
        return _dev_fstypes

    def get_commons(self):
        return {
            'cmddir': self.cmddir,
            'logdir': self.logdir,
            'rptdir': self.rptdir,
            'tmpdir': self.tmpdir,
            'soslog': self.soslog,
            'policy': self.policy,
            'sysroot': self.sysroot,
            'verbosity': self.opts.verbosity,
            'cmdlineopts': self.opts,
            'devices': self.devices,
            'namespaces': self.namespaces
        }

    def get_temp_file(self):
        return self.tempfile_util.new()

    def _make_archive_paths(self):
        self.archive.makedirs(self.cmddir, 0o755)
        self.archive.makedirs(self.logdir, 0o755)
        self.archive.makedirs(self.rptdir, 0o755)

    def _set_directories(self):
        self.cmddir = 'sos_commands'
        self.logdir = 'sos_logs'
        self.rptdir = 'sos_reports'

    def _set_debug(self):
        if self.opts.debug:
            sys.excepthook = self._exception
            self.raise_plugins = True
        else:
            self.raise_plugins = False

    @staticmethod
    def _exception(etype, eval_, etrace):
        """ Wrap exception in debugger if not in tty """
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
            # we are in interactive mode or we don't have a tty-like
            # device, so we call the default hook
            sys.__excepthook__(etype, eval_, etrace)
        else:
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, eval_, etrace, limit=2,
                                      file=sys.stdout)
            print()
            # ...then start the debugger in post-mortem mode.
            pdb.pm()

    def handle_exception(self, plugname=None, func=None):
        if self.raise_plugins or self.exit_process:
            # retrieve exception info for the current thread and stack.
            (etype, val, tb) = sys.exc_info()
            # we are NOT in interactive mode, print the exception...
            traceback.print_exception(etype, val, tb, file=sys.stdout)
            print()
            # ...then start the debugger in post-mortem mode.
            pdb.post_mortem(tb)
        if plugname and func:
            self._log_plugin_exception(plugname, func)

    def _add_sos_logs(self):
        # Make sure the log files are added before we remove the log
        # handlers. This prevents "No handlers could be found.." messages
        # from leaking to the console when running in --quiet mode when
        # Archive classes attempt to acess the log API.
        if getattr(self, "sos_log_file", None):
            self.archive.add_file(self.sos_log_file,
                                  dest=os.path.join('sos_logs', 'sos.log'))
        if getattr(self, "sos_ui_log_file", None):
            self.archive.add_file(self.sos_ui_log_file,
                                  dest=os.path.join('sos_logs', 'ui.log'))

    def _is_in_profile(self, plugin_class):
        only_plugins = self.opts.only_plugins
        if not self.opts.profiles:
            return True
        if not hasattr(plugin_class, "profiles"):
            return False
        if only_plugins and not self._is_not_specified(plugin_class.name()):
            return True
        return any(p in self.opts.profiles for p in plugin_class.profiles)

    def _is_skipped(self, plugin_name):
        return plugin_name in self.opts.skip_plugins

    def _is_inactive(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).check_enabled() and
                plugin_name not in self.opts.enable_plugins and
                plugin_name not in self.opts.only_plugins)

    def _is_not_default(self, plugin_name, pluginClass):
        return (not pluginClass(self.get_commons()).default_enabled() and
                plugin_name not in self.opts.enable_plugins and
                plugin_name not in self.opts.only_plugins)

    def _is_not_specified(self, plugin_name):
        return (self.opts.only_plugins and
                plugin_name not in self.opts.only_plugins)

    def _skip(self, plugin_class, reason="unknown"):
        self.skipped_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons()),
            reason
        ))

    def _load(self, plugin_class):
        self.loaded_plugins.append((
            plugin_class.name(),
            plugin_class(self.get_commons())
        ))

    def load_plugins(self):
        import_plugin = sos.report.plugins.import_plugin
        helper = ImporterHelper(sos.report.plugins)
        plugins = helper.get_modules()
        self.plugin_names = []
        self.profiles = set()
        using_profiles = len(self.opts.profiles)
        policy_classes = self.policy.valid_subclasses
        extra_classes = []

        if self.opts.experimental:
            extra_classes.append(sos.report.plugins.ExperimentalPlugin)
        valid_plugin_classes = tuple(policy_classes + extra_classes)
        validate_plugin = self.policy.validate_plugin
        remaining_profiles = list(self.opts.profiles)

        # validate and load plugins
        for plug in plugins:
            plugbase, __ = os.path.splitext(plug)
            try:
                plugin_classes = import_plugin(plugbase, valid_plugin_classes)
                if not plugin_classes:
                    # no valid plugin classes for this policy
                    continue

                plugin_class = self.policy.match_plugin(plugin_classes)

                if not validate_plugin(plugin_class,
                                       experimental=self.opts.experimental):
                    self.soslog.warning(
                        _(f"plugin {plug} does not validate, skipping"))
                    if self.opts.verbosity > 0:
                        self._skip(plugin_class, _("does not validate"))
                        continue

                # plug-in is valid, let's decide whether run it or not
                self.plugin_names.append(plugbase)

                in_profile = self._is_in_profile(plugin_class)
                if not in_profile:
                    self._skip(plugin_class, _("excluded"))
                    continue

                if self._is_skipped(plugbase):
                    self._skip(plugin_class, _("skipped"))
                    continue

                if self._is_inactive(plugbase, plugin_class):
                    self._skip(plugin_class, _("inactive"))
                    continue

                if self._is_not_default(plugbase, plugin_class):
                    self._skip(plugin_class, _("optional"))
                    continue

                # only add the plugin's profiles once we know it is usable
                if hasattr(plugin_class, "profiles"):
                    self.profiles.update(plugin_class.profiles)

                # true when the null (empty) profile is active
                default_profile = not using_profiles and in_profile
                if self._is_not_specified(plugbase) and default_profile:
                    self._skip(plugin_class, _("not specified"))
                    continue

                for i in plugin_class.profiles:
                    if i in remaining_profiles:
                        remaining_profiles.remove(i)
                self._load(plugin_class)
            except Exception as e:
                self.soslog.warning(_(f"plugin {plug} does not install, "
                                      f"skipping: {e}"))
                self.handle_exception()
        if len(remaining_profiles) > 0:
            self.soslog.error(_('Unknown or inactive profile(s) provided:'
                                f' {", ".join(remaining_profiles)}'))
            self.list_profiles()
            self._exit(1)

    def _set_all_options(self):
        if self.opts.alloptions:
            for __, plug in self.loaded_plugins:
                for opt in plug.options.values():
                    if bool in opt.val_type:
                        opt.value = True

    def _set_tunables(self):
        if self.opts.plugopts:
            opts = {}
            for opt in self.opts.plugopts:
                try:
                    opt, val = opt.split("=")
                except ValueError:
                    val = True

                if isinstance(val, str):
                    val = val.lower()
                    if val in ["on", "enable", "enabled", "true", "yes"]:
                        val = True
                    elif val in ["off", "disable", "disabled", "false", "no"]:
                        val = False
                    else:
                        # try to convert string "val" to int()
                        try:
                            val = int(val)
                        except ValueError:
                            # not a number to convert back to int from argparse
                            pass

                try:
                    plug, opt = opt.split(".")
                except ValueError:
                    plug = opt
                    opt = True

                try:
                    opts[plug]
                except KeyError:
                    opts[plug] = {}
                opts[plug][opt] = val

            for plugname, plug in self.loaded_plugins:
                if plugname in opts:
                    for opt in opts[plugname]:
                        if opt not in plug.options:
                            self.soslog.error(f'no such option "{opt}" for '
                                              f'plugin ({plugname})')
                            self._exit(1)
                        try:
                            plug.options[opt].set_value(opts[plugname][opt])
                            self.soslog.debug(
                                f"Set {plugname} plugin option to "
                                f"{plug.options[opt]}")
                        except Exception as err:
                            self.soslog.error(err)
                            self._exit(1)
                    del opts[plugname]
            for plugname in opts:
                self.soslog.error('WARNING: unable to set option for disabled '
                                  f'or non-existing plugin ({plugname}).')
            # in case we printed warnings above, visually intend them from
            # subsequent header text
            if opts.keys():
                self.soslog.error('')

    def _check_for_unknown_plugins(self):
        import itertools
        for plugin in itertools.chain(self.opts.only_plugins,
                                      self.opts.enable_plugins):
            plugin_name = plugin.split(".")[0]
            if plugin_name not in self.plugin_names:
                self.soslog.fatal(f'a non-existing plugin ({plugin_name}) was '
                                  'specified in the command line.')
                self._exit(1)
        for plugin in self.opts.skip_plugins:
            if plugin not in self.plugin_names:
                self.soslog.warning(
                    f"Requested to skip non-existing plugin '{plugin}'."
                )

    def _set_plugin_options(self):
        for __, plugin in self.loaded_plugins:
            for opt in plugin.options:
                self.all_options.append(plugin.options[opt])

    def _set_estimate_only(self):
        # set estimate-only mode by enforcing some options settings
        # and return a corresponding log messages string
        msg = "\nEstimate-only mode enabled"
        ext_msg = []
        if self.opts.threads > 1:
            ext_msg += [f"--threads={self.opts.threads} overriden to 1", ]
            self.opts.threads = 1
        if not self.opts.build:
            ext_msg += ["--build enabled", ]
            self.opts.build = True
        if not self.opts.no_postproc:
            ext_msg += ["--no-postproc enabled", ]
            self.opts.no_postproc = True
        if self.opts.clean:
            ext_msg += ["--clean disabled", ]
            self.opts.clean = False
        if self.opts.upload:
            ext_msg += ["--upload* options disabled", ]
            self.opts.upload = False
        if ext_msg:
            msg += ", which overrides some options:\n  " + "\n  ".join(ext_msg)
        else:
            msg += "."
        msg += "\n\n"
        return msg

    def _report_profiles_and_plugins(self):
        self.ui_log.info("")
        if self.loaded_plugins:
            self.ui_log.info(f" {len(self.profiles)} profiles, "
                             f"{len(self.loaded_plugins)} plugins")
        else:
            # no valid plugins for this profile
            self.ui_log.info(f" {len(self.profiles)} profiles")
        self.ui_log.info("")

    def list_plugins(self):
        if not self.loaded_plugins and not self.skipped_plugins:
            self.soslog.fatal(_("no valid plugins found"))
            return

        if self.loaded_plugins:
            self.ui_log.info(_("The following plugins are currently enabled:"))
            self.ui_log.info("")
            for (plugname, plug) in self.loaded_plugins:
                self.ui_log.info(f" {plugname:<20} {plug.get_description()}")
        else:
            self.ui_log.info(_("No plugin enabled."))
        self.ui_log.info("")

        if self.skipped_plugins:
            self.ui_log.info(_("The following plugins are currently "
                               "disabled:"))
            self.ui_log.info("")
            for (plugname, plugclass, reason) in self.skipped_plugins:
                self.ui_log.info(f" {plugname:<20} {reason:<14} "
                                 f"{plugclass.get_description()}")

        self.ui_log.info("")

        if self.all_options:
            self.ui_log.info(_("The following options are available for ALL "
                               "plugins:"))
            _defaults = self.loaded_plugins[0][1].get_default_plugin_opts()
            for _opt in _defaults:
                opt = _defaults[_opt]
                val = opt.value
                if opt.value == -1:
                    if _opt == 'timeout':
                        val = self.opts.plugin_timeout or TIMEOUT_DEFAULT
                    elif _opt == 'cmd-timeout':
                        val = self.opts.cmd_timeout or TIMEOUT_DEFAULT
                    else:
                        val = TIMEOUT_DEFAULT
                if opt.name == 'postproc':
                    val = not self.opts.no_postproc
                self.ui_log.info(f" {opt.name:<25} {val:<15} {opt.desc}")
            self.ui_log.info("")

            self.ui_log.info(_("The following plugin options are available:"))
            for opt in self.all_options:
                if opt.name in ('timeout', 'postproc', 'cmd-timeout'):
                    if opt.value == opt.default:
                        continue
                # format option value based on its type (int or bool)
                if isinstance(opt.value, bool):
                    if opt.value is True:
                        tmpopt = "on"
                    else:
                        tmpopt = "off"
                else:
                    tmpopt = opt.value

                if tmpopt is None:
                    tmpopt = 0

                self.ui_log.info(f" {f'{opt.plugin}.{opt.name}':<25} "
                                 f"{tmpopt:<15} {opt.desc}")
        else:
            self.ui_log.info(_("No plugin options available."))

        self.ui_log.info("")
        profiles = list(self.profiles)
        profiles.sort()
        lines = _format_list("Profiles: ", profiles, indent=True)
        for line in lines:
            self.ui_log.info(f" {line}")
        self._report_profiles_and_plugins()

    def list_profiles(self):
        if not self.profiles:
            self.soslog.fatal(_("no valid profiles found"))
            return
        self.ui_log.info(_("The following profiles are available:"))
        self.ui_log.info("")

        def _has_prof(c):
            return hasattr(c, "profiles")

        profiles = list(self.profiles)
        profiles.sort()
        for profile in profiles:
            plugins = []
            for name, plugin in self.loaded_plugins:
                if _has_prof(plugin) and profile in plugin.profiles:
                    plugins.append(name)
            lines = _format_list(f"{profile:<15}", plugins, indent=True)
            for line in lines:
                self.ui_log.info(f" {line}")
        self._report_profiles_and_plugins()

    def list_presets(self):
        if not self.policy.presets:
            self.soslog.fatal(_("no valid presets found"))
            return
        self.ui_log.info(_("The following presets are available:"))
        self.ui_log.info("")

        for preset in self.policy.presets.keys():
            if not preset:
                continue
            preset = self.policy.find_preset(preset)
            self.ui_log.info(f"{'name:':>14} {preset.name}")
            self.ui_log.info(f"{'description:':>14} {preset.desc}")
            if preset.note:
                self.ui_log.info(f"{'note:':>14} {preset.note}")

            if self.opts.verbosity > 0:
                args = preset.opts.to_args()
                options_str = f"{'options:':>14} "
                lines = _format_list(options_str, args, indent=True, sep=' ')
                for line in lines:
                    self.ui_log.info(line)
            self.ui_log.info("")

    def add_preset(self, name, desc="", note=""):
        """Add a new command line preset for the current options with the
            specified name.

            :param name: the name of the new preset
            :returns: True on success or False otherwise
        """
        policy = self.policy
        if policy.find_preset(name):
            self.ui_log.error(f"A preset named '{name}' already exists")
            return False

        desc = desc or self.opts.desc
        note = note or self.opts.note

        try:
            policy.add_preset(name=name, desc=desc, note=note, opts=self.opts)
        except Exception as e:
            self.ui_log.error(f"Could not add preset: {e}")
            return False

        # Filter --add-preset <name> from arguments list
        arg_index = self.cmdline.index("--add-preset")
        args = self.cmdline[0:arg_index] + self.cmdline[arg_index + 2:]

        self.ui_log.info(
            f"Added preset '{name}' with options {' '.join(args)}\n")
        return True

    def del_preset(self, name):
        """Delete a named command line preset.

            :param name: the name of the preset to delete
            :returns: True on success or False otherwise
        """
        policy = self.policy
        if not policy.find_preset(name):
            self.ui_log.error(f"Preset '{name}' not found")
            return False

        try:
            policy.del_preset(name=name)
        except Exception as e:
            self.ui_log.error(f"{str(e)}\n")
            return False

        self.ui_log.info(f"Deleted preset '{name}'\n")
        return True

    def batch(self):
        msg = self.policy.get_msg()
        if self.opts.estimate_only:
            msg += self._set_estimate_only()
        if self.opts.batch:
            self.ui_log.info(msg)
        else:
            msg += _("Press ENTER to continue, or CTRL-C to quit.\n")
            try:
                input(msg)
            except KeyboardInterrupt:
                self.ui_log.error("Exiting on user cancel")
                self._exit(130)
            except Exception as e:
                self._exit(1, e)

    def _log_plugin_exception(self, plugin, method):
        trace = traceback.format_exc()
        msg = "caught exception in plugin method"
        plugin_err_log = f"{plugin}-plugin-errors.txt"
        logpath = os.path.join(self.logdir, plugin_err_log)
        self.soslog.error(f'{msg} "{plugin}.{method}()"')
        self.soslog.error(f'writing traceback to {logpath}')
        self.archive.add_string(f"{trace}\n", logpath, mode='a')

    def prework(self):
        self.policy.pre_work()
        try:
            self.ui_log.info(_(" Setting up archive ..."))
            self.setup_archive()
            self._make_archive_paths()
            return
        except (OSError, IOError) as e:
            # we must not use the logging subsystem here as it is potentially
            # in an inconsistent or unreliable state (e.g. an EROFS for the
            # file system containing our temporary log files).
            if e.errno in fatal_fs_errors:
                print("")
                print(f" {e.strerror} while setting up archive")
                print("")
            else:
                print(f"Error setting up archive: {e}")
                raise
        except Exception as e:
            self.ui_log.error("")
            self.ui_log.error(" Unexpected exception setting up archive:")
            traceback.print_exc()
            self.ui_log.error(e)
        self._exit(1)

    def setup(self):
        self.ui_log.info(_(" Setting up plugins ..."))
        for plugname, plug in self.loaded_plugins:
            try:
                self.report_md.plugins.add_section(plugname)
                plug.set_plugin_manifest(getattr(self.report_md.plugins,
                                                 plugname))
                start = datetime.now()
                plug.manifest.add_field('setup_start', start)
                plug.archive = self.archive
                plug.add_default_collections()
                plug.setup()
                self.env_vars.update(plug._env_vars)
                if self.opts.verify:
                    plug.setup_verify()
                end = datetime.now()
                plug.manifest.add_field('setup_end', end)
                plug.manifest.add_field('setup_time', end - start)
            except KeyboardInterrupt:
                raise KeyboardInterrupt  # pylint: disable=raise-missing-from
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(
                        f" {e.strerror} while setting up plugins")
                    self.ui_log.error("")
                    self._exit(1)
                self.handle_exception(plugname, "setup")
            except Exception:
                self.handle_exception(plugname, "setup")

    def version(self):
        """Fetch version information from all plugins and store in the report
        version file"""

        versions = []
        versions.append(f"sos report: {__version__}")

        self.archive.add_string(content="\n".join(versions),
                                dest='version.txt')

    def collect(self):
        self.ui_log.info(_(" Running plugins. Please wait ..."))
        self.ui_log.info("")

        plugruncount = 0
        self.pluglist = []
        self.running_plugs = []
        for i in self.loaded_plugins:
            plugruncount += 1
            self.pluglist.append((plugruncount, i[0]))
        try:
            results = []
            with ThreadPoolExecutor(self.opts.threads) as executor:
                results = executor.map(self._collect_plugin,
                                       list(self.pluglist))
            for res in results:
                if not res:
                    self.soslog.debug(f"Unexpected plugin task result: {res}")
            self.ui_log.info("")
        except KeyboardInterrupt:
            # We may not be at a newline when the user issues Ctrl-C
            self.ui_log.error("\nExiting on user cancel\n")
            os._exit(1)

    def _collect_plugin(self, plugin):
        """Wraps the collect_plugin() method so we can apply a timeout
        against the plugin as a whole"""
        with ThreadPoolExecutor(1) as pool:
            try:
                _plug = self.loaded_plugins[plugin[0]-1][1]
                t = pool.submit(self.collect_plugin, plugin)
                # Re-type int 0 to NoneType, as otherwise result() will treat
                # it as a literal 0-second timeout
                timeout = _plug.timeout or None
                start = datetime.now()
                _plug.manifest.add_field('start_time', start)
                t.result(timeout=timeout)
                end = datetime.now()
                _plug.manifest.add_field('end_time', end)
                _plug.manifest.add_field('run_time', end - start)
            except FuturesTimeoutError:
                msg = f"Plugin {plugin[1]} timed out"
                # log to ui_log.error to show the user, log to soslog.info
                # so that someone investigating the sos execution has it all
                # in one place, but without double notifying the user.
                self.ui_log.error(f"\n {msg}\n")
                self.soslog.info(msg)
                self.running_plugs.remove(plugin[1])
                self.loaded_plugins[plugin[0]-1][1].set_timeout_hit()
                pool.shutdown(wait=True)
                pool._threads.clear()
        if self.opts.estimate_only:
            # call "du -s -B1" for the tmp dir to get the disk usage of the
            # data collected by the plugin - if the command fails, count with 0
            tmpdir = self.archive.get_tmp_dir()
            try:
                du = sos_get_command_output(f'du -sB1 {tmpdir}')
                self.estimated_plugsizes[plugin[1]] = \
                    int(du['output'].split()[0])
            except Exception:
                self.estimated_plugsizes[plugin[1]] = 0
            # remove whole tmp_dir content - including "sos_commands" and
            # similar dirs that will be re-created on demand by next plugin
            # if needed; it is less error-prone approach than skipping
            # deletion of some dirs but deleting their content
            for f in os.listdir(tmpdir):
                f = os.path.join(tmpdir, f)
                if os.path.isdir(f) and not os.path.islink(f):
                    rmtree(f)
                else:
                    os.unlink(f)
        return True

    def collect_plugin(self, plugin):
        try:
            count, plugname = plugin
            plug = self.loaded_plugins[count-1][1]
            self.running_plugs.append(plugname)
        except Exception:
            return False
        numplugs = len(self.loaded_plugins)
        status_line = (f"  Starting {f'{count}/{numplugs}':<5} {plugname:<15} "
                       f"[Running: {' '.join(p for p in self.running_plugs)}]")
        self.ui_progress(status_line)
        try:
            plug.collect_plugin()
            # certain exceptions can cause either of these lists to no
            # longer contain the plugin, which will result in sos hanging
            # so we can't blindly call remove() on these two.
            try:
                self.pluglist.remove(plugin)
            except ValueError:
                self.soslog.debug(
                    f"Could not remove {plugin} from plugin list, ignoring..."
                )
            try:
                self.running_plugs.remove(plugname)
            except ValueError:
                self.soslog.debug(
                    f"Could not remove {plugin} from running plugin list, "
                    f"ignoring..."
                )
            status = ''
            if (len(self.pluglist) <= int(self.opts.threads) and
                    self.running_plugs):
                status = (f"  Finishing plugins {' ':<12} [Running: "
                          f"{' '.join(p for p in self.running_plugs)}]")
            if not self.running_plugs and not self.pluglist:
                status = "\n  Finished running plugins"
            if status:
                self.ui_progress(status)
        except SoSTimeoutError:
            # we already log and handle the plugin timeout in the nested thread
            # pool this is running in, so don't do anything here.
            pass
        except (OSError, IOError) as e:
            if e.errno in fatal_fs_errors:
                self.ui_log.error(
                    f"\n {e.strerror} while collecting plugin data")
                self.ui_log.error(
                    f" Data collected still available at {self.tmpdir}\n")
                os._exit(1)
            self.handle_exception(plugname, "collect")
        except Exception:
            self.handle_exception(plugname, "collect")
        return None

    def ui_progress(self, status_line):
        if self.opts.verbosity == 0 and not self.opts.batch:
            status_line = f"\r{status_line.ljust(90)}"
        else:
            status_line = f"{status_line}\n"
        if not self.opts.quiet:
            sys.stdout.write(status_line)
            sys.stdout.flush()

    def collect_env_vars(self):
        if not self.env_vars:
            return
        env = '\n'.join([
            f"{name}={val}" for (name, val) in
            [(name, f'{os.environ.get(name)}') for name in self.env_vars if
             os.environ.get(name) is not None]
        ]) + '\n'
        self.archive.add_string(env, 'environment')

    def generate_reports(self):
        report = Report()

        # generate report content
        for plugname, plug in self.loaded_plugins:
            section = Section(name=plugname)

            for alert in plug.alerts:
                section.add(Alert(alert))

            if plug.custom_text:
                section.add(Note(plug.custom_text))

            for f in plug.copied_files:
                section.add(CopiedFile(name=f['srcpath'],
                                       href=".." + f['dstpath']))

            for cmd in plug.executed_commands:
                section.add(Command(name=cmd['cmd'], return_code=0,
                                    href=os.path.join(
                                        "..",
                                        self.get_commons()['cmddir'],
                                        cmd['file']
                                    )))

            for __, f, __ in plug.copy_strings:
                section.add(CreatedFile(name=f,
                                        href=os.path.join("..", f)))

            report.add(section)

        # print it in text, JSON and HTML formats
        formatlist = (
            (PlainTextReport, "sos.txt",  "text"),
            (JSONReport,      "sos.json", "JSON"),
            (HTMLReport,      "sos.html", "HTML")
        )
        for class_, filename, type_ in formatlist:
            try:
                fd = self.get_temp_file()
                output = class_(report).unicode()
                # safeguard against non-UTF characters
                output = output.encode('utf-8', 'replace').decode()
                fd.write(output)
                fd.flush()
                self.archive.add_file(fd, dest=os.path.join('sos_reports',
                                                            filename))
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(
                        f" {e.strerror} while writing {type_} report")
                    self.ui_log.error("")
                    self._exit(1)

    def postproc(self):
        for plugname, plug in self.loaded_plugins:
            try:
                if plug.get_option('postproc'):
                    plug.postproc()
                else:
                    self.soslog.info(
                        f"Skipping postproc for plugin {plugname}")
            except (OSError, IOError) as e:
                if e.errno in fatal_fs_errors:
                    self.ui_log.error("")
                    self.ui_log.error(
                        f" {e.strerror} while post-processing plugin data")
                    self.ui_log.error("")
                    self._exit(1)
                self.handle_exception(plugname, "postproc")
            except Exception:
                self.handle_exception(plugname, "postproc")

    def _create_checksum(self, archive, hash_name):
        if not archive:
            return False

        try:
            hash_size = 1024**2  # Hash 1MiB of content at a time.
            digest = hashlib.new(hash_name)
            with open(archive, 'rb') as archive_fp:
                while True:
                    hashdata = archive_fp.read(hash_size)
                    if not hashdata:
                        break
                    digest.update(hashdata)
        except Exception:
            self.handle_exception()
        return digest.hexdigest()

    def _write_checksum(self, archive, hash_name, checksum):
        # store checksum into file
        with open(archive + "." + hash_name, "w", encoding='utf-8') as fp:
            if checksum:
                fp.write(checksum + "\n")

    def final_work(self):
        archive = None    # archive path
        directory = None  # report directory path (--build)
        map_file = None  # path of the map file generated for the report

        self.generate_manifest_tag_summary()

        # use this instead of self.opts.clean beyond the initial check if
        # cleaning was requested in case SoSCleaner fails for some reason
        do_clean = False
        if self.opts.clean:
            try:
                hook_commons = {
                    'policy': self.policy,
                    'tmpdir': self.tmpdir,
                    'sys_tmp': self.sys_tmp,
                    'options': self.opts,
                    'manifest': self.manifest
                }
                cleaner = SoSCleaner(in_place=True, hook_commons=hook_commons)
                cleaner.set_target_path(self.archive.get_archive_path())
                # ignore the returned paths here
                map_file, _paths = cleaner.execute()
                do_clean = True
            except Exception as err:
                print(_(f"ERROR: Unable to obfuscate report: {err}"))

        self._add_sos_logs()
        if self.manifest is not None:
            self.archive.add_final_manifest_data(self.opts.compression_type)
        # Hide upload passwords in the log files
        self._obfuscate_upload_passwords()
        # Now, separately clean the log files that cleaner also wrote to
        if do_clean:
            _dir = os.path.join(self.tmpdir, self.archive._name)
            cleaner.obfuscate_file(os.path.join(_dir, 'sos_logs', 'sos.log'),
                                   short_name='sos.log')
            cleaner.obfuscate_file(os.path.join(_dir, 'sos_logs', 'ui.log'),
                                   short_name='ui.log')
            cleaner.obfuscate_file(
                os.path.join(_dir, 'sos_reports', 'manifest.json'),
                short_name='manifest.json'
            )

        # Now, just (optionally) pack the report and print work outcome; let
        # print ui_log to stdout also in quiet mode. For non-quiet mode we
        # already added the handler
        if self.opts.quiet:
            self.add_ui_log_to_stdout()

        # print results in estimate mode (to include also just added manifest)
        if self.opts.estimate_only:
            from sos.utilities import get_human_readable
            from pathlib import Path
            # add sos_logs, sos_reports dirs, etc., basically everything
            # that remained in self.tmpdir after plugins' contents removal
            # that still will be moved to the sos report final directory path
            tmpdir_path = Path(self.tmpdir)
            self.estimated_plugsizes['sos_logs_reports'] = sum(
                    f.lstat().st_size for f in tmpdir_path.glob('**/*'))

            _sum = get_human_readable(sum(self.estimated_plugsizes.values()))
            self.ui_log.info("Estimated disk space requirement for whole "
                             f"uncompressed sos report directory: {_sum}")
            bigplugins = sorted(self.estimated_plugsizes.items(),
                                key=lambda x: x[1], reverse=True)[:5]
            bp_out = ",  ".join(f"{p}: {get_human_readable(v, precision=0)}"
                                for p, v in bigplugins)
            self.ui_log.info(f"Five biggest plugins:  {bp_out}")
            self.ui_log.info("")
            self.ui_log.info("Please note the estimation is relevant to the "
                             "current options.")
            self.ui_log.info("Be aware that the real disk space requirements "
                             "might be different. A rule of thumb is to "
                             "reserve at least double the estimation.")
            self.ui_log.info("")

        # package up and compress the results
        if not self.opts.build:
            old_umask = os.umask(0o077)
            if not self.opts.quiet:
                print(_("Creating compressed archive..."))
            # compression could fail for a number of reasons
            try:
                if do_clean:
                    self.archive.rename_archive_root(cleaner)
                archive = self.archive.finalize(
                    self.opts.compression_type)
            except (OSError, IOError) as e:
                print("")
                print(_(f" {e.strerror} while finalizing archive "
                        f"{self.archive.get_archive_path()}"))
                print("")
                if e.errno in fatal_fs_errors:
                    self._exit(1)
            except Exception:
                if self.opts.debug:
                    raise
                return False
            finally:
                os.umask(old_umask)
        else:
            if self.opts.encrypt_pass or self.opts.encrypt_key:
                self.ui_log.warning("\nUnable to encrypt when using --build. "
                                    "Encryption is only available for "
                                    "archives.")
            # move the archive root out of the private tmp directory.
            directory = self.archive.get_archive_path()
            dir_name = os.path.basename(directory)
            if do_clean:
                dir_name = cleaner.obfuscate_string(dir_name)
            try:
                final_dir = os.path.join(self.sys_tmp, dir_name)
                os.rename(directory, final_dir)
                directory = final_dir
            except (OSError, IOError):
                print(_(f"Error moving directory: {directory}"))
                return False

        checksum = None

        if not self.opts.build:
            # if creating archive file failed, report it and
            # skip generating checksum
            if not archive:
                print("Creating archive tarball failed.")
            else:
                try:
                    # compute and store the archive checksum
                    hash_name = self.policy.get_preferred_hash_name()
                    checksum = self._create_checksum(archive, hash_name)
                except Exception:
                    print(_("Error generating archive checksum after "
                            "archive creation.\n"))
                    return False
                try:
                    self._write_checksum(archive, hash_name, checksum)
                except (OSError, IOError):
                    print(_(f"Error writing checksum for file: {archive}"))

                # output filename is in the private tmpdir - move it to the
                # containing directory.
                base_archive = os.path.basename(archive)
                if do_clean:
                    base_archive = cleaner.obfuscate_string(
                            base_archive.replace('.tar', '-obfuscated.tar')
                    )
                final_name = os.path.join(self.sys_tmp, base_archive)
                # Get stat on the archive
                archivestat = os.stat(archive)

                archive_hash = archive + "." + hash_name
                final_hash = final_name + "." + hash_name

                # move the archive and checksum file
                try:
                    os.rename(archive, final_name)
                    archive = final_name
                except (OSError, IOError):
                    print(_(f"Error moving archive file: {archive}"))
                    return False

                # There is a race in the creation of the final checksum file:
                # since the archive has already been published and the checksum
                # file name is predictable once the archive name is known a
                # malicious user could attempt to create a symbolic link in
                # order to misdirect writes to a file of the attacker's choose.
                #
                # To mitigate this we write the checksum inside the private tmp
                # directory and use an atomic rename that is guaranteed to
                # either succeed or fail: at worst the move will fail and be
                # reported to the user. The correct checksum value is still
                # written to the terminal and nothing is written to a location
                # under the control of the user creating the link.
                try:
                    os.rename(archive_hash, final_hash)
                except (OSError, IOError):
                    print(_(f"Error moving checksum file: {archive_hash}"))

                self.policy.display_results(archive, directory, checksum,
                                            archivestat, map_file=map_file)
        else:
            self.policy.display_results(archive, directory, checksum,
                                        map_file=map_file)

        if (self.opts.upload or self.opts.upload_url
                or self.opts.upload_s3_endpoint):
            if not self.opts.build:
                try:
                    self.policy.upload_archive(archive)
                    self.ui_log.info(_("Uploaded archive successfully"))
                except Exception as err:
                    self.ui_log.error(f"Upload attempt failed: {err}")
            else:
                msg = ("Unable to upload archive when using --build as no "
                       "archive is created.")
                self.ui_log.error(msg)

        # clean up
        logging.shutdown()
        if self.tempfile_util:
            self.tempfile_util.clean()
        if self.tmpdir and os.path.isdir(self.tmpdir):
            rmtree(self.tmpdir)

        return True

    def verify_plugins(self):
        if not self.loaded_plugins:
            self.soslog.error(_("no valid plugins were enabled"))
            return False
        return True

    def add_manifest_data(self):
        """Add 'global' data to the manifest, that is any information that is
        not plugin-specific
        """
        self.report_md.add_field('sysroot', self.sysroot)
        self.report_md.add_field('preset', self.preset.name if self.preset else
                                 'unset')
        self.report_md.add_list('profiles', self.opts.profiles)

        _io_class = 'unknown'
        if is_executable('ionice'):
            _io = sos_get_command_output(f"ionice -p {os.getpid()}")
            if _io['status'] == 0:
                _io_class = _io['output'].split()[0].strip(':')
        self.report_md.add_section('priority')
        self.report_md.priority.add_field('io_class', _io_class)
        self.report_md.priority.add_field('niceness', os.nice(0))

        self.report_md.add_section('devices')
        for key, value in self.devices.items():
            self.report_md.devices.add_field(key, value)
        self.report_md.add_list('enabled_plugins', self.opts.enable_plugins)
        self.report_md.add_list('disabled_plugins', self.opts.skip_plugins)
        self.report_md.add_section('plugins')

    def generate_manifest_tag_summary(self):
        """Add a section to the manifest that contains a dict summarizing the
        tags that were created and assigned during this report's creation.

        This summary dict can be used for easier inspection of tagged items by
        inspection/analyzer projects such as Red Hat Insights. The format of
        this dict is `{tag_name: [file_list]}`.
        """
        def compile_tags(ent, key='filepath'):
            for tag in ent['tags']:
                if not ent[key] or not tag:
                    continue
                try:
                    path = tag_summary[tag]
                except KeyError:
                    path = []
                path.extend(
                    ent[key] if isinstance(ent[key], list) else [ent[key]]
                )
                tag_summary[tag] = sorted(list(set(path)))

        tag_summary = {}
        for plug in self.report_md.plugins:
            for cmd in plug.commands:
                compile_tags(cmd)
            for _file in plug.files:
                compile_tags(_file, 'files_copied')
            for collection in plug.collections:
                compile_tags(collection)
        self.report_md.add_field('tag_summary',
                                 dict(sorted(tag_summary.items())))

    def _merge_preset_options(self):
        # Log command line options
        self.soslog.info(f"[{__name__}:setup] executing "
                         f"'sos {' '.join(self.cmdline)}'")

        # Log active preset defaults
        preset_args = self.preset.opts.to_args()
        msg = (f"[{__name__}:setup] using '{self.preset.name}' preset defaults"
               f" ({' '.join(preset_args)})")
        self.soslog.info(msg)

        # Log effective options after applying preset defaults
        self.soslog.info(f"[{__name__}:setup] effective options now: "
                         f"{' '.join(self.opts.to_args())}")

    def execute(self):
        try:
            self.policy.set_commons(self.get_commons())
            self.load_plugins()
            self._set_all_options()
            self._merge_preset_options()
            self._set_tunables()
            self._check_for_unknown_plugins()
            self._set_plugin_options()

            if self.opts.list_plugins:
                self.list_plugins()
                raise SystemExit
            if self.opts.list_profiles:
                self.list_profiles()
                raise SystemExit
            if self.opts.list_presets:
                self.list_presets()
                raise SystemExit
            if self.opts.add_preset:
                self.add_preset(self.opts.add_preset)
                raise SystemExit
            if self.opts.del_preset:
                self.del_preset(self.opts.del_preset)
                raise SystemExit
            # verify that at least one plug-in is enabled
            if not self.verify_plugins():
                raise SystemExit

            self.batch()
            self.prework()
            self.add_manifest_data()
            self.setup()
            self.collect()
            if not self.opts.no_env_vars:
                self.collect_env_vars()
            if not self.opts.no_report:
                self.generate_reports()
            if not self.opts.no_postproc:
                self.postproc()
            else:
                self.ui_log.info("Skipping postprocessing of collected data")
            self.version()
            return self.final_work()

        except OSError:
            if self.opts.debug:
                raise
            if not os.getenv('SOS_TEST_LOGS', None) == 'keep':
                self.cleanup()
        except KeyboardInterrupt:
            self.ui_log.error("\nExiting on user cancel")
            self.cleanup()
            self._exit(130)
        except SystemExit as e:
            if not os.getenv('SOS_TEST_LOGS', None) == 'keep':
                self.cleanup()
            sys.exit(e.code)

        self._exit(1)
        # Never gets here. This is to fix "inconsistent-return-statements
        return False

# vim: set et ts=4 sw=4 :
