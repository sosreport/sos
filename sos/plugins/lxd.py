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
    commands = ('lxd',)

    # Version 2.0.X:
    # - /etc/default/lxd-bridge
    # - /var/lib/lxd/lxd.db
    #
    # Version 3.0.X:
    # - /var/lib/lxd/database/local.db
    # - /var/lib/lxd/database/global/*
    # - lxd-bridge no longer exist.
    #
    def setup(self):
        self.add_copy_spec([
            "/etc/default/lxd-bridge",
            "/var/lib/lxd/lxd.db",
            "/var/lib/lxd/database/local.db",
            "/var/lib/lxd/database/global/*",
            "/var/log/lxd/*"
        ])

        self.add_cmd_output([
            "lxc image list",
            "lxc list",
            "lxc network list",
            "lxc profile list",
            "lxc storage list"
        ])

        self.add_cmd_output([
            "find /var/lib/lxd -maxdepth 2 -type d -ls",
        ], suggest_filename='var-lxd-dirs.txt')

# vim: set et ts=4 sw=4 :
