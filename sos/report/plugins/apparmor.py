# Copyright (c) 2012 Adam Stokes <adam.stokes@canonical.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, UbuntuPlugin


class Apparmor(Plugin, UbuntuPlugin):

    short_desc = 'Apparmor mandatory access control'

    plugin_name = 'apparmor'
    profiles = ('security',)

    def setup(self):
        self.add_copy_spec([
            "/etc/apparmor*"
        ])

        self.add_forbidden_path([
            "/etc/apparmor.d/cache",
            "/etc/apparmor.d/libvirt/libvirt*",
            "/etc/apparmor.d/abstractions"
        ])

        self.add_cmd_output([
            "apparmor_status",
            "ls -alh /etc/apparmor.d/abstractions",
            "ls -alh /etc/apparmor.d/libvirt",
        ])

# vim: set et ts=4 sw=4 :
