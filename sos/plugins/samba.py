# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Samba(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Samba Windows interoperability
    """
    packages = ('samba-common',)
    plugin_name = "samba"
    profiles = ('services',)

    def setup(self):
        self.limit = self.get_option("log_size")

        self.add_copy_spec([
            "/etc/samba/smb.conf",
            "/etc/samba/lmhosts",
        ])

        self.add_copy_spec("/var/log/samba/log.smbd", sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.nmbd", sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.winbindd", sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.winbindd-idmap",
                           sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.winbindd-dc-connet",
                           sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.wb-*", sizelimit=self.limit)

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/samba/", sizelimit=self.limit)

        self.add_cmd_output([
            "wbinfo --domain='.' -g",
            "wbinfo --domain='.' -u",
            "testparm -s",
        ])


class RedHatSamba(Samba, RedHatPlugin):

    def setup(self):
        super(RedHatSamba, self).setup()
        self.add_copy_spec("/etc/sysconfig/samba")

# vim: set et ts=4 sw=4 :
