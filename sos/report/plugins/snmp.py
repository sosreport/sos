# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Snmp(Plugin):

    short_desc = 'Simple network management protocol'
    plugin_name = "snmp"
    profiles = ('system', 'sysmgmt')

    files = ('/etc/snmp/snmpd.conf',)

    def setup(self):
        self.add_copy_spec("/etc/snmp")


class RedHatSnmp(Snmp, RedHatPlugin):

    packages = ('net-snmp',)

    def setup(self):
        super(RedHatSnmp, self).setup()


class DebianSnmp(Snmp, DebianPlugin, UbuntuPlugin):

    packages = ('snmp',)

    def setup(self):
        super(DebianSnmp, self).setup()

# vim: set et ts=4 sw=4 :
