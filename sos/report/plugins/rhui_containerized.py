# Copyright (C) 2025 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import fnmatch
from sos.report.plugins import Plugin, RedHatPlugin


class RhuiContainer(Plugin, RedHatPlugin):

    short_desc = 'Red Hat Update Infrastructure in Containers'

    plugin_name = "rhui_containerized"
    services = ("rhui_rhua", )
    files = ("/var/lib/rhui/config/rhua/rhui-tools.conf", )

    def setup(self):
        self.add_copy_spec([
            "/var/lib/rhui/config/rhua/rhui-tools.conf",
            "/var/lib/rhui/config/rhua/registered_subscriptions.conf",
            "/var/lib/rhui/pki/*",
            "/var/lib/rhui/cache/*",
            "/var/lib/rhui/root/.rhui/*",
            "/var/lib/rhui/log/*",
        ])
        # skip collecting certificate keys
        self.add_forbidden_path("/var/lib/rhui/pki/**/*.key")

        # call rhui-manager commands with 1m timeout and
        # with an env. variable ensuring that "RHUI Username:"
        # even unanswered prompt gets collected
        # TODO: is the timeout and env applicable?
        rhui_cont_exe = "podman exec rhui5-rhua rhui-manager --noninteractive"
        for subcmd in ["status", "cert info"]:
            suggest_fname = f"rhui-manager_{subcmd.replace(' ', '_')}"
            self.add_cmd_output(f"{rhui_cont_exe} {subcmd}",
                                runas="rhui",
                                runat="/var/lib/rhui",
                                suggest_filename=suggest_fname)

        self.add_dir_listing('/var/lib/rhui/remote_share', recursive=True)

        # collect postgres diagnostics data
        # ideally, postgresql plugin would do so but that would need bigger
        # changes to the plugin redundantly affecting its execution on
        # non-RHUI systems
        pghome = '/var/lib/pgsql'
        self.add_cmd_output(f"du -sh {pghome}", container='rhui5-rhua',
                            runas='rhui')
        # Copy PostgreSQL log and config files.
        # we must first find all their names, since `stat` inside add_copy_spec
        # does not treat globs at all
        podman_find = self.exec_cmd("podman exec rhui5-rhua find "
                                    f"{pghome}/data", runas="rhui")
        if podman_find['status'] == 0:
            allfiles = podman_find['output'].splitlines()
            logfiles = fnmatch.filter(allfiles, '*.log')
            configs = fnmatch.filter(allfiles, '*.conf')
            self.add_copy_spec(logfiles, container='rhui5-rhua', runas='rhui')
            self.add_copy_spec(configs, container='rhui5-rhua', runas='rhui')
        # copy PG_VERSION and postmaster.opts
        for file in ["PG_VERSION", "postmaster.opts"]:
            self.add_copy_spec(f"{pghome}/data/{file}",
                               container='rhui5-rhua', runas='rhui')

    def postproc(self):
        # hide registry_password value in rhui-tools.conf
        self.do_path_regex_sub("/var/lib/rhui/config/rhua/rhui-tools.conf",
                               r"(.+_pass(word|):)\s*(.+)",
                               r"\1 ********")
        # obfuscate two cookies for login session
        for cookie in ["csrftoken", "sessionid"]:
            self.do_path_regex_sub(
                r"/var/lib/rhui/root/\.rhui/.*/cookies.txt",
                fr"({cookie}\s+)(\S+)",
                r"\1********")


# vim: set et ts=4 sw=4 :
