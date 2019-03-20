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

        self.add_copy_spec([
            "/etc/samba/smb.conf",
            "/etc/samba/lmhosts",
        ])

        self.add_copy_spec("/var/log/samba/log.smbd")
        self.add_copy_spec("/var/log/samba/log.nmbd")
        self.add_copy_spec("/var/log/samba/log.winbindd")
        self.add_copy_spec("/var/log/samba/log.winbindd-idmap")
        self.add_copy_spec("/var/log/samba/log.winbindd-dc-connect")
        self.add_copy_spec("/var/log/samba/log.wb-*")

        if self.get_option("all_logs"):
            self.add_copy_spec("/var/log/samba/")

        self.add_cmd_output([
            "testparm -s",
            "wbinfo --domain='.' --domain-users",
            "wbinfo --domain='.' --domain-groups",
            "wbinfo --trusted-domains --verbose",
            "net primarytrust dumpinfo",
        ])


class RedHatSamba(Samba, RedHatPlugin):

    def setup(self):
        super(RedHatSamba, self).setup()
        self.add_copy_spec("/etc/sysconfig/samba")

# vim: set et ts=4 sw=4 :
