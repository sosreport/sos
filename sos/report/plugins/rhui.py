# Copyright (C) 2021 Red Hat, Inc., Pavel Moravec <pmoravec@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Rhui(Plugin, RedHatPlugin):

    short_desc = 'Red Hat Update Infrastructure'

    plugin_name = "rhui"
    commands = ("rhui-manager", )
    files = ("/etc/rhui/rhui-tools.conf", )

    def setup(self):
        self.add_copy_spec([
            "/etc/rhui/rhui-tools.conf",
            "/etc/rhui/registered_subscriptions.conf",
            "/etc/pki/rhui/*",
            "/var/log/rhui-subscription-sync.log",
            "/var/cache/rhui/*",
            "/root/.rhui/*",
            "/var/log/rhui/*",
        ])
        # skip collecting certificate keys
        self.add_forbidden_path("/etc/pki/rhui/**/*.key")

        # call rhui-manager commands with 1m timeout and
        # with an env. variable ensuring that "RHUI Username:"
        # even unanswered prompt gets collected
        self.add_cmd_output([
            "rhui-manager status",
            "rhui-manager cert info",
            "ls -lR /var/lib/rhui/remote_share",
        ], timeout=60, env={'PYTHONUNBUFFERED': '1'})

    def postproc(self):
        # hide rhui_manager_password value in (also rotated) answers file
        self.do_path_regex_sub(
                r"/root/\.rhui/answers.yaml.*",
                r"(\s*rhui_manager_password\s*:)\s*(\S+)",
                r"\1********")
        # obfuscate twoo cookies for login session
        for cookie in ["csrftoken", "sessionid"]:
            self.do_path_regex_sub(
                r"/root/\.rhui/.*/cookies.txt",
                r"(%s\s+)(\S+)" % cookie,
                r"\1********")


# vim: set et ts=4 sw=4 :
