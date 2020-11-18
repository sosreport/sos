# Copyright (C) 2007 Sadique Puthen <sputhenp@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, RedHatPlugin


class Oddjob(Plugin, RedHatPlugin):

    short_desc = 'OddJob task scheduler'

    plugin_name = 'oddjob'
    profiles = ('services', 'sysmgmt')

    files = ('/etc/oddjobd.conf',)
    packages = ('oddjob',)

    def setup(self):
        self.add_copy_spec([
            "/etc/oddjobd.conf",
            "/etc/oddjobd.conf.d",
            "/etc/dbus-1/system.d/oddjob.conf"
        ])

# vim: set et ts=4 sw=4 :
