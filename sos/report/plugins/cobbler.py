# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Cobbler(Plugin):
    plugin_name = "cobbler"
    short_desc = 'Cobbler installation server'


class RedHatCobbler(Cobbler, RedHatPlugin):

    packages = ('cobbler',)
    profiles = ('cluster', 'sysmgmt')

    def setup(self):
        self.add_copy_spec([
            "/etc/cobbler",
            "/var/log/cobbler",
            "/var/lib/rhn/kickstarts",
            "/var/lib/cobbler"
        ])


class DebianCobbler(Cobbler, DebianPlugin, UbuntuPlugin):

    packages = ('cobbler',)

    def setup(self):
        self.add_copy_spec([
            "/etc/cobbler",
            "/var/log/cobbler",
            "/var/lib/cobbler"
        ])
        self.add_forbidden_path("/var/lib/cobbler/isos")

# vim: set et ts=4 sw=4 :
