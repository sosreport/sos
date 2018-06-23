# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Auditd(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Audit daemon information
    """

    plugin_name = 'auditd'
    profiles = ('system', 'security')

    packages = ('audit',)

    def setup(self):
        self.add_copy_spec([
            "/etc/audit/auditd.conf",
            "/etc/audit/audit.rules"
        ])
        self.add_cmd_output([
            "ausearch --input-logs -m avc,user_avc -ts today",
            "auditctl -s",
            "auditctl -l"
        ])

        if not self.get_option("all_logs"):
            self.add_copy_spec("/var/log/audit/audit.log")
        else:
            self.add_copy_spec("/var/log/audit")

# vim: set et ts=4 sw=4 :
