# Copyright (C) 2016 Jorge Niedbalski <niedbalski@ubuntu.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, UbuntuPlugin


class LXD(Plugin, UbuntuPlugin):
    """LXD is a containers hypervisor.
    """
    plugin_name = 'lxd'
    profiles = ('container',)
    packages = ('lxd',)

    def setup(self):
        self.add_copy_spec([
            "/var/lib/lxd/lxd.db",
            "/etc/default/lxc-bridge",
        ])

        self.add_copy_spec("/var/log/lxd*")

        # List of containers available on the machine
        self.add_cmd_output([
            "lxc list",
            "lxc profile list",
            "lxc image list",
        ])

        self.add_cmd_output([
            "find /var/lib/lxd -maxdepth 2 -type d -ls",
        ], suggest_filename='var-lxd-dirs.txt')

# vim: set et ts=4 sw=4 :
