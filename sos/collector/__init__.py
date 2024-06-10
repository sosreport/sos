# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# pylint: disable=too-many-locals,too-many-branches

import fnmatch
import inspect
import json
import os
import random
import re
import string
import socket
import shutil
import sys

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from pathlib import Path
from shlex import quote
from textwrap import fill
from sos.cleaner import SoSCleaner
from sos.collector.sosnode import SosNode
from sos.options import ClusterOption, str_to_bool
from sos.component import SoSComponent
from sos.utilities import bold
from sos import __version__

COLLECTOR_CONFIG_DIR = '/etc/sos/groups.d'


class SoSCollector(SoSComponent):
    """
    sos collect, or SoS Collector, is the formerly standalone sos-collector
    project, brought into sos natively in 4.0 and later.

    It is meant to collect sos reports from an arbitrary number of remote
    nodes, as well as the localhost, at the same time. These nodes may be
    either user defined, defined by some clustering software, or both.

    For cluster defined lists of nodes, cluster profiles exist that not only
    define how these node lists are generated but may also influence the
    sos report command run on nodes depending upon their role within the
    cluster.

    Nodes are connected to via a 'transport' which defaults to the use of
    OpenSSH's Control Persist feature. Other transport types are available, and
    may be specifically linked to use with a certain cluster profile (or, at
    minimum, a node within a certain cluster type even if that profile is not
    used).

    sos collect may be run from either a node within the cluster that is
    capable of enumerating/discovering the other cluster nodes, or may be run
    from a user's workstation and instructed to first connect to such a node
    via the --primary option. If run in the latter manner, users will likely
    want to use the --no-local option, as by default sos collect will also
    collect an sos report locally.

    Users should expect this command to result in a tarball containing one or
    more sos report archives on the system that sos collect was executed on.
    """

    desc = 'Collect an sos report from multiple nodes simultaneously'

    arg_defaults = {
        'all_logs': False,
        'alloptions': False,
        'allow_system_changes': False,
        'become_root': False,
        'case_id': False,
        'chroot': 'auto',
        'clean': False,
        'cluster_options': [],
        'cluster_type': None,
        'container_runtime': 'auto',
        'domains': [],
        'disable_parsers': [],
        'enable_plugins': [],
        'encrypt_key': '',
        'encrypt_pass': '',
        'group': None,
        'image': '',
        'force_pull_image': True,
        'skip_cleaning_files': [],
        'jobs': 4,
        'journal_size': 0,
        'keywords': [],
        'keyword_file': None,
        'keep_binary_files': False,
        'label': '',
        'list_options': False,
        'log_size': 0,
        'low_priority': False,
        'map_file': '/etc/sos/cleaner/default_mapping',
        'primary': '',
        'namespaces': None,
        'nodes': [],
        'no_env_vars': False,
        'no_local': False,
        'nopasswd_sudo': False,
        'no_pkg_check': False,
        'no_update': False,
        'only_plugins': [],
        'password': False,
        'password_per_node': False,
        'plugopts': [],
        'plugin_timeout': None,
        'cmd_timeout': None,
        'preset': '',
        'registry_user': None,
        'registry_password': None,
        'registry_authfile': None,
        'save_group': '',
        'since': '',
        'skip_commands': [],
        'skip_files': [],
        'skip_plugins': [],
        'ssh_key': '',
        'ssh_port': 22,
        'ssh_user': 'root',
        'timeout': 600,
        'transport': 'auto',
        'verify': False,
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
        'upload_s3_object_prefix': None
    }

    def __init__(self, parser, parsed_args, cmdline_args):
        super().__init__(parser, parsed_args, cmdline_args)
        os.umask(0o77)
        self.client_list = []
        self.node_list = []
        self.primary = None
        self.retrieved = 0
        self.cluster = None
        self.cluster_type = None

        # add manifest section for collect
        self.manifest.components.add_section('collect')
        # shorthand reference
        self.collect_md = self.manifest.components.collect
        # placeholders in manifest organization
        self.collect_md.add_field('cluster_type', 'none')
        self.collect_md.add_list('node_list')
        # add a place to set/get the sudo password, but do not expose it via
        # the CLI, because security is a thing
        setattr(self.opts, 'sudo_pw', '')
        # get the local hostname and addresses to filter from results later
        self.hostname = socket.gethostname()
        try:
            self.ip_addrs = list(set([
                i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)
            ]))
        except Exception:
            # this is almost always a DNS issue with reverse resolution
            # set a safe fallback and log the issue
            self.log_error(
                "Could not get a list of IP addresses from this hostnamne. "
                "This may indicate a DNS issue in your environment"
            )
            self.ip_addrs = ['127.0.0.1']

        self._parse_options()
        self.clusters = self.load_clusters()

        if not self.opts.list_options:
            try:
                self.parse_node_strings()
                self.parse_cluster_options()
                self.log_debug(f'Executing {" ".join(s for s in sys.argv)}')
                self.log_debug(
                    f"Found cluster profiles: {self.clusters.keys()}")
                self.verify_cluster_options()

            except KeyboardInterrupt:
                self.exit('Exiting on user cancel', 130)
            except Exception:
                raise

    def load_clusters(self):
        """Loads all cluster types supported by the local installation for
        future comparison and/or use
        """
        import sos.collector.clusters
        package = sos.collector.clusters
        supported_clusters = {}
        clusters = self._load_modules(package, 'clusters')
        for cluster in clusters:
            supported_clusters[cluster[0]] = cluster[1](self.commons)
        return supported_clusters

    @classmethod
    def _load_modules(cls, package, submod):
        """Helper to import cluster and host types"""
        modules = []
        for path in package.__path__:
            if os.path.isdir(path):
                modules.extend(cls._find_modules_in_path(path, submod))
        return modules

    @classmethod
    def _find_modules_in_path(cls, path, modulename):
        """Given a path and a module name, find everything that can be imported
        and then import it

            path - the filesystem path of the package
            modulename - the name of the module in the package

        E.G. a path of 'clusters', and a modulename of 'ovirt' equates to
        importing sos.collector.clusters.ovirt
        """
        modules = []
        if os.path.exists(path):
            for pyfile in sorted(os.listdir(path)):
                if not pyfile.endswith('.py'):
                    continue
                if '__' in pyfile:
                    continue
                fname, ext = os.path.splitext(pyfile)
                modname = f'sos.collector.{modulename}.{fname}'
                modules.extend(cls._import_modules(modname))
        return modules

    @classmethod
    def _import_modules(cls, modname):
        """Import and return all found classes in a module"""
        mod_short_name = modname.split('.')[2]
        try:
            module = __import__(modname, globals(), locals(), [mod_short_name])
        except ImportError as e:
            print(f'Error while trying to load module {modname}: '
                  f' {e.__class__.__name__}')
            raise e
        modules = inspect.getmembers(module, inspect.isclass)
        for mod in modules:
            if mod[0] in ('SosHost', 'Cluster'):
                modules.remove(mod)
        return modules

    def parse_node_strings(self):
        """Parses the given --nodes option(s) to properly format the regex
        list that we use. We cannot blindly split on ',' chars since it is a
        valid regex character, so we need to scan along the given strings and
        check at each comma if we should use the preceeding string by itself
        or not, based on if there is a valid regex at that index.
        """
        if not self.opts.nodes:
            return
        nodes = []
        if not isinstance(self.opts.nodes, list):
            self.opts.nodes = [self.opts.nodes]
        for node in self.opts.nodes:
            idxs = [i for i, m in enumerate(node) if m == ',']
            idxs.append(len(node))
            start = 0
            pos = 0
            for idx in idxs:
                try:
                    pos = idx
                    reg = node[start:idx]
                    re.compile(re.escape(reg))
                    # make sure we aren't splitting a regex value
                    if '[' in reg and ']' not in reg:
                        continue
                    nodes.append(reg.lstrip(','))
                    start = idx
                except re.error:
                    continue
            if pos != len(node):
                nodes.append(node[pos+1:])
        self.opts.nodes = nodes

    @classmethod
    def add_parser_options(cls, parser):

        # Add the supported report passthru options to a group for logical
        # grouping in --help display
        sos_grp = parser.add_argument_group(
            'Report Passthru Options',
            'These options control how report is run on nodes'
        )
        sos_grp.add_argument('-a', '--alloptions', action='store_true',
                             help='Enable all sos report options')
        sos_grp.add_argument('--all-logs', action='store_true',
                             help='Collect logs regardless of size')
        sos_grp.add_argument('--allow-system-changes', action='store_true',
                             default=False,
                             help=('Allow sos report to run commands that may '
                                   'alter system state'))
        sos_grp.add_argument('--chroot', default='',
                             choices=['auto', 'always', 'never'],
                             help="chroot executed commands to SYSROOT")
        sos_grp.add_argument("--container-runtime", default="auto",
                             help="Default container runtime to use for "
                                  "collections. 'auto' for policy control.")
        sos_grp.add_argument('-e', '--enable-plugins', action="extend",
                             help='Enable specific plugins for sos report')
        sos_grp.add_argument('--journal-size', type=int, default=0,
                             help='Limit the size of journals in MiB')
        sos_grp.add_argument('-k', '--plugin-option', '--plugopts',
                             action="extend", dest='plugopts',
                             help='Plugin option as plugname.option=value')
        sos_grp.add_argument('--log-size', default=0, type=int,
                             help='Limit the size of individual logs '
                                  '(not journals) in MiB')
        sos_grp.add_argument('--low-priority', action='store_true',
                             default=False, help='Run reports as low priority')
        sos_grp.add_argument('-n', '--skip-plugins', action="extend",
                             help='Skip these plugins')
        sos_grp.add_argument('-o', '--only-plugins', action="extend",
                             default=[],
                             help='Run these plugins only')
        sos_grp.add_argument('--namespaces', default=None,
                             help='limit number of namespaces to collect '
                                  'output for - 0 means unlimited')
        sos_grp.add_argument('--no-env-vars', action='store_true',
                             default=False,
                             help='Do not collect env vars in sos reports')
        sos_grp.add_argument('--plugin-timeout', type=int, default=None,
                             help='Set the global plugin timeout value')
        sos_grp.add_argument('--cmd-timeout', type=int, default=None,
                             help='Set the global command timeout value')
        sos_grp.add_argument('--since', default=None,
                             help=('Escapes archived files older than date. '
                                   'This will also affect --all-logs. '
                                   'Format: YYYYMMDD[HHMMSS]'))
        sos_grp.add_argument('--skip-commands', default=[], action='extend',
                             dest='skip_commands',
                             help="do not execute these commands")
        sos_grp.add_argument('--skip-files', default=[], action='extend',
                             dest='skip_files',
                             help="do not collect these files")
        sos_grp.add_argument('--verify', action="store_true",
                             help='perform pkg verification during collection')

        # Add the collector specific options to a separate group to keep
        # everything organized
        collect_grp = parser.add_argument_group(
            'Collector Options',
            'These options control how collect runs locally'
        )
        collect_grp.add_argument('-b', '--become', action='store_true',
                                 dest='become_root',
                                 help='Become root on the remote nodes')
        collect_grp.add_argument('--case-id', help='Specify case number')
        collect_grp.add_argument('--cluster-type',
                                 help='Specify a type of cluster profile')
        collect_grp.add_argument('-c', '--cluster-option',
                                 dest='cluster_options', action='append',
                                 help=('Specify a cluster options used by a '
                                       'profile and takes the form of '
                                       'cluster.option=value'))
        collect_grp.add_argument('--group', default=None,
                                 help='Use a predefined group JSON file')
        collect_grp.add_argument('--save-group', default='',
                                 help='Save a resulting node list to a group')
        collect_grp.add_argument('--image',
                                 help=('Specify the container image to use for'
                                       ' containerized hosts.'))
        collect_grp.add_argument('--force-pull-image', '--pull',
                                 default=True, choices=(True, False),
                                 type=str_to_bool,
                                 help='Force pull the container image even if '
                                      'it already exists on the host')
        collect_grp.add_argument('--registry-user', default=None,
                                 help='Username to authenticate to the '
                                      'registry with for pulling an image')
        collect_grp.add_argument('--registry-password', default=None,
                                 help='Password to authenticate to the '
                                      'registry with for pulling an image')
        collect_grp.add_argument('--registry-authfile', default=None,
                                 help='Use this authfile to provide registry '
                                      'authentication when pulling an image')
        collect_grp.add_argument('-i', '--ssh-key', help='Specify an ssh key')
        collect_grp.add_argument('-j', '--jobs', default=4, type=int,
                                 help='Number of concurrent nodes to collect')
        collect_grp.add_argument('-l', '--list-options', action="store_true",
                                 help='List options available for profiles')
        collect_grp.add_argument('--label',
                                 help='Assign a label to the archives')
        collect_grp.add_argument('--primary', '--manager', '--controller',
                                 dest='primary', default='',
                                 help='Specify a primary node for cluster '
                                      'enumeration')
        collect_grp.add_argument('--nopasswd-sudo', action='store_true',
                                 help='Use passwordless sudo on nodes')
        collect_grp.add_argument('--nodes', action="append",
                                 help=('Provide a comma delimited list of '
                                       'nodes, or a regex to match against'))
        collect_grp.add_argument('--no-pkg-check', action='store_true',
                                 help=('Do not run package checks. Use this '
                                       'with --cluster-type if there are rpm '
                                       'or apt issues on node'))
        collect_grp.add_argument('--no-local', action='store_true',
                                 help='Do not collect a report from localhost')
        collect_grp.add_argument('-p', '--ssh-port', type=int,
                                 help='Specify SSH port for all nodes')
        collect_grp.add_argument('--password', action='store_true',
                                 default=False,
                                 help='Prompt for user password for nodes')
        collect_grp.add_argument('--password-per-node', action='store_true',
                                 default=False,
                                 help='Prompt for password for each node')
        collect_grp.add_argument('--preset', default='', required=False,
                                 help='Specify a sos preset to use')
        collect_grp.add_argument('--ssh-user',
                                 help='Specify an SSH user. Default root')
        collect_grp.add_argument('--timeout', type=int, required=False,
                                 help='Timeout for sos report on each node.')
        collect_grp.add_argument('--transport', default='auto', type=str,
                                 help='Remote connection transport to use')
        collect_grp.add_argument("--upload", action="store_true",
                                 default=False,
                                 help="Upload archive to a policy-default "
                                      "location")
        collect_grp.add_argument("--upload-url", default=None,
                                 help="Upload the archive to specified server")
        collect_grp.add_argument("--upload-directory", default=None,
                                 help="Specify upload directory for archive")
        collect_grp.add_argument("--upload-user", default=None,
                                 help="Username to authenticate with")
        collect_grp.add_argument("--upload-pass", default=None,
                                 help="Password to authenticate with")
        collect_grp.add_argument("--upload-method", default='auto',
                                 choices=['auto', 'put', 'post'],
                                 help="HTTP method to use for uploading")
        collect_grp.add_argument("--upload-no-ssl-verify", default=False,
                                 action='store_true',
                                 help="Disable SSL verification for upload url"
                                 )
        collect_grp.add_argument("--upload-s3-endpoint", default=None,
                                 help="Endpoint to upload to for S3 bucket")
        collect_grp.add_argument("--upload-s3-region", default=None,
                                 help="Region for the S3 bucket")
        collect_grp.add_argument("--upload-s3-bucket", default=None,
                                 help="Name of the S3 bucket to upload to")
        collect_grp.add_argument("--upload-s3-access-key", default=None,
                                 help="Access key for the S3 bucket")
        collect_grp.add_argument("--upload-s3-secret-key", default=None,
                                 help="Secret key for the S3 bucket")
        collect_grp.add_argument("--upload-s3-object-prefix", default=None,
                                 help="Prefix for the S3 object/key")
        collect_grp.add_argument("--upload-protocol", default='auto',
                                 choices=['auto', 'https', 'ftp', 'sftp',
                                          's3'],
                                 help="Manually specify the upload protocol")

        # Group the cleaner options together
        cleaner_grp = parser.add_argument_group(
            'Cleaner/Masking Options',
            'These options control how data obfuscation is performed'
        )
        cleaner_grp.add_argument('--clean', '--cleaner', '--mask',
                                 dest='clean',
                                 default=False, action='store_true',
                                 help='Obfuscate sensitive information')
        cleaner_grp.add_argument('--keep-binary-files', default=False,
                                 action='store_true', dest='keep_binary_files',
                                 help='Keep unprocessable binary files in the '
                                      'archive instead of removing them')
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
        cleaner_grp.add_argument('--usernames', dest='usernames', default=[],
                                 action='extend',
                                 help='List of usernames to obfuscate')

    @classmethod
    def display_help(cls, section):
        section.set_title('SoS Collect Detailed Help')
        section.add_text(cls.__doc__)

        hsections = {
            'collect.clusters': 'Information on cluster profiles',
            'collect.clusters.$cluster': 'Specific profile information',
            'collect.transports': 'Information on how connections are made',
            'collect.transports.$transport': 'Specific transport information'
        }
        section.add_text(
            'The following help sections may be of further interest:\n'
        )
        for hsec in hsections:
            section.add_text(
                f"{' ':>8}{bold(hsec):<40}{hsections[hsec]:<30}",
                newline=False
            )

    def exit(self, msg=None, error=0, force=False):
        """Used to terminate and ensure all cleanup is done, setting the exit
        code as specified if required.

        :param msg:     Log the provided message as an error
        :type msg:      ``str``

        :param error:   The exit code to use when terminating
        :type error:    ``int``

        :param force:   Use os.exit() to break out of nested threads if needed
        :type force:    ``bool``
        """
        if self.cluster:
            self.cluster.cleanup()
        if msg:
            self.log_error(msg)
        try:
            self.close_all_connections()
        except Exception:
            self.log_warn("Warning: Failed to close all remote connections")
        if error != 130:
            # keep the tempdir around when a user issues a keyboard interrupt
            # like we do for report
            self.cleanup()
        if not force:
            sys.exit(error)
        else:
            os._exit(error)

    def _parse_options(self):
        """From commandline options, defaults, etc... build a set of commons
        to hand to other collector mechanisms
        """
        self.commons = {
            'cmdlineopts': self.opts,
            'need_sudo': True if self.opts.ssh_user != 'root' else False,
            'tmpdir': self.tmpdir,
            'hostlen': max(len(self.opts.primary), len(self.hostname)),
            'policy': self.policy
        }

    def parse_cluster_options(self):
        opts = []
        if not isinstance(self.opts.cluster_options, list):
            self.opts.cluster_options = [self.opts.cluster_options]
        if self.opts.cluster_options:
            for option in self.opts.cluster_options:
                cluster = option.split('.')[0]
                name = option.split('.')[1].split('=')[0]
                try:
                    # there are no instances currently where any cluster option
                    # should contain a legitimate space.
                    value = option.split('=')[1].split()[0]
                except IndexError:
                    # conversion to boolean is handled during validation
                    value = 'True'

                opts.append(
                    ClusterOption(name, value, value.__class__, cluster)
                )
        self.opts.cluster_options = opts

    def verify_cluster_options(self):
        """Verify that requested cluster options exist"""
        if self.opts.cluster_options:
            for opt in self.opts.cluster_options:
                match = False
                for clust in self.clusters:
                    for option in self.clusters[clust].options:
                        if opt.name == option.name and opt.cluster == clust:
                            match = True
                            opt.value = self._validate_option(option, opt)
                            break
            if not match:
                self.exit('Unknown cluster option provided: '
                          f'{opt.cluster}.{opt.name}', 1)

    def _validate_option(self, default, cli):
        """Checks to make sure that the option given on the CLI is valid.
        Valid in this sense means that the type of value given matches what a
        cluster profile expects (str for str, bool for bool, etc).

        For bool options, this will also convert the string equivalent to an
        actual boolean value
        """
        if not default.opt_type == bool:
            if not default.opt_type == cli.opt_type:
                msg = "Invalid option type for %s. Expected %s got %s"
                self.exit(msg % (cli.name, default.opt_type, cli.opt_type), 1)
            return cli.value
        else:
            val = cli.value.lower()
            if val not in ['true', 'on', 'yes', 'false', 'off', 'no']:
                msg = ("Invalid value for %s. Accepted values are: 'true', "
                       "'false', 'on', 'off', 'yes', 'no'.")
                self.exit(msg % cli.name, 1)
            else:
                if val in ['true', 'on', 'yes']:
                    return True
                else:
                    return False
        self.exit(f"Unknown option type: {cli.opt_type}")

    def log_info(self, msg):
        """Log info messages to both console and log file"""
        self.soslog.info(msg)

    def log_warn(self, msg):
        """Log warn messages to both console and log file"""
        self.soslog.warning(msg)

    def log_error(self, msg):
        """Log error messages to both console and log file"""
        self.soslog.error(msg)

    def log_debug(self, msg):
        """Log debug message to both console and log file"""
        caller = inspect.stack()[1][3]
        msg = f'[sos_collector:{caller}] {msg}'
        self.soslog.debug(msg)

    def list_options(self):
        """Display options for available clusters"""

        sys.stdout.write('\nThe following clusters are supported by this '
                         'installation\n')
        sys.stdout.write('Use the short name with --cluster-type or cluster '
                         'options (-c)\n\n')
        for cluster in sorted(self.clusters):
            sys.stdout.write(
                f" {cluster:<15} {self.clusters[cluster].cluster_name:30}\n"
            )

        _opts = {}
        for _cluster in self.clusters:
            for opt in self.clusters[_cluster].options:
                if opt.name not in _opts.keys():
                    _opts[opt.name] = opt
                else:
                    for clust in opt.cluster:
                        if clust not in _opts[opt.name].cluster:
                            _opts[opt.name].cluster.append(clust)

        sys.stdout.write('\nThe following cluster options are available:\n\n')
        sys.stdout.write(
            f" {'Cluster':25} {'Option Name':15} {'Type':<10} {'Default':10} "
            f"{'Description':<}\n"
        )

        for _opt in sorted(_opts, key=lambda x: _opts[x].cluster):
            opt = _opts[_opt]
            optln = (
                f"  {', '.join(c for c in sorted(opt.cluster)):25} "
                f"{opt.name:15} {opt.opt_type.__name__:<10} "
                f"{str(opt.value):<10} {opt.description:<10}\n"
            )
            sys.stdout.write(optln)
        sys.stdout.write('\nOptions take the form of cluster.name=value'
                         '\nE.G. "ovirt.no-database=True" or '
                         '"pacemaker.offline=False"\n')

    def delete_tmp_dir(self):
        """Removes the temp directory and all collected sos reports"""
        shutil.rmtree(self.tmpdir)

    def _get_archive_name(self):
        """Generates a name for the tarball archive"""
        nstr = 'sos-collector'
        if self.opts.label:
            nstr += f'-{self.opts.label}'
        if self.opts.case_id:
            nstr += f'-{self.opts.case_id}'
        dt = datetime.strftime(datetime.now(), '%Y-%m-%d')

        try:
            string.lowercase = string.ascii_lowercase
        except NameError as err:
            self.log_debug(f"Could not cast to ascii_lowercase: {err}")

        rand = ''.join(random.choice(string.lowercase) for x in range(5))
        return f'{nstr}-{dt}-{rand}'

    def _get_archive_path(self):
        """Returns the path, including filename, of the tarball we build
        that contains the collected sos reports
        """
        self.arc_name = self._get_archive_name()
        compr = 'gz'
        return self.tmpdir + '/' + self.arc_name + '.tar.' + compr

    def _fmt_msg(self, msg):
        width = 80
        _fmt = ''
        for line in msg.splitlines():
            _fmt = _fmt + fill(line, width, replace_whitespace=False) + '\n'
        return _fmt

    def _load_group_config(self):
        """
        Attempts to load the host group specified on the command line.
        Host groups are defined via JSON files, typically saved under
        /etc/sos/groups.d/, although users can specify a full filepath
        on the commandline to point to one existing anywhere on the system

        Host groups define a list of nodes and/or regexes and optionally the
        primary and cluster-type options.
        """
        grp = self.opts.group
        paths = [
            grp,
            os.path.join(Path.home(), f'.config/sos/groups.d/{grp}'),
            os.path.join(COLLECTOR_CONFIG_DIR, grp)
        ]

        fname = None
        for path in paths:
            if os.path.exists(path):
                fname = path
                break
        if fname is None:
            raise OSError(f"no group definition for {grp}")

        self.log_debug(f"Loading host group {fname}")

        with open(fname, 'r') as hf:
            _group = json.load(hf)
            for key in ['primary', 'cluster_type']:
                if _group[key]:
                    self.log_debug(f"Setting option '{key}' to '{_group[key]}'"
                                   "per host group")
                    setattr(self.opts, key, _group[key])
            if _group['nodes']:
                self.log_debug(f"Adding {_group['nodes']} to node list")
                self.opts.nodes.extend(_group['nodes'])

    def write_host_group(self):
        """
        Saves the results of this run of sos collect to a host group file
        on the system so it can be used later on.

        The host group will save the options primary, cluster_type, and nodes
        as determined by sos collect prior to execution of sos reports.
        """
        cfg = {
            'name': self.opts.save_group,
            'primary': self.opts.primary,
            'cluster_type': self.cluster.cluster_type[0],
            'nodes': [n for n in self.node_list]
        }
        if os.getuid() != 0:
            group_path = os.path.join(Path.home(), '.config/sos/groups.d')
            # create the subdir within the user's home directory
            os.makedirs(group_path, exist_ok=True)
        else:
            group_path = COLLECTOR_CONFIG_DIR
        fname = os.path.join(group_path, cfg['name'])
        with open(fname, 'w') as hf:
            json.dump(cfg, hf)
        os.chmod(fname, 0o600)
        return fname

    def prep(self):
        self.policy.set_commons(self.commons)
        if (not self.opts.password and not
                self.opts.password_per_node):
            self.log_debug('password not specified, assuming SSH keys')
            msg = ('sos collect ASSUMES that SSH keys are installed on all '
                   'nodes unless the --password option is provided.\n')
            self.ui_log.info(self._fmt_msg(msg))

        try:
            if ((self.opts.password or (self.opts.password_per_node and
                                        self.opts.primary))
                    and not self.opts.batch):
                self.log_debug('password specified, not using SSH keys')
                msg = ('Provide the SSH password for user '
                       f'{self.opts.ssh_user}: ')
                self.opts.password = getpass(prompt=msg)

            if ((self.commons['need_sudo'] and not self.opts.nopasswd_sudo)
                    and not self.opts.batch):
                if not self.opts.password and not self.opts.password_per_node:
                    self.log_debug('non-root user specified, will request '
                                   'sudo password')
                    msg = ('A non-root user has been provided. Provide sudo '
                           f'password for {self.opts.ssh_user} on remote '
                           'nodes: ')
                    self.opts.sudo_pw = getpass(prompt=msg)
                else:
                    if not self.opts.nopasswd_sudo:
                        self.opts.sudo_pw = self.opts.password
        except KeyboardInterrupt:
            self.exit("\nExiting on user cancel\n", 130)

        if self.opts.become_root:
            if not self.opts.ssh_user == 'root':
                if self.opts.batch:
                    msg = ("Cannot become root without obtaining root "
                           "password. Do not use --batch if you need "
                           "to become root remotely.")
                    self.exit(msg, 1)
                self.log_debug('non-root user asking to become root remotely')
                msg = (f'User {self.opts.ssh_user} will attempt to become '
                       'root. Provide root password: ')
                self.opts.root_password = getpass(prompt=msg)
                self.commons['need_sudo'] = False
            else:
                self.log_info('Option to become root but ssh user is root.'
                              ' Ignoring request to change user on node')
                self.opts.become_root = False

        if self.opts.group:
            try:
                self._load_group_config()
            except Exception as err:
                msg = (f"Could not load specified group {self.opts.group}: "
                       f"{err}")
                self.exit(msg, 1)

        try:
            self.policy.pre_work()
        except KeyboardInterrupt:
            self.exit("Exiting on user cancel\n", 130)

        if self.opts.primary:
            self.connect_to_primary()
            self.opts.no_local = True
        else:
            try:
                can_run_local = True
                local_sudo = None
                skip_local_msg = (
                    "Local sos report generation forcibly skipped due "
                    "to lack of root privileges.\nEither use --nopasswd-sudo, "
                    "run as root, or do not use --batch so that you will be "
                    "prompted for a password\n"
                )
                if (not self.opts.no_local and (os.getuid() != 0 and not
                                                self.opts.nopasswd_sudo)):
                    if not self.opts.batch:
                        msg = ("Enter local sudo password to generate local "
                               "sos report: ")
                        local_sudo = getpass(msg)
                        if local_sudo == '':
                            self.ui_log.info(skip_local_msg)
                            can_run_local = False
                            self.opts.no_local = True
                            local_sudo = None
                    else:
                        self.ui_log.info(skip_local_msg)
                        can_run_local = False
                        self.opts.no_local = True
                self.primary = SosNode('localhost', self.commons,
                                       local_sudo=local_sudo,
                                       load_facts=can_run_local)
            except Exception as err:
                self.log_debug("Unable to determine local installation: "
                               f"{err}")
                self.exit('Unable to determine local installation. Use the '
                          '--no-local option if localhost should not be '
                          'included.\nAborting...\n', 1)

        self.collect_md.add_field('primary', self.primary.address)
        self.collect_md.add_section('nodes')
        self.collect_md.nodes.add_section(self.primary.address)
        self.primary.set_node_manifest(getattr(self.collect_md.nodes,
                                               self.primary.address))

        if self.opts.cluster_type:
            if self.opts.cluster_type == 'none':
                self.cluster = self.clusters['jbon']
            else:
                self.cluster = self.clusters[self.opts.cluster_type]
                self.cluster_type = self.opts.cluster_type
            self.cluster.primary = self.primary

        else:
            self.determine_cluster()
        if self.cluster is None and not self.opts.nodes:
            msg = ('Cluster type could not be determined and no nodes provided'
                   '\nAborting...')
            self.exit(msg, 1)
        elif self.cluster is None and self.opts.nodes:
            self.log_info("Cluster type could not be determined, but --nodes "
                          "is provided. Attempting to continue using JBON "
                          "cluster type and the node list")
            self.cluster = self.clusters['jbon']
            self.cluster_type = 'none'
        self.collect_md.add_field('cluster_type', self.cluster_type)
        if self.cluster:
            self.primary.cluster = self.cluster
            if self.opts.transport == 'auto':
                self.opts.transport = self.cluster.set_transport_type()
            self.cluster.setup()
            if self.cluster.cluster_ssh_key:
                if not self.opts.ssh_key:
                    self.log_debug(
                        f"Updating SSH key to {self.cluster.cluster_ssh_key} "
                        "per cluster")
                    self.opts.ssh_key = self.cluster.cluster_ssh_key

        self.get_nodes()
        if self.opts.save_group:
            gname = self.opts.save_group
            try:
                fname = self.write_host_group()
                self.log_info(f"Wrote group '{gname}' to {fname}")
            except Exception as err:
                self.log_error(f"Could not save group {gname}: {err}")

    def display_nodes(self):
        """Prints a list of nodes to collect from, if available. If no nodes
        are discovered or provided, abort.
        """
        self.ui_log.info('')

        if not self.node_list and not self.primary.connected:
            self.exit('No nodes were detected, or nodes do not have sos '
                      'installed.\nAborting...', 1)

        self.ui_log.info('The following is a list of nodes to collect from:')
        if self.primary.connected and self.primary.hostname is not None:
            if not ((self.primary.local and self.opts.no_local)
                    or self.cluster.strict_node_list):
                self.ui_log.info(
                    f"\t{self.primary.hostname:<{self.commons['hostlen']}}"
                )

        for node in sorted(self.node_list):
            self.ui_log.info(f"\t{node:<{self.commons['hostlen']}}")

        self.ui_log.info('')
        if not self.opts.batch:
            try:
                input("\nPress ENTER to continue with these nodes, or press "
                      "CTRL-C to quit\n")
                self.ui_log.info("")
            except KeyboardInterrupt:
                self.exit("Exiting on user cancel", 130)
            except Exception as e:
                self.exit(repr(e), 1)

    def configure_sos_cmd(self):
        """Configures the sos report command that is run on the nodes"""
        sos_cmd = 'sosreport --batch '

        sos_options = {}

        if self.opts.case_id:
            sos_options['case-id'] = quote(self.opts.case_id)
        if self.opts.alloptions:
            sos_options['alloptions'] = ''
        if self.opts.all_logs:
            sos_options['all-logs'] = ''
        if self.opts.verify:
            sos_options['verify'] = ''
        if self.opts.log_size:
            sos_options['log-size'] = quote(str(self.opts.log_size))
        if self.opts.sysroot:
            sos_options['sysroot'] = quote(self.opts.sysroot)
        if self.opts.chroot:
            sos_options['chroot'] = quote(self.opts.chroot)
        if self.opts.compression_type != 'auto':
            sos_options['compression-type'] = quote(self.opts.compression_type)

        for k, v in sos_options.items():
            sos_cmd += f"--{k} {v} "
        sos_cmd = sos_cmd.rstrip()
        self.log_debug(f"Initial sos cmd set to {sos_cmd}")
        self.commons['sos_cmd'] = 'sosreport --batch '
        self.commons['sos_options'] = sos_options
        self.collect_md.add_field('initial_sos_cmd', sos_cmd)

    def connect_to_primary(self):
        """If run with --primary, we will run cluster checks again that
        instead of the localhost.
        """
        try:
            self.primary = SosNode(self.opts.primary, self.commons)
            self.ui_log.info(f'Connected to {self.opts.primary}, determining '
                             'cluster type...')
        except Exception as e:
            self.log_debug(f'Failed to connect to primary node: {e}')
            self.exit('Could not connect to primary node. Aborting...', 1)

    def determine_cluster(self):
        """This sets the cluster type and loads that cluster's cluster.

        If no cluster type is matched and no list of nodes is provided by
        the user, then we abort.

        If a list of nodes is given, this is not run, however the cluster
        can still be run if the user sets a --cluster-type manually
        """
        checks = list(self.clusters.values())
        for cluster in self.clusters.values():
            checks.remove(cluster)
            cluster.primary = self.primary
            if cluster.check_enabled():
                cname = cluster.__class__.__name__
                self.log_debug(f"Installation matches {cname}, checking for "
                               "layered profiles")
                for remaining in checks:
                    if issubclass(remaining.__class__, cluster.__class__):
                        rname = remaining.__class__.__name__
                        self.log_debug(f"Layered profile {rname} found. "
                                       "Checking installation")
                        remaining.primary = self.primary
                        if remaining.check_enabled():
                            self.log_debug("Installation matches both layered "
                                           f"profile {rname} and base profile "
                                           f"{cname}, setting cluster type to "
                                           "layered profile")
                            cluster = remaining
                            break
                self.cluster = cluster
                self.cluster_type = cluster.name()
                self.commons['cluster'] = self.cluster
                self.ui_log.info(
                    f'Cluster type set to {self.cluster_type}')
                break

    def get_nodes_from_cluster(self):
        """Collects the list of nodes from the determined cluster cluster"""
        if self.cluster_type:
            nodes = self.cluster._get_nodes()
            self.log_debug(f'Node list: {nodes}')
            return nodes
        return []

    def reduce_node_list(self):
        """Reduce duplicate entries of the localhost and/or primary node
        if applicable"""
        if (self.hostname in self.node_list and self.opts.no_local):
            self.node_list.remove(self.hostname)
        if not self.cluster.strict_node_list:
            for i in self.ip_addrs:
                if i in self.node_list:
                    self.node_list.remove(i)
        # remove the primary node from the list, since we already have
        # an open session to it.
        if self.primary is not None and not self.cluster.strict_node_list:
            for n in self.node_list:
                if n == self.primary.hostname or n == self.opts.primary:
                    self.node_list.remove(n)
        self.node_list = list(set(n for n in self.node_list if n))
        self.log_debug(f'Node list reduced to {self.node_list}')
        self.collect_md.add_list('node_list', self.node_list)

    def compare_node_to_regex(self, node):
        """Compares a discovered node name to a provided list of nodes from
        the user. If there is not a match, the node is removed from the list"""
        for regex in self.opts.nodes:
            try:
                regex = fnmatch.translate(regex)
                if re.match(regex, node):
                    return True
            except re.error as err:
                msg = 'Error comparing %s to provided node regex %s: %s'
                self.log_debug(msg % (node, regex, err))
        return False

    def get_nodes(self):
        """ Sets the list of nodes to collect sos reports from """
        if not self.primary and not self.cluster:
            msg = ('Could not determine a cluster type and no list of '
                   'nodes or primary node was provided.\nAborting...'
                   )
            self.exit(msg, 1)

        try:
            nodes = self.get_nodes_from_cluster()
            if self.opts.nodes:
                for node in nodes:
                    if self.compare_node_to_regex(node):
                        self.node_list.append(node)
            else:
                self.node_list = nodes
        except Exception as e:
            self.log_debug(f"Error parsing node list: {e}")
            self.log_debug('Setting node list to --nodes option')
            self.node_list = self.opts.nodes
            for node in self.node_list:
                if any(i in node for i in ('*', '\\', '?', '(', ')', '/')):
                    self.node_list.remove(node)

        # force add any non-regex node strings from nodes option
        if self.opts.nodes:
            for node in self.opts.nodes:
                if any(i in node for i in '*\\?()/[]'):
                    continue
                if node not in self.node_list:
                    self.log_debug(f"Force adding {node} to node list")
                    self.node_list.append(node)

        if not self.primary:
            host = self.hostname.split('.')[0]
            # trust the local hostname before the node report from cluster
            for node in self.node_list:
                if host == node.split('.')[0]:
                    self.node_list.remove(node)
            if not self.cluster.strict_node_list:
                self.node_list.append(self.hostname)
        self.reduce_node_list()
        try:
            _node_max = len(max(self.node_list, key=len))
            self.commons['hostlen'] = max(_node_max, self.commons['hostlen'])
        except (TypeError, ValueError) as err:
            self.log_debug(f"Could not set UI spacing: {err}")

    def _connect_to_node(self, node):
        """Try to connect to the node, and if we can add to the client list to
        run sos report on

        Positional arguments
            node - a tuple specifying (address, password). If no password, set
                   to None
        """
        try:
            client = SosNode(node[0], self.commons, password=node[1])
            client.set_cluster(self.cluster)
            if client.connected:
                self.client_list.append(client)
                self.collect_md.nodes.add_section(node[0])
                client.set_node_manifest(getattr(self.collect_md.nodes,
                                                 node[0]))
            else:
                client.disconnect()
        except Exception:
            # all exception logging is handled within SoSNode
            pass

    def intro(self):
        """Print the intro message and prompts for a case ID if one is not
        provided on the command line
        """
        disclaimer = ("""\
This utility is used to collect sos reports from multiple \
nodes simultaneously. Remote connections are made and/or maintained \
to those nodes via well-known transport protocols such as SSH.

An archive of sos report tarballs collected from the nodes will be \
generated in %s and may be provided to an appropriate support representative.

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No configuration changes will be made to the system running \
this utility or remote systems that it connects to.
""")
        self.ui_log.info(f"\nsos collect (version {__version__})\n")
        intro_msg = self._fmt_msg(disclaimer % self.tmpdir)
        self.ui_log.info(intro_msg)

        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.opts.batch:
            try:
                input(prompt)
                self.ui_log.info("")
            except KeyboardInterrupt:
                self.exit("Exiting on user cancel", 130)
            except Exception as e:
                self.exit(e, 1)

    def execute(self):
        if self.opts.list_options:
            self.list_options()
            self.exit()

        self.intro()

        self.configure_sos_cmd()
        self.prep()
        self.display_nodes()

        self.archive_name = self._get_archive_name()
        self.setup_archive(name=self.archive_name)
        self.archive_path = self.archive.get_archive_path()
        self.archive.makedirs('sos_logs', 0o755)

        self.collect()
        self.exit()

    def collect(self):
        """ For each node, start a collection thread and then tar all
        collected sos reports """
        filters = set([self.primary.address, self.primary.hostname])
        # add primary if:
        # - we are connected to it and
        #   - its hostname is in node_list, or
        #   - we dont forcibly remove local host from collection
        #     (i.e. strict_node_list=False)
        if self.primary.connected and \
                (filters.intersection(set(self.node_list)) or
                 not self.cluster.strict_node_list):
            self.client_list.append(self.primary)

        self.ui_log.info("\nConnecting to nodes...")
        nodes = [(n, None) for n in self.node_list if n not in filters]

        if self.opts.password_per_node:
            _nodes = []
            for node in nodes:
                msg = (f"Please enter the password for {self.opts.ssh_user}@"
                       f"{node[0]}: ")
                node_pwd = getpass(msg)
                _nodes.append((node[0], node_pwd))
            nodes = _nodes

        try:
            pool = ThreadPoolExecutor(self.opts.jobs)
            pool.map(self._connect_to_node, nodes, chunksize=1)
            pool.shutdown(wait=True)

            if (self.opts.no_local and
                    self.client_list[0].address == 'localhost'):
                self.client_list.pop(0)

            self.report_num = len(self.client_list)

            if self.report_num == 0:
                self.exit("No nodes connected. Aborting...", 1)
            elif self.report_num == 1:
                if self.client_list[0].address == 'localhost':
                    self.exit(
                        "Collection would only gather from localhost due to "
                        "failure to either enumerate or connect to cluster "
                        "nodes. Assuming single collection from localhost is "
                        "not desired.\n"
                        "Aborting...", 1
                    )

            self.ui_log.info("\nBeginning collection of sos reports from "
                             f"{self.report_num} nodes, collecting a maximum "
                             f"of {self.opts.jobs} concurrently\n")

            npool = ThreadPoolExecutor(self.opts.jobs)
            npool.map(self._finalize_sos_cmd, self.client_list, chunksize=1)
            npool.shutdown(wait=True)

            pool = ThreadPoolExecutor(self.opts.jobs)
            pool.map(self._collect, self.client_list, chunksize=1)
            pool.shutdown(wait=True)
        except KeyboardInterrupt:
            self.exit("Exiting on user cancel\n", 130, force=True)
        except Exception as err:
            msg = f'Could not connect to nodes: {err}'
            self.exit(msg, 1, force=True)

        if hasattr(self.cluster, 'run_extra_cmd'):
            self.ui_log.info('Collecting additional data from primary node...')
            files = self.cluster._run_extra_cmd()
            if files:
                self.primary.collect_extra_cmd(files)
        msg = '\nSuccessfully captured %s of %s sos reports'
        self.log_info(msg % (self.retrieved, self.report_num))
        self.close_all_connections()
        if self.retrieved > 0:
            arc_name = self.create_cluster_archive()
        else:
            msg = 'No sos reports were collected, nothing to archive...'
            self.exit(msg, 1)

        if (self.opts.upload and self.policy.get_upload_url()) or \
                self.opts.upload_s3_endpoint:
            try:
                self.policy.upload_archive(arc_name)
                self.ui_log.info("Uploaded archive successfully")
            except Exception as err:
                self.ui_log.error(f"Upload attempt failed: {err}")

    def _finalize_sos_cmd(self, client):
        """Calls finalize_sos_cmd() on each node so that we have the final
        command before we thread out the actual execution of sos
        """
        try:
            client.finalize_sos_cmd()
        except Exception as err:
            self.log_error("Could not finalize sos command for "
                           f"{client.address}: {err}")

    def _collect(self, client):
        """Runs sos report on each node"""
        try:
            if not client.local:
                client.sosreport()
            else:
                if not self.opts.no_local:
                    client.sosreport()
            if client.retrieved:
                self.retrieved += 1
        except Exception as err:
            self.log_error(f"Error running sos report: {err}")

    def close_all_connections(self):
        """Close all sessions for nodes"""
        for client in self.client_list:
            if client.connected:
                self.log_debug(f'Closing connection to {client.address}')
                client.disconnect()

    def create_cluster_archive(self):
        """Calls for creation of tar archive then cleans up the temporary
        files created by sos collect"""
        map_file = None
        arc_paths = []
        for host in self.client_list:
            for fname in host.file_list:
                arc_paths.append(fname)

        do_clean = False
        if self.opts.clean:
            hook_commons = {
                'policy': self.policy,
                'tmpdir': self.tmpdir,
                'sys_tmp': self.sys_tmp,
                'options': self.opts,
                'manifest': self.manifest
            }
            try:
                self.ui_log.info('')
                cleaner = SoSCleaner(in_place=True,
                                     hook_commons=hook_commons)
                cleaner.set_target_path(self.tmpdir)
                map_file, arc_paths = cleaner.execute()
                do_clean = True
            except Exception as err:
                self.ui_log.error(f"ERROR: unable to obfuscate reports: {err}")

        try:
            self.log_info('Creating archive of sos reports...')
            for fname in arc_paths:
                dest = fname.split('/')[-1]
                if do_clean:
                    dest = cleaner.obfuscate_string(dest)
                name = os.path.join(self.tmpdir, fname)
                self.archive.add_file(name, dest=dest)
                if map_file:
                    # regenerate the checksum for the obfuscated archive
                    checksum = cleaner.get_new_checksum(fname)
                    if checksum:
                        name = os.path.join('checksums', fname.split('/')[-1])
                        name += '.sha256'
                        self.archive.add_string(checksum, name)
            self.archive.add_file(self.sos_log_file,
                                  dest=os.path.join('sos_logs', 'sos.log'))
            self.archive.add_file(self.sos_ui_log_file,
                                  dest=os.path.join('sos_logs', 'ui.log'))

            if self.manifest is not None:
                self.archive.add_final_manifest_data(
                    self.opts.compression_type
                )
            self._obfuscate_upload_passwords()
            if do_clean:
                _dir = os.path.join(self.tmpdir, self.archive._name)
                cleaner.obfuscate_file(
                    os.path.join(_dir, 'sos_logs', 'sos.log'),
                    short_name='sos.log'
                )
                cleaner.obfuscate_file(
                    os.path.join(_dir, 'sos_logs', 'ui.log'),
                    short_name='ui.log'
                )
                cleaner.obfuscate_file(
                    os.path.join(_dir, 'sos_reports', 'manifest.json'),
                    short_name='manifest.json'
                )

            arc_name = self.archive.finalize(self.opts.compression_type)
            final_name = os.path.join(self.sys_tmp, os.path.basename(arc_name))
            if do_clean:
                final_name = cleaner.obfuscate_string(
                    final_name.replace('.tar', '-obfuscated.tar')
                )
            os.rename(arc_name, final_name)

            if map_file:
                # rename the map file to match the collector archive name, not
                # the temp dir it was constructed in
                map_name = cleaner.obfuscate_string(
                    os.path.join(self.sys_tmp,
                                 f"{self.archive_name}_private_map")
                )
                os.rename(map_file, map_name)
                self.ui_log.info("A mapping of obfuscated elements is "
                                 f"available at\n\t{map_name}")

            self.soslog.info(f'Archive created as {final_name}')
            self.ui_log.info('\nThe following archive has been created. '
                             'Please provide it to your support team.')
            self.ui_log.info(f'\t{final_name}\n')
            return final_name
        except Exception as err:
            msg = (f"Could not finalize archive: {err}\n\nData may still be "
                   f"available uncompressed at {self.archive_path}")
            self.exit(msg, 2)
