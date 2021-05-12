# Copyright Red Hat 2020, Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import fnmatch
import inspect
import json
import os
import random
import re
import string
import socket
import shutil
import subprocess
import sys

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from pathlib import Path
from pipes import quote
from textwrap import fill
from sos.cleaner import SoSCleaner
from sos.collector.sosnode import SosNode
from sos.collector.exceptions import ControlPersistUnsupportedException
from sos.options import ClusterOption
from sos.component import SoSComponent
from sos import __version__

COLLECTOR_CONFIG_DIR = '/etc/sos/groups.d'


class SoSCollector(SoSComponent):
    """Collector is the formerly standalone sos-collector project, brought into
    sos natively in 4.0

    It is meant to collect reports from an arbitrary number of remote nodes,
    as well as the localhost, at the same time. These nodes may be either user
    defined, defined by some clustering software, or both.
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
        'domains': [],
        'enable_plugins': [],
        'encrypt_key': '',
        'encrypt_pass': '',
        'group': None,
        'image': '',
        'jobs': 4,
        'keywords': [],
        'keyword_file': None,
        'label': '',
        'list_options': False,
        'log_size': 0,
        'map_file': '/etc/sos/cleaner/default_mapping',
        'master': '',
        'nodes': [],
        'no_env_vars': False,
        'no_local': False,
        'nopasswd_sudo': False,
        'no_pkg_check': False,
        'no_update': False,
        'only_plugins': [],
        'password': False,
        'password_per_node': False,
        'plugin_options': [],
        'plugin_timeout': None,
        'cmd_timeout': None,
        'preset': '',
        'save_group': '',
        'since': '',
        'skip_commands': [],
        'skip_files': [],
        'skip_plugins': [],
        'sos_opt_line': '',
        'ssh_key': '',
        'ssh_port': 22,
        'ssh_user': 'root',
        'timeout': 600,
        'verify': False,
        'usernames': [],
        'upload': False,
        'upload_url': None,
        'upload_directory': None,
        'upload_user': None,
        'upload_pass': None,
        'upload_method': 'auto',
        'upload_no_ssl_verify': False
    }

    def __init__(self, parser, parsed_args, cmdline_args):
        super(SoSCollector, self).__init__(parser, parsed_args, cmdline_args)
        os.umask(0o77)
        self.client_list = []
        self.node_list = []
        self.master = False
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
                self._check_for_control_persist()
                self.log_debug('Executing %s' % ' '.join(s for s in sys.argv))
                self.log_debug("Found cluster profiles: %s"
                               % self.clusters.keys())
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

    def _load_modules(self, package, submod):
        """Helper to import cluster and host types"""
        modules = []
        for path in package.__path__:
            if os.path.isdir(path):
                modules.extend(self._find_modules_in_path(path, submod))
        return modules

    def _find_modules_in_path(self, path, modulename):
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
                modname = 'sos.collector.%s.%s' % (modulename, fname)
                modules.extend(self._import_modules(modname))
        return modules

    def _import_modules(self, modname):
        """Import and return all found classes in a module"""
        mod_short_name = modname.split('.')[2]
        module = __import__(modname, globals(), locals(), [mod_short_name])
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
                             help=('Allow sosreport to run commands that may '
                                   'alter system state'))
        sos_grp.add_argument('--chroot', default='',
                             choices=['auto', 'always', 'never'],
                             help="chroot executed commands to SYSROOT")
        sos_grp.add_argument('-e', '--enable-plugins', action="extend",
                             help='Enable specific plugins for sosreport')
        sos_grp.add_argument('-k', '--plugin-options', action="extend",
                             help='Plugin option as plugname.option=value')
        sos_grp.add_argument('--log-size', default=0, type=int,
                             help='Limit the size of individual logs (in MiB)')
        sos_grp.add_argument('-n', '--skip-plugins', action="extend",
                             help='Skip these plugins')
        sos_grp.add_argument('-o', '--only-plugins', action="extend",
                             default=[],
                             help='Run these plugins only')
        sos_grp.add_argument('--no-env-vars', action='store_true',
                             default=False,
                             help='Do not collect env vars in sosreports')
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
        collect_grp.add_argument('-i', '--ssh-key', help='Specify an ssh key')
        collect_grp.add_argument('-j', '--jobs', default=4, type=int,
                                 help='Number of concurrent nodes to collect')
        collect_grp.add_argument('-l', '--list-options', action="store_true",
                                 help='List options available for profiles')
        collect_grp.add_argument('--label',
                                 help='Assign a label to the archives')
        collect_grp.add_argument('--master', help='Specify a master node')
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
        collect_grp.add_argument('--sos-cmd', dest='sos_opt_line',
                                 help=('Manually specify the commandline '
                                       'for sos report on nodes'))
        collect_grp.add_argument('--ssh-user',
                                 help='Specify an SSH user. Default root')
        collect_grp.add_argument('--timeout', type=int, required=False,
                                 help='Timeout for sosreport on each node.')
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
        # Group the cleaner options together
        cleaner_grp = parser.add_argument_group(
            'Cleaner/Masking Options',
            'These options control how data obfuscation is performed'
        )
        cleaner_grp.add_argument('--clean', '--cleaner', '--mask',
                                 dest='clean',
                                 default=False, action='store_true',
                                 help='Obfuscate sensistive information')
        cleaner_grp.add_argument('--domains', dest='domains', default=[],
                                 action='extend',
                                 help='Additional domain names to obfuscate')
        cleaner_grp.add_argument('--keywords', action='extend', default=[],
                                 dest='keywords',
                                 help='List of keywords to obfuscate')
        cleaner_grp.add_argument('--keyword-file', default=None,
                                 dest='keyword_file',
                                 help='Provide a file a keywords to obfuscate')
        cleaner_grp.add_argument('--no-update', action='store_true',
                                 default=False, dest='no_update',
                                 help='Do not update the default cleaner map')
        cleaner_grp.add_argument('--map', dest='map_file',
                                 default='/etc/sos/cleaner/default_mapping',
                                 help=('Provide a previously generated mapping'
                                       ' file for obfuscation'))
        cleaner_grp.add_argument('--usernames', dest='usernames', default=[],
                                 action='extend',
                                 help='List of usernames to obfuscate')

    def _check_for_control_persist(self):
        """Checks to see if the local system supported SSH ControlPersist.

        ControlPersist allows OpenSSH to keep a single open connection to a
        remote host rather than building a new session each time. This is the
        same feature that Ansible uses in place of paramiko, which we have a
        need to drop in sos-collector.

        This check relies on feedback from the ssh binary. The command being
        run should always generate stderr output, but depending on what that
        output reads we can determine if ControlPersist is supported or not.

        For our purposes, a host that does not support ControlPersist is not
        able to run sos-collector.

        Returns
            True if ControlPersist is supported, else raise Exception.
        """
        ssh_cmd = ['ssh', '-o', 'ControlPersist']
        cmd = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out, err = cmd.communicate()
        err = err.decode('utf-8')
        if 'Bad configuration option' in err or 'Usage:' in err:
            raise ControlPersistUnsupportedException
        return True

    def exit(self, msg, error=1):
        """Used to safely terminate if sos-collector encounters an error"""
        self.log_error(msg)
        try:
            self.close_all_connections()
        except Exception:
            pass
        self.cleanup()
        sys.exit(error)

    def _parse_options(self):
        """From commandline options, defaults, etc... build a set of commons
        to hand to other collector mechanisms
        """
        self.commons = {
            'cmdlineopts': self.opts,
            'need_sudo': True if self.opts.ssh_user != 'root' else False,
            'tmpdir': self.tmpdir,
            'hostlen': len(self.opts.master) or len(self.hostname),
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
                self.exit('Unknown cluster option provided: %s.%s'
                          % (opt.cluster, opt.name))

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
                self.exit(msg % (cli.name, default.opt_type, cli.opt_type))
            return cli.value
        else:
            val = cli.value.lower()
            if val not in ['true', 'on', 'yes', 'false', 'off', 'no']:
                msg = ("Invalid value for %s. Accepted values are: 'true', "
                       "'false', 'on', 'off', 'yes', 'no'.")
                self.exit(msg % cli.name)
            else:
                if val in ['true', 'on', 'yes']:
                    return True
                else:
                    return False

    def log_info(self, msg):
        """Log info messages to both console and log file"""
        self.soslog.info(msg)

    def log_warn(self, msg):
        """Log warn messages to both console and log file"""
        self.soslog.warn(msg)

    def log_error(self, msg):
        """Log error messages to both console and log file"""
        self.soslog.error(msg)

    def log_debug(self, msg):
        """Log debug message to both console and log file"""
        caller = inspect.stack()[1][3]
        msg = '[sos_collector:%s] %s' % (caller, msg)
        self.soslog.debug(msg)

    def list_options(self):
        """Display options for available clusters"""

        sys.stdout.write('\nThe following clusters are supported by this '
                         'installation\n')
        sys.stdout.write('Use the short name with --cluster-type or cluster '
                         'options (-c)\n\n')
        for cluster in sorted(self.clusters):
            sys.stdout.write(" {:<15} {:30}\n".format(
                                cluster,
                                self.clusters[cluster].cluster_name))

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
        sys.stdout.write(' {:25} {:15} {:<10} {:10} {:<}\n'.format(
            'Cluster',
            'Option Name',
            'Type',
            'Default',
            'Description'
        ))

        for _opt in sorted(_opts, key=lambda x: _opts[x].cluster):
            opt = _opts[_opt]
            optln = ' {:25} {:15} {:<10} {:<10} {:<10}\n'.format(
                ', '.join(c for c in sorted(opt.cluster)),
                opt.name,
                opt.opt_type.__name__,
                str(opt.value),
                opt.description)
            sys.stdout.write(optln)
        sys.stdout.write('\nOptions take the form of cluster.name=value'
                         '\nE.G. "ovirt.no-database=True" or '
                         '"pacemaker.offline=False"\n')

    def delete_tmp_dir(self):
        """Removes the temp directory and all collected sosreports"""
        shutil.rmtree(self.tmpdir)

    def _get_archive_name(self):
        """Generates a name for the tarball archive"""
        nstr = 'sos-collector'
        if self.opts.label:
            nstr += '-%s' % self.opts.label
        if self.opts.case_id:
            nstr += '-%s' % self.opts.case_id
        dt = datetime.strftime(datetime.now(), '%Y-%m-%d')

        try:
            string.lowercase = string.ascii_lowercase
        except NameError:
            pass

        rand = ''.join(random.choice(string.lowercase) for x in range(5))
        return '%s-%s-%s' % (nstr, dt, rand)

    def _get_archive_path(self):
        """Returns the path, including filename, of the tarball we build
        that contains the collected sosreports
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
        master and cluster-type options.
        """
        grp = self.opts.group
        paths = [
            grp,
            os.path.join(Path.home(), '.config/sos/groups.d/%s' % grp),
            os.path.join(COLLECTOR_CONFIG_DIR, grp)
        ]

        fname = None
        for path in paths:
            if os.path.exists(path):
                fname = path
                break
        if fname is None:
            raise OSError("no group definition for %s" % grp)

        self.log_debug("Loading host group %s" % fname)

        with open(fname, 'r') as hf:
            _group = json.load(hf)
            for key in ['master', 'cluster_type']:
                if _group[key]:
                    self.log_debug("Setting option '%s' to '%s' per host group"
                                   % (key, _group[key]))
                    setattr(self.opts, key, _group[key])
            if _group['nodes']:
                self.log_debug("Adding %s to node list" % _group['nodes'])
                self.opts.nodes.extend(_group['nodes'])

    def write_host_group(self):
        """
        Saves the results of this run of sos-collector to a host group file
        on the system so it can be used later on.

        The host group will save the options master, cluster_type, and nodes
        as determined by sos-collector prior to execution of sosreports.
        """
        cfg = {
            'name': self.opts.save_group,
            'master': self.opts.master,
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
        os.chmod(fname, 0o644)
        return fname

    def prep(self):
        self.policy.set_commons(self.commons)
        if (not self.opts.password and not
                self.opts.password_per_node):
            self.log_debug('password not specified, assuming SSH keys')
            msg = ('sos-collector ASSUMES that SSH keys are installed on all '
                   'nodes unless the --password option is provided.\n')
            self.ui_log.info(self._fmt_msg(msg))

        if ((self.opts.password or (self.opts.password_per_node and
                                    self.opts.master))
                and not self.opts.batch):
            self.log_debug('password specified, not using SSH keys')
            msg = ('Provide the SSH password for user %s: '
                   % self.opts.ssh_user)
            self.opts.password = getpass(prompt=msg)

        if ((self.commons['need_sudo'] and not self.opts.nopasswd_sudo)
                and not self.opts.batch):
            if not self.opts.password and not self.opts.password_per_node:
                self.log_debug('non-root user specified, will request '
                               'sudo password')
                msg = ('A non-root user has been provided. Provide sudo '
                       'password for %s on remote nodes: '
                       % self.opts.ssh_user)
                self.opts.sudo_pw = getpass(prompt=msg)
            else:
                if not self.opts.nopasswd_sudo:
                    self.opts.sudo_pw = self.opts.password

        if self.opts.become_root:
            if not self.opts.ssh_user == 'root':
                if self.opts.batch:
                    msg = ("Cannot become root without obtaining root "
                           "password. Do not use --batch if you need "
                           "to become root remotely.")
                    self.exit(msg, 1)
                self.log_debug('non-root user asking to become root remotely')
                msg = ('User %s will attempt to become root. '
                       'Provide root password: ' % self.opts.ssh_user)
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
                self.log_error("Could not load specified group %s: %s"
                               % (self.opts.group, err))
                self._exit(1)

        self.policy.pre_work()

        if self.opts.master:
            self.connect_to_master()
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
                self.master = SosNode('localhost', self.commons,
                                      local_sudo=local_sudo,
                                      load_facts=can_run_local)
            except Exception as err:
                self.log_debug("Unable to determine local installation: %s" %
                               err)
                self.exit('Unable to determine local installation. Use the '
                          '--no-local option if localhost should not be '
                          'included.\nAborting...\n', 1)

        self.collect_md.add_field('master', self.master.address)
        self.collect_md.add_section('nodes')
        self.collect_md.nodes.add_section(self.master.address)
        self.master.set_node_manifest(getattr(self.collect_md.nodes,
                                              self.master.address))

        if self.opts.cluster_type:
            if self.opts.cluster_type == 'none':
                self.cluster = self.clusters['jbon']
            else:
                self.cluster = self.clusters[self.opts.cluster_type]
                self.cluster_type = self.opts.cluster_type
            self.cluster.master = self.master

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
            self.master.cluster = self.cluster
            self.cluster.setup()
            if self.cluster.cluster_ssh_key:
                if not self.opts.ssh_key:
                    self.log_debug("Updating SSH key to %s per cluster"
                                   % self.cluster.cluster_ssh_key)
                    self.opts.ssh_key = self.cluster.cluster_ssh_key

        self.get_nodes()
        if self.opts.save_group:
            gname = self.opts.save_group
            try:
                fname = self.write_host_group()
                self.log_info("Wrote group '%s' to %s" % (gname, fname))
            except Exception as err:
                self.log_error("Could not save group %s: %s" % (gname, err))

    def display_nodes(self):
        """Prints a list of nodes to collect from, if available. If no nodes
        are discovered or provided, abort.
        """
        self.ui_log.info('')

        if not self.node_list and not self.master.connected:
            self.exit('No nodes were detected, or nodes do not have sos '
                      'installed.\nAborting...')

        self.ui_log.info('The following is a list of nodes to collect from:')
        if self.master.connected and self.master.hostname is not None:
            if not (self.master.local and self.opts.no_local):
                self.ui_log.info('\t%-*s' % (self.commons['hostlen'],
                                             self.master.hostname))

        for node in sorted(self.node_list):
            self.ui_log.info("\t%-*s" % (self.commons['hostlen'], node))

        self.ui_log.info('')
        if not self.opts.batch:
            try:
                input("\nPress ENTER to continue with these nodes, or press "
                      "CTRL-C to quit\n")
                self.ui_log.info("")
            except KeyboardInterrupt:
                self.exit("Exiting on user cancel", 130)

    def configure_sos_cmd(self):
        """Configures the sosreport command that is run on the nodes"""
        self.sos_cmd = 'sosreport --batch '
        if self.opts.sos_opt_line:
            filt = ['&', '|', '>', '<', ';']
            if any(f in self.opts.sos_opt_line for f in filt):
                self.log_warn('Possible shell script found in provided sos '
                              'command. Ignoring --sos-opt-line entirely.')
                self.opts.sos_opt_line = None
            else:
                self.sos_cmd = '%s %s' % (
                    self.sos_cmd, quote(self.opts.sos_opt_line))
                self.log_debug("User specified manual sosreport command. "
                               "Command set to %s" % self.sos_cmd)
                return True

        sos_opts = []

        if self.opts.case_id:
            sos_opts.append('--case-id=%s' % (quote(self.opts.case_id)))
        if self.opts.alloptions:
            sos_opts.append('--alloptions')
        if self.opts.all_logs:
            sos_opts.append('--all-logs')
        if self.opts.verify:
            sos_opts.append('--verify')
        if self.opts.log_size:
            sos_opts.append(('--log-size=%s' % quote(str(self.opts.log_size))))
        if self.opts.sysroot:
            sos_opts.append('-s %s' % quote(self.opts.sysroot))
        if self.opts.chroot:
            sos_opts.append('-c %s' % quote(self.opts.chroot))
        if self.opts.compression_type != 'auto':
            sos_opts.append('-z %s' % (quote(self.opts.compression_type)))
        self.sos_cmd = self.sos_cmd + ' '.join(sos_opts)
        self.log_debug("Initial sos cmd set to %s" % self.sos_cmd)
        self.commons['sos_cmd'] = self.sos_cmd
        self.collect_md.add_field('initial_sos_cmd', self.sos_cmd)

    def connect_to_master(self):
        """If run with --master, we will run cluster checks again that
        instead of the localhost.
        """
        try:
            self.master = SosNode(self.opts.master, self.commons)
            self.ui_log.info('Connected to %s, determining cluster type...'
                             % self.opts.master)
        except Exception as e:
            self.log_debug('Failed to connect to master: %s' % e)
            self.exit('Could not connect to master node. Aborting...', 1)

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
            cluster.master = self.master
            if cluster.check_enabled():
                cname = cluster.__class__.__name__
                self.log_debug("Installation matches %s, checking for layered "
                               "profiles" % cname)
                for remaining in checks:
                    if issubclass(remaining.__class__, cluster.__class__):
                        rname = remaining.__class__.__name__
                        self.log_debug("Layered profile %s found. "
                                       "Checking installation"
                                       % rname)
                        remaining.master = self.master
                        if remaining.check_enabled():
                            self.log_debug("Installation matches both layered "
                                           "profile %s and base profile %s, "
                                           "setting cluster type to layered "
                                           "profile" % (rname, cname))
                            cluster = remaining
                            break
                self.cluster = cluster
                self.cluster_type = cluster.name()
                self.commons['cluster'] = self.cluster
                self.ui_log.info(
                    'Cluster type set to %s' % self.cluster_type)
                break

    def get_nodes_from_cluster(self):
        """Collects the list of nodes from the determined cluster cluster"""
        if self.cluster_type:
            nodes = self.cluster._get_nodes()
            self.log_debug('Node list: %s' % nodes)
            return nodes
        return []

    def reduce_node_list(self):
        """Reduce duplicate entries of the localhost and/or master node
        if applicable"""
        if (self.hostname in self.node_list and self.opts.no_local):
            self.node_list.remove(self.hostname)
        for i in self.ip_addrs:
            if i in self.node_list:
                self.node_list.remove(i)
        # remove the master node from the list, since we already have
        # an open session to it.
        if self.master:
            for n in self.node_list:
                if n == self.master.hostname or n == self.opts.master:
                    self.node_list.remove(n)
        self.node_list = list(set(n for n in self.node_list if n))
        self.log_debug('Node list reduced to %s' % self.node_list)
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
        """ Sets the list of nodes to collect sosreports from """
        if not self.master and not self.cluster:
            msg = ('Could not determine a cluster type and no list of '
                   'nodes or master node was provided.\nAborting...'
                   )
            self.exit(msg)

        try:
            nodes = self.get_nodes_from_cluster()
            if self.opts.nodes:
                for node in nodes:
                    if self.compare_node_to_regex(node):
                        self.node_list.append(node)
            else:
                self.node_list = nodes
        except Exception as e:
            self.log_debug("Error parsing node list: %s" % e)
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
                    self.log_debug("Force adding %s to node list" % node)
                    self.node_list.append(node)

        if not self.master:
            host = self.hostname.split('.')[0]
            # trust the local hostname before the node report from cluster
            for node in self.node_list:
                if host == node.split('.')[0]:
                    self.node_list.remove(node)
            self.node_list.append(self.hostname)
        self.reduce_node_list()
        try:
            self.commons['hostlen'] = len(max(self.node_list, key=len))
        except (TypeError, ValueError):
            self.commons['hostlen'] = len(self.opts.master)

    def _connect_to_node(self, node):
        """Try to connect to the node, and if we can add to the client list to
        run sosreport on

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
                client.close_ssh_session()
        except Exception:
            pass

    def intro(self):
        """Print the intro message and prompts for a case ID if one is not
        provided on the command line
        """
        disclaimer = ("""\
This utility is used to collect sosreports from multiple \
nodes simultaneously. It uses OpenSSH's ControlPersist feature \
to connect to nodes and run commands remotely. If your system \
installation of OpenSSH is older than 5.6, please upgrade.

An archive of sosreport tarballs collected from the nodes will be \
generated in %s and may be provided to an appropriate support representative.

The generated archive may contain data considered sensitive \
and its content should be reviewed by the originating \
organization before being passed to any third party.

No configuration changes will be made to the system running \
this utility or remote systems that it connects to.
""")
        self.ui_log.info("\nsos-collector (version %s)\n" % __version__)
        intro_msg = self._fmt_msg(disclaimer % self.tmpdir)
        self.ui_log.info(intro_msg)
        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.opts.batch:
            try:
                input(prompt)
                self.ui_log.info("")
            except KeyboardInterrupt:
                self.exit("Exiting on user cancel", 130)

        if not self.opts.case_id and not self.opts.batch:
            msg = 'Optionally, please enter the case id you are collecting ' \
                  'reports for: '
            self.opts.case_id = input(msg)

    def execute(self):
        if self.opts.list_options:
            self.list_options()
            self.cleanup()
            raise SystemExit

        self.intro()
        self.configure_sos_cmd()
        self.prep()
        self.display_nodes()

        self.archive_name = self._get_archive_name()
        self.setup_archive(name=self.archive_name)
        self.archive_path = self.archive.get_archive_path()
        self.archive.makedirs('sos_logs', 0o755)

        self.collect()
        self.cleanup()

    def collect(self):
        """ For each node, start a collection thread and then tar all
        collected sosreports """
        if self.master.connected:
            self.client_list.append(self.master)

        self.ui_log.info("\nConnecting to nodes...")
        filters = [self.master.address, self.master.hostname]
        nodes = [(n, None) for n in self.node_list if n not in filters]

        if self.opts.password_per_node:
            _nodes = []
            for node in nodes:
                msg = ("Please enter the password for %s@%s: "
                       % (self.opts.ssh_user, node[0]))
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
                self.exit("No nodes connected. Aborting...")
            elif self.report_num == 1:
                if self.client_list[0].address == 'localhost':
                    self.exit(
                        "Collection would only gather from localhost due to "
                        "failure to either enumerate or connect to cluster "
                        "nodes. Assuming single collection from localhost is "
                        "not desired.\n"
                        "Aborting..."
                    )

            self.ui_log.info("\nBeginning collection of sosreports from %s "
                             "nodes, collecting a maximum of %s "
                             "concurrently\n"
                             % (self.report_num, self.opts.jobs))

            pool = ThreadPoolExecutor(self.opts.jobs)
            pool.map(self._collect, self.client_list, chunksize=1)
            pool.shutdown(wait=True)
        except KeyboardInterrupt:
            self.log_error('Exiting on user cancel\n')
            os._exit(130)
        except Exception as err:
            self.log_error('Could not connect to nodes: %s' % err)
            os._exit(1)

        if hasattr(self.cluster, 'run_extra_cmd'):
            self.ui_log.info('Collecting additional data from master node...')
            files = self.cluster._run_extra_cmd()
            if files:
                self.master.collect_extra_cmd(files)
        msg = '\nSuccessfully captured %s of %s sosreports'
        self.log_info(msg % (self.retrieved, self.report_num))
        self.close_all_connections()
        if self.retrieved > 0:
            arc_name = self.create_cluster_archive()
        else:
            msg = 'No sosreports were collected, nothing to archive...'
            self.exit(msg, 1)

        if self.opts.upload and self.get_upload_url():
            try:
                self.policy.upload_archive(arc_name)
                self.ui_log.info("Uploaded archive successfully")
            except Exception as err:
                self.ui_log.error("Upload attempt failed: %s" % err)

    def _collect(self, client):
        """Runs sosreport on each node"""
        try:
            if not client.local:
                client.sosreport()
            else:
                if not self.opts.no_local:
                    client.sosreport()
            if client.retrieved:
                self.retrieved += 1
        except Exception as err:
            self.log_error("Error running sosreport: %s" % err)

    def close_all_connections(self):
        """Close all ssh sessions for nodes"""
        for client in self.client_list:
            self.log_debug('Closing SSH connection to %s' % client.address)
            client.close_ssh_session()

    def create_cluster_archive(self):
        """Calls for creation of tar archive then cleans up the temporary
        files created by sos-collector"""
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
                self.ui_log.error("ERROR: unable to obfuscate reports: %s"
                                  % err)

        try:
            self.log_info('Creating archive of sosreports...')
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
                                 "%s_private_map" % self.archive_name)
                )
                os.rename(map_file, map_name)
                self.ui_log.info("A mapping of obfuscated elements is "
                                 "available at\n\t%s" % map_name)

            self.soslog.info('Archive created as %s' % final_name)
            self.ui_log.info('\nThe following archive has been created. '
                             'Please provide it to your support team.')
            self.ui_log.info('\t%s\n' % final_name)
            return final_name
        except Exception as err:
            msg = ("Could not finalize archive: %s\n\nData may still be "
                   "available uncompressed at %s" % (err, self.archive_path))
            self.exit(msg, 2)
