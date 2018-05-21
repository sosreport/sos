# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

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
        self.add_copy_spec("/var/log/samba/log.winbindd-dc-connect",
                           sizelimit=self.limit)
        self.add_copy_spec("/var/log/samba/log.wb-*", sizelimit=self.limit)

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/samba/", sizelimit=self.limit)

        self.add_cmd_output([
            "wbinfo --domain='.' -g",
            "wbinfo --domain='.' -u",
            "wbinfo --trusted-domains --verbose",
            "testparm -s",
        ])


class RedHatSamba(Samba, RedHatPlugin):

    def setup(self):
        super(RedHatSamba, self).setup()
        self.add_copy_spec("/etc/sysconfig/samba")

# vim: set et ts=4 sw=4 :
