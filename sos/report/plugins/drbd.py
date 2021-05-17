# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, UbuntuPlugin


class drbd(Plugin, RedHatPlugin, UbuntuPlugin):

    short_desc = 'Distributed Replicated Block Device (DRBD)'

    plugin_name = 'drbd'
    profiles = ('storage',)
    packages = ('drbd*-utils',)

    def setup(self):
        self.add_cmd_output([
            "drbd-overview",
            "drbdadm dump-xml",
            "drbdsetup status all",
            "drbdsetup show all"
        ])
        self.add_copy_spec([
            "/etc/drbd.conf",
            "/etc/drbd.d/*",
            "/proc/drbd"
        ])

# vim: set et ts=4 sw=4 :
