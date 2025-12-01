# Copyright (c) 2025 Nagoor Shaik <nshaik@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import os
from sos.report.plugins import Plugin, RedHatPlugin, PluginOpt


class AAPContainerized(Plugin, RedHatPlugin):
    """Collects details about AAP Containerized setup
    under a user's home directory"""

    short_desc = "AAP Containerized Setup"
    plugin_name = "aap_containerized"
    profiles = ("sysmgmt", "ansible",)
    packages = ("podman",)

    option_list = [
        PluginOpt(
            "username",
            default="",
            val_type=str,
            desc="Username that was used to setup "
            "AAP containerized installation"
        ),
        PluginOpt(
            "directory",
            default="",
            val_type=str,
            desc="Absolute path to AAP containers volume directory. "
            "Defaults to 'aap' under provided user's home directory"
        )
    ]

    def setup(self):
        # Check if username is passed as argument
        username = self.get_option("username")
        if not username:
            self._log_warn("AAP username is missing, use '-k "
                           "aap_containerized.username=<user>' to set it")
            ps = self.exec_cmd("ps aux")
            if ps["status"] == 0:
                podman_users = set()
                for line in ps["output"].splitlines():
                    if ("/usr/bin/podman" in line) and \
                       ("/.local/share/containers/storage/" in line):
                        user, _ = line.split(maxsplit=1)
                        podman_users.add(user)
                if len(podman_users) == 1:
                    username = podman_users.pop()
                    self._log_warn(f"AAP username detected as '{username}'")
                else:
                    self._log_error("Unable to determine AAP username, "
                                    "terminating plugin.")
                    return

        # Grab aap installation directory under user's home
        if not self.get_option("directory"):
            user_home_directory = os.path.expanduser(f"~{username}")
            aap_directory_name = self.path_join(user_home_directory, "aap")
        else:
            aap_directory_name = self.get_option("directory")

        # Don't collect cert and key files from the installation directory
        if self.path_exists(aap_directory_name):
            forbidden_paths = [
                self.path_join(aap_directory_name, path)
                for path in [
                    "containers",
                    "tls",
                    "controller/etc/*.cert",
                    "controller/etc/*.key",
                    "eda/etc/*.cert",
                    "eda/etc/*.key",
                    "gateway/etc/*.cert",
                    "gateway/etc/*.key",
                    "hub/etc/*.cert",
                    "hub/etc/*.key",
                    "hub/etc/keys/*.pem",
                    "postgresql/*.crt",
                    "postgresql/*.key",
                    "receptor/etc/*.crt",
                    "receptor/etc/*.key",
                    "receptor/etc/*.pem",
                    "redis/*.crt",
                    "redis/*.key",
                ]
            ]
            self.add_forbidden_path(forbidden_paths)
            self.add_copy_spec(aap_directory_name)
        else:
            self._log_error(f"Directory {aap_directory_name} does not exist "
                            "or invalid absolute path provided")

        # Gather output of following podman commands as user
        podman_commands = [
            (f"su - {username} -c 'podman info --debug'", "podman_info"),
            (f"su - {username} -c 'podman ps -a --format json'",
                "podman_ps_all_json"),
        ]

        for command, filename in podman_commands:
            self.add_cmd_output(command, suggest_filename=filename)

        # Collect AAP container names
        aap_containers = self._get_aap_container_names(username)

        # Copy podman container log and inspect files
        # into their respective sub directories
        for container in aap_containers:
            self.add_cmd_output(
                    f"su - {username} -c 'podman logs {container}'",
                    suggest_filename=f"{container}.log",
                    subdir="aap_container_logs"
            )
            self.add_cmd_output(
                    f"su - {username} -c 'podman inspect {container}'",
                    suggest_filename=container,
                    subdir="podman_inspect_logs"
            )

        # command outputs from various containers
        # the su command is needed because mimicking it via runas leads to
        # stuck command execution
        pod_cmds = {
            "automation-controller-task": [
                "awx-manage check_license --data",
                "awx-manage list_instances",
            ],
            "automation-gateway": [
                "automation-gateway-service status",
                "aap-gateway-manage print_settings",
                "aap-gateway-manage authenticators",
                "aap-gateway-manage showmigrations",
                "aap-gateway-manage list_services",
                "aap-gateway-manage feature_flags --list",
                "aap-gateway-manage --version",
            ],
            "automation-controller-web": [
                "awx-manage showmigrations",
                "awx-manage list_instances",
                "awx-manage run_dispatcher --status",
                "awx-manage run_callback_receiver --status",
                "awx-manage check_license --data",
                "awx-manage run_wsrelay --status",
            ],
            "automation-eda-api": [
                "aap-eda-manage --version",
                "aap-eda-manage showmigrations",
            ],
            "receptor": [
                "receptorctl status",
                "receptorclt work list",
            ],
        }
        for pod, cmds in pod_cmds.items():
            if pod in aap_containers:
                for cmd in cmds:
                    fname = self._mangle_command(cmd)
                    self.add_cmd_output(f"su - {username} -c 'podman exec -it"
                                        f"  {pod} bash -c \"{cmd}\"'",
                                        suggest_filename=fname,
                                        subdir=pod)

    # Function to fetch podman container names
    def _get_aap_container_names(self, username):
        try:
            cmd = f"su - {username} -c 'podman ps -a --format {{{{.Names}}}}'"
            cmd_out = self.exec_cmd(cmd)
            if cmd_out['status'] == 0:
                return cmd_out['output'].strip().split("\n")
            return []
        except Exception:
            self._log_error("Error retrieving Podman containers")
            return []

    # Check and enable plugin on a AAP Containerized host
    def check_enabled(self):
        aap_processes = [
                'dumb-init -- /usr/bin/envoy',
                'dumb-init -- /usr/bin/supervisord',
                'dumb-init -- /usr/bin/launch_awx_web.sh',
                'dumb-init -- /usr/bin/launch_awx_task.sh',
                'dumb-init -- aap-eda-manage',
                'pulpcore-content --name pulp-content --bind 127.0.0.1',
            ]

        ps_output = self.exec_cmd("ps --noheaders -eo args")

        if ps_output['status'] == 0:
            for process in aap_processes:
                if process in ps_output['output']:
                    return True
        return False

    def postproc(self):
        # Mask PASSWORD from print_settings command
        jreg = r'((["\']?PASSWORD["\']?\s*[:=]\s*)[rb]?["\'])(.*?)(["\'])'
        self.do_cmd_output_sub(
            "aap-gateway-manage print_settings",
            jreg,
            r'\1**********\4')

        # Mask SECRET_KEY from print_settings command
        jreg = r'((SECRET_KEY\s*=\s*)([rb]?["\']))(.*?)(["\'])'
        self.do_cmd_output_sub(
            "aap-gateway-manage print_settings",
            jreg,
            r'\1**********\5')

# vim: set et ts=4 sw=4 :
