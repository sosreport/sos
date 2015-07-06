# Copyright (C) 2007 Red Hat, Inc., Pierre Carrier <pcarrier@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Sssd(Plugin):
    """System security service daemon
    """

    plugin_name = "sssd"
    profiles = ('services', 'security', 'identity')
    packages = ('sssd',)

    def setup(self):
        self.add_copy_spec([
            "/etc/sssd/sssd.conf",
            "/var/log/sssd/*"
        ])

    def postproc(self):
        self.do_file_sub("/etc/sssd/sssd.conf",
                         r"(\s*ldap_default_authtok\s*=\s*)\S+",
                         r"\1********")


class RedHatSssd(Sssd, RedHatPlugin):

    def setup(self):
        super(RedHatSssd, self).setup()


class DebianSssd(Sssd, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianSssd, self).setup()
        self.add_copy_spec("/etc/default/sssd")

# vim: set et ts=4 sw=4 :
