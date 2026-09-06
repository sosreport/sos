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
        ),
        PluginOpt(
            "log_lines",
            default=1000,
            val_type=int,
            desc="Number of lines to collect from each AAP "
            "container. Ignored when '--all-logs' is used."
        )
    ]

    def setup(self):
        # Determine which non-root user owns the AAP rootless containers
        username = self._get_username()
        if not username:
            return

        self.aap_directory_name = self._get_aap_directory(username)

        # Don't collect cert and key files from the installation directory
        if self.path_exists(self.aap_directory_name):
            forbidden_paths = [
                self.path_join(self.aap_directory_name, path)
                for path in [
                    "containers",
                    "tls",
                    "controller/etc/*.cert",
                    "controller/etc/*.key",
                    "controller/data",
                    "eda/etc/*.cert",
                    "eda/etc/*.key",
                    "gateway/etc/*.cert",
                    "gateway/etc/*.key",
                    "gatewayproxy/etc/*.cert",
                    "gatewayproxy/etc/*.key",
                    "hub/etc/*.cert",
                    "hub/etc/*.key",
                    "hub/etc/keys/*.pem",
                    "hub/etc/keys/*.key",
                    "lightspeed/etc/*.cert",
                    "lightspeed/etc/*.key",
                    "ansiblemcp/etc/*.cert",
                    "ansiblemcp/etc/*.key",
                    "pcp/etc/*.cert",
                    "pcp/etc/*.key",
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
            self.add_copy_spec(self.aap_directory_name)
        else:
            self._log_error(f"Directory {self.aap_directory_name} does not "
                            "exist or invalid absolute path provided.")

        self._runtime = self._get_container_runtime(runtime="podman")
        if self._runtime is not None:
            self.add_cmd_output(self._runtime.get_info_command(run_debug=True),
                                runas=username,
                                subdir="podman_cmd_outputs",
                                suggest_filename="podman_info")
            self.add_cmd_output(self._runtime.get_list_command(get_all=True),
                                runas=username,
                                subdir="podman_cmd_outputs",
                                suggest_filename="podman_ps")
            self.add_cmd_output(self._runtime.get_secrets_command(),
                                runas=username,
                                subdir="podman_cmd_outputs",
                                suggest_filename="podman_secrets")
            self.add_cmd_output(self._runtime.get_stats_command(),
                                runas=username,
                                subdir="podman_cmd_outputs",
                                suggest_filename="podman_stats")
            self.add_cmd_output(self._runtime.get_system_df_command(),
                                runas=username,
                                subdir="podman_cmd_outputs",
                                suggest_filename="podman_system_df")
            self.add_cmd_output(
                self._runtime.get_images_command(include_digests=True),
                runas=username,
                subdir="podman_cmd_outputs",
                suggest_filename="podman_images")

            # network and volumes: run each listing once, then inspect all
            # entities of a type in a single invocation instead of one call
            # per entity
            for ls_cmd, ins_cmd, fname, name_idx in (
                    (self._runtime.get_networks_command(),
                     self._runtime.get_networks_inspect,
                     "podman_networks", 0),
                    (self._runtime.get_volumes_command(),
                     self._runtime.get_volumes_inspect,
                     "podman_volumes", -1)):
                listing = self.exec_cmd(ls_cmd, runas=username, stderr=False)
                if listing['status'] != 0:
                    continue
                self.add_cmd_output(
                    ls_cmd,
                    runas=username,
                    subdir="podman_cmd_outputs",
                    suggest_filename=fname)
                entities = [
                    ln.split()[name_idx]
                    for ln in listing['output'].splitlines()[1:]
                    if ln.strip()
                ]
                if entities:
                    self.add_cmd_output(
                        ins_cmd(*entities),
                        runas=username,
                        subdir="podman_cmd_outputs",
                        suggest_filename=f"{fname}_inspect.json")

        # Collect lingering status of the rootless podman user
        self.add_cmd_output(f"loginctl show-user {username}")

        # Collect containers.conf to investigate custom changes
        container_config = os.path.expanduser(
            f"~{username}/.config/containers/containers.conf"
        )
        if self.path_exists(container_config):
            self.add_copy_spec(container_config)

        # Collect AAP container names from the user's rootless runtime
        aap_containers = self._get_aap_container_names(username)
        aap_containers_set = set(aap_containers)

        for container in aap_containers:
            self.add_podman_logs(container, username)

        # Inspect all AAP containers in a single invocation
        if aap_containers:
            self.add_podman_inspect(aap_containers, username)

        # command outputs from various containers
        pod_cmds = {
            "automation-controller-task": [
                "awx-manage check_license --data",
                "awx-manage list_instances",
            ],
            "automation-gateway": [
                "aap-gateway-manage print_settings",
                "aap-gateway-manage authenticators",
                "aap-gateway-manage showmigrations",
                "aap-gateway-manage list_services",
                "aap-gateway-manage feature_flags --list",
                "aap-gateway-manage --version",
            ],
            "automation-gateway-proxy": [
                "envoy --version",
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
            "automation-hub-api": [
                "pulpcore-manager --version",
                "pulpcore-manager showmigrations",
            ],
            "postgresql": [
                "psql --version",
                "pg_isready",
            ],
            "receptor": [
                "receptor --version",
            ],
        }
        for pod in aap_containers_set.intersection(pod_cmds):
            for cmd in pod_cmds[pod]:
                self.add_podman_exec(pod, cmd, username)

    # Function to fetch podman container names from user's rootless
    # container runtime.
    def _get_aap_container_names(self, username):
        return [
            con[1]
            for con in self.get_containers_by_user(username, get_all=True)
        ]

    # Collect podman logs of a single container owned by rootless user.
    # By default, last 1000 lines of logs are collected from each container.
    # To collect more than 1000 lines of logs, specify with
    # -k aap_containerized.log_lines=<number> option.
    # All logs are collected, if the user specifies the --all-logs option.
    def add_podman_logs(self, container, username):
        if self._runtime is None:
            return
        if self.get_option("all_logs"):
            log_lines = None
        else:
            log_lines = self.get_option("log_lines")
        # Names already come from get_containers_by_user; so
        # we don't need to re-run `podman ps` per container
        self.add_cmd_output(
            self._runtime.get_logs_command(container, log_lines=log_lines),
            runas=username,
            suggest_filename=f"{container}.log",
            subdir="aap_container_logs"
        )

    # Collect podman inspect of a all containers owned
    # by rootless user as a single JSON file.
    def add_podman_inspect(self, containers, username):
        if self._runtime is None:
            return
        self.add_cmd_output(
            self._runtime.get_inspect_command(*containers),
            runas=username,
            suggest_filename="podman_inspect_all.json",
            subdir="podman_cmd_outputs"
        )

    # Run a command inside a podman container owned by rootless user and
    # store the output under the container's subdirectory.
    def add_podman_exec(self, container, cmd, username):
        if self._runtime is None:
            return
        self.add_cmd_output(
            self._runtime.get_exec_command(container, cmd),
            runas=username,
            suggest_filename=self._mangle_command(cmd),
            subdir=f"aap_container_outputs/{container}"
        )

    # Determine the non-root user that owns the AAP rootless containers
    # Prefers the `username` plugin option, falling back to scanning the
    # process list for single user running a rootless podman instance.
    def _get_username(self):
        username = self.get_option("username")
        if username:
            return username

        self._log_warn("AAP username is missing, use '-k "
                       "aap_containerized.username=<username>' to specify it.")
        ps = self.exec_cmd("ps -eo user,args")
        if ps['status'] == 0:
            podman_users = set()
            for line in ps["output"].splitlines():
                if ("/usr/bin/podman" in line) and \
                   ("/.local/share/containers/storage/" in line):
                    user, _ = line.split(maxsplit=1)
                    podman_users.add(user)
            if len(podman_users) == 1:
                username = podman_users.pop()
                self._log_warn(f"Auto-detected AAP username: {username}. If "
                               "incorrect, use "
                               "'-k aap_containerized.username=<user>' "
                               "to specify it.")
                return username
            if len(podman_users) > 1:
                self._log_error("Multiple users running rootless podman "
                                "detected. Use '-k "
                                "aap_containerized.username=<user>' "
                                "to specify it.")
                return None
        self._log_error("Unable to determine AAP username, terminating "
                        "plugin.")
        return None

    # Resolve the absolute path of AAP containers volume directory.
    def _get_aap_directory(self, username):
        aap_directory_name = self.get_option("directory")
        if not aap_directory_name:
            user_home_directory = os.path.expanduser(f"~{username}")
            aap_directory_name = self.path_join(user_home_directory, "aap")
            self._log_warn("Auto-detected AAP directory: "
                           f"'{aap_directory_name}'. If incorrect, "
                           "use '-k aap_containerized.directory=<path>' to "
                           "specify it.")
        return aap_directory_name

    # Check and enable plugin on a AAP Containerized host
    def check_enabled(self):
        aap_processes = [
            'dumb-init -- /usr/bin/envoy',
            'dumb-init -- /usr/bin/supervisord',
            'dumb-init -- /usr/bin/launch_awx_web.sh',
            'dumb-init -- /usr/bin/launch_awx_task.sh',
            'dumb-init -- aap-eda-manage',
            'pulpcore-content --name pulp-content --bind 127.0.0.1',
            'gunicorn pulpcore.app.wsgi',
            'receptor --config',
            'metrics-service run',
        ]

        ps_output = self.exec_cmd("ps --noheaders -eo args")

        if ps_output['status'] == 0:
            for process in aap_processes:
                if process in ps_output['output']:
                    return True
        return False

    def postproc(self):
        # Nothing will be collected when setup() could not resolve AAP
        # directory (e.g. missing/invalid username or directory option), so
        # there is nothing to obfuscate -- skip to avoid attribute errors.
        if not getattr(self, 'aap_directory_name', None):
            return

        # remove controller email password
        file_path = f"{self.aap_directory_name}/controller/etc/settings.py"
        jreg = r"(EMAIL_HOST_PASSWORD\s*=\s*)\'(.+)\'"
        repl = r"\1********"
        self.do_path_regex_sub(file_path, jreg, repl)

        # remove controller database password (triple-quoted)
        file_path = (f"{self.aap_directory_name}"
                     "/controller/etc/conf.d/postgres.py")
        jreg = r"(\s*'PASSWORD'\s*:\s*)(\"\"\".*?\"\"\")"
        repl = r"\1********"
        self.do_path_regex_sub(file_path, jreg, repl)

        # remove gateway database password
        file_path = f"{self.aap_directory_name}/gateway/etc/settings.py"
        jreg = r"(\s*'PASSWORD'\s*:\s*)('.*')"
        repl = r"\1********"
        self.do_path_regex_sub(file_path, jreg, repl)

        # remove hub database password
        file_path = f"{self.aap_directory_name}/hub/etc/settings.py"
        jreg = r"(\s*'PASSWORD'\s*:\s*)('.*')"
        repl = r"\1********"
        self.do_path_regex_sub(file_path, jreg, repl)

        # remove hub Azure storage key
        jreg = r"(AZURE_ACCOUNT_KEY\s*=\s*)'(.+)'"
        repl = r"\1'********'"
        self.do_path_regex_sub(file_path, jreg, repl)

        # remove hub S3 secret key
        jreg = r"(AWS_SECRET_ACCESS_KEY\s*=\s*)'(.+)'"
        repl = r"\1'********'"
        self.do_path_regex_sub(file_path, jreg, repl)

        # Mask EDA optional secrets
        file_path = f"{self.aap_directory_name}/eda/etc/settings.yaml"
        regex = r"(\s*)(PASSWORD|MQ_USER_PASSWORD|SECRET_KEY)(:\s*)(.*$)"
        repl = r'\1\2\3********'
        self.do_path_regex_sub(file_path, regex, repl)

        # Mask redis ACL password hashes
        file_path = f"{self.aap_directory_name}/redis/redis-users.acl"
        regex = r"(user\s+\S+\s+on\s+)#\S+"
        repl = r'\1#********'
        self.do_path_regex_sub(file_path, regex, repl)

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
