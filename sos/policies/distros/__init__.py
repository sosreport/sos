# Copyright (C) 2020 Red Hat, Inc., Jake Hunsaker <jhunsake@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

# pylint: disable=too-many-branches

import os
import re

from sos import _sos as _
from sos.policies import Policy
from sos.policies.init_systems import InitSystem
from sos.policies.init_systems.systemd import SystemdInit
from sos.policies.runtimes.crio import CrioContainerRuntime
from sos.policies.runtimes.podman import PodmanContainerRuntime
from sos.policies.runtimes.docker import DockerContainerRuntime
from sos.policies.runtimes.lxd import LxdContainerRuntime

from sos.utilities import (shell_out, is_executable, bold,
                           sos_get_command_output)


OS_RELEASE = "/etc/os-release"
# Container environment variables for detecting if we're in a container
ENV_CONTAINER = 'container'
ENV_HOST_SYSROOT = 'HOST'


class LinuxPolicy(Policy):
    """This policy is meant to be an abc class that provides common
    implementations used in Linux distros"""
    vendor = "None"
    PATH = "/bin:/sbin:/usr/bin:/usr/sbin"
    init = None
    # the following will be used, in order, as part of check() to validate that
    # we are running on a particular distro
    os_release_file = ''
    os_release_name = ''
    os_release_id = ''
    _upload_url = None
    default_container_runtime = 'docker'
    _preferred_hash_name = None
    # collector-focused class attrs
    containerized = False
    container_image = None
    sos_path_strip = None
    sos_pkg_name = None
    sos_bin_path = '/usr/bin'
    sos_container_name = 'sos-collector-tmp'
    container_version_command = None
    container_authfile = None

    def __init__(self, sysroot=None, init=None, probe_runtime=True,
                 remote_exec=None):
        super().__init__(sysroot=sysroot,
                         probe_runtime=probe_runtime,
                         remote_exec=remote_exec)

        if sysroot:
            self.sysroot = sysroot
        else:
            self.sysroot = self._container_init() or '/'

        self.init_kernel_modules()

        if init is not None:
            self.init_system = init
        elif os.path.isdir("/run/systemd/system/"):
            self.init_system = SystemdInit(chroot=self.sysroot)
        else:
            self.init_system = InitSystem()

        self.runtimes = {}
        if self.probe_runtime:
            _crun = [
                PodmanContainerRuntime(policy=self),
                DockerContainerRuntime(policy=self),
                CrioContainerRuntime(policy=self),
                LxdContainerRuntime(policy=self),
            ]
            for runtime in _crun:
                if runtime.check_is_active():
                    self.runtimes[runtime.name] = runtime
                    if runtime.name == self.default_container_runtime:
                        self.runtimes['default'] = self.runtimes[runtime.name]
                    self.runtimes[runtime.name].load_container_info()

            if self.runtimes and 'default' not in self.runtimes:
                # still allow plugins to query a runtime present on the system
                # even if that is not the policy default one
                idx = list(self.runtimes.keys())
                self.runtimes['default'] = self.runtimes[idx[0]]

    @classmethod
    def set_forbidden_paths(cls):
        return [
            '/etc/passwd',
            '/etc/shadow'
        ]

    @classmethod
    def check(cls, remote=''):
        """
        This function is responsible for determining if the underlying system
        is supported by this policy.
        """
        def _check_release(content):
            _matches = [cls.os_release_name]
            if cls.os_release_id:
                _matches.append(cls.os_release_id)
            for line in content.splitlines():
                if line.startswith(('NAME=', 'ID=')):
                    _distro = line.split('=')[1:][0].strip("\"'")
                    if _distro in _matches:
                        return True
            return False

        if remote:
            return _check_release(remote)
        # use the os-specific file primarily
        # also check the symlink destination
        if (os.path.isfile(cls.os_release_file) and
            os.path.basename(cls.os_release_file)
                == os.path.basename(os.path.realpath(cls.os_release_file))):
            return True
        # next check os-release for a NAME or ID value we expect
        with open(OS_RELEASE, "r", encoding='utf-8') as f:
            return _check_release(f.read())

    def kernel_version(self):
        return self.release

    def host_name(self):
        return self.hostname

    def is_kernel_smp(self):
        return self.smp

    def get_arch(self):
        return self.machine

    def get_local_name(self):
        """Returns the name usd in the pre_work step"""
        return self.host_name()

    def sanitize_filename(self, name):
        return re.sub(r"[^-a-z,A-Z.0-9]", "", name)

    @classmethod
    def display_help(cls, section):
        if cls == LinuxPolicy:
            cls.display_self_help(section)
        else:
            section.set_title(f"{cls.os_release_name} Distribution Policy")
            cls.display_distro_help(section)

    @classmethod
    def display_self_help(cls, section):
        section.set_title("SoS Distribution Policies")
        section.add_text(
            'Distributions supported by SoS will each have a specific policy '
            'defined for them, to ensure proper operation of SoS on those '
            'systems.'
        )

    @classmethod
    def display_distro_help(cls, section):
        if cls.__doc__ and cls.__doc__ is not LinuxPolicy.__doc__:
            section.add_text(cls.__doc__)
        else:
            section.add_text(
                '\nDetailed help information for this policy is not available'
            )

        # instantiate the requested policy so we can report more interesting
        # information like $PATH and loaded presets
        _pol = cls(None, None, False)
        section.add_text(
            f"Default --upload location: {_pol._upload_url}"
        )
        section.add_text(
            f"Default container runtime: {_pol.default_container_runtime}",
            newline=False
        )
        section.add_text(
            f"$PATH used when running report: {_pol.PATH}",
            newline=False
        )

        refsec = section.add_section('Reference URLs')
        for url in cls.vendor_urls:
            refsec.add_text(f"{' ':>8}{url[0]:<30}{url[1]:<40}", newline=False)

        presec = section.add_section('Presets Available With This Policy\n')
        presec.add_text(
            bold(
                f"{' ':>8}{'Preset Name':<20}{'Description':<45}"
                f"{'Enabled Options':<30}"
            ),
            newline=False
        )
        for preset, value in _pol.presets.items():
            _opts = ' '.join(value.opts.to_args())
            presec.add_text(
                f"{' ':>8}{preset:<20}{value.desc:<45}{_opts:<30}",
                newline=False
            )

    def _container_init(self):
        """Check if sos is running in a container and perform container
        specific initialisation based on ENV_HOST_SYSROOT.
        """
        if ENV_CONTAINER in os.environ:
            if os.environ[ENV_CONTAINER] in ['docker', 'oci', 'podman']:
                self._in_container = True
                if ENV_HOST_SYSROOT in os.environ:
                    if not os.environ[ENV_HOST_SYSROOT]:
                        # guard against blank/improperly unset values
                        return None
                    self._tmp_dir = os.path.abspath(
                        os.environ[ENV_HOST_SYSROOT] + self._tmp_dir
                    )
                    return os.environ[ENV_HOST_SYSROOT]
        return None

    def init_kernel_modules(self):
        """Obtain a list of loaded kernel modules to reference later for plugin
        enablement and SoSPredicate checks
        """
        self.kernel_mods = []
        release = os.uname().release

        # first load modules from lsmod
        lines = shell_out("lsmod", timeout=0, chroot=self.sysroot).splitlines()
        self.kernel_mods.extend([
            line.split()[0].strip() for line in lines[1:]
        ])

        # next, include kernel builtins
        builtins = self.join_sysroot(
            f"/usr/lib/modules/{release}/modules.builtin"
        )
        try:
            with open(builtins, "r", encoding='utf-8') as mfile:
                for line in mfile:
                    kmod = line.split('/')[-1].split('.ko')[0]
                    self.kernel_mods.append(kmod)
        except IOError as err:
            self.soslog.warning(f"Unable to read kernel builtins: {err}")

        # finally, parse kconfig looking for specific kconfig strings that
        # have been verified to not appear in either lsmod or modules.builtin
        # regardless of how they are built
        config_strings = {
            'devlink': 'CONFIG_NET_DEVLINK',
            'dm_mod': 'CONFIG_BLK_DEV_DM'
        }

        kconfigs = (
            f"/boot/config-{release}",
            f"/lib/modules/{release}/config",
        )
        for kconfig in kconfigs:
            kconfig = self.join_sysroot(kconfig)
            if os.path.exists(kconfig):
                booted_config = kconfig
                break
        else:
            self.soslog.warning("Unable to find booted kernel config")
            return

        kconfigs = []
        try:
            with open(booted_config, "r", encoding='utf-8') as kfile:
                for line in kfile:
                    if '=y' in line:
                        kconfigs.append(line.split('=y')[0])
        except IOError as err:
            self.soslog.warning(f"Unable to read booted kernel config: {err}")

        for builtin, value in config_strings.items():
            if value in kconfigs:
                self.kernel_mods.append(builtin)

    def join_sysroot(self, path):
        if self.sysroot and self.sysroot != '/':
            path = os.path.join(self.sysroot, path.lstrip('/'))
        return path

    def pre_work(self):
        # this method will be called before the gathering begins

        cmdline_opts = self.commons['cmdlineopts']

        if cmdline_opts.low_priority:
            self._configure_low_priority()

        # set or query for case id
        self.case_id = self.prompt_for_case_id(cmdline_opts)

    def prompt_for_case_id(self, cmdline_opts):
        if not cmdline_opts.batch and not \
                cmdline_opts.quiet:
            if not cmdline_opts.case_id:
                cmdline_opts.case_id = input(
                    _("Optionally, please enter the case id that you are "
                      "generating this report for: ")
                )
        self.case_id = cmdline_opts.case_id if \
            cmdline_opts.case_id else ""

        return self.case_id

    def _configure_low_priority(self):
        """Used to constrain sos to a 'low priority' execution, potentially
        letting individual policies set their own definition of what that is.

        By default, this will attempt to assign sos to an idle io class via
        ionice if available. We will also renice our own pid to 19 in order to
        not cause competition with other host processes for CPU time.
        """
        _pid = os.getpid()
        if is_executable('ionice'):
            ret = sos_get_command_output(
                f"ionice -c3 -p {_pid}", timeout=5
            )
            if ret['status'] == 0:
                self.soslog.info('Set IO class to idle')
            else:
                msg = (f"Error setting IO class to idle: {ret['output']} "
                       f"(exit code {ret['status']})")
                self.soslog.error(msg)
        else:
            self.ui_log.warning(
                "Warning: unable to constrain report to idle IO class: "
                "ionice is not available."
            )

        try:
            os.nice(20)
            self.soslog.info('Set niceness of report to 19')
        except Exception as err:
            self.soslog.error(f"Error setting report niceness to 19: {err}")

    def set_sos_prefix(self):
        """If sos report commands need to always be prefixed with something,
        for example running in a specific container image, then it should be
        defined here.

        If no prefix should be set, return an empty string instead of None.
        """
        return ''

    def set_cleanup_cmd(self):
        """If a host requires additional cleanup, the command should be set and
        returned here
        """
        return ''

    # pylint: disable=unused-argument
    def create_sos_container(self, image=None, auth=None, force_pull=False):
        """Returns the command that will create the container that will be
        used for running commands inside a container on hosts that require it.

        This will use the container runtime defined for the host type to
        launch a container. From there, we use the defined runtime to exec into
        the container's namespace.

        :param image:   The name of the image if not using the policy default
        :type image:    ``str`` or ``None``

        :param auth:    The auth string required by the runtime to pull an
                        image from the registry
        :type auth:     ``str`` or ``None``

        :param force_pull:  Should the runtime forcibly pull the image
        :type force_pull:   ``bool``

        :returns:   The command to execute to launch the temp container
        :rtype:     ``str``
        """
        return ''

    def restart_sos_container(self):
        # pylint: disable=no-member
        """Restarts the container created for sos collect if it has stopped.

        This is called immediately after create_sos_container() as the command
        to create the container will exit and the container will stop. For
        current container runtimes, subsequently starting the container will
        default to opening a bash shell in the container to keep it running,
        thus allowing us to exec into it again.
        """
        return f"{self.container_runtime} start {self.sos_container_name}"

    def format_container_command(self, cmd):
        # pylint: disable=no-member
        """Returns the command that allows us to exec into the created
        container for sos collect.

        :param cmd: The command to run in the sos container
        :type cmd: ``str``

        :returns: The command to execute to run `cmd` in the container
        :rtype: ``str``
        """
        if self.container_runtime:
            return (f'{self.container_runtime} exec {self.sos_container_name} '
                    f'{cmd}')
        return cmd


class GenericLinuxPolicy(LinuxPolicy):
    """This Policy will be returned if no other policy can be loaded. This
    should allow for IndependentPlugins to be executed on any system"""

    vendor_urls = [('Upstream Project', 'https://github.com/sosreport/sos')]
    vendor = 'SoS'
    vendor_text = ('SoS was unable to determine that the distribution of this '
                   'system is supported, and has loaded a generic '
                   'configuration. This may not provide desired behavior, and '
                   'users are encouraged to request a new distribution-specifc'
                   ' policy at the GitHub project above.\n')

    @classmethod
    def check(cls, remote=''):
        """
        This function is responsible for determining if the underlying system
        is supported by this policy.
        """
        raise NotImplementedError

# vim: set et ts=4 sw=4 :
