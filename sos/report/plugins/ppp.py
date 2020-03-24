# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Ppp(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Point-to-point protocol
    """

    plugin_name = 'ppp'
    profiles = ('system', 'network')

    packages = ('ppp',)

    def setup(self):
        self.add_copy_spec([
            "/etc/wvdial.conf",
            "/etc/ppp",
            "/var/log/ppp"
        ])
        self.add_cmd_output("adsl-status")

# vim: set et ts=4 sw=4 :
