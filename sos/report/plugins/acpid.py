# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Acpid(Plugin):

    short_desc = 'ACPI daemon information'
    plugin_name = "acpid"
    profiles = ('hardware',)
    packages = ('acpid',)


class RedHatAcpid(Acpid, RedHatPlugin):
    def setup(self):
        self.add_copy_spec([
            "/var/log/acpid*",
            "/etc/acpi/events/power.conf"])


class DebianAcpid(Acpid, DebianPlugin, UbuntuPlugin):
    def setup(self):
        self.add_copy_spec([
            "/etc/acpi/events/powerbtn*"])

# vim: set et ts=4 sw=4 :
