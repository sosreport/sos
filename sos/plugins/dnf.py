# Copyright (C) 2016 Red Hat, Inc., Sachin Patil <sacpatil@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class DNFPlugin(Plugin, RedHatPlugin):
    """dnf package manager"""
    plugin_name = "dnf"
    profiles = ('system', 'packagemanager', 'sysmgmt')

    files = ('/etc/dnf/dnf.conf',)
    packages = ('dnf',)

    option_list = [
        ("history", "captures transaction history", "fast", False),
        ("history-info", "detailed transaction history", "slow", False),
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/dnf/dnf.conf",
            "/etc/dnf/plugins/*",
            "/etc/dnf/protected.d/*",
        ])

        self.limit = self.get_option("log_size")
        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/dnf.*", sizelimit=self.limit)
        else:
            self.add_copy_spec("/var/log/dnf.log", sizelimit=self.limit)
            self.add_copy_spec("/var/log/dnf.librepo.log",
                               sizelimit=self.limit)
            self.add_copy_spec("/var/log/dnf.rpm.log", sizelimit=self.limit)

        self.add_cmd_output("dnf --version",
                            suggest_filename="dnf_version")

        self.add_cmd_output("dnf list installed *dnf*",
                            suggest_filename="dnf_installed_plugins")

        self.add_cmd_output("dnf list extras",
                            suggest_filename="dnf_extra_packages")

        if self.get_option("history"):
            self.add_cmd_output("dnf history")

        if self.get_option("history-info"):
            history = self.call_ext_prog("dnf history")
            transactions = -1
            if history['output']:
                for line in history['output'].splitlines():
                    try:
                        transactions = int(line.split('|')[0].strip())
                        break
                    except ValueError:
                        pass
            for tr_id in range(1, transactions+1):
                self.add_cmd_output("dnf history info %d" % tr_id)

# vim: set et ts=4 sw=4 :
