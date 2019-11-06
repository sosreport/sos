# Copyright (C) 2019 Alexander Petrovskiy <alexpe@mellanox.com>
#
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin


class Bird(Plugin, RedHatPlugin, UbuntuPlugin, DebianPlugin):
    """Bird routing daemon
    """

    plugin_name = 'bird'
    profiles = ('network',)
    packages = ('bird',)

    def setup(self):
        self.add_copy_spec([
            "/etc/bird/*",
            "/etc/bird.conf"
        ])
        self.add_cmd_output([
            "birdc show status",
            "birdc show memory",
            "birdc show protocols all",
            "birdc show interfaces",
            "birdc show route all",
            "birdc show symbols",
            "birdc show bfd sessions",
            "birdc show babel interfaces",
            "birdc show babel neighbors",
            "birdc show babel entries",
            "birdc show babel routes",
            "birdc show ospf",
            "birdc show ospf neighbors",
            "birdc show ospf interface",
            "birdc show ospf topology",
            "birdc show ospf state all",
            "birdc show ospf lsadb",
            "birdc show rip interfaces",
            "birdc show rip neighbors",
            "birdc show static"
        ])

# vim: set et ts=4 sw=4 :
