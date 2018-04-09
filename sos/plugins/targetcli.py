# Copyright (C) 2015 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class TargetCli(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """TargetCLI TCM/LIO configuration
    """
    packages = ('targetcli', 'python-rtslib')
    profiles = ('storage', )
    plugin_name = 'targetcli'

    def setup(self):
        self.add_cmd_output([
            "targetcli ls",
            "targetcli status",
            "systemctl status target.service"
        ])
        self.add_journal(units="targetcli")
        self.add_copy_spec("/sys/kernel/config/target")
        self.add_copy_spec("/etc/target")

# vim: set et ts=4 sw=4 :
