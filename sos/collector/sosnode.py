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
import logging
import os
import re

from distutils.version import LooseVersion
from pipes import quote
from sos.policies import load
from sos.policies.init_systems import InitSystem
from sos.collector.transports.control_persist import SSHControlPersist
from sos.collector.transports.local import LocalTransport
from sos.collector.transports.oc import OCTransport
from sos.collector.exceptions import (CommandTimeoutException,
                                      ConnectionException,
                                      UnsupportedHostException,
                                      InvalidTransportException)

TRANSPORTS = {
    'local': LocalTransport,
    'control_persist': SSHControlPersist,
    'oc': OCTransport
}


class SosNode():

    def __init__(self, address, commons, password=None, local_sudo=None,
                 load_facts=True):
        self.address = address.strip()
        self.commons = commons
        self.opts = commons['cmdlineopts']
        self._assign_config_opts()
        self.tmpdir = commons['tmpdir']
        self.hostlen = commons['hostlen']
        self.need_sudo = commons['need_sudo']
        self.local = False
        self.host = None
        self.cluster = None
        self.hostname = None
        self.sos_env_vars = {}
        self._env_vars = {}
        self._password = password or self.opts.password
        if not self.opts.nopasswd_sudo and not self.opts.sudo_pw:
            self.opts.sudo_pw = self._password
        # override local sudo from any other source
        if local_sudo:
            self.opts.sudo_pw = local_sudo
        self.sos_path = None
        self.retrieved = False
        self.hash_retrieved = False
        self.file_list = []
        self.sos_info = {
            'version': None,
            'enabled': [],
            'disabled': [],
            'options': [],
            'presets': [],
            'sos_cmd': commons['sos_cmd']
        }
        self.sos_bin = 'sosreport'
        self.soslog = logging.getLogger('sos')
        self.ui_log = logging.getLogger('sos_ui')
        self._transport = self._load_remote_transport(commons)
        try:
            self._transport.connect(self._password)
        except Exception as err:
            self.log_error('Unable to open remote session: %s' % err)
            raise
        # load the host policy now, even if we don't want to load further
        # host information. This is necessary if we're running locally on the
        # cluster primary but do not want a local report as we still need to do
        # package checks in that instance
        self.host = self.determine_host_policy()
        self.hostname = self._transport.hostname
        if self.local and self.opts.no_local:
            load_facts = False
        if self.connected and load_facts:
            if not self.host:
                self._transport.disconnect()
                return None
            if self.local:
                if self.check_in_container():
                    self.host.containerized = False
            if self.host.containerized:
                self.create_sos_container()
            self._load_sos_info()

    @property
    def connected(self):
        if self._transport:
            return self._transport.connected
        # if no transport, we're running locally
        return True

    def disconnect(self):
        """Wrapper to close the remote session via our transport agent
        """
        self._transport.disconnect()

    def _load_remote_transport(self, commons):
        """Determine the type of remote transport to load for this node, then
        return an instantiated instance of that transport
        """
        if self.address in ['localhost', '127.0.0.1']:
            self.local = True
            return LocalTransport(self.address, commons)
        elif self.opts.transport in TRANSPORTS.keys():
            return TRANSPORTS[self.opts.transport](self.address, commons)
        elif self.opts.transport != 'auto':
            self.log_error(
                "Connection failed: unknown or unsupported transport %s"
                % self.opts.transport
            )
            raise InvalidTransportException(self.opts.transport)
        return SSHControlPersist(self.address, commons)

    def _fmt_msg(self, msg):
        return '{:<{}} : {}'.format(self._hostname, self.hostlen + 1, msg)

    @property
    def env_vars(self):
        if not self._env_vars:
            if self.local:
                self._env_vars = os.environ.copy()
            else:
                ret = self.run_command("env --null")
                if ret['status'] == 0:
                    for ln in ret['output'].split('\x00'):
                        if not ln:
                            continue
                        _val = ln.split('=')
                        self._env_vars[_val[0]] = _val[1]
        return self._env_vars

    def set_node_manifest(self, manifest):
        """Set the manifest section that this node will write to
        """
        self.manifest = manifest
        self.manifest.add_field('hostname', self._hostname)
        self.manifest.add_field('policy', self.host.distro)
        self.manifest.add_field('sos_version', self.sos_info['version'])
        self.manifest.add_field('final_sos_command', '')
        self.manifest.add_field('transport', self._transport.name)

    def check_in_container(self):
        """
        Tries to identify if we are currently running in a container or not.
        """
        if os.path.exists('/run/.containerenv'):
            self.log_debug('Found /run/.containerenv. Running in container.')
            return True
        if os.environ.get('container') is not None:
            self.log_debug("Found env var 'container'. Running in container")
            return True
        return False

    def create_sos_container(self):
        """If the host is containerized, create the container we'll be using
        """
        if self.host.containerized:
            cmd = self.host.create_sos_container(
                image=self.opts.image,
                auth=self.get_container_auth(),
                force_pull=self.opts.force_pull_image
            )
            res = self.run_command(cmd, need_root=True)
            if res['status'] in [0, 125]:
                if res['status'] == 125:
                    if 'unable to retrieve auth token' in res['output']:
                        self.log_error(
                            "Could not pull image. Provide either a username "
                            "and password or authfile"
                        )
                        raise Exception
                    elif 'unknown: Not found' in res['output']:
                        self.log_error('Specified image not found on registry')
                        raise Exception
                    # 'name exists' with code 125 means the container was
                    # created successfully, so ignore it.
                # initial creations leads to an exited container, restarting it
                # here will keep it alive for us to exec through
                ret = self.run_command(self.host.restart_sos_container(),
                                       need_root=True)
                if ret['status'] == 0:
                    self.log_info("Temporary container %s created"
                                  % self.host.sos_container_name)
                    return True
                else:
                    self.log_error("Could not start container after create: %s"
                                   % ret['output'])
                    raise Exception
            else:
                self.log_error("Could not create container on host: %s"
                               % res['output'])
                raise Exception

    def get_container_auth(self):
        """Determine what the auth string should be to pull the image used to
        deploy our temporary container
        """
        if self.opts.registry_user:
            return self.host.runtimes['default'].fmt_registry_credentials(
                self.opts.registry_user,
                self.opts.registry_password
            )
        else:
            return self.host.runtimes['default'].fmt_registry_authfile(
                self.opts.registry_authfile or self.host.container_authfile
            )

    def file_exists(self, fname, need_root=False):
        """Checks for the presence of fname on the remote node"""
        try:
            res = self.run_command("stat %s" % fname, need_root=need_root)
            return res['status'] == 0
        except Exception:
            return False

    @property
    def _hostname(self):
        if self.hostname and 'localhost' not in self.hostname:
            return self.hostname
        return self.address

    def _sanitize_log_msg(self, msg):
        """Attempts to obfuscate sensitive information in log messages such as
        passwords"""
        reg = r'(?P<var>(pass|key|secret|PASS|KEY|SECRET).*?=)(?P<value>.*?\s)'
        return re.sub(reg, r'\g<var>****** ', msg)

    def ui_msg(self, msg):
        """Format a ui message that includes host name and formatting"""
        self.ui_log.info(self._fmt_msg(msg))

    def log_info(self, msg):
        """Used to print and log info messages"""
        caller = inspect.stack()[1][3]
        lmsg = '[%s:%s] %s' % (self._hostname, caller, msg)
        self.soslog.info(lmsg)

    def log_error(self, msg):
        """Used to print and log error messages"""
        caller = inspect.stack()[1][3]
        lmsg = '[%s:%s] %s' % (self._hostname, caller, msg)
        self.soslog.error(lmsg)

    def log_debug(self, msg):
        """Used to print and log debug messages"""
        msg = self._sanitize_log_msg(msg)
        caller = inspect.stack()[1][3]
        msg = '[%s:%s] %s' % (self._hostname, caller, msg)
        self.soslog.debug(msg)

    def _format_cmd(self, cmd):
        """If we need to provide a sudo or root password to a command, then
        here we prefix the command with the correct bits
        """
        if self.opts.become_root:
            return "su -c %s" % quote(cmd)
        if self.need_sudo:
            return "sudo -S %s" % cmd
        return cmd

    def _load_sos_info(self):
        """Queries the node for information about the installed version of sos
        """
        ver = None
        rel = None
        if self.host.container_version_command is None:
            pkg = self.host.package_manager.pkg_version(self.host.sos_pkg_name)
            if pkg is not None:
                ver = '.'.join(pkg['version'])
                if pkg['release']:
                    rel = pkg['release']

        else:
            # use the containerized policy's command
            pkgs = self.run_command(self.host.container_version_command,
                                    use_container=True, need_root=True)
            if pkgs['status'] == 0:
                _, ver, rel = pkgs['output'].strip().split('-')

        if ver:
            if len(ver.split('.')) == 2:
                # safeguard against maintenance releases throwing off the
                # comparison by LooseVersion
                ver += '.0'
            try:
                ver += '-%s' % rel.split('.')[0]
            except Exception as err:
                self.log_debug("Unable to fully parse sos release: %s" % err)

        self.sos_info['version'] = ver

        if self.sos_info['version']:
            self.log_info('sos version is %s' % self.sos_info['version'])
        else:
            if not self.address == self.opts.primary:
                # in the case where the 'primary' enumerates nodes but is not
                # intended for collection (bastions), don't worry about sos not
                # being present
                self.log_error('sos is not installed on this node')
            self.connected = False
            return False
        # sos-4.0 changes the binary
        if self.check_sos_version('4.0'):
            self.sos_bin = 'sos report'
        cmd = "%s -l" % self.sos_bin
        sosinfo = self.run_command(cmd, use_container=True, need_root=True)
        if sosinfo['status'] == 0:
            self._load_sos_plugins(sosinfo['output'])
        if self.check_sos_version('3.6'):
            self._load_sos_presets()

    def _load_sos_presets(self):
        cmd = '%s --list-presets' % self.sos_bin
        res = self.run_command(cmd, use_container=True, need_root=True)
        if res['status'] == 0:
            for line in res['output'].splitlines():
                if line.strip().startswith('name:'):
                    pname = line.split('name:')[1].strip()
                    self.sos_info['presets'].append(pname)

    def _load_sos_plugins(self, sosinfo):
        ENABLED = 'The following plugins are currently enabled:'
        DISABLED = 'The following plugins are currently disabled:'
        ALL_OPTIONS = 'The following options are available for ALL plugins:'
        OPTIONS = 'The following plugin options are available:'
        PROFILES = 'Profiles:'

        enablereg = ENABLED + '(.*?)' + DISABLED
        disreg = DISABLED + '(.*?)' + ALL_OPTIONS
        optreg = OPTIONS + '(.*?)' + PROFILES
        proreg = PROFILES + '(.*?)' + '\n\n'

        self.sos_info['enabled'] = self._regex_sos_help(enablereg, sosinfo)
        self.sos_info['disabled'] = self._regex_sos_help(disreg, sosinfo)
        self.sos_info['options'] = self._regex_sos_help(optreg, sosinfo)
        self.sos_info['profiles'] = self._regex_sos_help(proreg, sosinfo, True)

    def _regex_sos_help(self, regex, sosinfo, is_list=False):
        res = []
        for result in re.findall(regex, sosinfo, re.S):
            for line in result.splitlines():
                if not is_list:
                    try:
                        res.append(line.split()[0])
                    except Exception:
                        pass
                else:
                    r = line.split(',')
                    res.extend(p.strip() for p in r if p.strip())
        return res

    def read_file(self, to_read):
        """Reads the specified file and returns the contents"""
        try:
            self.log_info("Reading file %s" % to_read)
            return self._transport.read_file(to_read)
        except Exception as err:
            self.log_error("Exception while reading %s: %s" % (to_read, err))
            return ''

    def determine_host_policy(self):
        """Attempts to identify the host installation against supported
        distributions
        """
        if self.local:
            self.log_info("using local policy %s"
                          % self.commons['policy'].distro)
            return self.commons['policy']
        host = load(cache={}, sysroot=self.opts.sysroot, init=InitSystem(),
                    probe_runtime=True,
                    remote_exec=self._transport.remote_exec,
                    remote_check=self.read_file('/etc/os-release'))
        if host:
            self.log_info("loaded policy %s for host" % host.distro)
            return host
        self.log_error('Unable to determine host installation. Ignoring node')
        raise UnsupportedHostException

    def check_sos_version(self, ver):
        """Checks to see if the sos installation on the node is AT LEAST the
        given ver. This means that if the installed version is greater than
        ver, this will still return True

        :param ver: Version number we are trying to verify is installed
        :type ver:  ``str``

        :returns:   True if installed version is at least ``ver``, else False
        :rtype:     ``bool``
        """
        def _format_version(ver):
            # format the version we're checking to a standard form of X.Y.Z-R
            try:
                _fver = ver.split('-')[0]
                _rel = ''
                if '-' in ver:
                    _rel = '-' + ver.split('-')[-1].split('.')[0]
                if len(_fver.split('.')) == 2:
                    _fver += '.0'

                return _fver + _rel
            except Exception as err:
                self.log_debug("Unable to format '%s': %s" % (ver, err))
                return ver

        _ver = _format_version(ver)

        try:
            _node_ver = LooseVersion(self.sos_info['version'])
            _test_ver = LooseVersion(_ver)
            return _node_ver >= _test_ver
        except Exception as err:
            self.log_error("Error checking sos version: %s" % err)
            return False

    def is_installed(self, pkg):
        """Checks if a given package is installed on the node"""
        if not self.host:
            return False
        return self.host.package_manager.pkg_by_name(pkg) is not None

    def run_command(self, cmd, timeout=180, get_pty=False, need_root=False,
                    use_container=False, env=None):
        """Runs a given cmd, either via the SSH session or locally

        Arguments:
            cmd - the full command to be run
            timeout - time in seconds to wait for the command to complete
            get_pty - If a shell is absolutely needed to run a command, set
                      this to True
            need_root - if a command requires root privileges, setting this to
                        True tells sos-collector to format the command with
                        sudo or su - as appropriate and to input the password
            use_container - Run this command in a container *IF* the host is
                            containerized
        """
        if not self.connected and not self.local:
            self.log_debug('Node is disconnected, attempting to reconnect')
            try:
                reconnected = self._transport.reconnect(self._password)
                if not reconnected:
                    self.log_debug('Failed to reconnect to node')
                    raise ConnectionException
            except Exception as err:
                self.log_debug("Error while trying to reconnect: %s" % err)
                raise
        if use_container and self.host.containerized:
            cmd = self.host.format_container_command(cmd)
        if need_root:
            cmd = self._format_cmd(cmd)

        if 'atomic' in cmd:
            get_pty = True

        if env:
            _cmd_env = self.env_vars
            env = _cmd_env.update(env)
        return self._transport.run_command(cmd, timeout, need_root, env,
                                           get_pty)

    def sosreport(self):
        """Run an sos report on the node, then collect it"""
        try:
            path = self.execute_sos_command()
            if path:
                self.finalize_sos_path(path)
            else:
                self.log_error('Unable to determine path of sos archive')
            if self.sos_path:
                self.retrieved = self.retrieve_sosreport()
        except Exception:
            pass
        self.cleanup()

    def _preset_exists(self, preset):
        """Verifies if the given preset exists on the node"""
        return preset in self.sos_info['presets']

    def _plugin_exists(self, plugin):
        """Verifies if the given plugin exists on the node"""
        return any(plugin in s for s in [self.sos_info['enabled'],
                                         self.sos_info['disabled']])

    def _check_enabled(self, plugin):
        """Checks to see if the plugin is default enabled on node"""
        return plugin in self.sos_info['enabled']

    def _check_disabled(self, plugin):
        """Checks to see if the plugin is default disabled on node"""
        return plugin in self.sos_info['disabled']

    def _plugin_option_exists(self, opt):
        """Attempts to verify that the given option is available on the node.
        Note that we only get available options for enabled plugins, so if a
        plugin has been force-enabled we cannot validate if the plugin option
        is correct or not"""
        plug = opt.split('.')[0]
        if not self._plugin_exists(plug):
            return False
        if (self._check_disabled(plug) and
                plug not in self.opts.enable_plugins):
            return False
        if self._check_enabled(plug):
            return opt in self.sos_info['options']
        # plugin exists, but is normally disabled. Assume user knows option is
        # valid when enabling the plugin
        return True

    def _fmt_sos_opt_list(self, opts):
        """Returns a comma delimited list for sos plugins that are confirmed
        to exist on the node"""
        return ','.join(o for o in opts if self._plugin_exists(o))

    def set_cluster(self, cluster):
        """Expose the node to the cluster profile determined for the
        environment
        """
        self.cluster = cluster

    def update_cmd_from_cluster(self):
        """This is used to modify the sos report command run on the nodes.
        By default, sos report is run without any options, using this will
        allow the profile to specify what plugins to run or not and what
        options to use.

        This will NOT override user supplied options.
        """
        if self.cluster.sos_preset:
            if not self.preset:
                self.preset = self.cluster.sos_preset
            else:
                self.log_info('Cluster specified preset %s but user has also '
                              'defined a preset. Using user specification.'
                              % self.cluster.sos_preset)
        if self.cluster.sos_plugins:
            for plug in self.cluster.sos_plugins:
                if plug not in self.enable_plugins:
                    self.enable_plugins.append(plug)

        if self.cluster.sos_plugin_options:
            for opt in self.cluster.sos_plugin_options:
                if not any(opt in o for o in self.plugopts):
                    option = '%s=%s' % (opt,
                                        self.cluster.sos_plugin_options[opt])
                    self.plugopts.append(option)

        # set primary-only options
        if self.cluster.check_node_is_primary(self):
            with self.cluster.lock:
                self.cluster.set_primary_options(self)
        else:
            with self.cluster.lock:
                self.cluster.set_node_options(self)

    def _assign_config_opts(self):
        """From the global opts configuration, assign those values locally
        to this node so that they may be acted on individually.
        """
        # assign these to new, private copies
        self.only_plugins = list(self.opts.only_plugins)
        self.skip_plugins = list(self.opts.skip_plugins)
        self.enable_plugins = list(self.opts.enable_plugins)
        self.plugopts = list(self.opts.plugopts)
        self.preset = list(self.opts.preset)

    def finalize_sos_cmd(self):
        """Use host facts and compare to the cluster type to modify the sos
        command if needed"""
        sos_cmd = self.sos_info['sos_cmd']
        label = self.determine_sos_label()
        if label:
            sos_cmd = '%s %s ' % (sos_cmd, quote(label))

        if self.opts.sos_opt_line:
            return '%s %s' % (sos_cmd, self.opts.sos_opt_line)

        sos_opts = []

        # sos-3.6 added --threads
        if self.check_sos_version('3.6'):
            # 4 threads is the project's default
            if self.opts.threads != 4:
                sos_opts.append('--threads=%s' % quote(str(self.opts.threads)))

        # sos-3.7 added options
        if self.check_sos_version('3.7'):
            if self.opts.plugin_timeout:
                sos_opts.append('--plugin-timeout=%s'
                                % quote(str(self.opts.plugin_timeout)))

        # sos-3.8 added options
        if self.check_sos_version('3.8'):
            if self.opts.allow_system_changes:
                sos_opts.append('--allow-system-changes')

            if self.opts.no_env_vars:
                sos_opts.append('--no-env-vars')

            if self.opts.since:
                sos_opts.append('--since=%s' % quote(self.opts.since))

        if self.check_sos_version('4.1'):
            if self.opts.skip_commands:
                sos_opts.append(
                    '--skip-commands=%s' % (
                        quote(','.join(self.opts.skip_commands)))
                )
            if self.opts.skip_files:
                sos_opts.append(
                    '--skip-files=%s' % (quote(','.join(self.opts.skip_files)))
                )

        if self.check_sos_version('4.2'):
            if self.opts.cmd_timeout:
                sos_opts.append('--cmd-timeout=%s'
                                % quote(str(self.opts.cmd_timeout)))

        # handle downstream versions that backported this option
        if self.check_sos_version('4.3') or self.check_sos_version('4.2-13'):
            if self.opts.container_runtime != 'auto':
                sos_opts.append(
                    "--container-runtime=%s" % self.opts.container_runtime
                )
            if self.opts.namespaces:
                sos_opts.append(
                    "--namespaces=%s" % self.opts.namespaces
                )

        self.update_cmd_from_cluster()

        sos_cmd = sos_cmd.replace(
            'sosreport',
            os.path.join(self.host.sos_bin_path, self.sos_bin)
        )

        if self.plugopts:
            opts = [o for o in self.plugopts
                    if self._plugin_exists(o.split('.')[0])
                    and self._plugin_option_exists(o.split('=')[0])]
            if opts:
                sos_opts.append('-k %s' % quote(','.join(o for o in opts)))

        if self.preset:
            if self._preset_exists(self.preset):
                sos_opts.append('--preset=%s' % quote(self.preset))
            else:
                self.log_debug('Requested to enable preset %s but preset does '
                               'not exist on node' % self.preset)

        if self.only_plugins:
            plugs = [o for o in self.only_plugins if self._plugin_exists(o)]
            if len(plugs) != len(self.only_plugins):
                not_only = list(set(self.only_plugins) - set(plugs))
                self.log_debug('Requested plugins %s were requested to be '
                               'enabled but do not exist' % not_only)
            only = self._fmt_sos_opt_list(self.only_plugins)
            if only:
                sos_opts.append('--only-plugins=%s' % quote(only))
            self.sos_cmd = "%s %s" % (sos_cmd, ' '.join(sos_opts))
            self.log_info('Final sos command set to %s' % self.sos_cmd)
            self.manifest.add_field('final_sos_command', self.sos_cmd)
            return

        if self.skip_plugins:
            # only run skip-plugins for plugins that are enabled
            skip = [o for o in self.skip_plugins if self._check_enabled(o)]
            if len(skip) != len(self.skip_plugins):
                not_skip = list(set(self.skip_plugins) - set(skip))
                self.log_debug('Requested to skip plugins %s, but plugins are '
                               'already not enabled' % not_skip)
            skipln = self._fmt_sos_opt_list(skip)
            if skipln:
                sos_opts.append('--skip-plugins=%s' % quote(skipln))

        if self.enable_plugins:
            # only run enable for plugins that are disabled
            opts = [o for o in self.enable_plugins
                    if o not in self.skip_plugins
                    and self._check_disabled(o) and self._plugin_exists(o)]
            if len(opts) != len(self.enable_plugins):
                not_on = list(set(self.enable_plugins) - set(opts))
                self.log_debug('Requested to enable plugins %s, but plugins '
                               'are already enabled or do not exist' % not_on)
            enable = self._fmt_sos_opt_list(opts)
            if enable:
                sos_opts.append('--enable-plugins=%s' % quote(enable))

        self.sos_cmd = "%s %s" % (sos_cmd, ' '.join(sos_opts))
        self.log_info('Final sos command set to %s' % self.sos_cmd)
        self.manifest.add_field('final_sos_command', self.sos_cmd)

    def determine_sos_label(self):
        """Determine what, if any, label should be added to the sos report"""
        label = ''
        label += self.cluster.get_node_label(self)

        if self.opts.label:
            label += ('%s' % self.opts.label if not label
                      else '-%s' % self.opts.label)

        if not label:
            return None

        self.log_debug('Label for sos report set to %s' % label)
        if self.check_sos_version('3.6'):
            lcmd = '--label'
        else:
            lcmd = '--name'
            label = '%s-%s' % (self.address.split('.')[0], label)
        return '%s=%s' % (lcmd, label)

    def finalize_sos_path(self, path):
        """Use host facts to determine if we need to change the sos path
        we are retrieving from"""
        pstrip = self.host.sos_path_strip
        if pstrip:
            path = path.replace(pstrip, '')
        path = path.split()[0]
        self.log_info('Final sos path: %s' % path)
        self.sos_path = path
        self.archive = path.split('/')[-1]
        self.manifest.add_field('collected_archive', self.archive)

    def determine_sos_error(self, rc, stdout):
        if rc == -1:
            return 'sos report process received SIGKILL on node'
        if rc == 1:
            if 'sudo' in stdout:
                return 'sudo attempt failed'
        if rc == 127:
            return 'sos report terminated unexpectedly. Check disk space'
        if len(stdout) > 0:
            return stdout.split('\n')[0:1]
        else:
            return 'sos exited with code %s' % rc

    def execute_sos_command(self):
        """Run sos report and capture the resulting file path"""
        self.ui_msg('Generating sos report...')
        try:
            path = False
            checksum = False
            res = self.run_command(self.sos_cmd,
                                   timeout=self.opts.timeout,
                                   get_pty=True, need_root=True,
                                   use_container=True,
                                   env=self.sos_env_vars)
            if res['status'] == 0:
                for line in res['output'].splitlines():
                    if fnmatch.fnmatch(line, '*sosreport-*tar*'):
                        path = line.strip()
                    if line.startswith((" sha256\t", " md5\t")):
                        checksum = line.split("\t")[1]
                    elif line.startswith("The checksum is: "):
                        checksum = line.split()[3]

                if checksum:
                    self.manifest.add_field('checksum', checksum)
                    if len(checksum) == 32:
                        self.manifest.add_field('checksum_type', 'md5')
                    elif len(checksum) == 64:
                        self.manifest.add_field('checksum_type', 'sha256')
                    else:
                        self.manifest.add_field('checksum_type', 'unknown')
                else:
                    self.manifest.add_field('checksum_type', 'unknown')
            else:
                err = self.determine_sos_error(res['status'], res['output'])
                self.log_debug("Error running sos report. rc = %s msg = %s"
                               % (res['status'], res['output']))
                raise Exception(err)
            return path
        except CommandTimeoutException:
            self.log_error('Timeout exceeded')
            raise
        except Exception as e:
            self.log_error('Error running sos report: %s' % e)
            raise

    def retrieve_file(self, path):
        """Copies the specified file from the host to our temp dir"""
        destdir = self.tmpdir + '/'
        dest = os.path.join(destdir, path.split('/')[-1])
        try:
            if self.file_exists(path):
                self.log_info("Copying remote %s to local %s" %
                              (path, destdir))
                return self._transport.retrieve_file(path, dest)
            else:
                self.log_debug("Attempting to copy remote file %s, but it "
                               "does not exist on filesystem" % path)
                return False
        except Exception as err:
            self.log_debug("Failed to retrieve %s: %s" % (path, err))
            return False

    def remove_file(self, path):
        """Removes the spciefied file from the host. This should only be used
        after we have retrieved the file already
        """
        path = ''.join(path.split())
        try:
            if len(path.split('/')) <= 2:  # ensure we have a non '/' path
                self.log_debug("Refusing to remove path %s: appears to be "
                               "incorrect and possibly dangerous" % path)
                return False
            if self.file_exists(path):
                self.log_info("Removing file %s" % path)
                cmd = "rm -f %s" % path
                res = self.run_command(cmd, need_root=True)
                return res['status'] == 0
            else:
                self.log_debug("Attempting to remove remote file %s, but it "
                               "does not exist on filesystem" % path)
                return False
        except Exception as e:
            self.log_debug('Failed to remove %s: %s' % (path, e))
            return False

    def retrieve_sosreport(self):
        """Collect the sosreport archive from the node"""
        if self.sos_path:
            if self.need_sudo or self.opts.become_root:
                try:
                    self.make_archive_readable(self.sos_path)
                except Exception:
                    self.log_error('Failed to make archive readable')
                    return False
            self.log_info('Retrieving sos report from %s' % self.address)
            self.ui_msg('Retrieving sos report...')
            try:
                ret = self.retrieve_file(self.sos_path)
            except Exception as err:
                self.log_error(err)
                return False
            if ret:
                self.ui_msg('Successfully collected sos report')
                self.file_list.append(self.sos_path.split('/')[-1])
                return True
            else:
                self.ui_msg('Failed to retrieve sos report')
                return False
        else:
            # sos sometimes fails but still returns a 0 exit code
            if self.stderr.read():
                e = self.stderr.read()
            else:
                e = [x.strip() for x in self.stdout.readlines() if x.strip][-1]
            self.soslog.error(
                'Failed to run sos report on %s: %s' % (self.address, e))
            self.log_error('Failed to run sos report. %s' % e)
            return False

    def remove_sos_archive(self):
        """Remove the sosreport archive from the node, since we have
        collected it and it would be wasted space otherwise"""
        if self.sos_path is None or self.local:
            # local transport moves the archive rather than copies it, so there
            # is no archive at the original location to remove
            return
        if 'sosreport' not in self.sos_path:
            self.log_debug("Node sos report path %s looks incorrect. Not "
                           "attempting to remove path" % self.sos_path)
            return
        removed = self.remove_file(self.sos_path)
        if not removed:
            self.log_error('Failed to remove sos report')

    def cleanup(self):
        """Remove the sos archive from the node once we have it locally"""
        self.remove_sos_archive()
        if self.sos_path:
            for ext in ['.sha256', '.md5']:
                if self.remove_file(self.sos_path + ext):
                    break
        cleanup = self.host.set_cleanup_cmd()
        if cleanup:
            self.run_command(cleanup, need_root=True)

    def collect_extra_cmd(self, filenames):
        """Collect the file created by a cluster outside of sos"""
        for filename in filenames:
            try:
                if self.need_sudo or self.opts.become_root:
                    try:
                        self.make_archive_readable(filename)
                    except Exception as err:
                        self.log_error("Unable to retrieve file %s" % filename)
                        self.log_debug("Failed to make file %s readable: %s"
                                       % (filename, err))
                        continue
                ret = self.retrieve_file(filename)
                if ret:
                    self.file_list.append(filename.split('/')[-1])
                    self.remove_file(filename)
                else:
                    self.log_error("Unable to retrieve file %s" % filename)
            except Exception as e:
                msg = 'Error collecting additional data from primary: %s' % e
                self.log_error(msg)

    def make_archive_readable(self, filepath):
        """Used to make the given archive world-readable, which is slightly
        better than changing the ownership outright.

        This is only used when we're not connecting as root.
        """
        cmd = 'chmod o+r %s' % filepath
        res = self.run_command(cmd, timeout=10, need_root=True)
        if res['status'] == 0:
            return True
        else:
            msg = "Exception while making %s readable. Return code was %s"
            self.log_error(msg % (filepath, res['status']))
            raise Exception

# vim: set et ts=4 sw=4 :
