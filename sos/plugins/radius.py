# Copyright (C) 2007 Navid Sheikhol-Eslami <navid@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Radius(Plugin):
    """RADIUS service information
    """

    plugin_name = "radius"
    profiles = ('network', 'identity')
    packages = ('freeradius',)


class RedHatRadius(Radius, RedHatPlugin):

    files = ('/etc/raddb',)

    def setup(self):
        super(RedHatRadius, self).setup()
        self.add_copy_spec([
            "/etc/raddb",
            "/etc/pam.d/radiusd",
            "/var/log/radius"
        ])

    def postproc(self):
        self.do_file_sub(
            "/etc/raddb/sql.conf", r"(\s*password\s*=\s*)\S+", r"\1***")


class DebianRadius(Radius, DebianPlugin, UbuntuPlugin):

    files = ('/etc/freeradius',)

    def setup(self):
        super(DebianRadius, self).setup()
        self.add_copy_spec([
            "/etc/freeradius",
            "/etc/pam.d/radiusd",
            "/etc/default/freeradius",
            "/var/log/freeradius"
        ])

# vim: set et ts=4 sw=4 :
