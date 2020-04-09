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
import logging
import os
import random
import re
import string
import tarfile
import tempfile
import shutil
import subprocess
import sys

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from pipes import quote
from textwrap import fill
from sos.collector.configuration import Configuration
from sos.collector.sosnode import SosNode
from sos.collector.exceptions import ControlPersistUnsupportedException
from sos.component import SoSComponent
from sos import __version__

COLLECTOR_LIB_DIR = '/var/lib/sos-collector'


class SoSCollector(SoSComponent):
    """Collect an sos report from multiple nodes simultaneously
    """

    arg_defaults = {
        'alloptions': False,
        'all_logs': False,
        'become_root': False,
        'batch': False,
        'case_id': False,
        'cluster_type': None,
        'cluster_options': [],
        'chroot': 'auto',
        'enable_plugins': [],
        'group': None,
        'save_group': '',
        'image': '',
        'ssh_key': '',
        'insecure_sudo': False,
        'plugin_options': [],
        'list_options': False,
        'label': '',
        'log_size': 0,
        'skip_plugins': [],
        'nodes': [],
        'no_pkg_check': False,
        'no_local': False,
        'master': '',
        'only_plugins': [],
        'ssh_port': 22,
        'password': False,
        'password_per_node': False,
        'preset': '',
        'sos_opt_line': '',
        'ssh_user': 'root',
        'timeout': 600,
        'verify': False,
        'compression': 'auto'
    }

    def __init__(self, parser, parsed_args, cmdline_args):
        super(SoSCollector, self).__init__(parser, parsed_args, cmdline_args)
        os.umask(0o77)
        self.client_list = []
        self.node_list = []
        self.master = False
        self.retrieved = 0
        self.need_local_sudo = False
        self.config = Configuration(parsed_args)
        if not self.config['list_options']:
            try:
                self._check_for_control_persist()
                self.log_debug('Executing %s' % ' '.join(s for s in sys.argv))
                self.log_debug("Found cluster profiles: %s"
                               % self.clusters.keys())
                self.log_debug("Found supported host types: %s"
                               % self.config['host_types'].keys())
                self._parse_options()
                self.prep()
            except KeyboardInterrupt:
                self._exit('Exiting on user cancel', 130)
            except Exception:
                raise        

    @classmethod
    def add_parser_options(cls, parser):
        parser.add_argument('-a', '--alloptions', action='store_true',
                            help='Enable all sos options')
        parser.add_argument('--all-logs', action='store_true',
                            help='Collect logs regardless of size')
        parser.add_argument('-b', '--become', action='store_true',
                            dest='become_root',
                            help='Become root on the remote nodes')
        parser.add_argument('--batch', action='store_true',
                            help='Do not prompt interactively (except passwords)')
        parser.add_argument('--case-id', help='Specify case number')
        parser.add_argument('--cluster-type',
                            help='Specify a type of cluster profile')
        parser.add_argument('-c', '--cluster-option', dest='cluster_options',
                            action='append',
                            help=('Specify a cluster options used by a profile'
                                  ' and takes the form of cluster.option=value'
                                  )
                            )
        parser.add_argument('--chroot', default='',
                            choices=['auto', 'always', 'never'],
                            help="chroot executed commands to SYSROOT")
        parser.add_argument('-e', '--enable-plugins', action="append",
                            help='Enable specific plugins for sosreport')
        parser.add_argument('--group', default=None,
                            help='Use a predefined group JSON file')
        parser.add_argument('--save-group', default='',
                            help='Save the resulting node list to a group')
        parser.add_argument('--image',
                            help=('Specify the container image to use for '
                                  'containerized hosts. Defaults to the '
                                  'rhel7/support-tools image'))
        parser.add_argument('-i', '--ssh-key', help='Specify an ssh key to use')
        parser.add_argument('--insecure-sudo', action='store_true',
                            help='Use when passwordless sudo is configured')
        parser.add_argument('-k', '--plugin-options', action="append",
                            help='Plugin option as plugname.option=value')
        parser.add_argument('-l', '--list-options', action="store_true",
                            help='List options available for profiles')
        parser.add_argument('--label', help='Assign a label to the archives')
        parser.add_argument('--log-size', default=0, type=int,
                            help='Limit the size of individual logs (in MiB)')
        parser.add_argument('-n', '--skip-plugins', action="append",
                            help='Skip these plugins')
        parser.add_argument('--nodes', action="append",
                            help='Provide a comma delimited list of nodes, or a '
                                 'regex to match against')
        parser.add_argument('--no-pkg-check', action='store_true',
                            help=('Do not run package checks. Use this '
                                  'with --cluster-type if there are rpm '
                                  'or apt issues on node'
                                  )
                            )
        parser.add_argument('--no-local', action='store_true',
                            help='Do not collect a sosreport from localhost')
        parser.add_argument('--master', help='Specify a remote master node')
        parser.add_argument('-o', '--only-plugins', action="append",
                            help='Run these plugins only')
        parser.add_argument('-p', '--ssh-port', type=int,
                            help='Specify SSH port for all nodes')
        parser.add_argument('--password', action='store_true', default=False,
                            help='Prompt for user password for nodes')
        parser.add_argument('--password-per-node', action='store_true',
                            default=False,
                            help='Prompt for password separately for each node')
        parser.add_argument('--preset', default='', required=False,
                            help='Specify a sos preset to use')
        parser.add_argument('--sos-cmd', dest='sos_opt_line',
                            help=("Manually specify the commandline options for "
                                  "sosreport on remote nodes")
                            )
        parser.add_argument('--ssh-user',
                            help='Specify an SSH user. Default root')
        parser.add_argument('--timeout', type=int, required=False,
                            help='Timeout for sosreport on each node. Default 300.'
                            )
        parser.add_argument('--verify', action="store_true",
                            help="perform data verification during collection")
        parser.add_argument('-z', '--compression-type', dest="compression",
                            choices=['auto', 'gzip', 'bzip2', 'xz'],
                            help="compression technology to use")

    def _check_for_control_persist(self):
        '''Checks to see if the local system supported SSH ControlPersist.

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
        '''
        ssh_cmd = ['ssh', '-o', 'ControlPersist']
        cmd = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out, err = cmd.communicate()
        err = err.decode('utf-8')
        if 'Bad configuration option' in err or 'Usage:' in err:
            raise ControlPersistUnsupportedException
        return True

    def _exit(self, msg, error=1):
        '''Used to safely terminate if sos-collector encounters an error'''
        self.log_error(msg)
        try:
            self.close_all_connections()
        except Exception:
            pass
        sys.exit(error)

    def _parse_options(self):
        '''If there are cluster options set on the CLI, override the defaults
        '''
        if self.config['cluster_options']:
            for opt in self.config['cluster_options']:
                match = False
                for clust in self.clusters:
                    for option in self.clusters[clust].options:
                        if opt.name == option.name:
                            match = True
                            break
            if not match:
                self._exit('Unknown cluster option provided: %s.%s'
                           % (opt.cluster, opt.name))

    def _validate_option(self, default, cli):
        '''Checks to make sure that the option given on the CLI is valid.
        Valid in this sense means that the type of value given matches what a
        cluster profile expects (str for str, bool for bool, etc).

        For bool options, this will also convert the string equivalent to an
        actual boolean value
        '''
        if not default.opt_type == bool:
            if not default.opt_type == cli.opt_type:
                msg = "Invalid option type for %s. Expected %s got %s"
                self._exit(msg % (cli.name, default.opt_type, cli.opt_type))
            return cli.value
        else:
            val = cli.value.lower()
            if val not in ['true', 'on', 'false', 'off']:
                msg = ("Invalid value for %s. Accepted values are: 'true', "
                       "'false', 'on', 'off'")
                self._exit(msg % cli.name)
            else:
                if val in ['true', 'on']:
                    return True
                else:
                    return False

    def log_info(self, msg):
        '''Log info messages to both console and log file'''
        self.logger.info(msg)
        self.console.info(msg)

    def log_warn(self, msg):
        '''Log warn messages to both console and log file'''
        self.logger.warn(msg)
        self.console.warn('WARNING: %s' % msg)

    def log_error(self, msg):
        '''Log error messages to both console and log file'''
        self.logger.error(msg)
        self.console.error(msg)

    def log_debug(self, msg):
        '''Log debug message to both console and log file'''
        caller = inspect.stack()[1][3]
        msg = '[sos_collector:%s] %s' % (caller, msg)
        self.logger.debug(msg)
        if self.config['verbose']:
            self.console.debug(msg)

    def create_tmp_dir(self, location='/var/tmp'):
        '''Creates a temp directory to transfer sosreports to'''
        tmpdir = tempfile.mkdtemp(prefix='sos-collector-', dir=location)
        self.config['tmp_dir'] = tmpdir
        self.config['tmp_dir_created'] = True

    def list_options(self):
        '''Display options for available clusters'''

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
        '''Removes the temp directory and all collected sosreports'''
        shutil.rmtree(self.config['tmp_dir'])

    def _get_archive_name(self):
        '''Generates a name for the tarball archive'''
        nstr = 'sos-collector'
        if self.config['label']:
            nstr += '-%s' % self.config['label']
        if self.config['case_id']:
            nstr += '-%s' % self.config['case_id']
        dt = datetime.strftime(datetime.now(), '%Y-%m-%d')

        try:
            string.lowercase = string.ascii_lowercase
        except NameError:
            pass

        rand = ''.join(random.choice(string.lowercase) for x in range(5))
        return '%s-%s-%s' % (nstr, dt, rand)

    def _get_archive_path(self):
        '''Returns the path, including filename, of the tarball we build
        that contains the collected sosreports
        '''
        self.arc_name = self._get_archive_name()
        compr = 'gz'
        return self.config['out_dir'] + self.arc_name + '.tar.' + compr

    def _fmt_msg(self, msg):
        width = 80
        _fmt = ''
        for line in msg.splitlines():
            _fmt = _fmt + fill(line, width, replace_whitespace=False) + '\n'
        return _fmt

    def _load_group_config(self):
        '''
        Attempts to load the host group specified on the command line.
        Host groups are defined via JSON files, typically saved under
        /var/lib/sos-collector/, although users can specify a full filepath
        on the commandline to point to one existing anywhere on the system

        Host groups define a list of nodes and/or regexes and optionally the
        master and cluster-type options.
        '''
        if os.path.exists(self.config['group']):
            fname = self.config['group']
        elif os.path.exists(
                os.path.join(COLLECTOR_LIB_DIR, self.config['group'])
             ):
            fname = os.path.join(COLLECTOR_LIB_DIR, self.config['group'])
        else:
            raise OSError('Group not found')

        self.log_debug("Loading host group %s" % fname)

        with open(fname, 'r') as hf:
            _group = json.load(hf)
            for key in ['master', 'cluster_type']:
                if _group[key]:
                    self.log_debug("Setting option '%s' to '%s' per host group"
                                   % (key, _group[key]))
                    self.config[key] = _group[key]
            if _group['nodes']:
                self.log_debug("Adding %s to node list" % _group['nodes'])
                self.config['nodes'].extend(_group['nodes'])

    def write_host_group(self):
        '''
        Saves the results of this run of sos-collector to a host group file
        on the system so it can be used later on.

        The host group will save the options master, cluster_type, and nodes
        as determined by sos-collector prior to execution of sosreports.
        '''
        cfg = {
            'name': self.config['save_group'],
            'master': self.config['master'],
            'cluster_type': self.config['cluster_type'],
            'nodes': [n for n in self.node_list]
        }
        if not os.path.isdir(COLLECTOR_LIB_DIR):
            raise OSError("%s no such directory" % COLLECTOR_LIB_DIR)
        fname = COLLECTOR_LIB_DIR + '/' + cfg['name']
        with open(fname, 'w') as hf:
            json.dump(cfg, hf)
        os.chmod(fname, 0o644)
        return fname

    def prep(self):
        '''Based on configuration, performs setup for collection'''
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
        self.console.info("\nsos-collector (version %s)\n" % __version__)
        intro_msg = self._fmt_msg(disclaimer % self.config['tmp_dir'])
        self.console.info(intro_msg)
        prompt = "\nPress ENTER to continue, or CTRL-C to quit\n"
        if not self.config['batch']:
            input(prompt)

        if (not self.config['password'] and not
                self.config['password_per_node']):
            self.log_debug('password not specified, assuming SSH keys')
            msg = ('sos-collector ASSUMES that SSH keys are installed on all '
                   'nodes unless the --password option is provided.\n')
            self.console.info(self._fmt_msg(msg))

        if self.config['password'] or self.config['password_per_node']:
            self.log_debug('password specified, not using SSH keys')
            msg = ('Provide the SSH password for user %s: '
                   % self.config['ssh_user'])
            self.config['password'] = getpass(prompt=msg)

        if self.config['need_sudo'] and not self.config['insecure_sudo']:
            if not self.config['password']:
                self.log_debug('non-root user specified, will request '
                               'sudo password')
                msg = ('A non-root user has been provided. Provide sudo '
                       'password for %s on remote nodes: '
                       % self.config['ssh_user'])
                self.config['sudo_pw'] = getpass(prompt=msg)
            else:
                if not self.config['insecure_sudo']:
                    self.config['sudo_pw'] = self.config['password']

        if self.config['become_root']:
            if not self.config['ssh_user'] == 'root':
                self.log_debug('non-root user asking to become root remotely')
                msg = ('User %s will attempt to become root. '
                       'Provide root password: ' % self.config['ssh_user'])
                self.config['root_password'] = getpass(prompt=msg)
                self.config['need_sudo'] = False
            else:
                self.log_info('Option to become root but ssh user is root.'
                              ' Ignoring request to change user on node')
                self.config['become_root'] = False

        if self.config['group']:
            try:
                self._load_group_config()
            except Exception as err:
                self.log_error("Could not load specified group %s: %s"
                               % (self.config['group'], err))

        if self.config['master']:
            self.connect_to_master()
            self.config['no_local'] = True
        else:
            try:
                self.master = SosNode('localhost', self.config)
            except Exception as err:
                self.log_debug("Unable to determine local installation: %s" %
                               err)
                self._exit('Unable to determine local installation. Use the '
                           '--no-local option if localhost should not be '
                           'included.\nAborting...\n', 1)

        if self.config['cluster_type']:
            if self.config['cluster_type'] == 'none':
                self.config['cluster'] = self.clusters['jbon']
            else:
                self.config['cluster'] = self.clusters[
                                            self.config['cluster_type']
                                        ]
            self.config['cluster'].master = self.master
        else:
            self.determine_cluster()
        if self.config['cluster'] is None and not self.config['nodes']:
            msg = ('Cluster type could not be determined and no nodes provided'
                   '\nAborting...')
            self._exit(msg, 1)
        if self.config['cluster']:
            self.config['cluster'].setup()
            self.config['cluster'].modify_sos_cmd()
        self.get_nodes()
        if self.config['save_group']:
            gname = self.config['save_group']
            try:
                fname = self.write_host_group()
                self.log_info("Wrote group '%s' to %s" % (gname, fname))
            except Exception as err:
                self.log_error("Could not save group %s: %s" % (gname, err))
        self.intro()
        self.configure_sos_cmd()

    def intro(self):
        '''Prints initial messages and collects user and case if not
        provided already.
        '''
        self.console.info('')

        if not self.node_list and not self.master.connected:
            self._exit('No nodes were detected, or nodes do not have sos '
                       'installed.\nAborting...')

        self.console.info('The following is a list of nodes to collect from:')
        if self.master.connected:
            self.console.info('\t%-*s' % (self.config['hostlen'],
                                          self.config['master']))

        for node in sorted(self.node_list):
            self.console.info("\t%-*s" % (self.config['hostlen'], node))

        self.console.info('')

        if not self.config['case_id'] and not self.config['batch']:
            msg = 'Please enter the case id you are collecting reports for: '
            self.config['case_id'] = input(msg)

    def configure_sos_cmd(self):
        '''Configures the sosreport command that is run on the nodes'''
        if self.config['sos_opt_line']:
            filt = ['&', '|', '>', '<', ';']
            if any(f in self.config['sos_opt_line'] for f in filt):
                self.log_warn('Possible shell script found in provided sos '
                              'command. Ignoring --sos-cmd option entirely.')
                self.config['sos_opt_line'] = None
            else:
                self.config['sos_cmd'] = '%s %s' % (
                    self.config['sos_cmd'], quote(self.config['sos_opt_line']))
                self.log_debug("User specified manual sosreport command. "
                               "Command set to %s" % self.config['sos_cmd'])
                return True
        if self.config['case_id']:
            self.config['sos_cmd'] += ' --case-id=%s' % (
                quote(self.config['case_id']))
        if self.config['alloptions']:
            self.config['sos_cmd'] += ' --alloptions'
        if self.config['all_logs']:
            self.config['sos_cmd'] += ' --all-logs'
        if self.config['verify']:
            self.config['sos_cmd'] += ' --verify'
        if self.config['log_size']:
            self.config['sos_cmd'] += (' --log-size=%s'
                                       % quote(self.config['log_size']))
        if self.config['sysroot']:
            self.config['sos_cmd'] += ' -s %s' % quote(self.config['sysroot'])
        if self.config['chroot']:
            self.config['sos_cmd'] += ' -c %s' % quote(self.config['chroot'])
        if self.config['compression']:
            self.config['sos_cmd'] += ' -z %s' % (
                quote(self.config['compression']))
        self.log_debug('Initial sos cmd set to %s' % self.config['sos_cmd'])

    def connect_to_master(self):
        '''If run with --master, we will run cluster checks again that
        instead of the localhost.
        '''
        try:
            self.master = SosNode(self.config['master'], self.config)
        except Exception as e:
            self.log_debug('Failed to connect to master: %s' % e)
            self._exit('Could not connect to master node. Aborting...', 1)

    def determine_cluster(self):
        '''This sets the cluster type and loads that cluster's cluster.

        If no cluster type is matched and no list of nodes is provided by
        the user, then we abort.

        If a list of nodes is given, this is not run, however the cluster
        can still be run if the user sets a --cluster-type manually
        '''
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

                self.config['cluster'] = cluster
                self.config['cluster_type'] = cluster.name()
                self.log_info(
                    'Cluster type set to %s' % self.config['cluster_type'])
                break

    def get_nodes_from_cluster(self):
        '''Collects the list of nodes from the determined cluster cluster'''
        if self.config['cluster_type']:
            nodes = self.config['cluster']._get_nodes()
            self.log_debug('Node list: %s' % nodes)
            return nodes

    def reduce_node_list(self):
        '''Reduce duplicate entries of the localhost and/or master node
        if applicable'''
        if (self.config['hostname'] in self.node_list and
                self.config['no_local']):
            self.node_list.remove(self.config['hostname'])
        for i in self.config['ip_addrs']:
            if i in self.node_list:
                self.node_list.remove(i)
        # remove the master node from the list, since we already have
        # an open session to it.
        if self.config['master']:
            for n in self.node_list:
                if n == self.master.hostname or n == self.config['master']:
                    self.node_list.remove(n)
        self.node_list = list(set(n for n in self.node_list if n))
        self.log_debug('Node list reduced to %s' % self.node_list)

    def compare_node_to_regex(self, node):
        '''Compares a discovered node name to a provided list of nodes from
        the user. If there is not a match, the node is removed from the list'''
        for regex in self.config['nodes']:
            try:
                regex = fnmatch.translate(regex)
                if re.match(regex, node):
                    return True
            except re.error as err:
                msg = 'Error comparing %s to provided node regex %s: %s'
                self.log_debug(msg % (node, regex, err))
        return False

    def get_nodes(self):
        ''' Sets the list of nodes to collect sosreports from '''
        if not self.config['master'] and not self.config['cluster']:
            msg = ('Could not determine a cluster type and no list of '
                   'nodes or master node was provided.\nAborting...'
                   )
            self._exit(msg)

        try:
            nodes = self.get_nodes_from_cluster()
            if self.config['nodes']:
                for node in nodes:
                    if self.compare_node_to_regex(node):
                        self.node_list.append(node)
            else:
                self.node_list = nodes
        except Exception as e:
            self.log_debug("Error parsing node list: %s" % e)
            self.log_debug('Setting node list to --nodes option')
            self.node_list = self.config['nodes']
            for node in self.node_list:
                if any(i in node for i in ('*', '\\', '?', '(', ')', '/')):
                    self.node_list.remove(node)

        # force add any non-regex node strings from nodes option
        if self.config['nodes']:
            for node in self.config['nodes']:
                if any(i in node for i in '*\\?()/[]'):
                    continue
                if node not in self.node_list:
                    self.log_debug("Force adding %s to node list" % node)
                    self.node_list.append(node)

        if not self.config['master']:
            host = self.config['hostname'].split('.')[0]
            # trust the local hostname before the node report from cluster
            for node in self.node_list:
                if host == node.split('.')[0]:
                    self.node_list.remove(node)
            self.node_list.append(self.config['hostname'])
        self.reduce_node_list()
        try:
            self.config['hostlen'] = len(max(self.node_list, key=len))
        except (TypeError, ValueError):
            self.config['hostlen'] = len(self.config['master'])

    def _connect_to_node(self, node):
        '''Try to connect to the node, and if we can add to the client list to
        run sosreport on

        Positional arguments
            node - a tuple specifying (address, password). If no password, set
                   to None
        '''
        try:
            client = SosNode(node[0], self.config, password=node[1])
            if client.connected:
                self.client_list.append(client)
            else:
                client.close_ssh_session()
        except Exception:
            pass

    def collect(self):
        ''' For each node, start a collection thread and then tar all
        collected sosreports '''
        if self.master.connected:
            self.client_list.append(self.master)

        self.console.info("\nConnecting to nodes...")
        filters = [self.master.address, self.master.hostname]
        nodes = [(n, None) for n in self.node_list if n not in filters]

        if self.config['password_per_node']:
            _nodes = []
            for node in nodes:
                msg = ("Please enter the password for %s@%s: "
                       % (self.config['ssh_user'], node[0]))
                node_pwd = getpass(msg)
                _nodes.append((node[0], node_pwd))
            nodes = _nodes

        try:
            pool = ThreadPoolExecutor(self.config['threads'])
            pool.map(self._connect_to_node, nodes, chunksize=1)
            pool.shutdown(wait=True)

            self.report_num = len(self.client_list)
            if self.config['no_local'] and self.master.address == 'localhost':
                self.report_num -= 1

            self.console.info("\nBeginning collection of sosreports from %s "
                              "nodes, collecting a maximum of %s "
                              "concurrently\n"
                              % (self.report_num, self.config['threads'])
                              )

            pool = ThreadPoolExecutor(self.config['threads'])
            pool.map(self._collect, self.client_list, chunksize=1)
            pool.shutdown(wait=True)
        except KeyboardInterrupt:
            self.log_error('Exiting on user cancel\n')
            os._exit(130)
        except Exception as err:
            self.log_error('Could not connect to nodes: %s' % err)
            os._exit(1)

        if hasattr(self.config['cluster'], 'run_extra_cmd'):
            self.console.info('Collecting additional data from master node...')
            files = self.config['cluster']._run_extra_cmd()
            if files:
                self.master.collect_extra_cmd(files)
        msg = '\nSuccessfully captured %s of %s sosreports'
        self.log_info(msg % (self.retrieved, self.report_num))
        self.close_all_connections()
        if self.retrieved > 0:
            self.create_cluster_archive()
        else:
            msg = 'No sosreports were collected, nothing to archive...'
            self._exit(msg, 1)

    def _collect(self, client):
        '''Runs sosreport on each node'''
        try:
            if not client.local:
                client.sosreport()
            else:
                if not self.config['no_local']:
                    client.sosreport()
            if client.retrieved:
                self.retrieved += 1
        except Exception as err:
            self.log_error("Error running sosreport: %s" % err)

    def close_all_connections(self):
        '''Close all ssh sessions for nodes'''
        for client in self.client_list:
            self.log_debug('Closing SSH connection to %s' % client.address)
            client.close_ssh_session()

    def create_cluster_archive(self):
        '''Calls for creation of tar archive then cleans up the temporary
        files created by sos-collector'''
        self.log_info('Creating archive of sosreports...')
        self.create_sos_archive()
        if self.archive:
            self.logger.info('Archive created as %s' % self.archive)
            self.cleanup()
            self.console.info('\nThe following archive has been created. '
                              'Please provide it to your support team.')
            self.console.info('    %s' % self.archive)

    def create_sos_archive(self):
        '''Creates a tar archive containing all collected sosreports'''
        try:
            self.archive = self._get_archive_path()
            with tarfile.open(self.archive, "w:gz") as tar:
                for host in self.client_list:
                    for fname in host.file_list:
                        try:
                            if '.md5' in fname:
                                arc_name = (self.arc_name + '/md5/' +
                                            fname.split('/')[-1])
                            else:
                                arc_name = (self.arc_name + '/' +
                                            fname.split('/')[-1])
                            tar.add(
                                os.path.join(self.config['tmp_dir'], fname),
                                arcname=arc_name
                            )
                        except Exception as err:
                            self.log_error("Could not add %s to archive: %s"
                                           % (arc_name, err))
                tar.add(
                    self.logfile.name,
                    arcname=self.arc_name + '/logs/sos-collector.log'
                )
                tar.add(
                    self.console_log_file.name,
                    arcname=self.arc_name + '/logs/ui.log'
                )
                tar.close()
        except Exception as e:
            msg = 'Could not create archive: %s' % e
            self._exit(msg, 2)

    def cleanup(self):
        ''' Removes the tmp dir and all sosarchives therein.

            If tmp dir was supplied by user, only the sos archives within
            that dir are removed.
        '''
        if self.config['tmp_dir_created']:
            self.delete_tmp_dir()
        else:
            for f in os.listdir(self.config['tmp_dir']):
                if re.search('sosreport-*tar*', f):
                    os.remove(os.path.join(self.config['tmp_dir'], f))
